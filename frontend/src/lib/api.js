import { parsePdfSources } from './pdfSources.js';

function sourceMetadata(sources, t) {
  if (sources === undefined) return {};
  try {
    return { sources: parsePdfSources(sources) };
  } catch (error) {
    throw new Error(t('sourcesResponseError'), { cause: error });
  }
}

export async function checkBackendHealth(signal) {
  const timeoutSignal = AbortSignal.timeout(5000);
  const response = await fetch('/api/health', {
    signal: signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal,
    cache: 'no-store'
  });

  if (!response.ok) {
    throw new Error(`Health check failed (HTTP ${response.status}).`);
  }

  const data = await response.json();
  if (data?.status !== 'ok') {
    throw new Error('Health check returned an unexpected response.');
  }

  return data;
}

export async function sendChatRequest({ stop, requestType, mode, query, language = 'EN', onProgress }, signal) {
  if (!['EN', 'ES'].includes(language)) {
    throw new Error('Select English (EN) or Spanish (ES).');
  }
  const t = getTranslator(language.toLowerCase());
  if (typeof stop !== 'string' || !stop.trim()) {
    throw new Error(t('selectStopError'));
  }
  if (requestType !== undefined && !['historic', 'restaurant'].includes(requestType)) {
    throw new Error(t('requestTypeError'));
  }
  if (!['text', 'tts', 'stt', 'full'].includes(mode)) {
    throw new Error(t('chatModeError'));
  }

  const audioInput = mode === 'stt' || mode === 'full';
  if (audioInput) {
    if (!(query instanceof Blob) || !query.type.startsWith('audio/') || !query.size) {
      throw new Error(t('audioInputError'));
    }
    if (query.size > 14_000_000) {
      throw new Error(t('audioSizeError'));
    }
  } else if (typeof query !== 'string' || !query.trim()) {
    throw new Error(t('queryError'));
  }

  const body = new FormData();
  body.append('stop', stop.trim());
  if (requestType !== undefined) body.append('request_type', requestType);
  body.append('language', language);
  body.append('mode', mode);
  if (onProgress) body.append('stream', 'true');
  if (audioInput) {
    body.append('query', query, query.name || 'question.webm');
  } else {
    body.append('query', query.trim());
  }

  const timeoutSignal = AbortSignal.timeout(120_000);
  const response = await fetch('/api/chat', {
    method: 'POST',
    body,
    signal: signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal
  });

  if (!response.ok) {
    let detail;
    if (response.headers.get('content-type')?.includes('application/json')) {
      const error = await response.json();
      detail = typeof error?.detail === 'string'
        ? error.detail
        : Array.isArray(error?.detail)
          ? error.detail.map((issue) => `${issue.loc?.join('.')}: ${issue.msg}`).join('; ')
          : '';
    } else {
      detail = await response.text();
    }
    throw new Error(t('chatHttpError', {
      status: response.status, detail: detail ? `: ${detail}` : '.'
    }));
  }

  if (onProgress) {
    if (response.headers.get('content-type')?.split(';')[0] !== 'application/x-ndjson') {
      throw new Error(t('progressResponseError'));
    }
    return readChatStream(response, mode, onProgress, t);
  }

  if (mode === 'tts' || mode === 'full') {
    if (response.headers.get('content-type')?.split(';')[0] !== 'audio/wav') {
      throw new Error(t('audioResponseError'));
    }
    const audio = await response.blob();
    if (!audio.size) throw new Error(t('emptyAudioError'));
    const sources = response.headers.get('X-PDF-Sources');
    return { audio, ...sourceMetadata(sources === null ? undefined : JSON.parse(sources), t) };
  }

  const data = await response.json();
  if (typeof data?.text !== 'string' || !data.text.trim()) {
    throw new Error(t('textResponseError'));
  }
  return { text: data.text, ...sourceMetadata(data.sources, t) };
}

const PROGRESS_STEPS = new Set([
  'starting', 'transcribing', 'routing', 'retrieving', 'generating', 'synthesizing'
]);

async function readChatStream(response, mode, onProgress, t) {
  if (!response.body) throw new Error(t('progressResponseError'));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  function parseEvent(line) {
    const event = JSON.parse(line);
    if (event?.type === 'progress' && PROGRESS_STEPS.has(event.step)) {
      onProgress(event.step);
      return null;
    }
    if (event?.type === 'error' && typeof event.detail === 'string') {
      throw new Error(t('progressFailed', { detail: event.detail }));
    }
    if (event?.type !== 'result') throw new Error(t('progressResponseError'));
    if (mode === 'tts' || mode === 'full') {
      if (event.mime_type !== 'audio/wav' || typeof event.audio !== 'string' || !event.audio) {
        throw new Error(t('audioResponseError'));
      }
      const audio = Uint8Array.from(atob(event.audio), (character) => character.charCodeAt(0));
      return {
        audio: new Blob([audio], { type: 'audio/wav' }),
        ...sourceMetadata(event.sources, t)
      };
    }
    if (typeof event.text !== 'string' || !event.text.trim()) {
      throw new Error(t('textResponseError'));
    }
    return { text: event.text, ...sourceMetadata(event.sources, t) };
  }

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let newline;
      while ((newline = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (!line) continue;
        const result = parseEvent(line);
        if (result) return result;
      }
      if (done) {
        if (buffer.trim()) {
          const result = parseEvent(buffer);
          if (result) return result;
        }
        throw new Error(t('progressInterrupted'));
      }
    }
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}
import { getTranslator } from '../i18n/translations.js';
