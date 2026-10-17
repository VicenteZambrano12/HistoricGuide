import base64
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, call, create_autospec, patch
import wave

from pydantic import ValidationError

from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline
from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.systems.Pipeline import Pipeline
from src.systems.STT.STT import STT
from src.systems.TTS.TTS import TTS
from src.utils.general.GeminiApiCall import GeminiClient


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agents = create_autospec(AgentPipeline, instance=True)
        self.stt = create_autospec(STT, instance=True)
        self.tts = create_autospec(TTS, instance=True)
        self.agents.run.return_value = "An answer from the agents."
        self.stt.transcribe.return_value = "Tell me about the Pantheon."
        self.tts.synthesize.return_value = b"wav-answer"
        self.pipeline = Pipeline(
            agent_pipeline=self.agents, stt=self.stt, tts=self.tts
        )

    def test_all_modes_always_include_agents_in_order(self) -> None:
        for mode in ("STT", "TTS", "full", "only text"):
            with self.subTest(mode=mode):
                self.agents.reset_mock()
                self.stt.reset_mock()
                self.tts.reset_mock()
                order = Mock()
                order.attach_mock(self.stt, "stt")
                order.attach_mock(self.agents, "agents")
                order.attach_mock(self.tts, "tts")
                audio_input = mode in ("STT", "full")
                audio_output = mode in ("TTS", "full")
                kwargs = {"mime_type": "audio/webm"} if audio_input else {}
                result = self.pipeline.run(
                    b"recording" if audio_input else "Tell me about the Pantheon.",
                    mode,
                    stop="Pantheon",
                    voice="Puck",
                    context=["Retrieved fact."],
                    **kwargs,
                )
                expected = []
                if audio_input:
                    expected.append(call.stt.transcribe(b"recording", mime_type="audio/webm"))
                expected.append(call.agents.run(
                    "Pantheon",
                    user_query="Tell me about the Pantheon.",
                    context=["Retrieved fact."],
                    language="en",
                ))
                if audio_output:
                    expected.append(call.tts.synthesize("An answer from the agents.", voice="Puck"))
                self.assertEqual(order.mock_calls, expected)
                self.assertEqual(
                    result, b"wav-answer" if audio_output else "An answer from the agents."
                )

    def test_audio_file_path_is_passed_to_stt(self) -> None:
        path = Path("recording.wav")
        self.pipeline.run(path, "STT", stop="Pantheon")
        self.stt.transcribe.assert_called_once_with(path, mime_type=None)
        self.agents.run.assert_called_once()

    def test_invalid_requests_do_not_invoke_any_stage(self) -> None:
        cases = [
            {"data": "question", "mode": "unknown", "stop": "Pantheon"},
            {"data": "question", "mode": "only text", "stop": " "},
            {"data": " ", "mode": "only text", "stop": "Pantheon"},
            {"data": b"audio", "mode": "TTS", "stop": "Pantheon"},
            {"data": Path("audio.wav"), "mode": "only text", "stop": "Pantheon"},
            {"data": b"", "mode": "STT", "stop": "Pantheon", "mime_type": "audio/wav"},
            {"data": b"audio", "mode": "full", "stop": "Pantheon"},
            {"data": b"audio", "mode": "STT", "stop": "Pantheon", "mime_type": "text/plain"},
            {"data": "question", "mode": "TTS", "stop": "Pantheon", "voice": ""},
            {"data": "question", "mode": "only text", "stop": "Pantheon", "context": [""]},
            {"data": "question", "mode": "only text", "stop": "Pantheon", "mime_type": "audio/wav"},
            {"data": "question", "mode": "only text", "stop": "Pantheon", "language": "fr"},
            {"data": b"audio", "mode": "full", "stop": "Pantheon", "mime_type": "audio/wav", "language": None},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    self.pipeline.run(**kwargs)
        self.stt.transcribe.assert_not_called()
        self.agents.run.assert_not_called()
        self.tts.synthesize.assert_not_called()

    def test_spanish_is_forwarded_in_every_mode_and_answer_is_synthesized(self) -> None:
        for mode in ("STT", "TTS", "full", "only text"):
            with self.subTest(mode=mode):
                self.agents.reset_mock()
                self.tts.reset_mock()
                self.agents.run.return_value = "Una respuesta en castellano."
                audio_input = mode in ("STT", "full")
                kwargs = {"mime_type": "audio/wav"} if audio_input else {}
                result = self.pipeline.run(
                    b"audio" if audio_input else "Explain this place.",
                    mode, stop="Pantheon", language="es", **kwargs,
                )
                self.assertEqual(self.agents.run.call_args.kwargs["language"], "es")
                if mode in ("TTS", "full"):
                    self.tts.synthesize.assert_called_once_with(
                        "Una respuesta en castellano.", voice="Kore"
                    )
                    self.assertEqual(result, b"wav-answer")
                else:
                    self.tts.synthesize.assert_not_called()
                    self.assertEqual(result, "Una respuesta en castellano.")

    def test_stt_error_stops_before_agents_and_tts(self) -> None:
        self.stt.transcribe.side_effect = RuntimeError("Transcription failed")
        with self.assertRaisesRegex(RuntimeError, "Transcription failed"):
            self.pipeline.run(b"audio", "full", stop="Pantheon", mime_type="audio/wav")
        self.agents.run.assert_not_called()
        self.tts.synthesize.assert_not_called()

    def test_agent_error_stops_before_tts(self) -> None:
        self.agents.run.side_effect = RuntimeError("Generation failed")
        with self.assertRaisesRegex(RuntimeError, "Generation failed"):
            self.pipeline.run("question", "TTS", stop="Pantheon")
        self.tts.synthesize.assert_not_called()

    def test_tts_error_propagates(self) -> None:
        self.tts.synthesize.side_effect = RuntimeError("Synthesis failed")
        with self.assertRaisesRegex(RuntimeError, "Synthesis failed"):
            self.pipeline.run("question", "TTS", stop="Pantheon")
        self.agents.run.assert_called_once()

    @patch("src.utils.Pipeline.run.STT")
    @patch("src.utils.Pipeline.run.TTS")
    def test_speech_components_are_lazy_and_reused(self, tts_class, stt_class) -> None:
        pipeline = Pipeline(agent_pipeline=self.agents)
        stt_class.return_value = self.stt
        tts_class.return_value = self.tts
        pipeline.run("question", "only text", stop="Pantheon")
        stt_class.assert_not_called()
        tts_class.assert_not_called()
        for _ in range(2):
            pipeline.run(b"audio", "full", stop="Pantheon", mime_type="audio/wav")
        stt_class.assert_called_once_with()
        tts_class.assert_called_once_with()

    def test_default_agent_pipelines_are_independent(self) -> None:
        first = Pipeline()
        second = Pipeline()
        self.assertIsNot(first.agent_pipeline, second.agent_pipeline)
        self.assertIsNone(first.stt)
        self.assertIsNone(first.tts)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_all_modes_with_real_components_and_mocked_gemini(self, urlopen) -> None:
        pcm = b"\x00\x00\x01\x00"
        for mode in ("STT", "TTS", "full", "only text"):
            with self.subTest(mode=mode):
                pipeline = Pipeline(
                    agent_pipeline=AgentPipeline(
                        orchestrator=Orchestrator(client=GeminiClient(api_key="test-key")),
                        response_generator=ResponseGenerator(client=GeminiClient(api_key="test-key")),
                    ),
                    stt=STT(client=GeminiClient(api_key="test-key")),
                    tts=TTS(client=GeminiClient(api_key="test-key")),
                )
                texts = (
                    ["Tell me about the Pantheon.", "historic", "El Panteon tiene una cupula."]
                    if mode in ("STT", "full")
                    else ["historic", "El Panteon tiene una cupula."]
                )
                responses = [
                    {"candidates": [{
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": text}]},
                    }]}
                    for text in texts
                ]
                if mode in ("TTS", "full"):
                    responses.append({"candidates": [{
                        "finishReason": "STOP",
                        "content": {"parts": [{"inlineData": {
                            "mimeType": "audio/L16;codec=pcm;rate=24000",
                            "data": base64.b64encode(pcm).decode("ascii"),
                        }}]},
                    }]})
                urlopen.reset_mock()
                urlopen.side_effect = [
                    BytesIO(json.dumps(response).encode()) for response in responses
                ]
                audio_input = mode in ("STT", "full")
                kwargs = {"mime_type": "audio/wav"} if audio_input else {}
                result = pipeline.run(
                    b"recording" if audio_input else "Tell me about the Pantheon.",
                    mode,
                    stop="Pantheon",
                    language="es",
                    **kwargs,
                )
                self.assertEqual(urlopen.call_count, len(responses))
                generation_call = urlopen.call_args_list[2 if audio_input else 1]
                generation = json.loads(generation_call.args[0].data)
                generation_input = json.loads(generation["contents"][0]["parts"][0]["text"])
                self.assertEqual(generation_input["language"], "es")
                if mode in ("TTS", "full"):
                    speech = json.loads(urlopen.call_args.args[0].data)
                    self.assertEqual(
                        speech["contents"][0]["parts"][0]["text"],
                        "El Panteon tiene una cupula.",
                    )
                    with wave.open(BytesIO(result), "rb") as wav:
                        self.assertEqual(wav.readframes(wav.getnframes()), pcm)
                else:
                    self.assertEqual(result, "El Panteon tiene una cupula.")


if __name__ == "__main__":
    unittest.main()
