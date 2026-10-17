from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from pydantic import ValidationError

from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline
from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.utils.general.GeminiApiCall import GeminiClient


class AgentPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = AgentPipeline(
            orchestrator=Orchestrator(client=GeminiClient(api_key="routing-key")),
            response_generator=ResponseGenerator(
                client=GeminiClient(api_key="generation-key", max_output_tokens=1024)
            ),
        )

    def api_response(self, text: str) -> BytesIO:
        return BytesIO(json.dumps({
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": text}]},
            }],
        }).encode())

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_text_query_routes_then_generates(self, urlopen) -> None:
        for category, query in (
            ("historic", "What is special about this dome?"),
            ("restaurant", "Where can I have coffee?"),
        ):
            with self.subTest(category=category):
                urlopen.reset_mock()
                urlopen.side_effect = [
                    self.api_response(category),
                    self.api_response("  A complete spoken answer.\n"),
                ]
                answer = self.pipeline.run("Pantheon", user_query=query)
                self.assertEqual(answer, "A complete spoken answer.")
                self.assertEqual(urlopen.call_count, 2)
                routing_request = urlopen.call_args_list[0].args[0]
                generation_request = urlopen.call_args_list[1].args[0]
                self.assertEqual(routing_request.get_header("X-goog-api-key"), "routing-key")
                self.assertEqual(generation_request.get_header("X-goog-api-key"), "generation-key")
                routing = json.loads(routing_request.data)
                generation = json.loads(generation_request.data)
                self.assertEqual(
                    json.loads(routing["contents"][0]["parts"][0]["text"]),
                    {"stop": "Pantheon", "user_query": query},
                )
                self.assertEqual(
                    json.loads(generation["contents"][0]["parts"][0]["text"]),
                    {
                        "stop": "Pantheon", "category": category,
                        "user_query": query, "context": [], "language": "en",
                    },
                )
                self.assertIn(
                    f"You are the {category} guide",
                    generation["systemInstruction"]["parts"][0]["text"],
                )

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_explicit_category_only_calls_response_generator(self, urlopen) -> None:
        for category in ("historic", "restaurant"):
            with self.subTest(category=category):
                urlopen.reset_mock()
                urlopen.return_value = self.api_response("An introduction.")
                self.assertEqual(
                    self.pipeline.run("Pantheon", param=category), "An introduction."
                )
                urlopen.assert_called_once()
                payload = json.loads(urlopen.call_args.args[0].data)
                data = json.loads(payload["contents"][0]["parts"][0]["text"])
                self.assertEqual(data["category"], category)
                self.assertIsNone(data["user_query"])

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_spanish_reaches_generation_for_queries_and_explicit_categories(self, urlopen) -> None:
        for kwargs in ({"user_query": "Tell me more"}, {"param": "historic"}):
            with self.subTest(kwargs=kwargs):
                responses = []
                if "user_query" in kwargs:
                    responses.append(self.api_response("historic"))
                responses.append(self.api_response("Una respuesta en castellano."))
                urlopen.side_effect = responses
                self.assertEqual(
                    self.pipeline.run("Pantheon", language="es", **kwargs),
                    "Una respuesta en castellano.",
                )
                payload = json.loads(urlopen.call_args.args[0].data)
                data = json.loads(payload["contents"][0]["parts"][0]["text"])
                self.assertEqual(data["language"], "es")

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_context_and_normalized_request_reach_generator(self, urlopen) -> None:
        urlopen.side_effect = [
            self.api_response("historic"), self.api_response("The dome has an oculus.")
        ]
        chunks = ["The dome has an open oculus."]
        self.pipeline.run(
            " Pantheon ", user_query=" Explain the dome. ", context=chunks
        )
        payload = json.loads(urlopen.call_args.args[0].data)
        data = json.loads(payload["contents"][0]["parts"][0]["text"])
        self.assertEqual(data["stop"], "Pantheon")
        self.assertEqual(data["user_query"], "Explain the dome.")
        self.assertEqual(data["context"], chunks)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_requests_fail_before_any_api_call(self, urlopen) -> None:
        cases = [
            {"stop": "Pantheon"},
            {"stop": "Pantheon", "user_query": "history", "param": "historic"},
            {"stop": "Pantheon", "user_query": " "},
            {"stop": "", "param": "historic"},
            {"stop": 1, "param": "historic"},
            {"stop": "Pantheon", "param": "response"},
            {"stop": "Pantheon", "user_query": "history", "context": [" "]},
            {"stop": "Pantheon", "user_query": "history", "context": [123]},
            {"stop": "Pantheon", "param": "historic", "context": "not a list"},
            {"stop": "Pantheon", "user_query": "history", "language": "fr"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    self.pipeline.run(**kwargs)
        urlopen.assert_not_called()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_invalid_classification_stops_before_generation(self, urlopen) -> None:
        urlopen.return_value = self.api_response("not a category")
        with self.assertRaises(ValidationError):
            self.pipeline.run("Pantheon", user_query="Tell me more")
        urlopen.assert_called_once()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_routing_failure_propagates_without_generation(self, urlopen) -> None:
        urlopen.side_effect = HTTPError("https://example.com", 429, "Quota", {}, None)
        with self.assertRaises(HTTPError):
            self.pipeline.run("Pantheon", user_query="Tell me more")
        urlopen.assert_called_once()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_generation_failure_propagates(self, urlopen) -> None:
        urlopen.side_effect = [
            self.api_response("historic"),
            HTTPError("https://example.com", 429, "Quota", {}, None),
        ]
        with self.assertRaises(HTTPError):
            self.pipeline.run("Pantheon", user_query="Tell me more")
        self.assertEqual(urlopen.call_count, 2)

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_empty_answer_raises_instead_of_returning_route(self, urlopen) -> None:
        urlopen.side_effect = [
            self.api_response("historic"), self.api_response(" ")
        ]
        with self.assertRaises(RuntimeError):
            self.pipeline.run("Pantheon", user_query="Tell me more")

    def test_default_components_are_lazy_and_not_shared(self) -> None:
        first = AgentPipeline()
        second = AgentPipeline()
        self.assertIsNone(first.orchestrator.client)
        self.assertIsNone(first.response_generator.client)
        self.assertIsNot(first.orchestrator, second.orchestrator)
        self.assertIsNot(first.response_generator, second.response_generator)


if __name__ == "__main__":
    unittest.main()
