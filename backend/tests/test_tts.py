import base64
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import wave

from src.systems.TTS.TTS import TTS
from src.systems.TTS.utils.prepare_audio import prepare_audio
from src.utils.general.GeminiApiCall import GeminiClient


class TTSTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tts = TTS(client=GeminiClient(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            max_output_tokens=8192,
            timeout=120.0,
        ))
        self.pcm = b"\x00\x00\x01\x00\xff\xff"
        self.part = {"inlineData": {
            "mimeType": "audio/L16;codec=pcm;rate=24000",
            "data": base64.b64encode(self.pcm).decode("ascii"),
        }}
        self.response = {"candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [self.part]},
        }]}

    def api_response(self) -> BytesIO:
        return BytesIO(json.dumps(self.response).encode())

    def assert_wav(self, audio: bytes, pcm: bytes, rate: int = 24000) -> None:
        with wave.open(BytesIO(audio), "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), rate)
            self.assertEqual(wav.getnframes(), len(pcm) // 2)
            self.assertEqual(wav.readframes(wav.getnframes()), pcm)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_synthesis_request_and_playable_wav(self, urlopen) -> None:
        urlopen.return_value = self.api_response()
        audio = self.tts.synthesize("Welcome to Rome.", voice="Puck")
        self.assert_wav(audio, self.pcm)
        request = urlopen.call_args.args[0]
        self.assertIn("gemini-2.5-flash-preview-tts:generateContent", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "test-key")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 120.0)
        payload = json.loads(request.data)
        self.assertEqual(payload["contents"], [{
            "role": "user", "parts": [{"text": "Welcome to Rome."}],
        }])
        config = payload["generationConfig"]
        self.assertEqual(config["responseModalities"], ["AUDIO"])
        self.assertEqual(config["maxOutputTokens"], 8192)
        self.assertEqual(
            config["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"],
            "Puck",
        )
        self.assertNotIn("responseMimeType", config)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_default_voice(self, urlopen) -> None:
        urlopen.return_value = self.api_response()
        self.tts.synthesize("Hello.")
        config = json.loads(urlopen.call_args.args[0].data)["generationConfig"]
        self.assertEqual(
            config["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"],
            "Kore",
        )

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_input_does_not_make_requests(self, urlopen) -> None:
        for text, voice in [("", "Kore"), (" \n", "Kore"), ("Hello", " ")]:
            with self.subTest(text=text, voice=voice):
                with self.assertRaises(ValueError):
                    self.tts.synthesize(text, voice=voice)
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_input_types_do_not_make_requests(self, urlopen) -> None:
        for text, voice in [(None, "Kore"), (b"Hello", "Kore"), ("Hello", None)]:
            with self.subTest(text=text, voice=voice):
                with self.assertRaises(TypeError):
                    self.tts.synthesize(text, voice=voice)
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_blocked_empty_and_incomplete_responses_raise(self, urlopen) -> None:
        responses = [
            {"promptFeedback": {"blockReason": "SAFETY"}},
            {"candidates": [{"finishReason": "STOP", "content": {"parts": []}}]},
            {"candidates": [{
                "finishReason": "STOP", "content": {"parts": [{"text": "No audio"}]},
            }]},
            {"candidates": [{
                "finishReason": "MAX_TOKENS", "content": {"parts": [self.part]},
            }]},
            {"candidates": [{"finishReason": "SAFETY"}]},
            {"candidates": [{"content": {"parts": [self.part]}}]},
        ]
        for response in responses:
            with self.subTest(response=response):
                self.response = response
                urlopen.return_value = self.api_response()
                with self.assertRaises(RuntimeError):
                    self.tts.synthesize("Hello.")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_inline_audio_raises(self, urlopen) -> None:
        for data, mime_type in [
            ("!invalid!", "audio/L16;rate=24000"),
            ("non-ascii-\u00e9", "audio/L16;rate=24000"),
            (None, "audio/L16;rate=24000"),
            ("", "audio/L16;rate=24000"),
            ("AAAA", "audio/L16;rate=24000"),
            ("AAAAAA==", "text/plain"),
            ("AAAAAA==", None),
            ("AAAAAA==", "audio/mp3"),
        ]:
            with self.subTest(data=data, mime_type=mime_type):
                self.part["inlineData"] = {"data": data, "mimeType": mime_type}
                urlopen.return_value = self.api_response()
                with self.assertRaises(RuntimeError):
                    self.tts.synthesize("Hello.")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_multiple_audio_parts_and_thought_filter(self, urlopen) -> None:
        self.response["candidates"][0]["content"]["parts"] = [
            {"text": "Internal", "thought": True},
            {"inlineData": {"data": "invalid"}, "thought": True},
            self.part,
            self.part,
        ]
        urlopen.return_value = self.api_response()
        self.assert_wav(self.tts.synthesize("Hello."), self.pcm * 2)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_inconsistent_formats_raise(self, urlopen) -> None:
        self.response["candidates"][0]["content"]["parts"].append({
            "inlineData": {
                "mimeType": "audio/L16;rate=16000",
                "data": base64.b64encode(self.pcm).decode("ascii"),
            }
        })
        urlopen.return_value = self.api_response()
        with self.assertRaisesRegex(RuntimeError, "inconsistent"):
            self.tts.synthesize("Hello.")

    def test_prepare_audio_uses_response_sample_rate(self) -> None:
        self.assert_wav(
            prepare_audio(self.pcm, mime_type="audio/L16;rate=16000"),
            self.pcm,
            rate=16000,
        )

    def test_prepare_audio_rejects_invalid_pcm(self) -> None:
        for mime_type in [
            "audio/L16", "audio/L16;rate=bad", "audio/L16;rate=0",
            "audio/L16;rate=-1", "audio/L16;rate=999999999999",
            "audio/L16;rate=24000;channels=2",
            "audio/L16;rate=24000;codec=mp3", "audio/L16;rate",
        ]:
            with self.subTest(mime_type=mime_type):
                with self.assertRaises(RuntimeError):
                    prepare_audio(self.pcm, mime_type=mime_type)
        for audio in (b"", b"\x00"):
            with self.subTest(audio=audio):
                with self.assertRaises(RuntimeError):
                    prepare_audio(audio, mime_type="audio/L16;rate=24000")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_network_errors_propagate(self, urlopen) -> None:
        error = HTTPError("https://example.com", 429, "Quota", {}, None)
        self.addCleanup(error.close)
        urlopen.side_effect = error
        with self.assertRaises(HTTPError):
            self.tts.synthesize("Hello.")

    @patch("src.utils.general.GeminiApiCall._configuration_value")
    def test_default_client_uses_tts_model_and_existing_key_configuration(self, config) -> None:
        config.return_value = "configured-key"
        tts = TTS()
        self.assertEqual(tts.client.api_key, "configured-key")
        self.assertEqual(tts.client.model, "gemini-2.5-flash-preview-tts")
        self.assertEqual(tts.client.max_output_tokens, 8192)
        self.assertEqual(tts.client.timeout, 120.0)


if __name__ == "__main__":
    unittest.main()
