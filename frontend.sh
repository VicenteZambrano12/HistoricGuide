mkdir -p \
  src/components/Navbar \
  src/components/VoiceOrb \
  src/components/MonumentIllustration \
  src/features/map/RomeMapCanvas \
  src/features/map/StopTimelineBar \
  src/features/voiceGuide/HistorianVoicePanel \
  src/features/voiceGuide/ActionPromptChips \
  src/features/rag/RagTelemetryDrawer \
  src/hooks \
  src/i18n \
  src/layouts/MainLayout \
  src/lib \
  src/pages/TourWorkstationPage \
  src/pages/ArchitecturePreviewPage \
  src/router \
  src/store \
  src/utils

# ==========================================
# 1. THEME & GLOBAL STYLES
# ==========================================
cat << 'EOF' > src/theme.css
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700;800&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,400;1,600&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
  --bg-obsidian: #0b0a09;
  --bg-panel: #141210;
  --bg-card: #1c1916;
  --bg-card-hover: #25211d;
  --bg-glass: rgba(20, 18, 16, 0.86);

  --gold-primary: #d4af37;
  --gold-soft: rgba(212, 175, 55, 0.16);
  --gold-border: rgba(212, 175, 55, 0.32);

  --crimson-imperial: #9e2a2b;
  --crimson-soft: rgba(158, 42, 43, 0.2);

  --emerald-rag: #10b981;
  --emerald-soft: rgba(16, 185, 129, 0.15);

  --amber-gastro: #f59e0b;
  --amber-soft: rgba(245, 158, 11, 0.15);

  --cyan-gps: #38bdf8;

  --text-marble: #f5f2eb;
  --text-travertine: #c8c1b4;
  --text-muted: #8a8275;

  --border-subtle: rgba(245, 242, 235, 0.09);

  --font-display: 'Cinzel', serif;
  --font-editorial: 'Cormorant Garamond', serif;
  --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --shadow-elevated: 0 16px 40px rgba(0, 0, 0, 0.55);
}
EOF

cat << 'EOF' > src/index.css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body,
#root {
  width: 100%;
  height: 100%;
  background-color: var(--bg-obsidian);
  color: var(--text-marble);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-obsidian);
}

::-webkit-scrollbar-thumb {
  background: #2f2a24;
  border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--gold-primary);
}
EOF

cat << 'EOF' > src/App.css
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at 15% 10%, rgba(212, 175, 55, 0.07), transparent 45%),
              radial-gradient(circle at 85% 85%, rgba(158, 42, 43, 0.08), transparent 45%),
              var(--bg-obsidian);
}
EOF

