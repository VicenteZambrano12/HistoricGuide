# Plinius frontend

Plinius uses `public/logo.jpeg` for the navbar logo and browser tab icon.

## Appearance

The app opens directly to the live tour, without page-switching tabs.
Use the **Light mode / Dark mode** button in the navbar to
switch themes. Dark mode is the default. The Roman walking-atlas design uses
slate-blue surfaces, river-blue controls, and bronze route lines; light mode
uses limestone-white surfaces with darker blue controls.
Marcellus landmark headings and DM Sans interface text load from Google Fonts,
with local serif and sans-serif fallbacks when unavailable.
The current landmark's architectural illustration heads the tour, followed by
a five-stop route, illustrated map, guide conversation, and PDF sources.
On small screens the route scrolls horizontally, the content stacks, and map
pins use numbers corresponding to the route instead of tiny place labels.
Map pins support Enter and Space, the current stop is announced, and a
keyboard skip link leads directly to the tour. Motion respects reduced-motion
preferences; new chat messages scroll only the transcript, not the whole page.
The choice is saved in browser local storage and restored before the app renders.
If storage is blocked, switching still works for the current visit and a warning
is logged in the browser console.

## Language

English is the default. Use the **EN / ES** button in the navbar to switch
between English and Spanish. The choice is saved in browser local storage;
if storage is blocked, switching still works for the current visit and logs a warning.
Interface translations, stop labels, and suggested questions live in
[`src/i18n/en.json`](src/i18n/en.json) and [`src/i18n/es.json`](src/i18n/es.json).
Keep both dictionaries' keys and interpolation placeholders in sync.

Switching updates the page language, backend answer language, and browser
narration voice. Switching cancels pending chat and recording and stops audio
playback without resetting the tour. Existing user messages and backend
answers stay in their original language; new requests use the selected language.

Tour action buttons, map pins, source links, and audio controls are locked while
a chat request, simulated walk, or voice recording is in progress, preventing
another tour action before the current one finishes. The navbar's language,
theme, narration, and restart buttons always remain enabled. Restart cancels the
current request, walk, and recording; changing language cancels chat and
recording. During recording, **Stop and send** also remains enabled. Action
controls unlock on completion or failure; audio playback itself does not hold
the lock. Background document preparation does not block the first action:
chat, arrival, and suggested questions wait for readiness inside their request.

## Running with the backend

Start the API in a separate terminal from the repository root:

```sh
uv run --project backend --locked uvicorn src.app:app --app-dir backend --reload
```

No virtual environment activation is needed. If the root `.venv` is active,
run `deactivate` first; `uv` uses `backend/.venv`.

Then start the frontend from the repository root:

```sh
cd frontend
npm install
npm run dev
```

On app load, the frontend requests `/api/health` in the background without
displaying a status bar. Vite proxies `/api/*` to `http://127.0.0.1:8000/*`, so
`/api/health` reaches the backend's `GET /health` without requiring CORS.
The check times out after five seconds; HTTP, network, and unexpected-response
errors are logged to the browser console. Reload the page to check again.

Availability only confirms API liveness, not chat or external-service readiness.
Walking and GPS remain simulated.

The tour also prepares its document service through same-origin
`GET /api/demo/ready` and `POST /api/demo/start`. In GCP mode the backend reuses the
existing public Qdrant VM starter. The guide panel shows a translated startup or
failure message and retry button. Message, microphone, arrival, and suggested
question controls are available immediately; submitted requests wait for
readiness before contacting chat. Preparation stops after three minutes and
never continues polling after success. Each new chat rechecks readiness to handle
the shared VM shutting down while the page is idle. No background heartbeat or
new infrastructure is introduced, preserving its existing idle shutdown.
In LOCAL mode these endpoints are immediately ready without cloud access.
Collection/configuration errors are shown rather than silently sending chat.

The map scales to show all five stops and explicitly labels the walk and
position as simulated. It is an illustrated route, not street navigation.
The current-stop panel sits below the
map rather than covering the route or labels. Press **I arrived** when you
reach a stop to request its introduction.

For production, configure the web server to proxy `/api/*` to the backend,
stripping the `/api` prefix. Vite's development proxy is not part of the build.

Run `npm test` for health-client tests, `npm run build` for the production build,
and `npm run lint` for lint checks.

