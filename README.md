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

## Backend API

From the repository root:

```sh
cd backend
uv sync
uv run uvicorn src.app:app --reload
```

`GET http://127.0.0.1:8000/health` returns HTTP 200 with `{"status":"ok"}`.
This is a liveness check; it does not contact external services.
Interactive API documentation is available at `http://127.0.0.1:8000/docs`.
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

All modes execute the agent pipeline. `stt` transcribes audio and returns an
answer as JSON; `text` returns an answer as JSON without transcription.
Both return `{"text":"..."}`. `tts` generates an answer from text and returns
WAV audio; `full` accepts audio and returns WAV audio.
Uploaded files must declare an `audio/*` MIME type and contain at most
14,000,000 bytes. Invalid requests return HTTP 422; oversized audio returns 413.
Chat requires the `GEMINI_API_KEY` configuration described below.

```sh
curl http://127.0.0.1:8000/chat \
  -F 'query=Tell me about the Pantheon' \
  -F 'mode=text' -F 'language=EN' -F 'stop=Pantheon'

curl http://127.0.0.1:8000/chat \
  -F 'query=@recording.webm;type=audio/webm' \
  -F 'mode=full' -F 'language=ES' -F 'stop=Pantheon' \
  --output answer.wav
```

Run the endpoint tests from the backend directory:

```sh
uv run python -m unittest tests.test_chat tests.test_health
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

`STT` defaults to the low-cost `gemini-2.5-flash-lite` model, independently of
`LLM_MODEL`. It returns only transcription text in the original language.
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

# A future retriever can supply text chunks filtered by stop and category:
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
passing to `TTS`. With no context it uses Gemini's general knowledge; with context,
the prompt instructs it to ground factual claims in the supplied chunks.
Prompt instructions do not guarantee factual accuracy. No database retrieval
or metadata filtering is implemented yet: the caller must supply relevant chunks
for the requested stop and category.

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

# Optional chunks from a future retriever are passed through to generation:
answer = pipeline.run(
    "Pantheon",
    user_query="Describe the dome.",
    context=["The Pantheon's dome has an open central oculus."],
)
```

Supply exactly one of `user_query` or `param`, plus the stop. Text queries make
two Gemini calls: classification, then answer generation using the original query
and routed category. Explicit `historic` or `restaurant` parameters skip the
classification call and generate an introduction using the selected prompt.
The entire input, including optional context chunks, is validated before any
API call. Errors propagate without returning a route or fabricated answer.

The pipeline accepts existing components as
`AgentPipeline(orchestrator=..., response_generator=...)` for client overrides
or testing. Default components are independent per pipeline, and their Gemini
clients are created lazily and reused. The thin class lives under
`backend/src/systems/AgentSystem/AgentPipeline/`; its helper and Pydantic request
model live under `backend/src/utils/AgentSystem/AgentPipeline/`.
This is synchronous text-to-text processing only: no STT, TTS, database retrieval,
metadata filtering, or HTTP endpoint is added. The offline tests also cover the
complete routing-to-generation flow.

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
The agents classify the input text or transcript and generate the answer;
TTS speaks that answer, not the original query.

`Pipeline` accepts `agent_pipeline`, `stt`, and `tts` components for injection.
Default speech components are created only when needed and reused, so text-only
mode does not initialize speech clients. The thin class lives in
`backend/src/systems/Pipeline.py`; helper functions and Pydantic validation live
under `backend/src/utils/Pipeline/`. Invalid requests and stage failures raise
exceptions, stopping subsequent stages. The offline tests cover all four modes,
including complete flows using mocked Gemini HTTP responses.