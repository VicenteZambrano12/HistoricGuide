import unittest

from fastapi.testclient import TestClient

from src.app import app


class HealthTests(unittest.TestCase):
    def test_health_check(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["content-type"], "application/json")

    def test_health_response_schema(self) -> None:
        schema = app.openapi()
        response = schema["paths"]["/health"]["get"]["responses"]["200"]
        self.assertEqual(
            response["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/HealthResponse",
        )


if __name__ == "__main__":
    unittest.main()
