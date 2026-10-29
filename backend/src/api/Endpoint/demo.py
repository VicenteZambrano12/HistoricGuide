import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Response
from qdrant_client import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from src.api.DataClass.demo import DemoFailureReason, DemoStatus
from src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant import qdrant_client
from src.utils.general.cloud import environment
from src.utils.general.GeminiApiCall import _configuration_value
from src.utils.logger import Logger


router = APIRouter(prefix="/demo", tags=["demo"])
logger = Logger(__name__)
STARTER_URL = "https://start-qdrant-vm-ksvn4nelea-no.a.run.app"


def unavailable(response: Response, reason: DemoFailureReason, *, retryable: bool) -> DemoStatus:
    """Build a noncacheable dependency failure with bounded retry guidance.

    Args:
        response (Response): Framework response whose status and headers are updated.
        reason (DemoFailureReason): Allowlisted public failure reason.
        retryable (bool): Whether the client should retry after five seconds.

    Returns:
        DemoStatus: A waiting or unavailable result accompanied by HTTP 503.

    Raises:
        pydantic.ValidationError: The supplied reason or retry flag is invalid.
    """
    response.status_code = 503
    response.headers["Cache-Control"] = "no-store"
    if retryable:
        response.headers["Retry-After"] = "5"
    return DemoStatus(
        status="waiting" if retryable else "unavailable", reason=reason, retryable=retryable,
    )


@router.post("/start", response_model=DemoStatus, responses={503: {"model": DemoStatus}})
def start_demo(response: Response) -> DemoStatus:
    """Request on-demand startup through the existing shared VM starter.

    **Permissions:** Public, matching the existing public starter. LOCAL mode
    performs no cloud calls. Repeated requests reuse the same VM; no resource
    is created and the shared idle-shutdown watchdog is not modified.

    Args:
        response (Response): Framework response used to set cache and retry headers.

    Returns:
        DemoStatus: Ready locally (200), starting remotely (202), or a sanitized
        failure with retry guidance (503).

    Raises:
        ValueError: Environment or shared configuration is invalid before startup.
        OSError: The local configuration file cannot be read.
    """
    response.headers["Cache-Control"] = "no-store"
    if environment() == "LOCAL":
        return DemoStatus(status="ready")
    try:
        request = Request(STARTER_URL, data=b"", method="POST")
        with urlopen(request, timeout=10) as upstream:
            data = json.load(upstream)
            code = upstream.status
        if not isinstance(data, dict):
            logger.error("Invalid VM starter response shape", extra={"event": "demo.start_invalid"})
            return unavailable(response, "startup_failed", retryable=False)
        if code == 200 and data.get("status") == "already_running":
            # A running VM does not establish that Qdrant or its collection is ready.
            response.status_code = 202
            return DemoStatus(status="starting", retryable=True)
        if code == 202 and data.get("status") in {
            "starting", "stopping", "suspending", "provisioning", "staging",
        }:
            response.status_code = 202
            return DemoStatus(status="starting", retryable=True)
        logger.error("Unexpected VM starter response", extra={"event": "demo.start_invalid"})
        return unavailable(response, "startup_failed", retryable=False)
    except HTTPError as error:
        # Concurrent callers of the shared starter can race between VM get/start.
        logger.warning(
            "VM starter request failed",
            extra={"event": "demo.start_failed", "status_code": error.code},
        )
        return unavailable(
            response, "startup_failed",
            retryable=error.code in {409, 429, 500, 502, 503, 504},
        )
    except (URLError, TimeoutError, OSError) as error:
        logger.warning("VM starter is unreachable", exc_info=error, extra={"event": "demo.start_failed"})
        return unavailable(response, "startup_failed", retryable=True)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        logger.error("Invalid VM starter response", exc_info=error, extra={"event": "demo.start_invalid"})
        return unavailable(response, "startup_failed", retryable=False)


@router.get("/ready", response_model=DemoStatus, responses={503: {"model": DemoStatus}})
def demo_readiness(response: Response) -> DemoStatus:
    """Check Qdrant and the configured collection without starting the VM.

    **Permissions:** Public. This bounded dependency check makes no Gemini calls.
    Clients must stop polling after readiness and must not use it as a heartbeat:
    the existing VM watchdog must remain able to shut down an idle demo.
    LOCAL mode retains the existing local-data behavior.

    Args:
        response (Response): Framework response used to set cache and retry headers.

    Returns:
        DemoStatus: Ready when collection metadata is compatible, otherwise a
        sanitized waiting/unavailable result with HTTP 503.

    Raises:
        ValueError: Environment or shared configuration is invalid before the check.
        OSError: The local configuration file cannot be read before the check.
    """
    response.headers["Cache-Control"] = "no-store"
    if environment() == "LOCAL":
        return DemoStatus(status="ready")
    try:
        collection = _configuration_value("QDRANT_COLLECTION", "historic_guide").strip()
        model = _configuration_value("EMBEDDING_MODEL", "gemini-embedding-001").strip().removeprefix("models/")
        if not collection or not model:
            raise ValueError("Missing collection or embedding model configuration.")
        remote = qdrant_client(timeout=3)
        try:
            info = remote.get_collection(collection)
            if not info.points_count:
                logger.warning("Demo collection is empty", extra={"event": "demo.collection_empty"})
                return unavailable(response, "collection_empty", retryable=False)
            vectors = info.config.params.vectors
            if not isinstance(vectors, models.VectorParams) or vectors.distance != models.Distance.COSINE:
                logger.warning("Incompatible demo vectors", extra={"event": "demo.collection_incompatible"})
                return unavailable(response, "collection_incompatible", retryable=False)
            # A bounded payload sample checks migration compatibility without embedding a query.
            records, _ = remote.scroll(collection, limit=1, with_payload=True, with_vectors=False)
            payload = records[0].payload if records else None
            if (
                not payload or payload.get("embedding_model") != model
                or payload.get("embedding_dimensions") != vectors.size
            ):
                logger.warning("Incompatible demo embeddings", extra={"event": "demo.collection_incompatible"})
                return unavailable(response, "collection_incompatible", retryable=False)
            return DemoStatus(status="ready")
        finally:
            remote.close()
    except UnexpectedResponse as error:
        logger.warning(
            "Qdrant readiness request failed",
            extra={"event": "demo.readiness_failed", "status_code": error.status_code},
        )
        if error.status_code == 404:
            return unavailable(response, "collection_missing", retryable=False)
        return unavailable(response, "unreachable", retryable=error.status_code >= 500 or error.status_code == 429)
    except (ResponseHandlingException, TimeoutError, OSError) as error:
        logger.warning("Qdrant is not reachable yet", exc_info=error, extra={"event": "demo.readiness_waiting"})
        return unavailable(response, "unreachable", retryable=True)
    except ValueError as error:
        logger.error("Invalid demo configuration", exc_info=error, extra={"event": "demo.configuration_invalid"})
        return unavailable(response, "configuration", retryable=False)