# ==========================================
# 2. DATA, RAG ENGINE, I18N & UTILS
# ==========================================
cat << 'EOF' > src/lib/romeStopsData.js
export const ROME_STOPS = [
  {
    id: 'torre-argentina',
    order: 1,
    name: 'Largo di Torre Argentina',
    subtitle: 'Curia of Pompey & Sacred Area',
    era: 'Roman Republic • 44 BC',
    periodTag: 'REPUBLIC',
    coords: { lat: 41.8954, lng: 12.4768, mapX: 280, mapY: 310 },
    distanceMeters: 420,
    walkSeconds: 4,
    overviewSpeech:
      "Ave, traveler. You have arrived at Largo di Torre Argentina—specifically before the sunken tufa foundations of the Curia of Pompey. On the Ides of March, 44 BC, the Roman Senate convened here while the Senate House in the Forum was under renovation. Directly beneath those pines lies the exact spot where Gaius Julius Caesar fell at the base of Pompey's statue. Would you like to explore the historical and cultural RAG archives, visit a nearby Roman coffee roastery or trattoria, or walk to our next stop?",
    historicalRag: {
      query: 'vector_search("Curia of Pompey assassination Julius Caesar Ides of March 44 BC architectural context")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 142,
      answerSpeech:
        "According to Suetonius and Plutarch, Caesar received twenty-three stab wounds here, yet the physician Antistius determined only the second blow to the breast was fatal. Culturally, the irony was profound: Caesar was slain at the feet of a statue of his greatest rival, Pompey the Great. Following the assassination, Augustus walled off the chamber and declared it a 'locus sceleratus'—an accursed place—converting it into a public latrine.",
      chunks: [
        {
          id: 'doc_suet_div_jul_82',
          source: 'Suetonius • De Vita Caesarum (Divus Julius, 82)',
          score: 0.96,
          snippet: 'Assailed by the conspirators inside the Curia Pompeii, Caesar wrapped his toga around his head and drew the folds down to his feet so he might fall more decently.'
        },
        {
          id: 'doc_topo_campus_martius_14',
          source: 'Platner & Ashby • Topographical Dictionary of Ancient Rome',
          score: 0.92,
          snippet: 'Exhedra inside the Porticus Pompeiana; later sealed under Augustus as locus sceleratus with concrete tufa blocks still visible behind Temple B.'
        }
      ]
    },
    gastroRag: {
      query: 'geo_rag_search(lat=41.8954, lng=12.4768, radius="250m", filter="historic_caffetteria_trattoria")',
      collection: 'roma_artisan_gastronomy_geo_v2',
      latencyMs: 118,
      answerSpeech:
        "Just 180 meters north toward the Pantheon is Sant'Eustachio Il Caffè, roasting wood-fired Arabica since 1938 with water fed by the ancient Aqua Virgo aqueduct. If you prefer a sit-down Roman lunch, Armando al Pantheon offers authentic Pasta alla Gricia—the ancestor of Carbonara that predates New World tomatoes, much closer to what plebeians ate of cured pork cheek and pecorino.",
      places: [
        {
          name: "Sant'Eustachio Il Caffè",
          type: 'Historic Wood-Fired Roastery (Est. 1938)',
          distance: '180m • 2 min walk',
          rating: '4.8 ★',
          specialty: 'Gran Caffè (Whipped sugar & secret Arabica blend)',
          score: 0.95
        },
        {
          name: 'Armando al Pantheon',
          type: 'Traditional Roman Trattoria (Est. 1961)',
          distance: '240m • 3 min walk',
          rating: '4.9 ★',
          specialty: 'Rigatoni alla Gricia & Abbacchio alla Scottadito',
          score: 0.91
        }
      ]
    }
  },
  {
    id: 'forum-boarium',
    order: 2,
    name: 'Forum Boarium',
    subtitle: 'Temples of Portunus & Hercules Victor',
    era: 'Mid-Late Republic • 2nd Century BC',
    periodTag: 'REPUBLIC',
    coords: { lat: 41.8887, lng: 12.4807, mapX: 335, mapY: 465 },
    distanceMeters: 680,
    walkSeconds: 4,
    overviewSpeech:
      "Welcome to the Forum Boarium, ancient Rome's bustling river port and cattle market along the bend of the Tiber. Before you stand two of the best-preserved Republican temples in existence: the rectangular Ionic Temple of Portunus, god of keys and harbors, and the circular Pentelic marble Temple of Hercules Victor. Shall we dive into the Republican trade and architectural archives, stop for an espresso or Jewish-Roman artichokes nearby, or walk toward the Roman Forum?",
    historicalRag: {
      query: 'vector_search("Forum Boarium Temple of Hercules Victor Greek marble Republican merchants")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 134,
      answerSpeech:
        "The circular Temple of Hercules Victor, dating from around 120 BC, is the earliest surviving marble building in Rome. Designed by the Greek architect Hermodorus of Salamis and funded by Marcus Octavius Herrenus—a wealthy olive-oil merchant—it reflects the exact historical moment when Republican Rome conquered Greece and began importing Hellenistic luxury, sparking fierce condemnation from traditionalists like Cato the Elder.",
      chunks: [
        {
          id: 'doc_vitruvius_de_arch_3_2',
          source: 'Vitruvius • De Architectura (Book IV, Peripteral Tholos)',
          score: 0.94,
          snippet: 'Constructed of imported Greek Pentelic marble with twenty Corinthian columns resting on a stepped tufa stylobate.'
        },
        {
          id: 'doc_livy_ab_urbe_21',
          source: 'Livy • Ab Urbe Condita (Republican River Commerce)',
          score: 0.89,
          snippet: 'Here at the Portus Tiberinus grain, olive oil, and cattle entered the city before the expansion of Ostia.'
        }
      ]
    },
    gastroRag: {
      query: 'geo_rag_search(lat=41.8887, lng=12.4807, radius="350m", filter="cucina_romana_giudia")',
      collection: 'roma_artisan_gastronomy_geo_v2',
      latencyMs: 126,
      answerSpeech:
        "Crossing just north toward the Portico of Octavia brings you into the historic Ghetto, home to Europe's oldest continuous Jewish community—present in Rome since the 2nd century BC under Judas Maccabeus's envoys. I highly recommend Nonna Betta for Carciofi alla Giudia, or Pasticceria Boccione for rustic ricotta and sour-cherry tart.",
      places: [
        {
          name: 'Nonna Betta',
          type: 'Historic Kosher-Roman Osteria',
          distance: '310m • 4 min walk',
          rating: '4.7 ★',
          specialty: 'Carciofi alla Giudia (Crispy fried Roman artichokes)',
          score: 0.96
        },
        {
          name: 'Forno Boccione',
          type: 'Artisan Heritage Bakery (Est. 1815)',
          distance: '340m • 4 min walk',
          rating: '4.9 ★',
          specialty: 'Crostata di Ricotta e Viscioli (Baked warm)',
          score: 0.93
        }
      ]
    }
  },
  {
    id: 'roman-forum',
    order: 3,
    name: 'The Roman Forum',
    subtitle: 'Curia Julia, Rostra & Via Sacra',
    era: 'Republic to Principate • 44 BC – 14 AD',
    periodTag: 'TRANSITION',
    coords: { lat: 41.8925, lng: 12.4853, mapX: 495, mapY: 365 },
    distanceMeters: 590,
    walkSeconds: 4,
    overviewSpeech:
      "You now stand at the political nerve center of the ancient Mediterranean: the Forum Romanum. Directly ahead rises the brick facade of the Curia Julia, begun by Julius Caesar and completed by Augustus in 29 BC, adjacent to the Rostra—the speaker's platform adorned with the bronze prows of captured enemy warships. Would you like to hear more historical details from Cicero's and Augustus's era, pause for a rooftop coffee or trattoria, or continue to Trajan's Markets?",
    historicalRag: {
      query: 'vector_search("Rostra Curia Julia Cicero Philippics Mark Antony Augustus Res Gestae")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 151,
      answerSpeech:
        "The Rostra before you witnessed both the zenith and death of Republican oratory. In 43 BC, after Cicero delivered his blistering Philippics against Mark Antony, Antony had Cicero's head and right hand—the hand that wrote the speeches—nailed to these very bronze prows. Just fourteen years later, Augustus dedicated the adjacent Curia Julia, famously boasting in his Res Gestae that he found Rome a city of sun-dried brick and left it a city of marble.",
      chunks: [
        {
          id: 'doc_appian_bell_civ_4_20',
          source: 'Appian • Bella Civilia (Book IV, Proscriptions)',
          score: 0.97,
          snippet: 'Cicero’s head and hand were suspended on the Rostra in the Forum, where formerly he had been heard speaking by the Roman people.'
        },
        {
          id: 'doc_aug_res_gestae_19',
          source: 'Augustus • Res Gestae Divi Augusti (Section 19)',
          score: 0.94,
          snippet: 'Curiam et continens ei Chalcidicum templumque Apollinis in Palatio cum porticibus feci.'
        }
      ]
    },
    gastroRag: {
      query: 'geo_rag_search(lat=41.8925, lng=12.4853, radius="400m", filter="monti_caffetteria_enoteca")',
      collection: 'roma_artisan_gastronomy_geo_v2',
      latencyMs: 112,
      answerSpeech:
        "Stepping out of the Forum into the Monti district—ancient Rome's densely populated Subura neighborhood—you have two standout choices: La Casina delle Civette or Aroma Bistro for an espresso overlooking the archaeological park, or Hostaria La Carbonara in Campo de' Fiori / Monti's Taverna dei Fori Imperiali for classic Tonnarelli Cacio e Pepe.",
      places: [
        {
          name: 'Taverna dei Fori Imperiali',
          type: 'Family-Run Roman Trattoria (Monti)',
          distance: '290m • 4 min walk',
          rating: '4.8 ★',
          specialty: 'Tonnarelli Cacio e Pepe & Burrata Romana',
          score: 0.95
        },
        {
          name: 'Caffè Propaganda',
          type: 'Artisan Specialty Coffee & Bistro',
          distance: '410m • 5 min walk',
          rating: '4.6 ★',
          specialty: 'Single-Origin Espresso & Roman Maritozzo con Panna',
          score: 0.90
        }
      ]
    }
  },
  {
    id: 'trajans-markets',
    order: 4,
    name: "Trajan's Forum & Markets",
    subtitle: 'Mercati di Traiano & Ulpian Basilica',
    era: 'High Empire • 107 – 113 AD',
    periodTag: 'EMPIRE',
    coords: { lat: 41.8956, lng: 12.4861, mapX: 525, mapY: 270 },
    distanceMeters: 450,
    walkSeconds: 4,
    overviewSpeech:
      "Behold the architectural peak of the High Roman Empire: Trajan's Forum and the multi-level Mercati di Traiano. Built between 107 and 113 AD by the brilliant Syrian-Greek engineer Apollodorus of Damascus, this entire complex was financed by the colossal gold and silver spoils of Emperor Trajan's Dacian Wars. Would you like to query the RAG archives on Apollodorus and Trajan's Column, grab a specialty coffee or lunch in Monti, or walk to our final stop at the Pantheon?",
    historicalRag: {
      query: 'vector_search("Apollodorus of Damascus Trajan Markets Quirinal Hill excavation Dacian gold")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 138,
      answerSpeech:
        "Look at the inscription at the base of Trajan's Column: it records that Roman engineers literally carved away a 38-meter-high saddle of the Quirinal Hill—over 60 million cubic feet of volcanic rock—to level this plaza. The semicircular brick hemicycle of the Markets acted as a gigantic structural retaining wall holding back the cut hillside, housing over 150 administrative offices (tabernae) and the annona grain distribution headquarters.",
      chunks: [
        {
          id: 'doc_cil_vi_960',
          source: 'Corpus Inscriptionum Latinarum (CIL VI 960 • Trajan Column Base)',
          score: 0.98,
          snippet: 'Ad declarandum quantae altitudinis mons et locus tantis operibus sit egestus — To declare how lofty a hill and place was dug away for such great works.'
        },
        {
          id: 'doc_cassius_dio_68_16',
          source: 'Cassius Dio • Roman History (Book 68, Trajan & Apollodorus)',
          score: 0.93,
          snippet: 'Apollodorus of Damascus constructed the Forum, the Odeon, and the great gymnasium in Rome, Marvels celebrated across the Empire.'
        }
      ]
    },
    gastroRag: {
      query: 'geo_rag_search(lat=41.8956, lng=12.4861, radius="300m", filter="specialty_coffee_enoteca_monti")',
      collection: 'roma_artisan_gastronomy_geo_v2',
      latencyMs: 119,
      answerSpeech:
        "Right behind Trajan's Markets along Via Panisperna in Rione Monti, you'll find Barzilai/Faro pathways or Ai Tre Scalini—a historic wine and cicchetti institution operating since 1895—alongside La Bottega del Caffè on Piazza della Madonna dei Monti, an ideal Roman square to sip a macchiato beside the 16th-century fountain.",
      places: [
        {
          name: 'Ai Tre Scalini (Rione Monti)',
          type: 'Historic Bottiglieria & Roman Kitchen (Est. 1895)',
          distance: '260m • 3 min walk',
          rating: '4.8 ★',
          specialty: 'Polpette al Sugo & Cesanese del Piglio Red Wine',
          score: 0.96
        },
        {
          name: 'La Bottega del Caffè',
          type: 'Piazza Espresso Bar (Madonna dei Monti)',
          distance: '280m • 3 min walk',
          rating: '4.6 ★',
          specialty: 'Artisan Cappuccino & Cornetto Artigianale on the Piazza',
          score: 0.91
        }
      ]
    }
  },
  {
    id: 'pantheon',
    order: 5,
    name: 'The Pantheon',
    subtitle: 'Rotunda of Agrippa & Hadrian',
    era: 'High Empire • 118 – 128 AD',
    periodTag: 'EMPIRE',
    coords: { lat: 41.8986, lng: 12.4769, mapX: 290, mapY: 205 },
    distanceMeters: 740,
    walkSeconds: 4,
    overviewSpeech:
      "You have reached our fifth and final stop in the Campus Martius: the Pantheon. Although the bronze frieze on the portico reads 'Marcus Agrippa, son of Lucius, consul for the third time, built this'—referencing the 27 BC Augustan temple—the miraculous concrete rotunda standing before you was completely rebuilt under Emperor Hadrian around 126 AD. Would you like to explore the engineering secrets of the unreinforced dome via RAG, celebrate with Rome's finest coffee, or conclude your tour?",
    historicalRag: {
      query: 'vector_search("Pantheon Hadrian unreinforced concrete dome oculus aggregate gradation")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 129,
      answerSpeech:
        "Nearly two thousand years after Hadrian's architects completed it, the Pantheon's 43.3-meter dome remains the largest unreinforced concrete dome on Earth. Roman engineers achieved this by grading the volcanic pozzolana aggregate in horizontal rings: heavy travertine at the base, lighter tufa bricks in the middle, and featherweight volcanic pumice around the 9-meter open oculus at the zenith—creating a perfect sphere where height equals diameter.",
      chunks: [
        {
          id: 'doc_cassius_dio_69_7',
          source: 'Cassius Dio • Roman History (Book 69, Hadrian)',
          score: 0.97,
          snippet: 'Perhaps because its vaulted roof resembles the heavens, the Pantheon served as the seat where Hadrian held court aided by the leading senators.'
        },
        {
          id: 'doc_lanciani_concrete_dome',
          source: 'Roman Concrete Aggregate Stratigraphy • Corpus Latericium',
          score: 0.95,
          snippet: 'Gradated caementa density from 1,600 kg/m³ travertine base down to 1,350 kg/m³ Vesuvian pumice at the oculus ring.'
        }
      ]
    },
    gastroRag: {
      query: 'geo_rag_search(lat=41.8986, lng=12.4769, radius="200m", filter="iconic_roastery_gelateria")',
      collection: 'roma_artisan_gastronomy_geo_v2',
      latencyMs: 109,
      answerSpeech:
        "Just steps from the Pantheon's portico sits La Casa del Caffè Tazza d'Oro, famous since 1946 for its 'Granita di Caffè con Panna'—layered espresso ice topped with unsweetened whipped cream. For a celebratory final meal, Da Fortunato al Pantheon offers classic Roman tables right beside the ancient columns.",
      places: [
        {
          name: "La Casa del Caffè Tazza d'Oro",
          type: 'Legendary Roman Coffee Roastery (Est. 1946)',
          distance: '95m • 1 min walk',
          rating: '4.8 ★',
          specialty: 'Granita di Caffè con Panna (Queen of the Woods blend)',
          score: 0.98
        },
        {
          name: 'Giolitti (Via Uffici del Vicario)',
          type: 'Historic Royal Gelateria & Pastry House (Est. 1900)',
          distance: '210m • 3 min walk',
          rating: '4.7 ★',
          specialty: 'Artisan Pistachio of Bronte & Zabaione Gelato',
          score: 0.92
        }
      ]
    }
  }
];
EOF

