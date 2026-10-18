"""Reusable Gemini Developer API client with text, JSON, and audio output."""

import base64
from binascii import Error as Base64Error
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from dotenv import dotenv_values


ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def _configuration_value(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    if not ENV_FILE.exists():
        return default
    with ENV_FILE.open(encoding="utf-8") as stream:
        return dotenv_values(stream=stream, interpolate=False).get(name, default) or ""


@dataclass
class GeminiClient:
    api_key: str = field(
        default_factory=lambda: _configuration_value("GEMINI_API_KEY"),
        repr=False,
    )
    model: str = field(
        default_factory=lambda: _configuration_value("LLM_MODEL", "gemini-2.5-flash-lite")
    )
    max_output_tokens: int = 256
    timeout: float = 30.0
    embedding_model: str = field(
        default_factory=lambda: _configuration_value("EMBEDDING_MODEL", "gemini-embedding-001")
    )

    def __post_init__(self) -> None:
        self.api_key = self.api_key.strip()
        if not self.api_key:
            raise ValueError(
                "Set GEMINI_API_KEY in .env or the environment to your Google AI Studio API key."
            )
        self.model = self.model.strip()
        if not self.model:
            raise ValueError("model (LLM_MODEL) must not be empty.")
        if self.max_output_tokens <= 0 or self.timeout <= 0:
            raise ValueError("max_output_tokens and timeout must be positive.")

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_mime_type: Literal["text/plain", "application/json"] = "text/plain",
        audio: bytes | None = None,
        audio_mime_type: str | None = None,
    ) -> str:
        """Return generated text; API, network, and response errors propagate."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty.")
        if system_prompt is not None and not system_prompt.strip():
            raise ValueError("system_prompt must not be empty.")
        if response_mime_type not in ("text/plain", "application/json"):
            raise ValueError("response_mime_type must be text/plain or application/json.")
        if audio is not None and not audio:
            raise ValueError("audio must not be empty.")
        if audio is not None and (
            audio_mime_type is None or not audio_mime_type.startswith("audio/")
        ):
            raise ValueError("audio_mime_type must be an audio MIME type.")
        if audio is None and audio_mime_type is not None:
            raise ValueError("audio_mime_type requires audio.")

        parts: list[dict[str, object]] = [{"text": prompt}]
        if audio is not None:
            parts.append({
                "inlineData": {
                    "mimeType": audio_mime_type,
                    "data": base64.b64encode(audio).decode("ascii"),
                }
            })
        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": response_mime_type,
            },
        }
        if system_prompt is not None:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        data = json.dumps(payload).encode("utf-8")
        if audio is not None and len(data) >= 20_000_000:
            raise ValueError("Inline audio requests must be smaller than 20 MB.")
        result = self._generate_content(data)

        candidates = result.get("candidates", [])
        if not candidates:
            reason = result.get("promptFeedback", {}).get("blockReason", "no candidates")
            raise RuntimeError(f"Gemini returned no text: {reason}.")
        candidate = candidates[0]
        if audio is not None and candidate.get("finishReason") != "STOP":
            reason = candidate.get("finishReason", "missing finish reason")
            raise RuntimeError(f"Gemini audio generation did not complete: {reason}.")
        text = "".join(
            part["text"]
            for part in candidate.get("content", {}).get("parts", [])
            if "text" in part and not part.get("thought", False)
        )
        if not text.strip():
            reason = candidate.get("finishReason", "empty response")
            raise RuntimeError(f"Gemini returned no text: {reason}.")
        return text

    def generate_audio(self, text: str, *, voice: str = "Kore") -> tuple[bytes, str]:
        """Return decoded speech and its MIME type; errors propagate."""
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        if not text.strip():
            raise ValueError("text must not be empty.")
        if not isinstance(voice, str):
            raise TypeError("voice must be a string.")
        if not voice.strip():
            raise ValueError("voice must not be empty.")
        payload = {
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "maxOutputTokens": self.max_output_tokens,
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice.strip()}
                    }
                },
            },
        }
        result = self._generate_content(json.dumps(payload).encode("utf-8"))
        candidates = result.get("candidates", [])
        if not candidates:
            reason = result.get("promptFeedback", {}).get("blockReason", "no candidates")
            raise RuntimeError(f"Gemini returned no audio: {reason}.")
        candidate = candidates[0]
        if candidate.get("finishReason") != "STOP":
            reason = candidate.get("finishReason", "missing finish reason")
            raise RuntimeError(f"Gemini speech generation did not complete: {reason}.")
        chunks = []
        mime_type = None
        for part in candidate.get("content", {}).get("parts", []):
            if part.get("thought", False) or "inlineData" not in part:
                continue
            inline_data = part["inlineData"]
            chunk_mime_type = inline_data.get("mimeType")
            if not isinstance(chunk_mime_type, str) or not chunk_mime_type.startswith("audio/"):
                raise RuntimeError("Gemini returned an invalid audio MIME type.")
            if mime_type is not None and chunk_mime_type != mime_type:
                raise RuntimeError("Gemini returned inconsistent audio MIME types.")
            mime_type = chunk_mime_type
            encoded = inline_data.get("data")
            if not isinstance(encoded, str):
                raise RuntimeError("Gemini returned invalid base64 audio.")
            try:
                chunk = base64.b64decode(encoded, validate=True)
            except (Base64Error, ValueError) as error:
                raise RuntimeError("Gemini returned invalid base64 audio.") from error
            if not chunk:
                raise RuntimeError("Gemini returned empty audio.")
            chunks.append(chunk)
        if not chunks or mime_type is None:
            raise RuntimeError("Gemini returned no audio.")
        return b"".join(chunks), mime_type

    def embed(
        self,
        texts: list[str],
        *,
        task_type: Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"] = "RETRIEVAL_DOCUMENT",
        titles: list[str] | None = None,
    ) -> list[list[float]]:
        """Embed up to 100 texts in order, using EMBEDDING_MODEL rather than LLM_MODEL."""
        if not texts or len(texts) > 100 or any(not text.strip() for text in texts):
            raise ValueError("Provide between 1 and 100 nonempty embedding texts.")
        if task_type not in ("RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"):
            raise ValueError("Unsupported embedding task_type.")
        if titles is not None and (
            task_type != "RETRIEVAL_DOCUMENT"
            or len(titles) != len(texts)
            or any(not title.strip() for title in titles)
        ):
            raise ValueError("titles must match document texts and cannot be used for queries.")
        model = self.embedding_model.strip().removeprefix("models/")
        if not model:
            raise ValueError("EMBEDDING_MODEL must not be empty.")
        requests = []
        for index, text in enumerate(texts):
            item = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
            }
            if titles is not None:
                item["title"] = titles[index]
            requests.append(item)
        result = self._request(
            model, "batchEmbedContents", json.dumps({"requests": requests}).encode("utf-8")
        )
        embeddings = result.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise RuntimeError("Gemini returned an unexpected number of embeddings.")
        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = embedding.get("values") if isinstance(embedding, dict) else None
            if not isinstance(values, list) or not values or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in values
            ):
                raise RuntimeError("Gemini returned an invalid embedding vector.")
            vector = [float(value) for value in values]
            if not any(vector) or (vectors and len(vector) != len(vectors[0])):
                raise RuntimeError("Gemini returned zero or inconsistent embedding vectors.")
            vectors.append(vector)
        return vectors

    def _generate_content(self, data: bytes) -> dict:
        return self._request(self.model, "generateContent", data)

    def _request(self, model: str, action: str, data: bytes) -> dict:
        request = Request(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(model, safe='')}:{action}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def list_models(self) -> list[str]:
        """List models supporting text generation for this API key."""
        models = []
        page_token = ""
        while True:
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            if page_token:
                url += "?" + urlencode({"pageToken": page_token})
            request = Request(url, headers={"x-goog-api-key": self.api_key})
            with urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
            models.extend(
                model["name"].removeprefix("models/")
                for model in result.get("models", [])
                if "generateContent" in model.get("supportedGenerationMethods", [])
            )
            page_token = result.get("nextPageToken", "")
            if not page_token:
                break
        if not models:
            raise RuntimeError("No text-generation models are available for this API key.")
        return models