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


def _json_configuration() -> dict[str, str]:
    """Parse the optional environment-injected application configuration object.

    Args:
        None.

    Returns:
        dict[str, str]: String-valued configuration, or an empty mapping when absent.

    Raises:
        ValueError: APP_SECRETS_JSON is malformed, empty, not an object, or contains
            non-string values.
    """
    raw = os.environ.get("APP_SECRETS_JSON")
    if raw is None:
        return {}
    try:
        configuration = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("APP_SECRETS_JSON must contain a valid JSON object.") from None
    if not isinstance(configuration, dict) or not configuration or any(
        not isinstance(value, str) for value in configuration.values()
    ):
        raise ValueError("APP_SECRETS_JSON must be a nonempty object of string values.")
    return configuration


def _configuration_value(name: str, default: str = "") -> str:
    """Resolve one setting without expanding references inside dotenv values.

    Args:
        name (str): Configuration key to resolve.
        default (str): Value used when the key is absent; defaults to an empty string.

    Returns:
        str: Value selected from process environment, injected JSON, root dotenv,
        then default, preserving explicitly configured empty values.

    Raises:
        ValueError: The injected JSON configuration is invalid.
        OSError: The dotenv file exists but cannot be read.
        UnicodeDecodeError: The dotenv file is not valid UTF-8.
    """
    value = os.environ.get(name)
    if value is not None:
        return value
    configuration = _json_configuration()
    if name in configuration:
        return configuration[name]
    if not ENV_FILE.exists():
        return default
    with ENV_FILE.open(encoding="utf-8") as stream:
        return dotenv_values(stream=stream, interpolate=False).get(name, default) or ""


@dataclass
class GeminiClient:
    """Call Gemini generation and embedding endpoints through bounded HTTP requests.

    Args:
        api_key (str): API credential; defaults to GEMINI_API_KEY from shared settings.
        model (str): Generation model; defaults to LLM_MODEL or "gemini-2.5-flash-lite".
        max_output_tokens (int): Positive generation limit; defaults to 256.
        timeout (float): Positive per-request timeout in seconds; defaults to 30.0.
        embedding_model (str): Embedding model; defaults to EMBEDDING_MODEL or
            "gemini-embedding-001" and is validated when embedding is requested.

    Returns:
        GeminiClient: Configured synchronous REST client.

    Raises:
        ValueError: Credentials, generation settings, or injected configuration are invalid.
        OSError: Shared configuration cannot be read.
    """

    # Credential values must not appear in the generated dataclass representation.
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
        """Normalize credentials and validate settings before the first API call.

        Args:
            None.

        Returns:
            None: Trimmed credentials and model names are stored on the instance.

        Raises:
            ValueError: The API key or model is blank, the model contains whitespace,
                or token/timeout limits are not positive.
        """
        self.api_key = self.api_key.strip()
        if not self.api_key:
            raise ValueError(
                "Set GEMINI_API_KEY in .env or the environment to your Google AI Studio API key."
            )
        self.model = self.model.strip()
        if not self.model:
            raise ValueError("model (LLM_MODEL) must not be empty.")
        if any(character.isspace() for character in self.model):
            raise ValueError(
                "model (LLM_MODEL) must be a model ID without whitespace, "
                "for example gemini-3.5-flash-lite. Check .env and the environment."
            )
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
        """Generate user-facing text from a prompt and optional inline audio.

        Args:
            prompt (str): Nonblank user instruction.
            system_prompt (str | None): Optional nonblank system instruction.
            response_mime_type (Literal["text/plain", "application/json"]): Output format;
                defaults to "text/plain".
            audio (bytes | None): Optional nonempty audio content; defaults to None.
            audio_mime_type (str | None): Required audio/* MIME type when audio is supplied.

        Returns:
            str: Concatenated non-thought text from the first generation candidate.

        Raises:
            ValueError: Inputs, MIME settings, or the inline-audio payload size are invalid.
            RuntimeError: No usable text is returned or audio processing is incomplete.
            urllib.error.URLError: The API rejects the request or the connection fails.
            OSError: Transport I/O fails or the request times out.
            json.JSONDecodeError: The API response is not valid JSON.
        """
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
        # Provider reasoning parts must not enter the user-facing answer.
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
        """Generate speech and validate a consistent, complete audio result.

        Args:
            text (str): Nonblank text to synthesize.
            voice (str): Nonblank provider voice identifier; defaults to "Kore".

        Returns:
            tuple[bytes, str]: Decoded provider audio and its declared audio MIME type.

        Raises:
            TypeError: Text or voice is not a string.
            ValueError: Text or voice is blank.
            RuntimeError: Generation is incomplete or audio chunks are missing,
                inconsistent, empty, or invalid base64.
            urllib.error.URLError: The API rejects the request or the connection fails.
            OSError: Transport I/O fails or the request times out.
            json.JSONDecodeError: The API response is not valid JSON.
        """
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
        # Validate every chunk before concatenation so mixed formats cannot masquerade as audio.
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
        """Embed a bounded text batch using the configured embedding model.

        Args:
            texts (list[str]): Between 1 and 100 nonblank texts in output order.
            task_type (Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]): Embedding role;
                defaults to "RETRIEVAL_DOCUMENT".
            titles (list[str] | None): Optional nonblank document titles matching texts;
                prohibited for query embeddings.

        Returns:
            list[list[float]]: Finite, nonzero, equally sized vectors in input order.

        Raises:
            ValueError: Batch size, text, titles, task type, or embedding model is invalid.
            RuntimeError: Response count or embedding vector contents are incompatible.
            urllib.error.URLError: The API rejects the request or the connection fails.
            OSError: Transport I/O fails or the request times out.
            json.JSONDecodeError: The API response is not valid JSON.
        """
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
        # Invalid or inconsistent vectors would silently corrupt downstream similarity scores.
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
        """Send serialized generation content to the configured language model.

        Args:
            data (bytes): UTF-8 encoded Gemini generation request JSON.

        Returns:
            dict: Decoded provider response expected to contain generation candidates.

        Raises:
            urllib.error.URLError: The API rejects the request or the connection fails.
            OSError: Transport I/O fails or the request times out.
            json.JSONDecodeError: The API response is not valid JSON.
        """
        return self._request(self.model, "generateContent", data)

    def _request(self, model: str, action: str, data: bytes) -> dict:
        """Execute an authenticated, timeout-bounded Gemini POST request.

        Args:
            model (str): Model identifier encoded as a single URL path component.
            action (str): Gemini operation name, such as generateContent.
            data (bytes): Serialized UTF-8 JSON request body.

        Returns:
            dict: Decoded JSON response expected by the caller.

        Raises:
            urllib.error.URLError: The API rejects the request or the connection fails.
            OSError: Transport I/O fails or the request times out.
            json.JSONDecodeError: The response body is not valid JSON.
            UnicodeDecodeError: The response uses an invalid JSON text encoding.
        """
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
        """Collect all accessible models that advertise content generation.

        Args:
            None.

        Returns:
            list[str]: Model identifiers without the models/ prefix.

        Raises:
            RuntimeError: No generation-capable models are returned.
            urllib.error.URLError: A page request is rejected or cannot connect.
            OSError: Transport I/O fails or a page request times out.
            json.JSONDecodeError: A model-list response is not valid JSON.
        """
        models = []
        page_token = ""
        # Capability discovery must cover every page, not only the provider's first batch.
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