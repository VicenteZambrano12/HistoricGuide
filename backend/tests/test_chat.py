import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.Endpoint.chat import MAX_AUDIO_BYTES
from src.app import app


class ChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        pipeline_patch = patch("src.api.Endpoint.chat.Pipeline")
        self.pipeline_class = pipeline_patch.start()
        self.addCleanup(pipeline_patch.stop)
        self.pipeline = self.pipeline_class.return_value

    def test_all_modes_and_languages(self) -> None:
        modes = {"stt": "STT", "tts": "TTS", "full": "full", "text": "only text"}
        for mode, pipeline_mode in modes.items():
            for language in ("ES", "EN"):
                with self.subTest(mode=mode, language=language):
                    audio_input = mode in ("stt", "full")
                    audio_output = mode in ("tts", "full")
                    result = b"wav-answer" if audio_output else "An answer."
                    self.pipeline.run.return_value = result
                    data = {"mode": mode, "language": language, "stop": "Pantheon"}
                    files = {
                        "query": ("query.webm", b"recording", "audio/webm")
                        if audio_input else (None, "Tell me about the Pantheon.")
                    }
                    response = self.client.post("/chat", data=data, files=files)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.pipeline.run.assert_called_with(
                        b"recording" if audio_input else "Tell me about the Pantheon.",
                        pipeline_mode,
                        stop="Pantheon",
                        mime_type="audio/webm" if audio_input else None,
                        language=language.lower(),
                    )
                    if audio_output:
                        self.assertEqual(response.headers["content-type"], "audio/wav")
                        self.assertEqual(response.content, result)
                    else:
                        self.assertEqual(response.json(), {"text": result})

    def test_invalid_fields_are_rejected_before_pipeline(self) -> None:
        valid = {"query": "Question", "mode": "text", "language": "EN", "stop": "Pantheon"}
        cases = [
            {**valid, "mode": "unknown"},
            {**valid, "language": "FR"},
            {**valid, "stop": " "},
            {**valid, "query": " "},
            {**valid, "mode": "stt"},
            {**valid, "mode": "full"},
        ]
        cases.extend({key: value for key, value in valid.items() if key != missing}
                     for missing in valid)
        for data in cases:
            with self.subTest(data=data):
                response = self.client.post("/chat", data=data)
                self.assertEqual(response.status_code, 422, response.text)
        self.pipeline_class.assert_not_called()

    def test_invalid_audio_is_rejected_before_pipeline(self) -> None:
        for mode, audio, mime_type in (
            ("stt", b"", "audio/wav"),
            ("full", b"audio", "text/plain"),
            ("text", b"audio", "audio/wav"),
            ("tts", b"audio", "audio/wav"),
        ):
            with self.subTest(mode=mode, audio=audio):
                response = self.client.post(
                    "/chat",
                    data={"mode": mode, "language": "EN", "stop": "Pantheon"},
                    files={"query": ("query.wav", audio, mime_type)},
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.pipeline_class.assert_not_called()

    def test_audio_size_limit(self) -> None:
        self.pipeline.run.return_value = "Answer"
        for size, expected_status in (
            (MAX_AUDIO_BYTES, 200),
            (MAX_AUDIO_BYTES + 1, 413),
        ):
            with self.subTest(size=size):
                self.pipeline_class.reset_mock()
                response = self.client.post(
                    "/chat",
                    data={"mode": "stt", "language": "EN", "stop": "Pantheon"},
                    files={"query": ("query.wav", b"x" * size, "audio/wav")},
                )
                self.assertEqual(response.status_code, expected_status, response.text)
                if expected_status == 413:
                    self.pipeline_class.assert_not_called()

    def test_pipeline_failure_is_not_a_success_response(self) -> None:
        self.pipeline.run.side_effect = RuntimeError("Generation failed")
        with self.assertRaisesRegex(RuntimeError, "Generation failed"):
            self.client.post("/chat", data={
                "query": "Question", "mode": "text", "language": "EN", "stop": "Pantheon",
            })


if __name__ == "__main__":
    unittest.main()