cat << 'EOF' > src/lib/ragEngine.js
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
EOF

cat << 'EOF' > src/i18n/translations.js
export const UI_STRINGS = {
  appName: 'AURELIUS',
  appTagline: 'Peripatetic Voice AI Historian • Ancient Rome RAG Demo',
  arrivalButton: "📍 Simulate 'I Have Arrived'",
  choiceHistorical: '🏛️ 1. Historical & Cultural Details (RAG)',
  choiceGastro: '☕ 2. Go to Coffee / Trattoria (Geo-RAG)',
  choiceNextStop: '🚶 3. Walk to Next Monument',
  choiceFinish: '🏁 4. Finish Historical Tour'
};
EOF

cat << 'EOF' > src/utils/formatters.js
export function formatCoordinates(lat, lng) {
  if (!lat || !lng) return '41.8925° N, 12.4853° E';
  return `${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`;
}

export function formatConfidence(score) {
  return `${Math.round((score || 0.95) * 100)}% match`;
}
EOF

# ==========================================
# 3. CUSTOM HOOKS
# ==========================================
cat << 'EOF' > src/hooks/useSpeechSynthesis.js
import { useState, useEffect, useCallback } from 'react';

export function useSpeechSynthesis() {
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const stopSpeech = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  }, []);

  const speakText = useCallback(
    (text) => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        return;
      }

      window.speechSynthesis.cancel();

      if (!audioEnabled) {
        setIsSpeaking(true);
        const simulatedDuration = Math.min(4500, Math.max(1800, text.length * 16));
        const timer = setTimeout(() => setIsSpeaking(false), simulatedDuration);
        return () => clearTimeout(timer);
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-GB';
      utterance.rate = 1.02;
      utterance.pitch = 0.95;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    },
    [audioEnabled]
  );

  const toggleAudio = useCallback(() => {
    setAudioEnabled((prev) => {
      const next = !prev;
      if (!next && typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return {
    audioEnabled,
    isSpeaking,
    speakText,
    stopSpeech,
    toggleAudio
  };
}
EOF

cat << 'EOF' > src/hooks/useGpsSimulation.js
import { useState, useEffect, useRef, useCallback } from 'react';

export function useGpsSimulation(initialPoint) {
  const [gpsPosition, setGpsPosition] = useState(initialPoint);
  const [isWalking, setIsWalking] = useState(false);
  const [walkProgress, setWalkProgress] = useState(100);
  const animRef = useRef(null);

  const startWalkSimulation = useCallback((fromPoint, toPoint, durationMs = 2200, onNearTarget) => {
    if (animRef.current) cancelAnimationFrame(animRef.current);

    setIsWalking(true);
    setWalkProgress(0);
    const startTime = performance.now();

    const step = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / durationMs);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

      const currentX = fromPoint.mapX + (toPoint.mapX - fromPoint.mapX) * ease;
      const currentY = fromPoint.mapY + (toPoint.mapY - fromPoint.mapY) * ease;
      const currentLat = fromPoint.lat + (toPoint.lat - fromPoint.lat) * ease;
      const currentLng = fromPoint.lng + (toPoint.lng - fromPoint.lng) * ease;

      setGpsPosition({
        mapX: currentX,
        mapY: currentY,
        lat: currentLat,
        lng: currentLng
      });
      setWalkProgress(Math.round(t * 100));

      if (t < 1) {
        animRef.current = requestAnimationFrame(step);
      } else {
        setIsWalking(false);
        setWalkProgress(100);
        if (onNearTarget) onNearTarget();
      }
    };

    animRef.current = requestAnimationFrame(step);
  }, []);

  useEffect(() => {
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, []);

  return {
    gpsPosition,
    setGpsPosition,
    isWalking,
    walkProgress,
    startWalkSimulation
  };
}
EOF

# ==========================================
# 4. GLOBAL STATE STORE (CONTEXT)
# ==========================================
cat << 'EOF' > src/store/TourContext.jsx
import React, { createContext, useContext, useState, useCallback } from 'react';
import { ROME_STOPS } from '../lib/romeStopsData';
import { buildRagTelemetry } from '../lib/ragEngine';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useGpsSimulation } from '../hooks/useGpsSimulation';

const TourContext = createContext(null);

export function TourProvider({ children }) {
  const [activePage, setActivePage] = useState('WORKSTATION'); // 'WORKSTATION' | 'ARCHITECTURE'
  const [layoutMode, setLayoutMode] = useState('SPLIT'); // 'SPLIT' | 'MOBILE'
  const [currentStopIndex, setCurrentStopIndex] = useState(0);
  // Phases: 'WALKING_TO_STOP' | 'READY_TO_ARRIVE' | 'ARRIVED_OVERVIEW' | 'HISTORICAL_RAG' | 'GASTRO_RAG' | 'TOUR_COMPLETED'
  const [tourPhase, setTourPhase] = useState('READY_TO_ARRIVE');

  const currentStop = ROME_STOPS[currentStopIndex];

  const [messages, setMessages] = useState([
    {
      id: 'init-msg',
      sender: 'AURELIUS',
      tag: 'PERIPATETIC GPS GUIDE',
      timestamp: '09:30 AM',
      text: `Salve! We are walking through the Campus Martius toward Stop #1: ${ROME_STOPS[0].name} (${ROME_STOPS[0].era}). Tap "Simulate 'I Have Arrived'" as soon as you reach the monument perimeter.`
    }
  ]);

  const [ragTelemetry, setRagTelemetry] = useState(() =>
    buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW')
  );

  const { audioEnabled, isSpeaking, speakText, stopSpeech, toggleAudio } =
    useSpeechSynthesis();

  const {
    gpsPosition,
    setGpsPosition,
    isWalking,
    walkProgress,
    startWalkSimulation
  } = useGpsSimulation(ROME_STOPS[0].coords);

  const appendMessage = useCallback((sender, text, tag = '') => {
    const now = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
    setMessages((prev) => [
      ...prev,
      {
        id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        sender,
        tag,
        timestamp: now,
        text
      }
    ]);
  }, []);

  const walkToStopIndex = useCallback(
    (targetIdx) => {
      if (targetIdx < 0 || targetIdx >= ROME_STOPS.length) return;
      const targetStop = ROME_STOPS[targetIdx];
      const fromCoords = gpsPosition || currentStop.coords;

      stopSpeech();
      setCurrentStopIndex(targetIdx);
      setTourPhase('WALKING_TO_STOP');

      appendMessage(
        'USER',
        `🎙️ "Let's walk to Stop #${targetStop.order}: ${targetStop.name}."`,
        'VOICE INTENT'
      );

      startWalkSimulation(fromCoords, targetStop.coords, 2000, () => {
        setTourPhase('READY_TO_ARRIVE');
        const arrivalPrompt = `You are now approaching ${targetStop.name} (${targetStop.era}). Let me know when you've arrived at the monument to begin the overview.`;
        appendMessage('AURELIUS', arrivalPrompt, 'GPS PROXIMITY ALERT');
        speakText(arrivalPrompt);
      });
    },
    [gpsPosition, currentStop, stopSpeech, appendMessage, startWalkSimulation, speakText]
  );

  const confirmArrivalAtStop = useCallback(() => {
    setGpsPosition(currentStop.coords);
    setTourPhase('ARRIVED_OVERVIEW');
    setRagTelemetry(buildRagTelemetry(currentStop, 'OVERVIEW'));

    appendMessage(
      'USER',
      `🎙️ "I've arrived at ${currentStop.name}."`,
      'GPS ARRIVAL TRIGGER'
    );
    appendMessage(
      'AURELIUS',
      currentStop.overviewSpeech,
      `MONUMENT OVERVIEW • ${currentStop.era}`
    );
    speakText(currentStop.overviewSpeech);
  }, [currentStop, setGpsPosition, appendMessage, speakText]);

  const askHistoricalRag = useCallback(() => {
    setTourPhase('HISTORICAL_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'HISTORICAL'));

    appendMessage(
      'USER',
      '🎙️ "Tell me more historical and cultural details about this monument."',
      'RAG QUERY: CLASSICAL HISTORY'
    );
    appendMessage(
      'AURELIUS',
      currentStop.historicalRag.answerSpeech,
      `QDRANT VECTOR RAG • ${currentStop.historicalRag.latencyMs}ms`
    );
    speakText(currentStop.historicalRag.answerSpeech);
  }, [currentStop, appendMessage, speakText]);

  const askGastroRag = useCallback(() => {
    setTourPhase('GASTRO_RAG');
    setRagTelemetry(buildRagTelemetry(currentStop, 'GASTRO'));

    appendMessage(
      'USER',
      '🎙️ "Where can I get a great coffee or traditional Roman food nearby?"',
      'RAG QUERY: GEO-GASTRONOMY'
    );
    appendMessage(
      'AURELIUS',
      currentStop.gastroRag.answerSpeech,
      `GEO-RAG PLACES • ${currentStop.gastroRag.latencyMs}ms`
    );
    speakText(currentStop.gastroRag.answerSpeech);
  }, [currentStop, appendMessage, speakText]);

  const advanceToNextStop = useCallback(() => {
    const nextIdx = currentStopIndex + 1;
    if (nextIdx < ROME_STOPS.length) {
      walkToStopIndex(nextIdx);
    } else {
      setTourPhase('TOUR_COMPLETED');
      const farewell =
        'Optime! You have completed all five stops across Republican and Imperial Rome—from the Curia of Pompey to Hadrian’s Pantheon. May Fortuna guide your steps!';
      appendMessage('AURELIUS', farewell, 'TOUR COMPLETED');
      speakText(farewell);
    }
  }, [currentStopIndex, walkToStopIndex, appendMessage, speakText]);

  const finishTour = useCallback(() => {
    setTourPhase('TOUR_COMPLETED');
    const summaryText = `We have concluded our walk at ${currentStop.name}. Whenever you are ready, you can select any monument on the map to resume exploring Ancient Rome.`;
    appendMessage('USER', '🎙️ "Let’s finish the tour here for today."', 'VOICE INTENT');
    appendMessage('AURELIUS', summaryText, 'SESSION ENDED');
    speakText(summaryText);
  }, [currentStop, appendMessage, speakText]);

  const resetTour = useCallback(() => {
    stopSpeech();
    setCurrentStopIndex(0);
    setGpsPosition(ROME_STOPS[0].coords);
    setTourPhase('READY_TO_ARRIVE');
    setRagTelemetry(buildRagTelemetry(ROME_STOPS[0], 'OVERVIEW'));
    setMessages([
      {
        id: `reset_${Date.now()}`,
        sender: 'AURELIUS',
        tag: 'PERIPATETIC GPS GUIDE',
        timestamp: '09:30 AM',
        text: `Tour reset to Stop #1: ${ROME_STOPS[0].name}. Tap "Simulate 'I Have Arrived'" to begin the voice overview.`
      }
    ]);
  }, [stopSpeech, setGpsPosition]);

  return (
    <TourContext.Provider
      value={{
        stops: ROME_STOPS,
        activePage,
        setActivePage,
        layoutMode,
        setLayoutMode,
        currentStopIndex,
        currentStop,
        tourPhase,
        messages,
        ragTelemetry,
        gpsPosition,
        isWalking,
        walkProgress,
        audioEnabled,
        isSpeaking,
        toggleAudio,
        stopSpeech,
        walkToStopIndex,
        confirmArrivalAtStop,
        askHistoricalRag,
        askGastroRag,
        advanceToNextStop,
        finishTour,
        resetTour
      }}
    >
      {children}
    </TourContext.Provider>
  );
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error('useTour must be used within a TourProvider');
  }
  return context;
}
EOF

# ==========================================
# 5. SHARED COMPONENTS (ONE JSX + ONE CSS EACH)
# ==========================================
cat << 'EOF' > src/components/Navbar/Navbar.css
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: var(--bg-glass);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--gold-border);
  position: sticky;
  top: 0;
  z-index: 50;
  gap: 1rem;
  flex-wrap: wrap;
}

