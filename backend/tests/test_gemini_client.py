import unittest
from unittest.mock import patch

from src.utils.general.GeminiApiCall import GeminiClient


class GeminiClientConfigurationTests(unittest.TestCase):
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_corrupted_model_is_rejected_before_request(self, urlopen) -> None:
        for model in (
            "gemini-3.    Exception in ASGI application",
            "gemini-\n3.5-flash-lite",
            "gemini-\t3.5-flash-lite",
        ):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "LLM_MODEL.*without whitespace"):
                    GeminiClient(api_key="test-key", model=model)
        urlopen.assert_not_called()

    def test_model_surrounding_whitespace_is_trimmed(self) -> None:
        client = GeminiClient(api_key="test-key", model=" gemini-3.5-flash-lite\n")
        self.assertEqual(client.model, "gemini-3.5-flash-lite")

    def test_configured_model_is_validated(self) -> None:
        with patch.dict("os.environ", {"LLM_MODEL": "gemini-3. pasted traceback"}):
            with self.assertRaisesRegex(ValueError, "LLM_MODEL.*without whitespace"):
                GeminiClient(api_key="test-key")


if __name__ == "__main__":
    unittest.main()
