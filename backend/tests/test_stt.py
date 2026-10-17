import base64
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from src.systems.STT.STT import STT
from src.systems.STT.utils.prepare_audio import prepare_audio
from src.utils.general.GeminiApiCall import GeminiClient


class STTTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stt = STT(client=GeminiClient(api_key="test-key", max_output_tokens=8192))
        self.response = {
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": "  Hola, Roma. \n"}]},
            }]
        }

    def api_response(self) -> BytesIO:
        return BytesIO(json.dumps(self.response).encode())

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_audio_bytes_request_and_plain_transcript(self, urlopen) -> None:
        urlopen.return_value = self.api_response()
        self.assertEqual(
            self.stt.transcribe(b"audio-data", mime_type="audio/webm"),
            "Hola, Roma.",
        )
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertIn("gemini-2.5-flash-lite:generateContent", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "test-key")
        self.assertEqual(payload["contents"][0]["parts"][1]["inlineData"], {
            "mimeType": "audio/webm",
            "data": base64.b64encode(b"audio-data").decode("ascii"),
        })
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 8192)
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "text/plain")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_file_path_infers_mime_type(self, urlopen) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "recording.WAV"
            path.write_bytes(b"wav-audio")
            for audio in (path, str(path)):
                urlopen.return_value = self.api_response()
                self.assertEqual(self.stt.transcribe(audio), "Hola, Roma.")
                payload = json.loads(urlopen.call_args.args[0].data)
                self.assertEqual(
                    payload["contents"][0]["parts"][1]["inlineData"]["mimeType"],
                    "audio/wav",
                )

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_audio_does_not_make_requests(self, urlopen) -> None:
        for audio, mime_type in [
            (b"", "audio/wav"),
            (b"audio", None),
            (b"audio", "text/plain"),
        ]:
            with self.subTest(audio=audio, mime_type=mime_type):
                with self.assertRaises(ValueError):
                    self.stt.transcribe(audio, mime_type=mime_type)
        urlopen.assert_not_called()

    def test_missing_file_raises(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                self.stt.transcribe(Path(directory) / "missing.wav")

    def test_prepare_audio_preserves_bytes_and_explicit_mime_type(self) -> None:
        self.assertEqual(
            prepare_audio(b"audio-data", mime_type="audio/webm"),
            (b"audio-data", "audio/webm"),
        )

    def test_prepare_audio_explicit_mime_type_overrides_extension(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "recording.bin"
            path.write_bytes(b"audio-data")
            self.assertEqual(
                prepare_audio(path, mime_type="audio/wav"),
                (b"audio-data", "audio/wav"),
            )
            with self.assertRaisesRegex(ValueError, "Provide mime_type"):
                prepare_audio(path)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_unsuccessful_responses_raise(self, urlopen) -> None:
        responses = [
            {"promptFeedback": {"blockReason": "SAFETY"}},
            {"candidates": [{"finishReason": "STOP", "content": {"parts": []}}]},
            {"candidates": [{
                "finishReason": "MAX_TOKENS",
                "content": {"parts": [{"text": "Partial transcript"}]},
            }]},
            {"candidates": [{"finishReason": "SAFETY"}]},
        ]
        for response in responses:
            with self.subTest(response=response):
                self.response = response
                urlopen.return_value = self.api_response()
                with self.assertRaises(RuntimeError):
                    self.stt.transcribe(b"audio", mime_type="audio/wav")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_network_error_propagates(self, urlopen) -> None:
        urlopen.side_effect = HTTPError("https://example.com", 429, "Quota", {}, None)
        with self.assertRaises(HTTPError):
            self.stt.transcribe(b"audio", mime_type="audio/wav")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_oversized_audio_rejected_before_request(self, urlopen) -> None:
        with self.assertRaisesRegex(ValueError, "20 MB"):
            self.stt.transcribe(b"x" * 15_000_000, mime_type="audio/wav")
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_existing_text_and_json_generation_are_preserved(self, urlopen) -> None:
        for mime_type in ("text/plain", "application/json"):
            with self.subTest(mime_type=mime_type):
                urlopen.return_value = self.api_response()
                self.assertEqual(
                    self.stt.client.generate("Hello", response_mime_type=mime_type),
                    "  Hola, Roma. \n",
                )
                payload = json.loads(urlopen.call_args.args[0].data)
                self.assertEqual(payload["contents"][0]["parts"], [{"text": "Hello"}])
                self.assertEqual(payload["generationConfig"]["responseMimeType"], mime_type)

    @patch("src.utils.general.GeminiApiCall._configuration_value")
    def test_default_client_uses_cheap_model_and_existing_key_configuration(self, config) -> None:
        config.return_value = "configured-key"
        stt = STT()
        self.assertEqual(stt.client.api_key, "configured-key")
        self.assertEqual(stt.client.model, "gemini-2.5-flash-lite")
        self.assertEqual(stt.client.max_output_tokens, 8192)
        self.assertEqual(stt.client.timeout, 120.0)


if __name__ == "__main__":
    unittest.main()
