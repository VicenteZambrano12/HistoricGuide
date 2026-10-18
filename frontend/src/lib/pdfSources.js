export function pdfSourceHref({ source, page }) {
  return `/api/documents/${source.split('/').map(encodeURIComponent).join('/')}#page=${page}`;
}

export function parsePdfSources(sources) {
  if (!Array.isArray(sources) || sources.some((item) =>
    !item || typeof item.source !== 'string' || !item.source.toLowerCase().endsWith('.pdf') ||
    item.source.includes('\\') || [...item.source].some((character) =>
      character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127) ||
    item.source.split('/').some((part) => !part || part === '.' || part === '..') ||
    !Number.isSafeInteger(item.page) || item.page < 1
  )) {
    throw new Error('Invalid PDF source references.');
  }
  return sources.filter((item, index) =>
    sources.findIndex((other) => other.source === item.source && other.page === item.page) === index
  );
}
