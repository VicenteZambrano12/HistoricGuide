# vicentezambrano12.github.io

## Generate the PDF corpus

From the repository root, install the PDF generator's dependencies with
[uv](https://docs.astral.sh/uv/):

```sh
uv sync --script database/scripts/doc_generation.py
```

Run the generator:

```sh
uv run database/scripts/doc_generation.py
```

The script declares its own `reportlab` and `pypdf` dependencies, which `uv run`
also installs automatically if needed. It writes PDFs to `rag_corpus/` and
`public/rag_corpus/`, relative to the current working directory, and prints a
page-count verification table.

## Provisional RAG database

Place PDFs under `database/docs/<stop>/<type>/*.pdf`, then run from the repository
root:

```sh
uv run database/scripts/provisional_db_gen.py
```

Set `GEMINI_API_KEY` and `EMBEDDING_MODEL` in the root `.env` or environment.
The embedding model defaults to `gemini-embedding-001`; it is independent of
`LLM_MODEL`. The builder uses the existing `GeminiClient`, batches requests with
the `RETRIEVAL_DOCUMENT` task, and sends chunk text plus stop/type context to
Gemini. API errors are surfaced, never replaced with fake vectors.
Rate limits (HTTP 429) and temporary server errors receive up to three logged
retries with exponential waits of at least 60, 120, and 240 seconds. Numeric
`Retry-After` headers are respected; waits over 600 seconds fail explicitly.
Unavailable models (HTTP 404) are not retried. If your configuration still uses
the unavailable `text-embedding-004`, override it for a build without editing
`.env`:

```sh
EMBEDDING_MODEL=gemini-embedding-001 uv run database/scripts/provisional_db_gen.py
```

`ChunkGen` uses layout-aware PDF extraction to retain table rows, strips
repeated page-edge headers/footers and page numbers, preserves
Unicode, and prefers paragraph, line, sentence, then word boundaries. Defaults
are at most 400 tokens with up to 60 tokens of word-aligned overlap. Chunks never
cross PDF or page boundaries, preserving citations and page-level sections.
Token counts use local `cl100k_base`, an approximation rather than Gemini's
tokenizer; these conservative sizes leave room for metadata. Very long words
are split at character boundaries. Scanned/empty pages require OCR and fail
explicitly rather than disappearing from the corpus. The tokenizer data is
downloaded on first use.

The output is `database/provisional_db/chunks.sqlite3`. The `chunks` table stores
text, `stop` and `type` (exact folder names, including `restaurants`), relative
source path, 1-based page, 0-based per-document chunk index, token count, stable
SHA-256 ID, embedding model, dimensions, and a JSON float-array `embedding`.
An index supports filtering by `(stop, type)`; `build_info` records the model,
chunking settings, corpus counts, and creation time. This is ordinary SQLite,
not a vector-search extension. For retrieval, decode vectors with `json.loads`,
embed queries with the same model and `task_type="RETRIEVAL_QUERY"`, and compare
using cosine similarity after filtering by stop/type.

Re-running rebuilds the entire snapshot (including removal of deleted sources)
and atomically replaces the old file only after all embeddings and integrity
checks succeed. Close readers before rebuilding to use the new snapshot.
Generated databases are ignored by Git.

Optional settings:

```sh
uv run database/scripts/provisional_db_gen.py \
  --docs-dir database/docs \
  --output database/provisional_db/chunks.sqlite3 \
  --max-tokens 400 --overlap-tokens 60 --batch-size 32
```

Run the offline database and embedding-client tests (no API requests):

```sh
uv run --script database/scripts/provisional_db_gen.py --help
uv run --with pypdf --with tiktoken --with python-dotenv \
  python -m unittest discover -s database/tests
```

## Migrate the snapshot to Qdrant

The migration script copies the existing SQLite embeddings without calling
Gemini, rebuilding the corpus, or modifying the source database:

```sh
uv run scripts/migrate_to_qdrant.py --dry-run
uv run scripts/migrate_to_qdrant.py --url http://127.0.0.1:6333
```

The URL must reach Qdrant on the existing Compute Engine VM (`qdrant-vm`;
Terraform module name `qdrant_vm`). For a private VM, establish an authorized
tunnel first and use its localhost URL. The script does not create, start,
reconfigure, or expose the VM. Do not expose port 6333 publicly for migration.
Infrastructure and IAM setup are separate steps.

Alternatively set `QDRANT_URL`; if Qdrant requires authentication, supply
`QDRANT_API_KEY` through the environment, not a command-line argument.
Neither Google service-account JSON keys nor a Gemini API key are needed by
the migration script itself. Network/tunnel access may require Google credentials.
The script does not load `.env` automatically.

The default collection is **`historic_guide`**, using unnamed cosine vectors
with the dimensions stored in SQLite. Each chunk has top-level payload fields
`stop_id` (the existing API key, e.g. `Torre_Argentina`) and `type` (unchanged:
`historic` or `restaurants`), both with keyword indexes. Payloads also preserve
`stop`, text, original chunk ID, source PDF path, page, chunk index, token count,
embedding model and dimensions, so citations and model compatibility remain
available. Use the same embedding model with `RETRIEVAL_QUERY` for queries.

The script validates the entire snapshot before contacting Qdrant, uploads
batches with deterministic UUIDs, waits for completion, reads back every point
to verify its payload and cosine-normalized vector, then checks the exact
collection count. Reruns safely resume a partial upload of the **same snapshot**
without duplicates. An incompatible collection or any unrelated/changed payload
is rejected before writes; no collection or point is deleted, and the basic RAG
app's other collections are untouched. Do not run concurrent writers against
this dedicated collection during migration. Failures exit nonzero and may leave
completed batches in place; rerun after resolving the error.

Optional arguments: `--database PATH`, `--collection NAME`, `--batch-size 32`.
`--dry-run` validates locally only. This step does not switch backend retrieval
from SQLite to Qdrant or deploy any infrastructure.

Run the offline migration tests (in-memory Qdrant, no cloud/API calls):

```sh
uv run --with 'qdrant-client>=1.12,<2' \
  python -m unittest discover -s scripts/tests -p test_migrate_to_qdrant.py
```

## Migrate documents and prompts to Cloud Storage

Preview the upload plan without credentials or cloud requests:

```sh
uv run scripts/migrate_bucket.py --dry-run
```

The script targets the existing bucket `historic-guide` and preserves relative
paths: PDFs from `database/docs/` become `docs/<stop>/<type>/<filename>.pdf`;
YAML files from `backend/src/config/prompts/` become `prompts/<filename>.yaml`.
Only PDF and YAML files are included; empty sources/files and symlinks fail
explicitly. The current corpus contains 10 PDFs and 3 prompts.

When upload is approved and the bucket exists:

```sh
uv run scripts/migrate_bucket.py --bucket historic-guide
```

Authentication uses Application Default Credentials, including
`GOOGLE_APPLICATION_CREDENTIALS` when set. Alternatively pass
`--credentials /path/to/local-service-account-key.json` for the
`historicguide@basicrahgapp.iam.gserviceaccount.com` account. Never commit or
print the JSON key. Active `gcloud` CLI login alone does not necessarily
provide Application Default Credentials for the Python client.

The account needs bucket/object read access and object create/update access
(for example, bucket-scoped `roles/storage.objectUser` plus
`storage.buckets.get`). Grant only the required access in a separately approved
permissions step. The script does not create buckets, modify IAM, or change
Terraform; bucket provisioning/configuration remains Terraform-only.
The existing Terraform storage example names a different bucket,
`basicrahgapp-rag-data`; this script does not rename or reconfigure it.

Uploads verify CRC32C checksums, byte sizes and content types. Identical objects
are skipped; changed objects at the same path are updated using generation
preconditions to prevent overwriting concurrent changes. Unrelated or deleted
local files are never deleted remotely. Failures exit nonzero; completed
uploads remain and rerunning resumes safely. This is not an atomic multi-file
deployment; do not modify sources during migration.

Optional arguments: `--project` (default `basicrahgapp`), `--docs-dir`,
`--prompts-dir`, `--bucket`, `--credentials`, and `--dry-run`.
This script does not switch the backend to Cloud Storage.

Run the offline bucket tests (mocked storage, no cloud access):

```sh
uv run --with 'google-cloud-storage>=3,<4' --with 'google-crc32c>=1.5,<2' \
  python -m unittest discover -s scripts/tests -p test_migrate_bucket.py
```

## Backend API

### Local or GCP data sources

Set `ENV=LOCAL` or `ENV=GCP` in the root `.env` or process environment,
then restart the backend. Process environment values take precedence. If `ENV`
is absent, `LOCAL` preserves the previous behavior. Other values fail explicitly.

| Mode | Prompts | Retrieval | Source PDFs |
| --- | --- | --- | --- |
| `LOCAL` | Local YAML files | Existing SQLite snapshot | Local document corpus |
| `GCP` | `gs://historic-guide/prompts/` | Qdrant `historic_guide` | `gs://historic-guide/docs/` |

Example GCP settings for running on your laptop through the private VM tunnel:

```dotenv
ENV=GCP
GCS_BUCKET=historic-guide
GOOGLE_CLOUD_PROJECT=basicrahgapp
GOOGLE_APPLICATION_CREDENTIALS=config/your-service-account-key.json
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=historic_guide
EMBEDDING_MODEL=gemini-embedding-001
```

`QDRANT_URL`, when provided, takes precedence over `QDRANT_HOST`/`QDRANT_PORT`.
`QDRANT_API_KEY` is optional if the instance requires authentication.
On GCP, use the VM's reachable **private address** instead of `localhost`;
localhost is valid on your laptop only while the SSH/IAP tunnel is active.
The backend does not open tunnels or start the VM.

For the existing `qdrant-vm`, once it is running, open a separate terminal:

```sh
gcloud compute start-iap-tunnel qdrant-vm 6333 \
  --project=basicrahgapp --zone=europe-southwest1-a \
  --local-host-port=localhost:6333
```

Keep the tunnel open while using the backend. The tunnel uses your authorized
gcloud identity, not the backend's JSON key. It requires IAP tunnel access and
Compute instance discovery permissions; Qdrant authentication still uses
`QDRANT_API_KEY`. A stopped VM cannot serve requests through this tunnel.
Starting or reconfiguring infrastructure remains a separate Terraform task.

Use the existing service-account key only for local development; relative
credential paths resolve from the repository root, not the current directory.
On GCP omit `GOOGLE_APPLICATION_CREDENTIALS` and use the attached runtime
service account through Application Default Credentials, with bucket read
permissions and private network access to Qdrant. Never commit a key.
`GEMINI_API_KEY` and the existing model settings are still required.

The runtime service account `historicguide@basicrahgapp.iam.gserviceaccount.com`
only needs `roles/storage.objectViewer` on `historic-guide`, conditioned on
objects under `docs/` and `prompts/`. It does not need project-wide Storage
roles, bucket administration, object writes, or service-account token creation:
PDFs are proxied by the backend, not exposed through signed URLs. Migration
writes require separately authorized permissions; runtime read access is not
sufficient to rerun the bucket migration.

GCP mode retains stop/type filtering, the top two cosine matches, model/dimension
validation, PDF citations, inline PDF responses and HTTP byte-range support.
Prompts use the same YAML/Pydantic validation. Cloud failures propagate and
never silently fall back to local data. The Qdrant collection must already have
been migrated; selecting GCP does not populate it. No infrastructure is changed.

Offline regression tests (no cloud or Gemini requests):

```sh
ENV=LOCAL uv run --project backend --locked \
  python -m unittest discover -s backend/tests
```

From the repository root:

```sh
uv sync --project backend --locked
uv run --project backend --locked uvicorn src.app:app --app-dir backend --reload
```

No virtual environment activation is needed: `uv` uses `backend/.venv`.
If the repository-root `.venv` is already active, run `deactivate` first to
avoid the environment-mismatch warning. That warning is separate from import
errors.

Use `src.app:app` with `--app-dir backend`, not `app:app` with
`--app-dir backend/src`: the backend imports modules through the `src` package,
so its parent directory must be on the Python import path.
Alternatively, from inside `backend`, run
`uv run --locked uvicorn src.app:app --reload`.

### Backend logging

The shared `Logger` in `backend/src/utils/logger/Logger.py` uses standard Python
logging and configures one application-only stdout handler at startup. JSON is
the default, suitable for Cloud Run/Cloud Logging. Set process environment
variables `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL` (default `INFO`) and
`LOG_FORMAT=json|text` (default `json`); invalid values fail startup.
Root and third-party handlers are not changed. For a single application access
log without Uvicorn's additional access line, add `--no-access-log` to its command.
Uvicorn still owns server/process diagnostics.

Logs include UTC timestamps, severity, event names, and request IDs. Requests
record method, route template, status, and elapsed milliseconds, including stream
delivery time; 4xx responses use WARNING and 5xx/failures use ERROR. Unmatched URLs
are recorded as `<unmatched>`, not raw paths. Send a UUID in `X-Request-ID` to
reuse it, or let the server generate one; responses return that header, including
500 errors. Context is preserved through sync handlers and streaming workers,
then reset between requests. A streamed processing failure emits a separate
`chat.stream.failed` error even though its HTTP headers already report 200.
Pipeline start/completion events use INFO and operational stages use DEBUG.

Use `Logger(__name__)` and standard `info`, `debug`, or `exception` methods;
pass operational metadata through `extra`. Only the documented operational
fields are serialized. Never put secrets, prompts, questions, generated text,
audio, or document content in log messages. Exception logs include their type
and stack frame locations, but omit exception messages, source lines, and local
variables because provider errors can contain credentials or user data.

`GET http://127.0.0.1:8000/health` returns HTTP 200 with `{"status":"ok"}`.
This is a liveness check; it does not contact external services.
Interactive API documentation is available at `http://127.0.0.1:8000/docs`.
ReDoc is available at `http://127.0.0.1:8000/redoc`, and the machine-readable
OpenAPI schema at `http://127.0.0.1:8000/openapi.json`. Documentation includes
request examples, JSON and WAV response formats, and applicable error responses.
The current endpoints require no client authentication. `GEMINI_API_KEY` is
server-side configuration, not a client credential.
HTTP errors use a JSON `detail` string; automatic request validation uses a
`detail` array of validation issues. Unhandled server failures return HTTP 500
with plain text `Internal Server Error` in the default non-debug configuration.
The route lives in `backend/src/api/Endpoint/health.py`, with its Pydantic
response model in `backend/src/api/DataClass/health.py`.

Run the health-check tests from the backend directory:

```sh
uv run python -m unittest tests.test_health
```

### Chat

`POST /chat` accepts multipart form fields:

| Field | Values |
| --- | --- |
| `query` | Text for `text`/`tts`, or an audio file for `stt`/`full` |
| `mode` | `stt`, `tts`, `full`, `text` |
| `language` | `ES` or `EN` (answer language) |
| `stop` | Nonempty tour stop, such as `Pantheon` |
| `request_type` | Optional `historic` or `restaurant`; omitted uses automatic topic classification |
| `stream` | Optional boolean, default `false`; `true` streams progress and the answer as NDJSON |

All modes execute the agent pipeline. `stt` transcribes audio and returns an
answer as JSON; `text` returns an answer as JSON without transcription.
Both return `{"text":"..."}`. `tts` generates an answer from text and returns
WAV audio; `full` accepts audio and returns WAV audio.
With `stream=true`, all modes instead return `application/x-ndjson`. Each line
is a JSON event: `{"type":"progress","step":"routing"}`, followed eventually
by `{"type":"result","text":"..."}` or, for audio output,
`{"type":"result","audio":"<base64 WAV>","mime_type":"audio/wav"}`.
Progress steps are `starting`, `transcribing`, `routing`, `retrieving`,
`generating`, and `synthesizing`; only stages actually executed are emitted.
These are operational status updates, not internal model reasoning.
Input validation still returns the usual HTTP error before streaming begins.
A failure after streaming starts is logged server-side and emits a terminal
`{"type":"error","detail":"..."}` event instead of a result. Proxies must not
buffer this response. Client cancellation does not stop an in-flight provider call.
Uploaded files must declare an `audio/*` MIME type and contain at most
14,000,000 bytes. Invalid requests return HTTP 422; oversized audio returns 413.
Chat requires the `GEMINI_API_KEY` configuration described below.
Set `LLM_MODEL` to a model ID such as `gemini-3.5-flash-lite`, with no
embedded whitespace or pasted log output. A malformed value can cause Gemini
HTTP 400 (`GenerateContentRequest.model: unexpected model name format`).
For the existing RAG snapshot, set `EMBEDDING_MODEL=gemini-embedding-001`
in the root `.env` and restart the backend after changing configuration.
The model must match `build_info.embedding_model` in the database; a mismatch
fails before the query embedding request. An environment variable overrides
the `.env` value, so update or unset any conflicting `EMBEDDING_MODEL` export.
The frontend uses `language=EN`. Suggested questions send `request_type`;
freeform text and voice messages let the backend classify the topic.
Use the corpus stop keys for retrieval: `Torre_Argentina`, `Forum_Boarium`,
`Roman_Forum`, `Trajans_Markets`, or `Pantheon`.

```sh
curl http://127.0.0.1:8000/chat \
  -F 'query=Tell me about the Pantheon' \
  -F 'mode=text' -F 'language=EN' -F 'stop=Pantheon' \
  -F 'request_type=historic'

curl http://127.0.0.1:8000/chat \
  -F 'query=@recording.webm;type=audio/webm' \
  -F 'mode=full' -F 'language=ES' -F 'stop=Pantheon' \
  -F 'request_type=restaurant' \
  --output answer.wav
```

Run the endpoint tests from the backend directory:

```sh
uv run python -m unittest tests.test_chat tests.test_health tests.test_openapi
```

## Speech to text (Gemini)

Install backend dependencies with [uv](https://docs.astral.sh/uv/):

```sh
cd backend
uv sync
```

Set `GEMINI_API_KEY` in the repository-root `.env` file or environment to your
Google AI Studio API key. Do not commit your key.

From the backend directory:

```sh
uv run python -c 'from src.systems.STT.STT import STT; print(STT().transcribe("recording.wav"))'
```

```python
from src.systems.STT.STT import STT

stt = STT()
text = stt.transcribe("recording.mp3")
# For in-memory audio, specify its actual encoding:
text = stt.transcribe(audio_bytes, mime_type="audio/webm")
```

`STT` defaults to the low-cost `gemini-3.5-flash-lite` model, independently of
`LLM_MODEL`. It returns only transcription text in the original language.
The older `gemini-2.5-flash-lite` can return HTTP 404 for new users even when
it appears in the model listing. Restart the backend after updating the code.
To override the key, model, or output limit, pass an existing `GeminiClient`
as `STT(client=GeminiClient(...))`.
Inline requests must be smaller than 20 MB including base64 encoding and prompts
(roughly under 15 MB of raw audio). API/network errors, blocked or empty
responses, and truncated transcriptions raise exceptions instead of returning
partial or fabricated text. This is batch transcription, not streaming STT.

`STT` is a thin public wrapper. Its implementation lives in
`backend/src/systems/STT/utils/`, with one function per file:
`create_client.py` for client defaults, `prepare_audio.py` for audio loading and
MIME detection, and `transcribe.py` for the transcription request.

Run the offline tests without an API key:

```sh
uv run python -m unittest discover -s tests
```

## Text to speech (Gemini)

`TTS` uses the same backend installation and `GEMINI_API_KEY` configuration as
`STT`. From the backend directory:

```python
from pathlib import Path
from src.systems.TTS.TTS import TTS

tts = TTS()
audio = tts.synthesize("Welcome to Rome.", voice="Kore")
Path("guide.wav").write_bytes(audio)
```

`synthesize()` returns mono, 16-bit WAV bytes, ready to save or serve as
`audio/wav`. The default model is `gemini-2.5-flash-preview-tts`, independently
of `LLM_MODEL`; the default voice is `Kore`. Pass
`TTS(client=GeminiClient(...))` to override the model, key, timeout, or output
limit. The model must support Gemini audio generation.

Like `STT`, `TTS` is a thin public wrapper with one function per helper file in
`backend/src/systems/TTS/utils/`: `create_client.py` for defaults,
`synthesize.py` for synthesis, and `prepare_audio.py` for PCM-to-WAV conversion.
This is batch synthesis, not streaming or local playback. Empty input, blocked
or truncated responses, invalid audio, and API/network failures raise
exceptions. The offline test command above covers both speech systems.

## Request routing (Gemini)

After installing the backend dependencies with `uv sync`, use the orchestrator
from the backend directory:

```python
from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator

orchestrator = Orchestrator()
route = orchestrator.route("Pantheon", user_query="Where can I get coffee?")
# route.model_dump(): {"category": "restaurant", "stop": "Pantheon"}

route = orchestrator.route("Pantheon", param="historic")
# Direct routing: no Gemini request or API key required.
```

Supply a nonempty string stop and exactly one of `user_query` or `param`.
An explicit parameter must be exactly `historic` or `restaurant`. Queries use
the existing `GeminiClient` and its `GEMINI_API_KEY` / `LLM_MODEL` configuration;
pass `Orchestrator(client=GeminiClient(...))` to override the client.
The classification prompt lives in
`backend/src/config/prompts/orchestrator.yaml`. Pydantic validates the request,
the model's single-word classification, and the returned `Route`.

`Orchestrator` is a thin public wrapper. Each helper has its own file in
`backend/src/utils/AgentSystem/Orchestrator/`: `route.py` coordinates
routing, `load_prompt.py` loads the YAML prompt, and `classify_query.py` calls
Gemini and validates its label. Each Pydantic model has its own file in the
`dataclasses/` subfolder; shared field types live in `dataclasses/types.py`.

The orchestrator returns only a routing destination, not an answer or generated
guide content. It preserves the supplied stop (apart from surrounding whitespace)
and does not advance the tour or invoke downstream agents. Request validation,
invalid labels, prompt configuration errors, and API failures raise exceptions
instead of silently selecting a destination. The offline test command above also
covers routing without making live API calls.

## Response generation (Gemini)

`ResponseGenerator` uses the same backend dependencies and API-key configuration.
Pass the orchestrator's destination and, optionally, the original query:

```python
from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator

query = "What is special about this dome?"
route = Orchestrator().route("Pantheon", user_query=query)
generator = ResponseGenerator()
answer = generator.generate(**route.model_dump(), user_query=query)

# Explicit categories also work, with or without a query:
answer = generator.generate("Pantheon", "restaurant")

# Optional caller-supplied context is supplemented with two database matches:
answer = generator.generate(
    "Pantheon",
    "historic",
    user_query=query,
    context=["The Pantheon's dome has an open central oculus."],
)
```

The generator selects `backend/src/config/prompts/historic.yaml` or
`backend/src/config/prompts/restaurant.yaml` using the validated category
(`historic` or `restaurant`). It returns only the answer string, suitable for
passing to `TTS`. Before generating, it retrieves the two most similar chunks
from `database/provisional_db/chunks.sqlite3`, filtering by the exact stop folder
name and type (`historic`, or `restaurants` for category `restaurant`). Queries
use `RETRIEVAL_QUERY` embeddings and cosine similarity, not a text search.
When no query is provided, a category-specific introduction is embedded instead.
If only one chunk matches, that chunk is used; no matches raise an error.
Retrieved chunks are appended to optional caller-supplied context without
modifying the caller's list. Both prompts instruct Gemini to ground factual
claims in this context; prompt instructions do not guarantee factual accuracy.

Build the provisional database before using response generation or `/chat`.
The backend's `EMBEDDING_MODEL` must match the database model and dimensions.
Missing databases, missing stop/type matches, corrupt or incompatible vectors,
and embedding API failures propagate instead of silently generating an
ungrounded answer. The default database path is repository-relative regardless
of the working directory. Override it with
`ResponseGenerator(database_path=Path("/path/to/chunks.sqlite3"))`
after importing `Path` from `pathlib`. Each retrieval opens and closes a
read-only connection so subsequent requests can read a rebuilt snapshot.
The SQLite retrieval helper is separate from response generation; a future
Qdrant implementation can preserve the stop/type filters and top-two behavior
without changing the public generation API.

The public class stays under `backend/src/systems/AgentSystem/ResponseGenerator/`.
Helpers live in `backend/src/utils/AgentSystem/ResponseGenerator/`, one function
per file, with one Pydantic model per file in its `dataclasses/` subfolder.
Request fields reuse the orchestrator's route and text validation.
The default Gemini client is created lazily, reused, and allows 1024 output
tokens. Pass `ResponseGenerator(client=GeminiClient(...))` to override it.
Invalid requests, missing or invalid prompts, empty or blocked responses, and
API/network errors raise exceptions. The offline test command above also covers
response generation without live API calls.

### Response language

`ResponseGenerator.generate()`, `AgentPipeline.run()`, and `Pipeline.run()` accept
`language="en"` (English, the default) or `language="es"` (Spanish). Other values
raise a validation error before any API call or speech stage runs. Both category
prompts instruct Gemini to use the selected language regardless of the query or
context language; this replaces automatic response-language detection.

```python
from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.systems.Pipeline import Pipeline

generator = ResponseGenerator()
answer = generator.generate("Pantheon", "historic", language="es")
answer = AgentPipeline().run("Pantheon", user_query="Explain the dome.", language="es")
audio = Pipeline().run(
    "Explain the dome.", "TTS", stop="Pantheon", language="es"
)
```

STT continues to transcribe the original language. Language selection applies to
the generated answer; when TTS is enabled, it speaks that answer without an
additional translation step.

## Text-to-text agent pipeline

`AgentPipeline` connects the orchestrator to the response generator and returns
only the final answer text:

```python
from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline

pipeline = AgentPipeline()
answer = pipeline.run("Pantheon", user_query="What is special about this dome?")
answer = pipeline.run("Pantheon", param="restaurant")

# Optional extra context is passed through alongside database retrieval:
answer = pipeline.run(
    "Pantheon",
    user_query="Describe the dome.",
    context=["The Pantheon's dome has an open central oculus."],
)
```

Supply `user_query`, `param`, or both, plus the stop. Text queries without a topic make
three Gemini calls: classification, query embedding for filtered top-two
retrieval, then answer generation using the original query and routed category.
Explicit `historic` or `restaurant` parameters skip the classification call
and generate using the selected prompt. If a question is also supplied, it is
preserved for retrieval and generation; otherwise retrieval uses an introduction
query. The standalone orchestrator still requires exactly one routing input.
The entire input, including optional context chunks, is validated before any
API call. Errors propagate without returning a route or fabricated answer.

The pipeline accepts existing components as
`AgentPipeline(orchestrator=..., response_generator=...)` for client overrides
or testing. Default components are independent per pipeline, and their Gemini
clients are created lazily and reused. The thin class lives under
`backend/src/systems/AgentSystem/AgentPipeline/`; its helper and Pydantic request
model live under `backend/src/utils/AgentSystem/AgentPipeline/`.
This is synchronous text-to-text processing with database retrieval and metadata
filtering; speech stages and HTTP serving are separate wrappers. The offline
tests also cover retrieval ranking/filtering and the routing-to-generation flow.

## Audio and text pipeline

`Pipeline` always runs `AgentPipeline`, optionally adding speech input or output:

| Mode | Input | Stages | Output |
| --- | --- | --- | --- |
| `STT` | Audio | STT → agents | Answer text |
| `TTS` | Text | Agents → TTS | WAV bytes |
| `full` | Audio | STT → agents → TTS | WAV bytes |
| `only text` | Text | Agents | Answer text |

From the backend directory:

```python
from pathlib import Path
from src.systems.Pipeline import Pipeline

pipeline = Pipeline()
answer = pipeline.run("Tell me about the dome.", "only text", stop="Pantheon")
answer = pipeline.run("recording.wav", "STT", stop="Pantheon")
audio = pipeline.run("Where can I get coffee?", "TTS", stop="Pantheon", voice="Kore")
audio = pipeline.run(
    recording_bytes, "full", stop="Pantheon", mime_type="audio/webm"
)
Path("answer.wav").write_bytes(audio)
```

The mode is required and uses the exact spelling shown above. `STT` and `full`
accept audio bytes or a file path (`str` or `Path`); raw bytes require an explicit
audio MIME type. `TTS` and `only text` accept nonempty text, not audio bytes or
`Path` objects. A string in an audio-input mode is a file path, never query text.
The stop is required in every mode. Optional `context` chunks are passed through
to the agents, and `voice` selects the output voice when TTS is enabled.
Optional `request_type="historic"` or `request_type="restaurant"` selects a topic
without classification and preserves the input question or transcript.
Otherwise the agents classify the input text or transcript and generate the answer;
TTS speaks that answer, not the original query.

`Pipeline` accepts `agent_pipeline`, `stt`, and `tts` components for injection.
Default speech components are created only when needed and reused, so text-only
mode does not initialize speech clients. The thin class lives in
`backend/src/systems/Pipeline.py`; helper functions and Pydantic validation live
under `backend/src/utils/Pipeline/`. Invalid requests and stage failures raise
exceptions, stopping subsequent stages. The offline tests cover all four modes,
including complete flows using mocked Gemini HTTP responses.