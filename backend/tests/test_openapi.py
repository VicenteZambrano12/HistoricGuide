import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.DataClass.chat import ChatResponse
from src.api.DataClass.errors import (
    HTTPErrorResponse,
    RequestValidationErrorResponse,
    ValidationIssue,
)
from src.api.DataClass.health import HealthResponse
from src.app import app


class OpenAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = app.openapi()

    def test_application_metadata(self) -> None:
        info = self.schema["info"]
        for field in ("title", "summary", "version", "description", "contact", "license"):
            with self.subTest(field=field):
                self.assertTrue(info[field])
        self.assertEqual(info["version"], "0.1.0")
        self.assertIn("no client authentication", info["description"])
        self.assertEqual(
            {tag["name"] for tag in self.schema["tags"]},
            {"chat", "health", "demo"},
        )
        for tag in self.schema["tags"]:
            self.assertTrue(tag["description"])
        self.assertNotIn("security", self.schema)
        self.assertNotIn("securitySchemes", self.schema["components"])

    def test_operation_documentation_and_success_contracts(self) -> None:
        for path, method, tag, model in (
            ("/health", "get", "health", "HealthResponse"),
            ("/chat", "post", "chat", "ChatResponse"),
        ):
            with self.subTest(path=path):
                operation = self.schema["paths"][path][method]
                self.assertEqual(operation["tags"], [tag])
                self.assertLess(len(operation["summary"].split()), 8)
                self.assertIn("Permissions", operation["description"])
                self.assertNotIn("security", operation)
                responses = operation["responses"]
                self.assertEqual(
                    responses["200"]["content"]["application/json"]["schema"]["$ref"],
                    f"#/components/schemas/{model}",
                )
                self.assertNotIn("401", responses)
                self.assertNotIn("403", responses)
                failure = responses["500"]["content"]
                self.assertEqual(set(failure), {"application/json"})
                self.assertEqual(
                    failure["application/json"]["example"], {"detail": "Internal Server Error"},
                )
        content = self.schema["paths"]["/chat"]["post"]["responses"]["200"]["content"]
        self.assertEqual(
            content["audio/wav"]["schema"], {"type": "string", "format": "binary"},
        )

    def test_multipart_fields_remain_required_and_documented(self) -> None:
        body = self.schema["paths"]["/chat"]["post"]["requestBody"]
        self.assertTrue(body["required"])
        self.assertEqual(set(body["content"]), {"multipart/form-data"})
        reference = body["content"]["multipart/form-data"]["schema"]["$ref"]
        model = self.schema["components"]["schemas"][reference.rsplit("/", 1)[1]]
        self.assertEqual(set(model["required"]), {"query", "mode", "language", "stop"})
        for name, field in model["properties"].items():
            with self.subTest(field=name):
                self.assertTrue(field["description"])
                self.assertTrue(field["examples"])
        query_variants = model["properties"]["query"]["anyOf"]
        self.assertIn(
            query_variants,
            (
                [{"type": "string"}, {"type": "string", "format": "binary"}],
                [
                    {"type": "string"},
                    {"type": "string", "contentMediaType": "application/octet-stream"},
                ],
            ),
        )
        self.assertEqual(
            model["properties"]["mode"]["enum"], ["stt", "tts", "full", "text"],
        )
        self.assertEqual(model["properties"]["language"]["enum"], ["ES", "EN"])
        topic = model["properties"]["request_type"]
        self.assertEqual(topic["anyOf"][0]["enum"], ["historic", "restaurant"])

    def test_model_examples_are_complete_and_valid(self) -> None:
        for model in (
            ChatResponse, HealthResponse, HTTPErrorResponse,
            RequestValidationErrorResponse, ValidationIssue,
        ):
            with self.subTest(model=model.__name__):
                schema = self.schema["components"]["schemas"][model.__name__]
                self.assertTrue(schema["description"])
                self.assertEqual(set(schema["example"]), set(schema["properties"]))
                model.model_validate(schema["example"])
                for field in schema["properties"].values():
                    self.assertTrue(field["description"])
                    self.assertTrue(field["examples"])

    def test_documented_errors_match_actual_responses(self) -> None:
        responses = self.schema["paths"]["/chat"]["post"]["responses"]
        self.assertEqual(set(responses), {"200", "400", "413", "422", "500"})
        for code in ("400", "413", "422"):
            self.assertTrue(responses[code]["description"])
            self.assertIn(
                "$ref", responses[code]["content"]["application/json"]["schema"],
            )
        examples = responses["422"]["content"]["application/json"]["examples"]
        data = {"query": "Tell me about the Pantheon.", "mode": "text", "language": "EN"}
        with TestClient(app, raise_server_exceptions=False) as client:
            missing_stop = client.post("/chat", data=data)
            self.assertEqual(missing_stop.status_code, 422)
            RequestValidationErrorResponse.model_validate(missing_stop.json())
            expected_issue = examples["missing_stop"]["value"]["detail"][0]
            actual_issue = missing_stop.json()["detail"][0]
            for key, value in expected_issue.items():
                self.assertEqual(actual_issue[key], value)

            audio_required = client.post(
                "/chat", data={**data, "mode": "stt", "stop": "Pantheon"},
            )
            self.assertEqual(audio_required.status_code, 422)
            self.assertEqual(audio_required.json(), examples["audio_required"]["value"])

            malformed = client.post(
                "/chat",
                content=b"invalid multipart body",
                headers={"Content-Type": "multipart/form-data"},
            )
            self.assertEqual(malformed.status_code, 400)
            self.assertEqual(
                malformed.json(), responses["400"]["content"]["application/json"]["example"],
            )

            with patch("src.api.Endpoint.chat.Pipeline", side_effect=RuntimeError("Offline")):
                failed = client.post("/chat", data={**data, "stop": "Pantheon"})
            self.assertEqual(failed.status_code, 500)
            self.assertEqual(failed.headers["content-type"], "application/json")
            self.assertEqual(
                failed.json(), responses["500"]["content"]["application/json"]["example"],
            )

            unknown = client.get("/unknown")
            self.assertEqual(unknown.status_code, 404)
            self.assertEqual(unknown.json(), {"detail": "Not Found"})

    def test_documentation_is_served(self) -> None:
        with TestClient(app) as client:
            for path in ("/docs", "/redoc", "/openapi.json"):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
            self.assertEqual(client.get("/openapi.json").json(), self.schema)


if __name__ == "__main__":
    unittest.main()