.navbar__brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.navbar__seal {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2b2112, #15120d);
  border: 1px solid var(--gold-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gold-primary);
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 0.8rem;
  letter-spacing: 0.06em;
  box-shadow: 0 0 18px rgba(212, 175, 55, 0.2);
}

.navbar__title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-marble);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.navbar__badge {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--crimson-soft);
  border: 1px solid var(--crimson-imperial);
  color: #fca5a5;
  letter-spacing: 0.04em;
}

.navbar__subtitle {
  font-size: 0.76rem;
  color: var(--text-muted);
}

.navbar__controls {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.navbar__btn {
  background: var(--bg-card);
  color: var(--text-travertine);
  border: 1px solid var(--border-subtle);
  padding: 0.45rem 0.85rem;
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.navbar__btn:hover {
  border-color: var(--gold-primary);
  color: var(--text-marble);
}

.navbar__btn--active {
  background: var(--gold-soft);
  border-color: var(--gold-primary);
  color: var(--gold-primary);
}

.navbar__btn--audio-on {
  background: var(--emerald-soft);
  border-color: var(--emerald-rag);
  color: #6ee7b7;
}
EOF

cat << 'EOF' > src/components/Navbar/Navbar.jsx
import React from 'react';
import { useTour } from '../../store/TourContext';
import './Navbar.css';

export function Navbar() {
  const {
    activePage,
    setActivePage,
    layoutMode,
    setLayoutMode,
    audioEnabled,
    toggleAudio,
    resetTour
  } = useTour();

  return (
    <header className="navbar">
      <div className="navbar__brand">
        <div className="navbar__seal">SPQR</div>
        <div>
          <div className="navbar__title">
            AURELIUS
            <span className="navbar__badge">VOICE AI + QDRANT RAG</span>
          </div>
          <p className="navbar__subtitle">
            Peripatetic Ancient Rome Historian • Republic &amp; Empire Interactive Portfolio Demo
          </p>
        </div>
      </div>

      <div className="navbar__controls">
        <button
          type="button"
          className={`navbar__btn ${activePage === 'WORKSTATION' ? 'navbar__btn--active' : ''}`}
          onClick={() => setActivePage('WORKSTATION')}
        >
          🧭 Live Rome Tour
        </button>

        <button
          type="button"
          className={`navbar__btn ${activePage === 'ARCHITECTURE' ? 'navbar__btn--active' : ''}`}
          onClick={() => setActivePage('ARCHITECTURE')}
        >
          🖼️ UI Screens &amp; Architecture
        </button>

        {activePage === 'WORKSTATION' && (
          <>
            <button
              type="button"
              className={`navbar__btn ${layoutMode === 'SPLIT' ? 'navbar__btn--active' : ''}`}
              onClick={() => setLayoutMode(layoutMode === 'SPLIT' ? 'MOBILE' : 'SPLIT')}
            >
              {layoutMode === 'SPLIT' ? '📱 Switch to Mobile Frame' : '🖥️ Switch to Split Workstation'}
            </button>

            <button
              type="button"
              className={`navbar__btn ${audioEnabled ? 'navbar__btn--audio-on' : ''}`}
              onClick={toggleAudio}
            >
              {audioEnabled ? '🔊 Real Voice TTS: ON' : '🔇 Enable Real Voice TTS'}
            </button>

            <button type="button" className="navbar__btn" onClick={resetTour}>
              ↺ Reset Walk
            </button>
          </>
        )}
      </div>
    </header>
  );
}
EOF

cat << 'EOF' > src/components/MonumentIllustration/MonumentIllustration.css
.monument-art {
  width: 100%;
  height: 155px;
  border-radius: var(--radius-md);
  overflow: hidden;
  position: relative;
  border: 1px solid var(--gold-border);
  background: linear-gradient(180deg, #1b1610 0%, #0e0c0a 100%);
}

.monument-art__svg {
  width: 100%;
  height: 100%;
  display: block;
}

.monument-art__overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(11, 10, 9, 0.1) 0%, rgba(11, 10, 9, 0.85) 100%);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 0.85rem 1rem;
}

.monument-art__era {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--gold-primary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.monument-art__name {
  font-family: var(--font-display);
  font-size: 1.15rem;
  color: var(--text-marble);
  font-weight: 700;
}

.monument-art__sub {
  font-size: 0.76rem;
  color: var(--text-travertine);
}
EOF

cat << 'EOF' > src/components/MonumentIllustration/MonumentIllustration.jsx
import React from 'react';
import './MonumentIllustration.css';

export function MonumentIllustration({ stop }) {
  if (!stop) return null;

  const renderArchitecturalVector = (id) => {
    switch (id) {
      case 'torre-argentina':
        return (
          <g stroke="#d4af37" strokeWidth="1.6" fill="none">
            <rect x="40" y="95" width="320" height="16" fill="rgba(212,175,55,0.12)" />
            {[70, 115, 160, 205, 250, 295].map((x, i) => (
              <g key={i}>
                <rect
                  x={x}
                  y={i % 2 === 0 ? 38 : 52}
                  width="14"
                  height={i % 2 === 0 ? 57 : 43}
                  fill="rgba(212,175,55,0.15)"
                />
                <line x1={x - 3} y1={i % 2 === 0 ? 38 : 52} x2={x + 17} y2={i % 2 === 0 ? 38 : 52} />
              </g>
            ))}
            <circle cx="330" cy="34" r="14" stroke="rgba(158,42,43,0.8)" fill="rgba(158,42,43,0.25)" />
          </g>
        );
      case 'forum-boarium':
        return (
          <g stroke="#d4af37" strokeWidth="1.6" fill="none">
            <polygon points="55,45 115,18 175,45" fill="rgba(212,175,55,0.16)" />
            {[68, 95, 122, 149].map((x) => (
              <rect key={x} x={x} y="45" width="10" height="52" fill="rgba(212,175,55,0.1)" />
            ))}
            <path d="M225,45 Q285,12 345,45 Z" fill="rgba(212,175,55,0.18)" />
            {[238, 262, 286, 310, 332].map((x) => (
              <line key={x} x1={x} y1="45" x2={x} y2="97" strokeWidth="4" />
            ))}
            <rect x="40" y="97" width="320" height="12" fill="rgba(212,175,55,0.14)" />
          </g>
        );
      case 'roman-forum':
        return (
          <g stroke="#d4af37" strokeWidth="1.6" fill="none">
            <polygon points="130,38 200,12 270,38" fill="rgba(212,175,55,0.16)" />
            <rect x="142" y="38" width="116" height="60" fill="rgba(212,175,55,0.08)" />
            <rect x="184" y="62" width="32" height="36" fill="rgba(212,175,55,0.22)" />
            {[55, 82, 108, 295, 325].map((x) => (
              <rect key={x} x={x} y="30" width="11" height="68" fill="rgba(212,175,55,0.14)" />
            ))}
            <rect x="35" y="98" width="330" height="12" fill="rgba(212,175,55,0.15)" />
          </g>
        );
      case 'trajans-markets':
        return (
          <g stroke="#d4af37" strokeWidth="1.6" fill="none">
            <path d="M55,102 A145,75 0 0,1 345,102" fill="rgba(158,42,43,0.15)" />
            {[85, 125, 165, 205, 245, 285, 315].map((x) => (
              <path
                key={x}
                d={`M${x - 10},98 L${x - 10},68 A10,10 0 0,1 ${x + 10},68 L${x + 10},98`}
                fill="rgba(212,175,55,0.14)"
              />
            ))}
            <rect x="192" y="14" width="16" height="86" fill="rgba(212,175,55,0.24)" />
          </g>
        );
      case 'pantheon':
      default:
        return (
          <g stroke="#d4af37" strokeWidth="1.6" fill="none">
            <path d="M75,78 A125,62 0 0,1 325,78 Z" fill="rgba(212,175,55,0.12)" />
            <polygon points="120,52 200,22 280,52" fill="rgba(212,175,55,0.2)" />
            {[132, 156, 180, 204, 228, 252, 268].map((x) => (
              <rect key={x} x={x} y="52" width="7" height="46" fill="rgba(212,175,55,0.15)" />
            ))}
            <rect x="65" y="98" width="270" height="10" fill="rgba(212,175,55,0.18)" />
          </g>
        );
    }
  };

  return (
    <div className="monument-art">
      <svg className="monument-art__svg" viewBox="0 0 400 130" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="goldGlow" cx="50%" cy="30%" r="65%">
            <stop offset="0%" stopColor="rgba(212, 175, 55, 0.25)" />
            <stop offset="100%" stopColor="rgba(11, 10, 9, 0)" />
          </radialGradient>
        </defs>
        <rect width="400" height="130" fill="url(#goldGlow)" />
        {renderArchitecturalVector(stop.id)}
      </svg>
      <div className="monument-art__overlay">
        <span className="monument-art__era">
          STOP #{stop.order} • {stop.era}
        </span>
        <h3 className="monument-art__name">{stop.name}</h3>
        <p className="monument-art__sub">{stop.subtitle}</p>
      </div>
    </div>
  );
}
EOF

cat << 'EOF' > src/components/VoiceOrb/VoiceOrb.css
.voice-orb {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 1rem;
  background: rgba(212, 175, 55, 0.07);
  border: 1px solid var(--gold-border);
  border-radius: var(--radius-md);
  gap: 0.85rem;
}

.voice-orb__left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.voice-orb__core {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--gold-primary) 0%, #7a5c12 70%, #1d1608 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 16px rgba(212, 175, 55, 0.35);
  transition: transform 0.3s ease;
}

.voice-orb__core--speaking {
  animation: pulseOrb 1.2s infinite ease-in-out;
}

@keyframes pulseOrb {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 14px rgba(212, 175, 55, 0.35);
  }
  50% {
    transform: scale(1.12);
    box-shadow: 0 0 28px rgba(212, 175, 55, 0.75);
  }
}

