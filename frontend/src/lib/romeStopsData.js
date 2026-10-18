export const ROME_STOPS = [
  {
    id: 'torre-argentina',
    apiStop: 'Torre_Argentina',
    order: 1,
    name: 'Largo di Torre Argentina',
    subtitle: 'Curia of Pompey & Sacred Area',
    era: 'Roman Republic • 44 BC',
    periodTag: 'REPUBLIC',
    coords: { lat: 41.8954, lng: 12.4768, mapX: 280, mapY: 310 },
    distanceMeters: 420,
    walkSeconds: 4,
    historicalRag: {
      query: 'vector_search("Curia of Pompey assassination Julius Caesar Ides of March 44 BC architectural context")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 142,
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
    apiStop: 'Forum_Boarium',
    order: 2,
    name: 'Forum Boarium',
    subtitle: 'Temples of Portunus & Hercules Victor',
    era: 'Mid-Late Republic • 2nd Century BC',
    periodTag: 'REPUBLIC',
    coords: { lat: 41.8887, lng: 12.4807, mapX: 335, mapY: 465 },
    distanceMeters: 680,
    walkSeconds: 4,
    historicalRag: {
      query: 'vector_search("Forum Boarium Temple of Hercules Victor Greek marble Republican merchants")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 134,
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
    apiStop: 'Roman_Forum',
    order: 3,
    name: 'The Roman Forum',
    subtitle: 'Curia Julia, Rostra & Via Sacra',
    era: 'Republic to Principate • 44 BC – 14 AD',
    periodTag: 'TRANSITION',
    coords: { lat: 41.8925, lng: 12.4853, mapX: 495, mapY: 365 },
    distanceMeters: 590,
    walkSeconds: 4,
    historicalRag: {
      query: 'vector_search("Rostra Curia Julia Cicero Philippics Mark Antony Augustus Res Gestae")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 151,
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
    apiStop: 'Trajans_Markets',
    order: 4,
    name: "Trajan's Forum & Markets",
    subtitle: 'Mercati di Traiano & Ulpian Basilica',
    era: 'High Empire • 107 – 113 AD',
    periodTag: 'EMPIRE',
    coords: { lat: 41.8956, lng: 12.4861, mapX: 525, mapY: 270 },
    distanceMeters: 450,
    walkSeconds: 4,
    historicalRag: {
      query: 'vector_search("Apollodorus of Damascus Trajan Markets Quirinal Hill excavation Dacian gold")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 138,
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
    apiStop: 'Pantheon',
    order: 5,
    name: 'The Pantheon',
    subtitle: 'Rotunda of Agrippa & Hadrian',
    era: 'High Empire • 118 – 128 AD',
    periodTag: 'EMPIRE',
    coords: { lat: 41.8986, lng: 12.4769, mapX: 290, mapY: 205 },
    distanceMeters: 740,
    walkSeconds: 4,
    historicalRag: {
      query: 'vector_search("Pantheon Hadrian unreinforced concrete dome oculus aggregate gradation")',
      collection: 'ancient_rome_primary_sources_v3',
      latencyMs: 129,
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