## Client logging and error tracking

[`src/lib/logger.js`](src/lib/logger.js) is the only application console sink.
Use `logger.debug(event, context)`, `info`, `warn`, or `error`, with stable event
names such as `http.request_failed` and structured metadata. Each record includes
an ISO timestamp, uppercase level, event, and context. Vite production builds
suppress DEBUG and INFO before serializing metadata; WARN and ERROR remain in
the browser console. Nothing is sent to an external tracking service.
ESLint rejects direct console calls outside the logger and tests.

The logger serializes error names, messages, stacks, and causes, limits nested
metadata, and redacts sensitive keys (including bodies, queries, credentials,
tokens, and audio). URL query strings, fragments, and URL credentials are removed
from logged strings. Do not pass personal information, user messages, raw
request/response payloads, headers, or audio into log metadata: redaction is
defense in depth, not a guarantee that arbitrary text contains no private data.
Unreadable metadata produces a minimal `logger.serialization_failed` error
instead of letting serialization crash the application.
Console logs are not durable storage; centralized retention would require an
explicitly configured, privacy-reviewed collection service.

[`src/lib/http.js`](src/lib/http.js) wraps fetch and response consumption:

```js
return apiRequest('/api/health', { signal, cache: 'no-store' },
  (response) => response.json());
```

It generates a fresh UUID per request and sends it in **both `X-Correlation-ID`
and `X-Request-ID`**. The current FastAPI logger accepts/returns `X-Request-ID`
and writes that value as `request_id` in server logs. If a response includes
`X-Correlation-ID`, the client uses that as its correlation ID; otherwise it uses
`X-Request-ID`, then the generated UUID. Both server IDs and the original client
ID are retained when they differ. Unusable response IDs warn and fall back.
Trace context stays per request, including concurrent requests, HTTP failures,
JSON decoding, and the complete chat stream. Audio blobs retain the originating
trace for subsequent playback-error logs. `getErrorContext(error)` retrieves
trace metadata without mutating errors. Chat failures show an error reference
that can be matched against the console and backend logs.

Outgoing requests, response headers, and completed body consumption are separate
events with method, route, status, and elapsed milliseconds. No request bodies
or successful response bodies are logged. Expected cancellation logs at DEBUG;
timeouts and failed requests log at ERROR. Existing response shapes, multipart
boundaries, cancellation, and timeouts are preserved.

The same-origin `/api` proxy must forward both trace request and response
headers. A future cross-origin deployment must allow both custom request
headers and expose `X-Correlation-ID` and `X-Request-ID` through CORS. This change
does not modify backend middleware or CORS settings.

[`ErrorBoundary`](src/components/ErrorBoundary/ErrorBoundary.jsx) surrounds the
whole app, including its provider and layout. Render crashes log the React
component stack and show a theme-aware English/Spanish recovery screen with
retry, reload, and an error reference. A render-only reference is a client
incident ID, not a backend trace unless the error originated in a traced request.
Retry remounts the app and can clear the current conversation.

[`src/lib/globalErrors.js`](src/lib/globalErrors.js) installs `error` and
`unhandledrejection` listeners before rendering. It also reports resource-loading
failures without logging asset URLs. Listeners are idempotent and cleaned up on
Vite hot disposal; browser default error reporting is not suppressed.
Async errors are logged without replacing an otherwise working tour. Rendering
errors are handled by the boundary; microphone and playback failures keep their
existing inline error states and also use structured logging.

Run `npm test` for logger redaction, production-level filtering, global listener
cleanup, concurrent request tracing, stream errors, cancellation, and existing
API behavior; use `npm run build` to validate production compilation.

## Chat

The transcript starts empty and clears on reset, without prefilled welcome or
reset narration. Every guide response calls the backend, including approaching
a stop, arrival overviews, historical/restaurant quick questions, and tour
farewells. Navigation itself remains local; completing a simulated walk requests
orientation for the destination in the currently selected language and voice mode.
The chat has a message box,
**Send**, and a **Microphone** control, with suggested questions for nearby food,
coffee, and more history.
Chat controls and suggestions use inline SVG icons with visible text labels,
keyboard focus indicators, and theme-aware colors. No icon package is required.