.voice-orb__meta {
  display: flex;
  flex-direction: column;
}

.voice-orb__speaker {
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--gold-primary);
  letter-spacing: 0.06em;
}

.voice-orb__status {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-travertine);
}

.voice-orb__bars {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 22px;
}

.voice-orb__bar {
  width: 3px;
  height: 6px;
  border-radius: 99px;
  background: var(--gold-primary);
  opacity: 0.45;
  transition: height 0.2s ease;
}

.voice-orb__bars--active .voice-orb__bar {
  opacity: 1;
  animation: soundWave 0.75s infinite ease-in-out alternate;
}

.voice-orb__bars--active .voice-orb__bar:nth-child(2) { animation-delay: 0.12s; }
.voice-orb__bars--active .voice-orb__bar:nth-child(3) { animation-delay: 0.24s; }
.voice-orb__bars--active .voice-orb__bar:nth-child(4) { animation-delay: 0.36s; }
.voice-orb__bars--active .voice-orb__bar:nth-child(5) { animation-delay: 0.18s; }

@keyframes soundWave {
  0% { height: 5px; }
  100% { height: 22px; }
}
EOF

cat << 'EOF' > src/components/VoiceOrb/VoiceOrb.jsx
import React from 'react';
import { useTour } from '../../store/TourContext';
import './VoiceOrb.css';

