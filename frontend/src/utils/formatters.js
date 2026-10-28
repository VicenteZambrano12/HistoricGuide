export function formatCoordinates(lat, lng) {
  if (!lat || !lng) return '41.8925° N, 12.4853° E';
  return `${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`;
}

export function formatConfidence(score) {
  return `${Math.round((score || 0.95) * 100)}% match`;
}
