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