export function VoiceOrb() {
  const { isSpeaking, isWalking, tourPhase } = useTour();

  const getStatusLabel = () => {
    if (isWalking) return 'GPS WALKING SIMULATION ACTIVE...';
    if (isSpeaking) return 'SYNTHESIZING VOICE NARRATION...';
    if (tourPhase === 'READY_TO_ARRIVE') return 'AWAITING ARRIVAL CONFIRMATION';
    return 'LISTENING FOR TOURIST VOICE INTENT';
  };

  return (
    <div className="voice-orb">
      <div className="voice-orb__left">
        <div className={`voice-orb__core ${isSpeaking ? 'voice-orb__core--speaking' : ''}`}>
          🎙️
        </div>
        <div className="voice-orb__meta">
          <span className="voice-orb__speaker">AURELIUS // VOICE AI HISTORIAN</span>
          <span className="voice-orb__status">{getStatusLabel()}</span>
        </div>
      </div>

      <div className={`voice-orb__bars ${isSpeaking ? 'voice-orb__bars--active' : ''}`}>
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
        <span className="voice-orb__bar" />
      </div>
    </div>
  );
}
EOF

# ==========================================
# 6. FEATURES: MAP, VOICE GUIDE & RAG DRAWER
# ==========================================
cat << 'EOF' > src/features/map/RomeMapCanvas/RomeMapCanvas.css
.rome-map {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: var(--shadow-elevated);
}

.rome-map__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.8rem 1.1rem;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(15, 13, 11, 0.9);
  flex-wrap: wrap;
  gap: 0.5rem;
}

.rome-map__title {
  font-family: var(--font-display);
  font-size: 0.88rem;
  letter-spacing: 0.08em;
  color: var(--gold-primary);
}

.rome-map__gps-pill {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cyan-gps);
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
}

