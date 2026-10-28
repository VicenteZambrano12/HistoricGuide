"""Stream operational progress and a final answer over a single POST request."""

import base64
from collections.abc import Callable, Iterator
from contextvars import copy_context
import json
from queue import Queue
from threading import Event, Thread

from fastapi.responses import StreamingResponse

from src.utils.general.progress import ProgressStep, progress_reporting, report_progress
from src.utils.general.sources import collecting_sources
from src.utils.logger import Logger

logger = Logger(__name__)


def stream_chat(run: Callable[[], str | bytes], *, audio_output: bool) -> StreamingResponse:
    context = copy_context()

    def events() -> Iterator[str]:
        queue: Queue[dict[str, object]] = Queue()
        disconnected = Event()

        def progress(step: ProgressStep) -> None:
            if not disconnected.is_set():
                queue.put({"type": "progress", "step": step})

        def worker() -> None:
            try:
                with progress_reporting(progress), collecting_sources() as sources:
                    report_progress("starting")
                    result = run()
                if audio_output:
                    if not isinstance(result, bytes) or not result:
                        raise TypeError("The pipeline must return nonempty WAV bytes.")
                    event: dict[str, object] = {
                        "type": "result", "audio": base64.b64encode(result).decode("ascii"),
                        "mime_type": "audio/wav",
                    }
                else:
                    if not isinstance(result, str) or not result.strip():
                        raise TypeError("The pipeline must return nonempty text.")
                    event = {"type": "result", "text": result}
                if sources:
                    event["sources"] = [source.model_dump() for source in sources]
            except Exception:
                # Headers have already been sent; failures must be explicit stream events.
                logger.exception(
                    "Streaming chat pipeline failed", extra={"event": "chat.stream.failed"},
                )
                event = {"type": "error", "detail": "Guide processing failed. Please try again."}
            if not disconnected.is_set():
                queue.put(event)

        Thread(target=context.run, args=(worker,), daemon=True).start()
        try:
            while True:
                event = queue.get()
                yield json.dumps(event) + "\n"
                if event["type"] != "progress":
                    return
        finally:
            # An in-flight provider call may finish after the client disconnects.
            disconnected.set()

    return StreamingResponse(
        events(), media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