Every request posts multipart form data to `/api/chat`, proxied to `/chat`:
`stop` (the exact corpus key), `language` (`EN` or `ES`, matching the toggle),
`mode`, `query`, and `stream=true`.
Suggested questions also send `request_type` (`historic` or `restaurant`);
freeform messages omit it so the backend selects the topic automatically.

| Mode | Input | Backend reply |
| --- | --- | --- |
| `text` | Typed message, arrival/replay, or suggested question with narration off | Streamed result text shown in the transcript |
| `tts` | Typed message, arrival/replay, or suggested question with narration on | Streamed base64 WAV decoded for narration and playback controls |
| `full` | Recorded voice message | Streamed base64 WAV decoded for automatic playback and playback controls |

Press **Microphone** to record, then **Stop and send** to submit the voice
message. Recording requires microphone permission and HTTPS or localhost.
Sent recordings appear as blue-accented voice bubbles with a microphone icon,
a decorative waveform, and a translated "Voice message" label instead of the
filename. User voice bubbles are visual only, without audio playback controls;
the guide's audio replies use the orb player described below.
Permission and recording errors are shown in the chat. The microphone is released
after recording, on errors, and when leaving the app, including when a pending
permission request resolves after the recorder has unmounted. Tour navigation
remains locked until recording finishes; navbar restart or language switching
cancels the recording.
Recordings must be nonempty and at most 14,000,000 bytes. WAV replies
from recorded voice messages play automatically when the request finishes,
even when the narration toggle is off. Playback controls remain available.
Enabling the navbar's voice toggle only affects future responses: it
does not send a request or replay the current answer. While enabled, **Replay
introduction**, typed messages, and suggested questions request backend `tts` audio
instead of browser speech synthesis. All guide audio replies, including the
closing response, attempt to play automatically; if the browser blocks playback,
an error is shown and the orb
remains available for manual playback. Disabling narration pauses its audio
and restores text replies. The navbar toggle remains available during other
interactions and does not change the mode of an already submitted request.
Turning narration back on does not automatically replay an older reply.

Guide audio replies use a river-blue orb instead of
the browser's native player. Tap the orb to play or pause; the swirling animation
runs only during playback and respects reduced-motion preferences. Seeking,
elapsed/total time, volume, and mute controls support keyboard input and English
and Spanish labels. This is a visual treatment only; audio generation uses the
existing backend, not an ElevenLabs service.

While requests run, the chat displays plain-language progress updates in English
or Spanish under "Your guide is working on your answer": getting ready, turning
voice messages into text (when needed), choosing how to help, looking up
information, putting the answer together, and preparing it to play aloud (when
needed). Technical terms such as pipeline, agent, STT, and TTS are not shown in
these updates.
Steps come from backend execution over a newline-delimited JSON response, not
timers or internal model reasoning. The current step is highlighted and previous
steps remain visible until the answer arrives. Proxies must disable buffering
for `application/x-ndjson` responses.
Errors and interrupted streams are shown without falling back to demo answers.
Chat times out after two minutes. Changing stops and finishing are blocked until
the current request or simulated walk finishes. Navbar restart and language
switching can cancel a pending request; restart also cancels walking and clears
the transcript. Leaving the app cancels a pending client request. Late responses
are not added to the transcript. Finishing requests a new backend-generated
closing response.
Cancellation does not guarantee the server stops an in-flight
generation or avoids provider charges.

Backend chat requires server-side Gemini configuration and a matching RAG
database. The Sources tab below the map shows the PDFs and page numbers of the
chunks retrieved for the latest answer, including voice replies. Each link opens
the PDF in a new tab at its one-based physical page (`#page=N`), using the
browser's PDF viewer. Multiple chunks from the same PDF page share one link;
different pages have separate links. References clear when a new request starts
or the tour context changes, so old sources are not shown for a new answer.
The backend serves corpus PDFs inline at `/documents/{source}`; the frontend
uses `/api/documents/{source}` through the same API proxy. Production deployments
must include `database/docs` alongside the backend. No similarity scores or
latency metadata are displayed.

## Vite template details

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is enabled on this template. See [this documentation](https://react.dev/learn/react-compiler) for more information.

Note: This will impact Vite dev & build performances.
You can also try [the experimental native React Compiler support in plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md#rust-react-compiler) by using `compiler: true` in the plugin options instead of using the Babel plugin.

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
