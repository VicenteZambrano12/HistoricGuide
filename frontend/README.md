# Plinius frontend

Plinius uses `public/logo.jpeg` for the navbar logo and browser tab icon.

## Appearance

The app opens directly to the live tour, without page-switching tabs.
Use the **Light mode / Dark mode** button in the navbar to
switch themes. Dark mode is the default; light mode uses warm marble surfaces
with darker gold, green, and blue accents across the tour and map.
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
narration voice. It cancels pending chat and microphone recording and stops
audio playback without resetting the tour. Existing user messages and backend
answers stay in their original language; new requests use the selected language.

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

The map scales to show all five stops. The current-stop panel sits below the
map rather than covering the route or labels. Press **I arrived** when you
reach a stop to request its introduction.

For production, configure the web server to proxy `/api/*` to the backend,
stripping the `/api` prefix. Vite's development proxy is not part of the build.

Run `npm test` for health-client tests, `npm run build` for the production build,
and `npm run lint` for lint checks.

## Chat

Arrival overviews and the historical/restaurant quick-question buttons now call
the backend rather than returning scripted answers. The chat has a message box,
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
| `full` | Recorded voice message | Streamed base64 WAV decoded for playback controls |

Press **Microphone** to record, then **Stop and send** to submit the voice
message. Recording requires microphone permission and HTTPS or localhost.
Sent recordings appear as gold-accented voice bubbles with a microphone icon,
a decorative waveform, and a translated "Voice message" label instead of the
filename. User voice bubbles are visual only, without audio playback controls;
the guide's audio replies use the orb player described below.
Permission and recording errors are shown in the chat. The microphone is released
after recording, on errors, and when leaving or resetting the chat, including
when a pending permission request resolves after navigation.
Recordings must be nonempty and at most 14,000,000 bytes. WAV replies
from recorded voice messages are played explicitly with the transcript's audio
controls. Enabling the navbar's voice toggle only affects future responses: it
does not send a request or replay the current answer. While enabled, **Replay Arrival
Overview**, typed messages, and suggested questions request backend `tts` audio
instead of browser speech synthesis. Narration replies attempt to play
automatically; if the browser blocks playback, an error is shown and the orb
remains available for manual playback. Disabling narration pauses its audio
and restores text replies. The toggle is disabled while chatting, walking, or
recording to avoid overlapping requests.

Guide audio replies use an ElevenLabs-inspired gold-and-marble orb instead of
the browser's native player. Tap the orb to play or pause; the swirling animation
runs only during playback and respects reduced-motion preferences. Seeking,
elapsed/total time, volume, and mute controls support keyboard input and English
and Spanish labels. This is a visual treatment only; audio generation uses the
existing backend, not an ElevenLabs service.

While requests run, the chat displays live pipeline and agent steps in the
selected language: preparation, voice transcription (when needed), orchestration,
source retrieval, answer generation, and speech synthesis (when needed).
Steps come from backend execution over a newline-delimited JSON response, not
timers or internal model reasoning. The current step is highlighted and previous
steps remain visible until the answer arrives. Proxies must disable buffering
for `application/x-ndjson` responses.
Errors and interrupted streams are shown without falling back to demo answers.
Chat times out after two minutes. Changing stops, finishing, or resetting the
tour cancels a pending client request, and late responses are not added to the
transcript. Cancellation does not guarantee the server stops an in-flight
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
