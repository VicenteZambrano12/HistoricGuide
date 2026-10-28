export function buildRagTelemetry(stop, mode) {
  if (!stop) return null;

  if (mode === 'HISTORICAL') {
    return {
      mode: 'HISTORICAL_RAG',
      badge: 'QDRANT // CLASSICAL CORPUS RAG',
      query: stop.historicalRag.query,
      collection: stop.historicalRag.collection,
      latencyMs: stop.historicalRag.latencyMs,
      topScore: stop.historicalRag.chunks[0]?.score || 0.95,
      items: stop.historicalRag.chunks.map((c) => ({
        id: c.id,
        title: c.source,
        subtitle: 'Primary Classical Source & Archaeological Index',
        snippet: c.snippet,
        score: c.score
      }))
    };
  }

  if (mode === 'GASTRO') {
    return {
      mode: 'GASTRO_GEO_RAG',
      badge: 'QDRANT // GEO-SPATIAL GASTRO RAG',
      query: stop.gastroRag.query,
      collection: stop.gastroRag.collection,
      latencyMs: stop.gastroRag.latencyMs,
      topScore: stop.gastroRag.places[0]?.score || 0.95,
      items: stop.gastroRag.places.map((p, idx) => ({
        id: `poi_${stop.id}_${idx}`,
        title: `${p.name} (${p.rating})`,
        subtitle: `${p.type} • ${p.distance}`,
        snippet: `Specialty: ${p.specialty}`,
        score: p.score
      }))
    };
  }

  return {
    mode: 'OVERVIEW_PROMPT',
    badge: 'GPS ARRIVAL // SYSTEM CONTEXT',
    query: `gps_trigger_arrival(stop_id="${stop.id}", lat=${stop.coords.lat}, lng=${stop.coords.lng})`,
    collection: 'monument_overview_graphs_v1',
    latencyMs: 64,
    topScore: 0.99,
    items: [
      {
        id: `overview_${stop.id}`,
        title: `${stop.name} (${stop.era})`,
        subtitle: stop.subtitle,
        snippet: 'Triggered automatic voice overview upon geofence arrival confirmation.',
        score: 0.99
      }
    ]
  };
}
