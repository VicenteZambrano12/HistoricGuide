from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from pydantic import ValidationError

from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.utils.AgentSystem.Orchestrator.dataclasses.Route import Route
from src.utils.general.GeminiApiCall import GeminiClient


UTILS = "src.utils.AgentSystem.Orchestrator"


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator(client=GeminiClient(api_key="test-key"))

    def api_response(self, text: str) -> BytesIO:
        return BytesIO(json.dumps({
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": text}]},
            }],
        }).encode())

    @patch(f"{UTILS}.route.GeminiClient")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_explicit_param_bypasses_gemini_and_needs_no_key(self, urlopen, client) -> None:
        orchestrator = Orchestrator()
        for category in ("historic", "restaurant"):
            with self.subTest(category=category):
                result = orchestrator.route("Pantheon", param=category)
                self.assertIsInstance(result, Route)
                self.assertEqual(result.model_dump(), {
                    "stop": "Pantheon", "category": category,
                })
        client.assert_not_called()
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_queries_classify_and_preserve_the_stop(self, urlopen) -> None:
        for query, label in (
            ("Who built this temple?", "historic"),
            ("Where can I have coffee?", "restaurant"),
            ("Quiero comer cerca.", "restaurant"),
        ):
            with self.subTest(query=query):
                urlopen.return_value = self.api_response(f"  {label}\n")
                result = self.orchestrator.route("Pantheon", user_query=query)
                self.assertEqual(result.model_dump(), {
                    "stop": "Pantheon", "category": label,
                })
                request = urlopen.call_args.args[0]
                payload = json.loads(request.data)
                self.assertIn(":generateContent", request.full_url)
                self.assertEqual(request.get_header("X-goog-api-key"), "test-key")
                self.assertEqual(
                    json.loads(payload["contents"][0]["parts"][0]["text"]),
                    {"stop": "Pantheon", "user_query": query},
                )
                self.assertEqual(payload["generationConfig"]["responseMimeType"], "text/plain")
                self.assertIn(
                    "Return only the single lowercase word historic or restaurant.",
                    payload["systemInstruction"]["parts"][0]["text"],
                )

    @patch(f"{UTILS}.route.GeminiClient")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_default_client_is_created_only_for_queries(self, urlopen, client) -> None:
        client.return_value = GeminiClient(api_key="test-key")
        urlopen.return_value = self.api_response("historic")
        result = Orchestrator().route("Roman Forum", user_query="Tell me its history")
        self.assertEqual(result.category, "historic")
        client.assert_called_once_with()

    @patch(f"{UTILS}.route.GeminiClient")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_default_client_is_reused_across_queries(self, urlopen, client) -> None:
        client.return_value = GeminiClient(api_key="test-key")
        orchestrator = Orchestrator()
        for label in ("historic", "restaurant"):
            urlopen.return_value = self.api_response(label)
            self.assertEqual(
                orchestrator.route("Pantheon", user_query="What is nearby?").category,
                label,
            )
        self.assertIs(orchestrator.client, client.return_value)
        client.assert_called_once_with()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_inputs_fail_before_api_call(self, urlopen) -> None:
        cases = [
            {"stop": "Pantheon"},
            {"stop": "Pantheon", "user_query": "history", "param": "historic"},
            {"stop": "Pantheon", "user_query": ""},
            {"stop": "Pantheon", "user_query": " \n "},
            {"stop": "Pantheon", "user_query": 123},
            {"stop": "", "param": "historic"},
            {"stop": "  ", "param": "historic"},
            {"stop": 2, "param": "historic"},
            {"stop": "Pantheon", "param": "restaurants"},
            {"stop": "Pantheon", "param": "Historic"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    self.orchestrator.route(**kwargs)
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_llm_labels_are_not_routes(self, urlopen) -> None:
        for text in (
            "Historic", "restaurants", "historic or restaurant",
            '{"category": "historic"}', "Here is the history of the Pantheon.",
            "```historic```",
        ):
            with self.subTest(text=text):
                urlopen.return_value = self.api_response(text)
                with self.assertRaises(ValidationError):
                    self.orchestrator.route("Pantheon", user_query="History?")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_empty_and_blocked_responses_raise(self, urlopen) -> None:
        responses = [
            self.api_response(""),
            BytesIO(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode()),
        ]
        for response in responses:
            urlopen.return_value = response
            with self.assertRaises(RuntimeError):
                self.orchestrator.route("Pantheon", user_query="History?")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_api_errors_propagate(self, urlopen) -> None:
        urlopen.side_effect = HTTPError("https://example.com", 429, "Quota", {}, None)
        with self.assertRaises(HTTPError):
            self.orchestrator.route("Pantheon", user_query="History?")

    @patch(f"{UTILS}.load_prompt.PROMPT_PATH")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_prompt_config_fails_before_api_call(self, urlopen, prompt_path) -> None:
        for content in ("system_prompt: ''", "unexpected: value", "[]"):
            with self.subTest(content=content):
                prompt_path.open.return_value.__enter__.return_value = BytesIO(content.encode())
                with self.assertRaises(ValidationError):
                    self.orchestrator.route("Pantheon", user_query="History?")
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_missing_prompt_does_not_affect_explicit_routes(self, urlopen) -> None:
        with TemporaryDirectory() as directory:
            with patch(f"{UTILS}.load_prompt.PROMPT_PATH", Path(directory) / "missing.yaml"):
                self.assertEqual(
                    self.orchestrator.route("Pantheon", param="historic").category,
                    "historic",
                )
                with self.assertRaises(FileNotFoundError):
                    self.orchestrator.route("Pantheon", user_query="History?")
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