.rome-map__stage {
  position: relative;
  width: 100%;
  height: 390px;
  background: radial-gradient(circle at 50% 50%, #1a1713 0%, #0d0b09 100%);
}

.rome-map__svg {
  width: 100%;
  height: 100%;
  display: block;
}

.rome-map__pin {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.rome-map__floating-hud {
  position: absolute;
  bottom: 14px;
  left: 14px;
  right: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 1rem;
  background: rgba(16, 14, 12, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid var(--gold-border);
  border-radius: var(--radius-md);
  gap: 0.75rem;
  flex-wrap: wrap;
}

.rome-map__hud-info {
  display: flex;
  flex-direction: column;
}

.rome-map__hud-label {
  font-family: var(--font-mono);
  font-size: 0.66rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.rome-map__hud-stop {
  font-family: var(--font-display);
  font-size: 0.92rem;
  color: var(--text-marble);
  font-weight: 700;
}

.rome-map__arrive-btn {
  background: linear-gradient(135deg, #d4af37, #b5891c);
  color: #0b0a09;
  font-weight: 700;
  font-size: 0.8rem;
  border: none;
  padding: 0.55rem 1.05rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(212, 175, 55, 0.35);
  transition: transform 0.15s ease;
}

.rome-map__arrive-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.rome-map__arrive-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
EOF

cat << 'EOF' > src/features/map/RomeMapCanvas/RomeMapCanvas.jsx
import React from 'react';
import { useTour } from '../../../store/TourContext';
import { formatCoordinates } from '../../../utils/formatters';
import './RomeMapCanvas.css';

export function RomeMapCanvas() {
  const {
    stops,
    currentStopIndex,
    currentStop,
    tourPhase,
    gpsPosition,
    isWalking,
    walkProgress,
    walkToStopIndex,
    confirmArrivalAtStop
  } = useTour();

  const routePoints = stops.map((s) => `${s.coords.mapX},${s.coords.mapY}`).join(' ');

  return (
    <section className="rome-map">
      <div className="rome-map__header">
        <span className="rome-map__title">
          🗺️ FORMA URBIS ROMAE // INTERACTIVE PERIPATETIC RADAR
        </span>
        <span className="rome-map__gps-pill">
          GPS: {formatCoordinates(gpsPosition?.lat, gpsPosition?.lng)}
        </span>
      </div>

      <div className="rome-map__stage">
        <svg className="rome-map__svg" viewBox="0 0 700 540">
          <defs>
            <pattern id="romanGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="rgba(212, 175, 55, 0.06)"
                strokeWidth="1"
              />
            </pattern>
          </defs>

          <rect width="700" height="540" fill="url(#romanGrid)" />

          {/* Ancient Aurelian Walls & Hills Contours */}
          <ellipse
            cx="520"
            cy="430"
            rx="95"
            ry="60"
            fill="rgba(212, 175, 55, 0.03)"
            stroke="rgba(212, 175, 55, 0.12)"
            strokeDasharray="4 4"
          />
          <text x="485" y="435" fill="rgba(212,175,55,0.28)" fontSize="11" fontFamily="Cinzel">
            MONS PALATINUS
          </text>

          <ellipse
            cx="575"
            cy="220"
            rx="90"
            ry="52"
            fill="rgba(212, 175, 55, 0.03)"
            stroke="rgba(212, 175, 55, 0.12)"
            strokeDasharray="4 4"
          />
          <text x="535" y="220" fill="rgba(212,175,55,0.28)" fontSize="11" fontFamily="Cinzel">
            COLLIS QUIRINALIS
          </text>

          <text x="190" y="145" fill="rgba(212,175,55,0.28)" fontSize="12" fontFamily="Cinzel">
            CAMPUS MARTIUS
          </text>

          {/* Tiber River (Flumen Tiberis) */}
          <path
            d="M 140,0 C 125,120 110,220 185,310 C 255,390 215,470 165,540"
            fill="none"
            stroke="rgba(56, 189, 248, 0.18)"
            strokeWidth="36"
            strokeLinecap="round"
          />
          <path
            d="M 140,0 C 125,120 110,220 185,310 C 255,390 215,470 165,540"
            fill="none"
            stroke="rgba(56, 189, 248, 0.45)"
            strokeWidth="2"
            strokeDasharray="6 6"
          />
          <text x="72" y="275" fill="rgba(56, 189, 248, 0.5)" fontSize="10" fontFamily="Cinzel">
            FLUMEN TIBERIS
          </text>

          {/* Tour Walking Route */}
          <polyline
            points={routePoints}
            fill="none"
            stroke="rgba(212, 175, 55, 0.45)"
            strokeWidth="3"
            strokeDasharray="7 5"
          />

          {/* 5 Monument Pins */}
          {stops.map((stop, index) => {
            const isSelected = index === currentStopIndex;
            const isVisited = index < currentStopIndex;
            return (
              <g
                key={stop.id}
                className="rome-map__pin"
                transform={`translate(${stop.coords.mapX}, ${stop.coords.mapY})`}
                onClick={() => walkToStopIndex(index)}
              >
                {isSelected && (
                  <circle
                    r="24"
                    fill="rgba(212, 175, 55, 0.16)"
                    stroke="#d4af37"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                  />
                )}
                <circle
                  r="14"
                  fill={isSelected ? '#d4af37' : isVisited ? '#2b251c' : '#171411'}
                  stroke="#d4af37"
                  strokeWidth="2"
                />
                <text
                  textAnchor="middle"
                  dy="4"
                  fill={isSelected ? '#0b0a09' : '#f5f2eb'}
                  fontSize="11"
                  fontWeight="700"
                  fontFamily="JetBrains Mono"
                >
                  {stop.order}
                </text>
                <rect
                  x="-78"
                  y="20"
                  width="156"
                  height="22"
                  rx="5"
                  fill="rgba(14, 12, 10, 0.9)"
                  stroke={isSelected ? '#d4af37' : 'rgba(255,255,255,0.12)'}
                />
                <text
                  x="0"
                  y="35"
                  textAnchor="middle"
                  fill={isSelected ? '#d4af37' : '#c8c1b4'}
                  fontSize="10"
                  fontWeight="600"
                >
                  {stop.name}
                </text>
              </g>
            );
          })}

          {/* Animated Live User GPS Marker */}
          {gpsPosition && (
            <g transform={`translate(${gpsPosition.mapX}, ${gpsPosition.mapY})`}>
              <circle r="18" fill="rgba(56, 189, 248, 0.22)" />
              <circle r="7" fill="#38bdf8" stroke="#0b0a09" strokeWidth="2" />
            </g>
          )}
        </svg>

        <div className="rome-map__floating-hud">
          <div className="rome-map__hud-info">
            <span className="rome-map__hud-label">
              {isWalking
                ? `WALKING ALONG VIA SACRA (${walkProgress}%)`
                : `CURRENT STOP #${currentStop.order} • ${currentStop.era}`}
            </span>
            <span className="rome-map__hud-stop">{currentStop.name}</span>
          </div>

          <button
            type="button"
            className="rome-map__arrive-btn"
            disabled={isWalking}
            onClick={confirmArrivalAtStop}
          >
            {tourPhase === 'READY_TO_ARRIVE'
              ? "📍 Simulate 'I Have Arrived'"
              : '🔄 Replay Arrival Overview'}
          </button>
        </div>
      </div>
    </section>
  );
}
EOF

cat << 'EOF' > src/features/map/StopTimelineBar/StopTimelineBar.css
.stop-timeline {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 0.6rem;
  overflow-x: auto;
}

.stop-timeline__item {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 0.65rem 0.75rem;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stop-timeline__item:hover {
  border-color: var(--gold-primary);
  background: var(--bg-card-hover);
}

.stop-timeline__item--active {
  background: var(--gold-soft);
  border-color: var(--gold-primary);
}

.stop-timeline__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--gold-primary);
}

.stop-timeline__name {
  font-family: var(--font-display);
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-marble);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stop-timeline__era {
  font-size: 0.68rem;
  color: var(--text-muted);
}
EOF

cat << 'EOF' > src/features/map/StopTimelineBar/StopTimelineBar.jsx
import React from 'react';
import { useTour } from '../../../store/TourContext';
import './StopTimelineBar.css';

export function StopTimelineBar() {
  const { stops, currentStopIndex, walkToStopIndex } = useTour();

  return (
    <div className="stop-timeline">
      {stops.map((stop, idx) => {
        const isActive = idx === currentStopIndex;
        return (
          <button
            key={stop.id}
            type="button"
            className={`stop-timeline__item ${isActive ? 'stop-timeline__item--active' : ''}`}
            onClick={() => walkToStopIndex(idx)}
          >
            <div className="stop-timeline__top">
              <span>STOP 0{stop.order}</span>
              <span>{stop.periodTag}</span>
            </div>
            <div className="stop-timeline__name">{stop.name}</div>
            <div className="stop-timeline__era">{stop.era}</div>
          </button>
        );
      })}
    </div>
  );
}
EOF

cat << 'EOF' > src/features/voiceGuide/ActionPromptChips/ActionPromptChips.css
.action-chips {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border-subtle);
}

.action-chips__label {
  font-family: var(--font-mono);
  font-size: 0.66rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.action-chips__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.action-chips__btn {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-marble);
  padding: 0.6rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.76rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.action-chips__btn:hover:not(:disabled) {
  border-color: var(--gold-primary);
  background: var(--bg-card-hover);
}

.action-chips__btn--primary {
  grid-column: span 2;
  background: linear-gradient(135deg, rgba(212, 175, 55, 0.22), rgba(212, 175, 55, 0.08));
  border-color: var(--gold-primary);
  color: var(--gold-primary);
  justify-content: center;
  font-size: 0.82rem;
}

.action-chips__btn--rag {
  border-color: rgba(16, 185, 129, 0.35);
}

.action-chips__btn--gastro {
  border-color: rgba(245, 158, 11, 0.35);
}

.action-chips__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
EOF

cat << 'EOF' > src/features/voiceGuide/ActionPromptChips/ActionPromptChips.jsx
import React from 'react';
import { useTour } from '../../../store/TourContext';
import './ActionPromptChips.css';

export function ActionPromptChips() {
  const {
    tourPhase,
    isWalking,
    currentStopIndex,
    stops,
    confirmArrivalAtStop,
    askHistoricalRag,
    askGastroRag,
    advanceToNextStop,
    finishTour
  } = useTour();

  const hasNextStop = currentStopIndex < stops.length - 1;

  return (
    <div className="action-chips">
      <span className="action-chips__label">
        🎙️ SIMULATE VOICE TOURIST RESPONSES (POST-ARRIVAL OPTIONS)
      </span>

      <div className="action-chips__grid">
        {tourPhase === 'READY_TO_ARRIVE' || tourPhase === 'WALKING_TO_STOP' ? (
          <button
            type="button"
            className="action-chips__btn action-chips__btn--primary"
            disabled={isWalking}
            onClick={confirmArrivalAtStop}
          >
            📍 &ldquo;I&apos;ve arrived at the monument&rdquo; (Trigger Overview)
          </button>
        ) : (
          <>
            <button
              type="button"
              className="action-chips__btn action-chips__btn--rag"
              onClick={askHistoricalRag}
            >
              🏛️ 1. Historical &amp; Cultural Details (RAG)
            </button>

            <button
              type="button"
              className="action-chips__btn action-chips__btn--gastro"
              onClick={askGastroRag}
            >
              ☕ 2. Go to Coffee / Trattoria (Geo-RAG)
            </button>

            <button
              type="button"
              className="action-chips__btn"
              onClick={advanceToNextStop}
            >
              🚶 3. {hasNextStop ? 'Walk to Next Stop' : 'Complete Final Stop'}
            </button>

            <button
              type="button"
              className="action-chips__btn"
              onClick={finishTour}
            >
              🏁 4. Finish Tour Here
            </button>
          </>
        )}
      </div>
    </div>
  );
}
EOF

cat << 'EOF' > src/features/voiceGuide/HistorianVoicePanel/HistorianVoicePanel.css
.voice-panel {
  background: var(--bg-panel);
  border: 1px solid var(--gold-border);
  border-radius: var(--radius-lg);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  box-shadow: var(--shadow-elevated);
  height: 100%;
}

.voice-panel__transcript {
  flex: 1;
  min-height: 230px;
  max-height: 310px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding-right: 0.25rem;
}

.voice-panel__msg {
  padding: 0.75rem 0.9rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.voice-panel__msg--ai {
  border-left: 3px solid var(--gold-primary);
}

.voice-panel__msg--user {
  background: rgba(212, 175, 55, 0.08);
  border-color: var(--gold-border);
  align-self: flex-end;
  max-width: 90%;
}

.voice-panel__msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--gold-primary);
}

.voice-panel__msg-text {
  font-family: var(--font-editorial);
  font-size: 1.04rem;
  line-height: 1.48;
  color: var(--text-marble);
}

.voice-panel__msg--user .voice-panel__msg-text {
  font-family: var(--font-sans);
  font-size: 0.82rem;
}
EOF

cat << 'EOF' > src/features/voiceGuide/HistorianVoicePanel/HistorianVoicePanel.jsx
import React, { useEffect, useRef } from 'react';
import { useTour } from '../../../store/TourContext';
import { MonumentIllustration } from '../../../components/MonumentIllustration/MonumentIllustration';
import { VoiceOrb } from '../../../components/VoiceOrb/VoiceOrb';
import { ActionPromptChips } from '../ActionPromptChips/ActionPromptChips';
import './HistorianVoicePanel.css';

export function HistorianVoicePanel() {
  const { currentStop, messages } = useTour();
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <aside className="voice-panel">
      <MonumentIllustration stop={currentStop} />
      <VoiceOrb />

      <div className="voice-panel__transcript">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`voice-panel__msg ${
              msg.sender === 'AURELIUS' ? 'voice-panel__msg--ai' : 'voice-panel__msg--user'
            }`}
          >
            <div className="voice-panel__msg-header">
              <span>
                {msg.sender} {msg.tag ? `// ${msg.tag}` : ''}
              </span>
              <span>{msg.timestamp}</span>
            </div>
            <p className="voice-panel__msg-text">{msg.text}</p>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <ActionPromptChips />
    </aside>
  );
}
EOF

cat << 'EOF' > src/features/rag/RagTelemetryDrawer/RagTelemetryDrawer.css
.rag-drawer {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 1rem 1.15rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rag-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.rag-drawer__badge {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: var(--emerald-soft);
  border: 1px solid var(--emerald-rag);
  color: #6ee7b7;
}

.rag-drawer__metrics {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.rag-drawer__query {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-sm);
  background: #090807;
  border: 1px solid var(--border-subtle);
  color: var(--gold-primary);
  overflow-x: auto;
}

.rag-drawer__chunks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0.65rem;
}

.rag-drawer__chunk {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.7rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.rag-drawer__chunk-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.rag-drawer__chunk-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-marble);
}

.rag-drawer__score {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--emerald-rag);
}

.rag-drawer__chunk-sub {
  font-size: 0.68rem;
  color: var(--gold-primary);
}

.rag-drawer__chunk-snippet {
  font-size: 0.75rem;
  color: var(--text-travertine);
  line-height: 1.4;
}
EOF

cat << 'EOF' > src/features/rag/RagTelemetryDrawer/RagTelemetryDrawer.jsx
import React from 'react';
import { useTour } from '../../../store/TourContext';
import { formatConfidence } from '../../../utils/formatters';
import './RagTelemetryDrawer.css';

