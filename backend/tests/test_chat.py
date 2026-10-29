import asyncio
import base64
import json
from threading import Event
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.Endpoint.chat import MAX_AUDIO_BYTES
from src.app import app
from src.api.Endpoint.chat_stream import stream_chat
from src.utils.general.progress import report_progress
from src.utils.general.sources import PdfSource, report_sources


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
                        request_type=None,
                    )
                    if audio_output:
                        self.assertEqual(response.headers["content-type"], "audio/wav")
                        self.assertEqual(response.content, result)
                    else:
                        self.assertEqual(response.json(), {"text": result})

    def test_explicit_request_type_is_forwarded_in_every_mode(self) -> None:
        for request_type in ("historic", "restaurant"):
            for mode in ("text", "tts", "stt", "full"):
                with self.subTest(request_type=request_type, mode=mode):
                    self.pipeline.run.return_value = (
                        b"wav-answer" if mode in ("tts", "full") else "Answer"
                    )
                    query = (
                        ("query.wav", b"audio", "audio/wav")
                        if mode in ("stt", "full") else (None, "Question")
                    )
                    response = self.client.post(
                        "/chat",
                        data={
                            "mode": mode, "language": "EN", "stop": "Pantheon",
                            "request_type": request_type,
                        },
                        files={"query": query},
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(
                        self.pipeline.run.call_args.kwargs["request_type"], request_type,
                    )

    def test_invalid_fields_are_rejected_before_pipeline(self) -> None:
        valid = {"query": "Question", "mode": "text", "language": "EN", "stop": "Pantheon"}
        cases = [
            {**valid, "mode": "unknown"},
            {**valid, "language": "FR"},
            {**valid, "stop": " "},
            {**valid, "query": " "},
            {**valid, "mode": "stt"},
            {**valid, "mode": "full"},
            {**valid, "request_type": "unknown"},
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

    def test_progress_stream_in_all_modes_and_languages(self) -> None:
        for mode in ("text", "stt", "tts", "full"):
            for language in ("EN", "ES"):
                with self.subTest(mode=mode, language=language):
                    audio_output = mode in ("tts", "full")

                    def run(*args, **kwargs):
                        report_progress("routing")
                        report_progress("generating")
                        return b"wav-answer" if audio_output else "An answer."

                    self.pipeline.run.side_effect = run
                    response = self.client.post(
                        "/chat",
                        data={
                            "mode": mode, "language": language, "stop": "Pantheon",
                            "stream": "true",
                        },
                        files={"query": ("voice.webm", b"voice", "audio/webm")
                               if mode in ("stt", "full") else (None, "Question")},
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["content-type"], "application/x-ndjson")
                    self.assertEqual(response.headers["x-accel-buffering"], "no")
                    events = [json.loads(line) for line in response.iter_lines()]
                    self.assertEqual(events[:-1], [
                        {"type": "progress", "step": step}
                        for step in ("starting", "routing", "generating")
                    ])
                    if audio_output:
                        self.assertEqual(events[-1]["mime_type"], "audio/wav")
                        self.assertEqual(base64.b64decode(events[-1]["audio"]), b"wav-answer")
                    else:
                        self.assertEqual(events[-1], {"type": "result", "text": "An answer."})

    def test_stream_failure_is_logged_and_never_returns_a_result(self) -> None:
        self.pipeline.run.side_effect = RuntimeError("private provider detail")
        with self.assertLogs("historicguide.src.api.Endpoint.chat_stream", level="ERROR") as logs:
            response = self.client.post("/chat", data={
                "query": "Question", "mode": "text", "language": "EN",
                "stop": "Pantheon", "stream": "true",
            })
        events = [json.loads(line) for line in response.iter_lines()]
        self.assertEqual(events[-1]["type"], "error")
        self.assertNotIn("private provider detail", response.text)
        self.assertEqual(getattr(logs.records[0], "event"), "chat.stream.failed")
        self.assertEqual(logs.records[0].levelname, "ERROR")
        self.assertFalse(any(event["type"] == "result" for event in events))

    def test_pdf_references_are_delivered_in_every_mode_with_and_without_streaming(self) -> None:
        references = [{"source": "Pantheon/historic/guide.pdf", "page": 7}]
        for stream in (False, True):
            for mode in ("text", "stt", "tts", "full"):
                with self.subTest(stream=stream, mode=mode):
                    audio_output = mode in ("tts", "full")

                    def run(*args, **kwargs):
                        report_sources([PdfSource.model_validate(references[0])])
                        return b"wav-answer" if audio_output else "Answer"

                    self.pipeline.run.side_effect = run
                    response = self.client.post(
                        "/chat",
                        data={
                            "mode": mode, "language": "EN", "stop": "Pantheon",
                            "stream": str(stream).lower(),
                        },
                        files={"query": ("voice.webm", b"voice", "audio/webm")
                               if mode in ("stt", "full") else (None, "Question")},
                    )
                    self.assertEqual(response.status_code, 200)
                    if stream:
                        result = json.loads(response.text.splitlines()[-1])
                        self.assertEqual(result["sources"], references)
                    elif audio_output:
                        self.assertEqual(json.loads(response.headers["X-PDF-Sources"]), references)
                    else:
                        self.assertEqual(response.json()["sources"], references)

    def test_invalid_stream_request_is_rejected_before_pipeline(self) -> None:
        response = self.client.post("/chat", data={
            "query": " ", "mode": "text", "language": "EN",
            "stop": "Pantheon", "stream": "true",
        })
        self.assertEqual(response.status_code, 422)
        self.pipeline_class.assert_not_called()

    def test_progress_is_available_before_pipeline_finishes(self) -> None:
        release = Event()

        def run() -> str:
            if not release.wait(timeout=5):
                raise TimeoutError("Test did not release the pipeline")
            return "Answer"

        async def consume() -> None:
            iterator = stream_chat(run, audio_output=False).body_iterator
            try:
                first = await asyncio.wait_for(anext(iterator), timeout=2)
                self.assertEqual(json.loads(first), {"type": "progress", "step": "starting"})
                release.set()
                final = await asyncio.wait_for(anext(iterator), timeout=2)
                self.assertEqual(json.loads(final), {"type": "result", "text": "Answer"})
            finally:
                release.set()
                await iterator.aclose()

        asyncio.run(consume())


if __name__ == "__main__":
    unittest.main()
