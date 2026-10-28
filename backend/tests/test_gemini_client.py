import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.utils.general.GeminiApiCall import GeminiClient, _configuration_value


class GeminiClientConfigurationTests(unittest.TestCase):
    def test_json_secret_provides_configuration_without_environment_mutation(self) -> None:
        configuration = {
            "GEMINI_API_KEY": "test-key", "LLM_MODEL": "test-model",
            "ENV": "GCP", "QDRANT_PORT": "6333",
        }
        with patch.dict(os.environ, {"APP_SECRETS_JSON": json.dumps(configuration)}, clear=True):
            client = GeminiClient()
            self.assertEqual(client.api_key, "test-key")
            self.assertEqual(client.model, "test-model")
            self.assertEqual(_configuration_value("ENV"), "GCP")
            self.assertEqual(_configuration_value("QDRANT_PORT"), "6333")
            self.assertNotIn("GEMINI_API_KEY", os.environ)

    def test_configuration_precedence_is_environment_json_dotenv_default(self) -> None:
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("LLM_MODEL=file-model\nGCS_BUCKET=file-bucket\n")
            with (
                patch("src.utils.general.GeminiApiCall.ENV_FILE", env_file),
                patch.dict(os.environ, {
                    "APP_SECRETS_JSON": '{"LLM_MODEL":"json-model"}',
                    "LLM_MODEL": "environment-model",
                }, clear=True),
            ):
                self.assertEqual(_configuration_value("LLM_MODEL"), "environment-model")
                del os.environ["LLM_MODEL"]
                self.assertEqual(_configuration_value("LLM_MODEL"), "json-model")
                self.assertEqual(_configuration_value("GCS_BUCKET"), "file-bucket")
                self.assertEqual(_configuration_value("MISSING", "fallback"), "fallback")

    def test_invalid_json_configuration_fails_without_exposing_values(self) -> None:
        for raw in ('{"sensitive-value"', '["sensitive-value"]', "null", "{}",
                    '{"KEY":123}', '{"KEY":{"value":"sensitive-value"}}'):
            with self.subTest(raw=raw), patch.dict(os.environ, {"APP_SECRETS_JSON": raw}, clear=True):
                with self.assertRaisesRegex(ValueError, "APP_SECRETS_JSON") as error:
                    _configuration_value("GEMINI_API_KEY")
                self.assertNotIn("sensitive-value", str(error.exception))

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