export function RagTelemetryDrawer() {
  const { ragTelemetry } = useTour();

  if (!ragTelemetry) return null;

  return (
    <section className="rag-drawer">
      <div className="rag-drawer__header">
        <span className="rag-drawer__badge">{ragTelemetry.badge}</span>
        <span className="rag-drawer__metrics">
          COLLECTION: {ragTelemetry.collection} • LATENCY: {ragTelemetry.latencyMs}ms
        </span>
      </div>

      <div className="rag-drawer__query">{ragTelemetry.query}</div>

      <div className="rag-drawer__chunks">
        {ragTelemetry.items.map((item) => (
          <article key={item.id} className="rag-drawer__chunk">
            <div className="rag-drawer__chunk-top">
              <span className="rag-drawer__chunk-title">{item.title}</span>
              <span className="rag-drawer__score">{formatConfidence(item.score)}</span>
            </div>
            <span className="rag-drawer__chunk-sub">{item.subtitle}</span>
            <p className="rag-drawer__chunk-snippet">{item.snippet}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
EOF

# ==========================================
# 7. LAYOUTS, PAGES & ROUTER
# ==========================================
cat << 'EOF' > src/layouts/MainLayout/MainLayout.css
.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main-layout__content {
  flex: 1;
  width: 100%;
  max-width: 1480px;
  margin: 0 auto;
  padding: 1.1rem 1.4rem 2rem;
}
EOF

cat << 'EOF' > src/layouts/MainLayout/MainLayout.jsx
import React from 'react';
import { Navbar } from '../../components/Navbar/Navbar';
import './MainLayout.css';

export function MainLayout({ children }) {
  return (
    <div className="main-layout">
      <Navbar />
      <main className="main-layout__content">{children}</main>
    </div>
  );
}
EOF

cat << 'EOF' > src/pages/TourWorkstationPage/TourWorkstationPage.css
.workstation-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.workstation-page__grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 1.1rem;
  align-items: stretch;
}

.workstation-page__left {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.workstation-page--mobile {
  max-width: 440px;
  margin: 0 auto;
}

.workstation-page--mobile .workstation-page__grid {
  grid-template-columns: 1fr;
}

@media (max-width: 1024px) {
  .workstation-page__grid {
    grid-template-columns: 1fr;
  }
}
EOF

cat << 'EOF' > src/pages/TourWorkstationPage/TourWorkstationPage.jsx
import React from 'react';
import { useTour } from '../../store/TourContext';
import { StopTimelineBar } from '../../features/map/StopTimelineBar/StopTimelineBar';
import { RomeMapCanvas } from '../../features/map/RomeMapCanvas/RomeMapCanvas';
import { HistorianVoicePanel } from '../../features/voiceGuide/HistorianVoicePanel/HistorianVoicePanel';
import { RagTelemetryDrawer } from '../../features/rag/RagTelemetryDrawer/RagTelemetryDrawer';
import './TourWorkstationPage.css';

export function TourWorkstationPage() {
  const { layoutMode } = useTour();

  return (
    <div
      className={`workstation-page ${
        layoutMode === 'MOBILE' ? 'workstation-page--mobile' : ''
      }`}
    >
      <StopTimelineBar />

      <div className="workstation-page__grid">
        <div className="workstation-page__left">
          <RomeMapCanvas />
          <RagTelemetryDrawer />
        </div>

        <HistorianVoicePanel />
      </div>
    </div>
  );
}
EOF

cat << 'EOF' > src/pages/ArchitecturePreviewPage/ArchitecturePreviewPage.css
.arch-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.arch-page__hero {
  background: var(--bg-panel);
  border: 1px solid var(--gold-border);
  border-radius: var(--radius-lg);
  padding: 1.4rem;
}

.arch-page__title {
  font-family: var(--font-display);
  font-size: 1.35rem;
  color: var(--gold-primary);
  margin-bottom: 0.4rem;
}

.arch-page__subtitle {
  font-size: 0.88rem;
  color: var(--text-travertine);
  line-height: 1.5;
}

.arch-page__screens {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
  gap: 1rem;
}

.arch-page__card {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.arch-page__step {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--gold-primary);
}

.arch-page__card-title {
  font-family: var(--font-display);
  font-size: 1rem;
  color: var(--text-marble);
}

.arch-page__card-desc {
  font-size: 0.8rem;
  color: var(--text-travertine);
  line-height: 1.45;
}

.arch-page__stops-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0.85rem;
}
EOF

cat << 'EOF' > src/pages/ArchitecturePreviewPage/ArchitecturePreviewPage.jsx
import React from 'react';
import { ROME_STOPS } from '../../lib/romeStopsData';
import { MonumentIllustration } from '../../components/MonumentIllustration/MonumentIllustration';
import './ArchitecturePreviewPage.css';

export function ArchitecturePreviewPage() {
  const uiStates = [
    {
      step: 'SCREEN STATE 01 // PERIPATETIC GPS MAP',
      title: 'Interactive Forma Urbis Radar',
      desc: 'Simulates walking between 5 Republican & Imperial monuments along the Tiber and Via Sacra with real-time coordinate interpolation.'
    },
    {
      step: 'SCREEN STATE 02 // GEOFENCE ARRIVAL OVERVIEW',
      title: 'Voice AI Monument Introduction',
      desc: 'When the user indicates arrival, Aurelius delivers a historically grounded overview of the monument and prompts for next actions.'
    },
    {
      step: 'SCREEN STATE 03 // CLASSICAL RAG DEEP DIVE',
      title: 'Primary Sources Vector Retrieval',
      desc: 'Queries embedded passages from Suetonius, Livy, Vitruvius, and Cassius Dio with live cosine similarity telemetry.'
    },
    {
      step: 'SCREEN STATE 04 // GASTRO GEO-RAG',
      title: 'Proximity Espresso & Trattoria RAG',
      desc: 'Performs geo-spatial filtering around the monument coordinates to recommend authentic Roman roasteries and historic osterie.'
    }
  ];

  return (
    <div className="arch-page">
      <div className="arch-page__hero">
        <h2 className="arch-page__title">
          AURELIUS // UI SCREENS &amp; MODULAR RAG ARCHITECTURE
        </h2>
        <p className="arch-page__subtitle">
          Built with strict modular separation: one JSX + one CSS file per component and feature,
          powered by a conversational state machine and dual-index RAG (Classical History Corpus +
          Geo-Spatial Roman Gastronomy).
        </p>
      </div>

      <div className="arch-page__screens">
        {uiStates.map((item) => (
          <div key={item.step} className="arch-page__card">
            <span className="arch-page__step">{item.step}</span>
            <h3 className="arch-page__card-title">{item.title}</h3>
            <p className="arch-page__card-desc">{item.desc}</p>
          </div>
        ))}
      </div>

      <h3 className="arch-page__title">5 Curated Ancient Rome Stops (Vector Artwork Previews)</h3>
      <div className="arch-page__stops-gallery">
        {ROME_STOPS.map((stop) => (
          <MonumentIllustration key={stop.id} stop={stop} />
        ))}
      </div>
    </div>
  );
}
EOF

cat << 'EOF' > src/router/AppRouter.css
.app-router {
  width: 100%;
}
EOF

cat << 'EOF' > src/router/AppRouter.jsx
import React from 'react';
import { useTour } from '../store/TourContext';
import { TourWorkstationPage } from '../pages/TourWorkstationPage/TourWorkstationPage';
import { ArchitecturePreviewPage } from '../pages/ArchitecturePreviewPage/ArchitecturePreviewPage';
import './AppRouter.css';

export function AppRouter() {
  const { activePage } = useTour();

  return (
    <div className="app-router">
      {activePage === 'ARCHITECTURE' ? (
        <ArchitecturePreviewPage />
      ) : (
        <TourWorkstationPage />
      )}
    </div>
  );
}
EOF

# ==========================================
# 8. ROOT APP & MAIN ENTRYPOINT
# ==========================================
cat << 'EOF' > src/App.jsx
import React from 'react';
import { TourProvider } from './store/TourContext';
import { MainLayout } from './layouts/MainLayout/MainLayout';
import { AppRouter } from './router/AppRouter';
import './App.css';

export function App() {
  return (
    <TourProvider>
      <div className="app-shell">
        <MainLayout>
          <AppRouter />
        </MainLayout>
      </div>
    </TourProvider>
  );
}

export default App;
EOF

cat << 'EOF' > src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import './theme.css';
import './index.css';
import App from './App.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
EOF

echo "✅ All modular JSX, CSS, Hook, Store, and RAG files created successfully!"