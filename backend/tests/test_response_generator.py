from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from pydantic import ValidationError

from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.utils.general.GeminiApiCall import GeminiClient


UTILS = "src.utils.AgentSystem.ResponseGenerator"


class ResponseGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = ResponseGenerator(client=GeminiClient(api_key="test-key"))
        retrieval_patch = patch(f"{UTILS}.generate_response.retrieve_chunks", return_value=[])
        self.retrieval = retrieval_patch.start()
        self.addCleanup(retrieval_patch.stop)

    def api_response(self, text: str) -> BytesIO:
        return BytesIO(json.dumps({
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": text}]},
            }],
        }).encode())

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_category_selects_prompt_and_returns_only_answer(self, urlopen) -> None:
        for category in ("historic", "restaurant"):
            with self.subTest(category=category):
                urlopen.return_value = self.api_response("  A spoken guide answer.\n")
                answer = self.generator.generate(
                    "Pantheon", category, user_query="Tell me more"
                )
                self.assertEqual(answer, "A spoken guide answer.")
                request = urlopen.call_args.args[0]
                payload = json.loads(request.data)
                self.assertIn(":generateContent", request.full_url)
                self.assertEqual(request.get_header("X-goog-api-key"), "test-key")
                self.assertEqual(
                    json.loads(payload["contents"][0]["parts"][0]["text"]),
                    {
                        "stop": "Pantheon", "category": category,
                        "user_query": "Tell me more", "context": [], "language": "en",
                    },
                )
                self.assertIn(
                    f"You are the {category} guide",
                    payload["systemInstruction"]["parts"][0]["text"],
                )
                self.assertEqual(payload["generationConfig"]["responseMimeType"], "text/plain")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_selected_language_is_sent_for_both_category_prompts(self, urlopen) -> None:
        for category in ("historic", "restaurant"):
            for language, query, answer in (
                ("en", "Explica este lugar.", "An English answer."),
                ("es", "Explain this place.", "Una respuesta en castellano."),
            ):
                with self.subTest(category=category, language=language):
                    urlopen.return_value = self.api_response(answer)
                    self.assertEqual(
                        self.generator.generate(
                            "Pantheon", category, user_query=query, language=language
                        ),
                        answer,
                    )
                    payload = json.loads(urlopen.call_args.args[0].data)
                    data = json.loads(payload["contents"][0]["parts"][0]["text"])
                    self.assertEqual(data["language"], language)
                    self.assertEqual(data["user_query"], query)
                    self.assertIn(
                        "en means English, es means Spanish.",
                        payload["systemInstruction"]["parts"][0]["text"],
                    )

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_orchestrator_route_can_be_passed_directly(self, urlopen) -> None:
        route = Orchestrator().route("Pantheon", param="historic")
        urlopen.return_value = self.api_response("An introduction to the Pantheon.")
        self.assertEqual(
            self.generator.generate(**route.model_dump()),
            "An introduction to the Pantheon.",
        )
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertIsNone(
            json.loads(payload["contents"][0]["parts"][0]["text"])["user_query"]
        )

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_supplied_chunks_are_included_as_data(self, urlopen) -> None:
        chunks = ["The Pantheon has a concrete dome.", "Its oculus is open to the sky."]
        urlopen.return_value = self.api_response("The dome has an open oculus.")
        self.generator.generate("Pantheon", "historic", context=chunks)
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(
            json.loads(payload["contents"][0]["parts"][0]["text"])["context"],
            chunks,
        )

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_retrieved_chunks_are_added_to_context_without_mutating_input(self, urlopen) -> None:
        self.retrieval.return_value = ["First retrieved fact.", "Second retrieved fact."]
        chunks = ["Caller-supplied fact."]
        urlopen.return_value = self.api_response("A grounded answer.")
        self.generator.generate(
            " Pantheon ", "historic", user_query=" Explain the dome. ",
            context=chunks, language="es",
        )
        self.retrieval.assert_called_once_with(
            self.generator.client, "Pantheon", "historic",
            user_query="Explain the dome.", database_path=self.generator.database_path,
        )
        payload = json.loads(urlopen.call_args.args[0].data)
        data = json.loads(payload["contents"][0]["parts"][0]["text"])
        self.assertEqual(data["context"], chunks + self.retrieval.return_value)
        self.assertEqual(data["language"], "es")
        self.assertEqual(chunks, ["Caller-supplied fact."])

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_retrieval_failure_stops_generation(self, urlopen) -> None:
        self.retrieval.side_effect = RuntimeError("Retrieval failed")
        with self.assertRaisesRegex(RuntimeError, "Retrieval failed"):
            self.generator.generate("Pantheon", "historic")
        urlopen.assert_not_called()

    @patch(f"{UTILS}.generate_response.GeminiClient")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_default_client_is_lazy_and_reused(self, urlopen, client) -> None:
        generator = ResponseGenerator()
        client.assert_not_called()
        client.return_value = GeminiClient(api_key="test-key", max_output_tokens=1024)
        for category in ("historic", "restaurant"):
            urlopen.return_value = self.api_response("A guide answer.")
            generator.generate("Pantheon", category)
        self.assertIs(generator.client, client.return_value)
        client.assert_called_once_with(max_output_tokens=1024)

    @patch(f"{UTILS}.generate_response.GeminiClient")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_inputs_fail_before_client_creation(self, urlopen, client) -> None:
        cases = [
            {"stop": "", "category": "historic"},
            {"stop": 123, "category": "historic"},
            {"stop": "Pantheon", "category": "response"},
            {"stop": "Pantheon", "category": "../historic"},
            {"stop": "Pantheon", "category": "historic", "user_query": " "},
            {"stop": "Pantheon", "category": "historic", "user_query": 123},
            {"stop": "Pantheon", "category": "historic", "context": "a chunk"},
            {"stop": "Pantheon", "category": "historic", "context": [" "]},
            {"stop": "Pantheon", "category": "historic", "context": [123]},
            {"stop": "Pantheon", "category": "historic", "language": "fr"},
            {"stop": "Pantheon", "category": "historic", "language": "EN"},
            {"stop": "Pantheon", "category": "historic", "language": ""},
            {"stop": "Pantheon", "category": "historic", "language": None},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    ResponseGenerator().generate(**kwargs)
        client.assert_not_called()
        urlopen.assert_not_called()
        self.retrieval.assert_not_called()

    @patch(f"{UTILS}.load_prompt.PROMPT_DIRECTORY")
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_prompts_raise_before_api_call(self, urlopen, directory) -> None:
        for text in ("system_prompt: ''", "unexpected: value", "[]"):
            with self.subTest(text=text):
                path = directory.__truediv__.return_value
                path.open.return_value.__enter__.return_value = BytesIO(text.encode())
                with self.assertRaises(ValidationError):
                    self.generator.generate("Pantheon", "historic")
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_missing_prompt_raises_before_api_call(self, urlopen) -> None:
        with TemporaryDirectory() as directory:
            with patch(f"{UTILS}.load_prompt.PROMPT_DIRECTORY", Path(directory)):
                with self.assertRaises(FileNotFoundError):
                    self.generator.generate("Pantheon", "restaurant")
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_empty_and_blocked_responses_raise(self, urlopen) -> None:
        responses = [
            self.api_response(""),
            self.api_response(" \n "),
            BytesIO(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode()),
        ]
        for response in responses:
            urlopen.return_value = response
            with self.assertRaises(RuntimeError):
                self.generator.generate("Pantheon", "historic")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_api_errors_propagate(self, urlopen) -> None:
        urlopen.side_effect = HTTPError("https://example.com", 429, "Quota", {}, None)
        with self.assertRaises(HTTPError):
            self.generator.generate("Pantheon", "historic")


if __name__ == "__main__":
    unittest.main()
