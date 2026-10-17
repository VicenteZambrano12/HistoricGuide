# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pypdf>=6.21.1",
#     "reportlab>=5.0.1",
# ]
# ///
import os
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
)
from pypdf import PdfReader

# Set to 10 pages per PDF (~100 pages total) as requested in prompt.
# Change to 5 if you strictly need the 5-page count from the screenshot.
PAGES_PER_PDF = 10

OUTPUT_DIRS = ["./rag_corpus", "./public/rag_corpus"]

STOPS_DATA = [
    {
        "stop_num": 1,
        "slug": "Torre_Argentina",
        "name": "Largo di Torre Argentina",
        "era": "Republican Era (4th–1st Century BC)",
        "location": "Campo Marzio / Sant'Eustachio, Rome",
        "coords": "41.8954° N, 12.4769° E",
        "hist_overview": (
            "Largo di Torre Argentina is an archaeological sanctuary sits in the ancient Campus Martius, "
            "housing four Republican Roman temples (designated A, B, C, and D by archaeologists because their "
            "original dedications were initially uncertain) alongside the monumental tufa foundations of the "
            "Curia of Pompey—the exact site where Gaius Julius Caesar was assassinated on the Ides of March (15 March, 44 BC)."
        ),
        "monuments": [
            ("Temple C (Feronia)", "Late 4th / Early 3rd Century BC", "Oldest of the four temples, dedicated to Feronia, ancient italic goddess of fertility, wildlife, and freedmen. Built on a high tufa podium with mosaic fragments post-80 BC fire."),
            ("Temple A (Juturna)", "Mid-3rd Century BC (241 BC)", "Vowed by Gaius Lutatius Catulus after the naval victory over Carthage at the Aegates Islands ending the First Punic War. Later integrated into the apse of the medieval church of San Nicola dei Cesarini."),
            ("Temple D (Lares Permarini)", "Early 2nd Century BC (190 BC)", "The largest temple of the complex, vowed by Pretor Lucius Aemilius Regillus during the naval Battle of Myonessus against Antiochus III; mostly unexcavated beneath Via Florida."),
            ("Temple B (Fortuna Huiusce Diei)", "101 BC", "Circular monopteros temple ('Fortune of This Present Day') vowed by Quintus Lutatius Catulus at the Battle of Vercellae against the Cimbri. Home to the colossal acrolithic statue found on site."),
            ("Curia of Pompey & Porticus Pompeiana", "55 BC", "Monumental rectangular meeting hall at the eastern edge of Pompey's theater complex where the Roman Senate convened temporarily while the Curia Julia was being rebuilt.")
        ],
        "arch_details": (
            "Excavated between 1926 and 1929 during urban demolition works, the Area Sacra exposes three distinct "
            "stratigraphic pavement levels: the original Republican tufa ground level, the post-111 BC fire restoration pavement "
            "combining Monteverde and Aniene tufa, and the Imperial travertine raising executed under Domitian after the devastating fire of AD 80."
        ),
        "figures": [
            ("Gaius Julius Caesar", "Dictator Perpetuo assassinated at the base of Pompey's statue inside the Curia Pompeia on March 15, 44 BC."),
            ("Gnaeus Pompeius Magnus (Pompey the Great)", "Triumvir who funded the first permanent stone theater and attached Curia in Rome outside the sacred pomerium."),
            ("Marcus Junius Brutus & Gaius Cassius Longinus", "Leaders of the Liberatores faction who orchestrated the senatorial conspiracy in the Porticus Pompeiana."),
            ("Emperor Augustus", "Walled off the Curia of Pompey after 44 BC, declaring it a locus sceleratus (accursed place) and converting it into public latrines.")
        ],
        "inscriptions": (
            "Key epigraphic and sculptural finds housed in the Centrale Montemartini and Capitoline Museums include the colossal marble "
            "head, arms, and feet of the acrolithic cult statue of Fortuna Huiusce Diei (sculpted by Skopas Minor), Republican altar dedications "
            "by Aulus Postumius Albinus (175 BC), and the imperial travertine drainage slabs marking Domitian's urban leveling."
        ),
        "venues": [
            ("Antico Forno Roscioli", "Via dei Chiavari 34", "Bakery & Roman Street Food", "€–€€", "Legendary thin, crispy Pizza Rossa, Supplì al Telefono, and artisanal sourdough focaccia baked steps from Pompey's Theater.", "07:00 – 19:30"),
            ("Salumeria Roscioli", "Via dei Giubbonari 21", "Gastronomic Trattoria & Wine Bar", "€€€", "World-renowned Carbonara made with guanciale di Amatrice, aged Parmigiano, and Paolo Parisi eggs; cellar with 2,800+ wine labels.", "12:30 – 16:00, 19:00 – 23:30"),
            ("Sant'Eustachio Il Caffè", "Piazza di Sant'Eustachio 82", "Historic Espresso Roaster (Est. 1938)", "€", "Famous wood-roasted 'Gran Caffè' whipped with a secret crema recipe; iconic yellow mosaic stag crest above the doorway.", "07:30 – 00:00"),
            ("Pasticceria Boccione", "Via del Portico d'Ottavia 1", "Historic Judeo-Roman Bakery", "€", "Unmarked family bakery serving Crostata di Ricotta e Visciole (sour cherry and ricotta tart) and Pizza Ebraica since 1815.", "08:00 – 19:30 (Closed Sat)"),
            ("Armando al Pantheon", "Salita de' Crescenzi 31", "Classic Roman Trattoria", "€€€", "Family-run since 1961; famous for Spaghetti alla Gricia, Coda alla Vaccinara, and Abbacchio a Scottadito.", "12:30 – 15:00, 19:00 – 23:00"),
            ("Emma Pizzeria con Cucina", "Via del Monte della Farina 28", "Roman Thin-Crust Pizzeria", "€€", "Crisp scrocchiarella Roman-style pizzas topped with Pierluigi meats and artisanal cheeses in a sleek courtyard dining room.", "12:30 – 15:30, 19:00 – 23:30"),
            ("Open Baladin Roma", "Via degli Specchi 6", "Craft Beer & Gourmet Burger Hub", "€€", "40+ Italian craft beers on tap created by Teo Musso, paired with cacio e pepe homemade potato chips and Roman maritozzi.", "12:00 – 01:00"),
            ("Da Enzo al 29 (Nearby Ripa/Ghetto walk)", "Via dei Vascellari 29", "Authentic Trattoria", "€€", "Benchmark Tonnarelli Cacio e Pepe, fried Carciofi alla Giudia, and mascarpone tiramisu served in brown paper-lined tables.", "12:15 – 15:00, 19:00 – 23:00")
        ]
    },
    {
        "stop_num": 2,
        "slug": "Forum_Boarium",
        "name": "Forum Boarium & Velabrum",
        "era": "Regal & Republican Era (7th–1st Century BC)",
        "location": "Piazza della Bocca della Verità / Ripa, Rome",
        "coords": "41.8887° N, 12.4814° E",
        "hist_overview": (
            "Positioned at the original natural ford of the Tiber River nestled between the Capitoline, Palatine, and Aventine hills, "
            "the Forum Boarium was ancient Rome's bustling river port (Portus Tiberinus) and cattle market. It represents the earliest "
            "commercial nexus of the city, housing two of the best-preserved Republican temples in the Mediterranean."
        ),
        "monuments": [
            ("Temple of Hercules Victor (Olivarius)", "Late 2nd Century BC (~120 BC)", "Oldest surviving marble building in Rome. A Greek-style circular peripteral monopteros of 20 Corinthian columns in Pentelic marble, commissioned by merchant Marcus Octavius Hersennus and sculpted by Scopas Minor."),
            ("Temple of Portunus", "Late 2nd / Early 1st Century BC", "Iconic rectangular Ionic pseudoperipteral temple dedicated to Portunus, god of keys, doors, livestock, and river harbors. Constructed of tufa and travertine with original stucco flutes."),
            ("Arcus Argentariorum (Arch of the Moneychangers)", "AD 204", "Elaborately carved marble lintel dedicated to Septimius Severus, Julia Domna, Caracalla, and Geta; Geta's figure was chiselled off following his damnatio memoriae in AD 212."),
            ("Arch of Janus (Ianus Quadrifrons)", "Early 4th Century AD", "Monumental four-way vaulted marble boundary marker erected under Constantine I at the crossroads of the Velabrum using repurposed imperial spolia."),
            ("Bocca della Verità & Santa Maria in Cosmedin", "2nd Century BC / 8th Century AD", "Colossal Pavonazzetto marble drain cover depicting Oceanus housed in the portico of Santa Maria in Cosmedin, built atop the ancient Ara Maxima of Hercules.")
        ],
        "arch_details": (
            "The survival of both Republican temples is owed to their early medieval Christian consecration—Hercules Victor became "
            "Santo Stefano alle Carrozze and Portunus became Santa Maria Egiziaca in AD 872. Underground beneath the piazza runs the "
            "Cloaca Maxima, engineered under the Etruscan Tarquin kings in the 6th century BC to drain the marshy Velabrum valley into the Tiber."
        ),
        "figures": [
            ("Hercules & Cacus", "Mythological foundation story where Hercules slew the fire-breathing giant Cacus on the Aventine slope after Cacus stole Geryon's cattle."),
            ("Marcus Octavius Hersennus", "Wealthy Tiburtine olive oil merchant who financed the Pentelic marble tholos of Hercules Olivarius."),
            ("Servius Tullius", "Sixth King of Rome credited with building the archaic twin sanctuary of Fortuna and Mater Matuta at adjacent Sant'Omobono."),
            ("Septimius Severus & Caracalla", "Severan emperors depicted performing sacrificial libations on the relief panels of the Argentarii gateway.")
        ],
        "inscriptions": (
            "The pedestal inscription of the statue of Hercules Olivarius reads 'HERCVLI VICTOR / OPUS SCOPAE MINORIS', settling centuries "
            "of misidentification as the Temple of Vesta. Nearby, the Arch of the Argentarii preserves the full Severan imperial titulature "
            "with visible chisel scars erasing Publius Septimius Geta's name and portrait."
        ),
        "venues": [
            ("Nonna Betta", "Via del Portico d'Ottavia 16", "Judeo-Roman Kosher Trattoria", "€€", "Crisp double-fried Carciofi alla Giudia (Jewish-style artichokes), homemade agnolotti con stracotto, and fried zucchini blossoms.", "11:00 – 23:00"),
            ("Sora Margherita", "Piazza delle Cinque Scole 30", "Historic Ghetto Osteria", "€€", "Hidden behind red velvet curtains; famous for handmade Fettuccine Cacio e Pepe, Polpette di Bollito, and sweet ricotta pie.", "12:30 – 15:30, 19:30 – 22:30"),
            ("Pasticceria Linari", "Via Nicola Zabaglia 9", "Testaccio Artisanal Café & Bakery", "€", "Beloved neighborhood morning hub for maritozzi con la panna, cornetti alla crema, and strong Roman espresso.", "06:30 – 21:00"),
            ("Flavio al Velavevodetto", "Via di Monte Testaccio 97", "Traditional Quinto Quarto Trattoria", "€€", "Carved directly into the ancient Roman amphora shard hill (Monte Testaccio); benchmark Rigatoni con la Pajata and Carbonara.", "12:30 – 15:00, 19:30 – 23:00"),
            ("Mordi e Vai (Mercato di Testaccio)", "Via Beniamino Franklin 12 (Box 15)", "Street Food Sandwich Stall", "€", "Sergio Esposito's legendary simmered Roman beef brisket (allesso di scottona) and trippa alla romana stuffed into crusty ciriole rolls.", "08:30 – 15:00 (Closed Sun)"),
            ("Rosso Aventino Café", "Via di Santa Sabina 26", "Aventine Espresso & Aperitivo Bar", "€–€€", "Quiet terrace coffee stop before climbing to the Giardino degli Aranci and the Knights of Malta Keyhole.", "07:30 – 20:00"),
            ("Trattoria Da Teo", "Piazza dei Ponziani 7A", "Trastevere Ripa Seafood & Roman Classics", "€€–€€€", "Ivy-draped piazza tables across the Ponte Palatino serving Rigatoni alla Amatriciana and fresh seasonal puntarelle salad.", "12:30 – 15:00, 19:30 – 23:00"),
            ("Gelateria del Teatro (Lungotevere Walk)", "Via dei Coronari / Lungotevere", "Artisanal Gelateria", "€", "Pure pistachio from Bronte, rosemary-honey-lemon sorbet, and dark chocolate infused with Nero d'Avola wine.", "11:00 – 23:30")
        ]
    },
    {
        "stop_num": 3,
        "slug": "Roman_Forum",
        "name": "Forum Romanum & Sacra Via",
        "era": "Regal, Republican & Imperial Eras (8th Century BC – 7th Century AD)",
        "location": "Via della Salara Vecchia 5/6 (Campidoglio / Palatine Valley), Rome",
        "coords": "41.8925° N, 12.4853° E",
        "hist_overview": (
            "The Forum Romanum was the political, religious, judicial, and triumphal heart of ancient Rome for well over a millennium. "
            "Traversed by the sacred basalt flagstones of the Via Sacra, this valley witnessed royal funerals, Republican senatorial debates, "
            "triumphal parades laden with foreign spoils, and the monumental marble transformations of the Roman Empire."
        ),
        "monuments": [
            ("Curia Julia & Comitium", "44–29 BC (Restored AD 284 by Diocletian)", "The official brick Senate House begun by Julius Caesar and completed by Augustus. Preserves its original polychrome opus sectile marble floor and bronze doors replicas."),
            ("Arch of Septimius Severus", "AD 203", "Triple-bay white Proconnesian marble triumphal arch celebrating Roman victories over the Parthian Empire in 194/195 and 197–199 AD."),
            ("Temple of Saturn & Aerarium", "497 BC (Rebuilt 42 BC & AD 283)", "Eight towering granite Ionic columns at the foot of the Capitoline Hill; served as the state treasury (Aerarium Saturni) and center of the December Saturnalia festival."),
            ("Basilica Julia & Basilica Aemilia", "54 BC – AD 14 / 179 BC", "Flanking judicial and banking halls of the main piazza; Basilica Aemilia still displays green copper stains from coins melted onto its marble floor during the Visigothic sack of AD 410."),
            ("Temple of Vesta, Atrium Vestae & Temple of Divus Julius", "29 BC – 3rd Century AD", "Sacred hearth of Rome tended by the six Vestal Virgins alongside the semicircular altar enclosing the cremation pyre of Julius Caesar.")
        ],
        "arch_details": (
            "Spanning from the Lapis Niger (an archaic 6th-century BC black marble shrine inscribed in early Latin bustrophedon script) "
            "to the Column of Phocas (AD 608, the last imperial monument erected in the Forum), the site illustrates the transition from "
            "peperino tufa and wood temples to monumental Proconnesian, Cipollino, and Pavonazzetto marble engineering."
        ),
        "figures": [
            ("Marcus Tullius Cicero", "Orator and Consul who delivered the Philippics from the Rostra; after his proscription in 43 BC, Mark Antony nailed his head and hands to the speaker's platform."),
            ("Emperor Augustus (Octavian)", "Transformed the Republican marketplace into a dynastic marble showcase centered on the Temple of the Deified Julius and his Parthian Arch."),
            ("Titus Flavius Vespasianus (Titus)", "Honored on the Arch of Titus (AD 81) along the Summa Sacra Via depicting the spoils of the Second Temple of Jerusalem, including the seven-branched Menorah."),
            ("Maxentius & Constantine I", "Rival emperors responsible for the colossal brick-and-concrete Basilica of Maxentius and Constantine, whose coffered vaults inspired Renaissance St. Peter's.")
        ],
        "inscriptions": (
            "The attic of the Arch of Septimius Severus displays original bronze peg holes where Geta's name was replaced with 'OPTIMIS FORTISSIMISQVE PRINCIPIBVS'. "
            "On the Arch of Titus, the inscription reads 'SENATVS POPVLVSQVE ROMANVS DIVO TITO DIVI VESPASIANI F VESPASIANO AVGVSTO'."
        ),
        "venues": [
            ("La Carbonara (Monti)", "Via Panisperna 214", "Historic Osteria (Est. 1906)", "€€", "Steps above the Forum in Rione Monti; famous for rigorous Rigatoni alla Carbonara, fried artichokes, and vintage graffiti walls.", "12:30 – 14:30, 19:00 – 23:00"),
            ("Ai Tre Scalini", "Via Panisperna 251", "Historic Wine Bar & Bottiglieria (Est. 1895)", "€€", "Ivy-covered doorway leading to cozy stone arches; serves braised beef cheek (guancia di manzo), lasagna, and 150+ Italian wines.", "12:30 – 01:00"),
            ("Caffè Propaganda", "Via Claudia 15", "Bistro, Specialty Coffee & Patisserie", "€€–€€€", "Parisian-style tiled bistro near the Colosseum exit offering artisanal pastries, specialty espresso, and modern Roman pasta dishes.", "12:00 – 00:00"),
            ("Al42 by Pasta Chef", "Via Baccina 42", "Artisanal Fresh Pasta Counter", "€", "Fast-casual Monti gem directly behind the Forum wall serving freshly extruded Amatriciana, Gricia, and Cacio e Pepe to order.", "12:00 – 22:30"),
            ("Fatamorgana Monti", "Piazza degli Zingari 5", "Artisanal Natural Gelateria", "€", "100% gluten-free natural gelato crafted by Maria Agnese Spagnuolo; inventive flavors like Basil-Walnut-Honey and Baklava.", "12:00 – 23:30"),
            ("Zia Rosetta", "Via Urbana 54", "Gourmet Rosetta Sandwiches", "€", "Mini and full-sized hollow Roman rosetta bread rolls stuffed with porchetta, stracciatella, zucchini scapece, and meatballs.", "11:30 – 22:00"),
            ("Taverna dei Fori Imperiali", "Via della Madonna dei Monti 9", "Family-Run Roman Trattoria", "€€", "Fourth-generation family kitchen minutes from the Forum exit; famous for Ravioli di Burrata and Coda alla Vaccinara.", "12:30 – 15:00, 19:30 – 22:30"),
            ("Analemma Specialty Coffee", "Via Leonina 77", "Third-Wave Coffee & Bakery", "€", "Specialty V60 filter pour-overs, flat whites, and cardamom buns in the heart of Rione Monti.", "08:30 – 19:00")
        ]
    },
    {
        "stop_num": 4,
        "slug": "Trajans_Markets",
        "name": "Trajan's Markets & Imperial Fora",
        "era": "High Imperial Era (AD 100–113)",
        "location": "Via Quattro Novembre 94, Rome",
        "coords": "41.8957° N, 12.4862° E",
        "hist_overview": (
            "Carved directly into the excavated saddle of the Quirinal Hill by the master engineer Apollodorus of Damascus, "
            "Trajan's Markets (Mercati di Traiano) and the adjacent Forum of Trajan represent the zenith of Roman concrete architecture (opus caementicium) "
            "and brick-faced engineering (opus latericium). Funded by the fabulous gold and silver booty of the Dacian Wars (AD 101–102, 105–106), "
            "this six-level terraced complex functioned as the administrative headquarters and commercial archive of the imperial capital."
        ),
        "monuments": [
            ("Great Hemicycle (Grande Emiciclo)", "AD 107–110", "Semicircular three-story brick facade lined with travertine-framed tabernae (shops) and topped by an arched ambulatio overlooking the eastern exedra of Trajan's Forum."),
            ("Aula Traiana (Great Hall)", "AD 110–113", "Monumental two-story groin-vaulted basilica hall Measuring 32 x 8 meters, flanked by 12 administrative offices used for the annona (imperial grain and oil distribution)."),
            ("Via Biberatica", "AD 107–113", "Perfectly preserved ancient Roman shopping street paved in basalt polygonal blocks (basoli) with travertine sidewalks, door thresholds, and rain gutters."),
            ("Column of Trajan", "Dedicated May 12, AD 113", "38-meter monument of 19 colossal Carrara (Luna) marble drums carved with a 200-meter continuous helical frieze of 2,662 figures chronicling the two Dacian campaigns."),
            ("Basilica Ulpia", "AD 112", "The largest civil basilica in ancient Rome (170 x 59 meters), roofed in gilded bronze tiles imported from Greece and forested with grey Mons Claudianus granite columns.")
        ],
        "arch_details": (
            "The cutting of the Quirinal slope required removing over 60 million cubic feet of earth and rock—a feat explicitly celebrated "
            "on the pedestal inscription of Trajan's Column, whose height (100 Roman feet / 29.78m shaft) indicates the exact elevation "
            "of the hill excavated away. The complex integrates medieval additions including the 13th-century Torre delle Milizie."
        ),
        "figures": [
            ("Marcus Ulpius Traianus (Emperor Trajan)", "First provincial emperor (born in Italica, Hispania Baetica), declared Optimus Princeps by the Senate after expanding the Empire to its greatest territorial extent."),
            ("Apollodorus of Damascus", "Nabataean-Greek military engineer and architect who designed the Danube bridge, Trajan's Forum, and the Markets."),
            ("King Decebalus of Dacia", "Formidable Dacian ruler whose defeat at Sarmizegetusa Regia in AD 106 financed the entire monumental program."),
            ("Emperor Constantius II", "Visited Trajan's Forum in AD 357 and stood dumbstruck by its scale, declaring his only hope was to imitate the bronze equestrian statue of Trajan.")
        ],
        "inscriptions": (
            "The famous SENATVS POPVLVSQVE ROMANVS inscription carved in classic Roman square capitals (capitalis monumentalis) at the base "
            "of Trajan's Column states the monument was raised 'AD DECLARANDVM QVANTAE ALTITVDINIS MONS ET LOCVS TANTIS OPERIBVS SIT EGESTVS' "
            "(to declare how high a mountain and place was dug away for such great works)."
        ),
        "venues": [
            ("Ristorante Aroma (Palazzo Manfredi)", "Via Labicana 125", "Michelin-Starred Rooftop Dining", "€€€€", "Chef Giuseppe Di Iorio's refined Roman cuisine with an unobstructed panoramic view over the Imperial Fora and Colosseum.", "12:30 – 15:00, 19:00 – 23:00"),
            ("Forno da Milvio", "Via dei Serpenti 7", "24/7 Historic Roman Bakery", "€", "Two minutes up Via dei Serpenti from Trajan's Markets; hot pizza al taglio con patate, supplì, and fresh midnight cornetti.", "06:00 – 02:00"),
            ("Barzilai Caffè & Bistrot", "Via Panisperna 126", "Quirinal / Monti Coffee & Lunch Bar", "€–€€", "Quiet local favorite along the ancient Suburra ridge serving artisanal espresso, tramezzini, and homemade pasta of the day.", "07:00 – 21:00"),
            ("Urbana 47", "Via Urbana 47", "Farm-to-Table Roman Bistro", "€€–€€€", "Zero-kilometer Lazio ingredients: organic pecorino romano, crispy guanciale, artisanal sourdough, and biodynamic wines.", "12:30 – 23:30"),
            ("Gelateria Ciuri Ciuri", "Via Leonina 18", "Sicilian Cannoli & Gelato Pastry Shop", "€", "Freshly filled sheep's milk ricotta cannoli dusted with Bronte pistachio, granita con brioche, and cassata siciliana.", "08:00 – 00:00"),
            ("L'Asino d'Oro", "Via del Boschetto 73", "Creative Umbrian-Roman Osteria", "€€", "Chef Lucio Sforza's legendary budget lunch menu and evening slow-braised meats steps from the Suburra stairs.", "12:30 – 14:45, 19:30 – 23:00"),
            ("Blackmarket Hall", "Via de' Ciancaleoni 31", "Speakeasy Cocktail & Jazz Lounge", "€€", "Hidden inside a former stable in ancient Suburra; botanical cocktails, artisanal cheese boards, and live acoustic jazz.", "18:30 – 02:00"),
            ("Antico Caffè Brasile", "Via dei Serpenti 23", "Classic Roman Espresso Bar", "€", "Old-school brass-counter bar right outside the Mercati di Traiano exit for a quick standing cappuccino and maritozzo.", "06:30 – 20:00")
        ]
    },
    {
        "stop_num": 5,
        "slug": "Pantheon",
        "name": "The Pantheon (Rotunda of Agrippa & Hadrian)",
        "era": "Augustan Foundation (27 BC) / Hadrianic Reconstruction (AD 118–128)",
        "location": "Piazza della Rotonda, Rome",
        "coords": "41.8986° N, 12.4768° E",
        "hist_overview": (
            "The Pantheon is the supreme architectural masterpiece of Roman antiquity and the best-preserved monument of the ancient world. "
            "Originally commissioned by Marcus Vipsanius Agrippa in 27 BC following the Battle of Actium, burned twice in AD 80 and AD 110, "
            "and completely rebuilt from the ground up under Emperor Hadrian around AD 126, it boasts the largest unreinforced solid concrete dome "
            "on Earth—a perfect sphere of 43.3 meters (142 feet) in both diameter and interior height."
        ),
        "monuments": [
            ("Pronaos (Portico of 16 Monolithic Columns)", "AD 118–125", "16 colossal 11.8-meter shafts of Aswan red and Mons Claudianus grey granite quarried in Egypt, dragged to the Nile, barged across the Mediterranean, and barged up the Tiber."),
            ("The Concrete Rotunda & Coffered Dome", "AD 120–128", "Five concentric rings of 28 sunken coffers (140 total) that lighten the load of the dome; aggregate grades from heavy travertine at the base to featherweight volcanic pumice around the oculus."),
            ("The Oculus (Eye of the Dome)", "AD 128", "An unglazed 8.9-meter circular opening at the apex that serves as the building's sole natural light source and structural compression ring."),
            ("The Bronze Doors & Polychrome Interior", "2nd Century AD", "Original 7.5-meter ancient bronze doors opening onto an opus sectile floor of imperial porphyry, yellow Numidian Giallo Antico, Phrygian Pavonazzetto, and Lucullan black marble."),
            ("Tombs of Raphael & the Italian Kings", "1520 / 1878 / 1900", "Resting place of Renaissance master Raffaello Sanzio (bearing Cardinal Bembo's epitaph), alongside Kings Vittorio Emanuele II, Umberto I, and Queen Margherita of Savoy.")
        ],
        "arch_details": (
            "Brick stamps (bolli doliari) embedded in the rotunda walls prove unequivocally that the standing building dates to the reign "
            "of Trajan and Hadrian (AD 118–125), despite Hadrian's modest preservation of Agrippa's original architrave inscription. "
            "In AD 609, Byzantine Emperor Phocas gifted the building to Pope Boniface IV, who consecrated it as Santa Maria ad Martyres, "
            "saving its marble interior from medieval lime kilns."
        ),
        "figures": [
            ("Marcus Vipsanius Agrippa", "Son-in-law, general, and chief builder of Augustus who erected the original rectangular Pantheon in 27 BC alongside the Baths of Agrippa."),
            ("Publius Aelius Hadrianus (Emperor Hadrian)", "Philhellene emperor and amateur architect who oversaw the daring spherical concrete dome reconstruction."),
            ("Raffaello Sanzio (Raphael)", "Renaissance painter and Chief Architect of St. Peter's who requested burial inside the Pantheon beneath the ancient tabernacle niche."),
            ("Pope Urban VIII Barberini", "Removed the ancient gilded bronze trusses from the portico ceiling in 1625 to cast Bernini's Baldacchino and Castel Sant'Angelo cannons—inspiring the pasquinade 'Quod non fecerunt barbari, fecerunt Barberini'.")
        ],
        "inscriptions": (
            "Across the frieze of the portico in 70-centimeter bronze-inlaid letters stands the famous inscription: "
            "'M·AGRIPPA·L·F·COS·TERTIVM·FECIT' (Marcus Agrippa, son of Lucius, Consul for the third time, built this). "
            "Directly beneath, in smaller letters on the architrave fascia, is the AD 202 restoration inscription of Septimius Severus and Caracalla."
        ),
        "venues": [
            ("La Casa del Caffè Tazza d'Oro", "Via degli Orfani 84", "Historic Roastery (Est. 1946)", "€", "World-famous 'La Regina dei Caffè' steps from the Pantheon portico; iconic Granita di Caffè con Panna layered with double whipped cream.", "07:00 – 20:00"),
            ("Sant'Eustachio Il Caffè", "Piazza di Sant'Eustachio 82", "Historic Wood-Fired Roaster", "€", "One block west of the Pantheon; secret froth-whipped espresso, chocolate-coated coffee beans, and moka pots.", "07:30 – 00:00"),
            ("Armando al Pantheon", "Salita de' Crescenzi 31", "Benchmark Roman Trattoria (Est. 1961)", "€€€", "30 meters from the Pantheon columns; legendary Spaghetti alla Gricia, Faraona (guinea fowl), and Torta Antica Roma.", "12:30 – 15:00, 19:00 – 23:00"),
            ("Giolitti", "Via Uffici del Vicario 40", "Rome's Oldest Gelateria (Est. 1900)", "€–€€", "Marble-floored Belle Époque parlor serving 70+ gelato flavors, Coppa Olimpica, and homemade maritozzi.", "07:30 – 00:00"),
            ("Salotto42", "Piazza di Pietra 42", "Bookbar & Cocktail Lounge", "€€", "Directly facing the 11 towering marble columns of the Temple of Hadrian (Hadrianeum); craft aperitivo and specialty coffee.", "10:30 – 02:00"),
            ("Retrobottega", "Via della Stelletta 4", "Avant-Garde Italian Gastronomy", "€€€", "Counter-seating culinary laboratory near the Pantheon focusing on foraged herbs, aged meats, and handmade pastas.", "12:30 – 15:00, 19:00 – 23:00"),
            ("Antica Salumeria al Pantheon", "Piazza della Rotonda 4", "Historic Charcuterie & Wine Shop (Est. 1375)", "€€", "Directly facing the Pantheon fountain; porchetta d'Ariccia panini, aged pecorino di fossa boards, and Frascati wine.", "09:00 – 23:00"),
            ("Gelateria Della Palma", "Via della Maddalena 19", "Artisanal Gelato & Chocolate Hub", "€", "150 rotating gelato flavors including 12 distinct dark chocolates, Sicilian cannolo gelato, and soy/vegan options.", "08:30 – 00:00")
        ]
    }
]


def get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocSuperTitle",
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=HexColor("#7A1C1C"),
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=14,
        textColor=HexColor("#4A4A4A"),
        spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        name="PageHeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=HexColor("#1F3A52"),
        spaceBefore=4,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="SubSectionTitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=HexColor("#7A1C1C"),
        spaceBefore=8,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="GuideBody",
        fontName="Helvetica",
        fontSize=9.8,
        leading=13.8,
        textColor=HexColor("#1E1E1E"),
        spaceAfter=7
    ))
    styles.add(ParagraphStyle(
        name="CalloutBox",
        fontName="Helvetica-Oblique",
        fontSize=9.2,
        leading=13,
        textColor=HexColor("#2C3E50"),
        backColor=HexColor("#F7F3EB"),
        borderPadding=7,
        spaceBefore=6,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#1E1E1E")
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=11,
        textColor=HexColor("#FFFFFF")
    ))
    return styles


def draw_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(HexColor("#7A1C1C"))
    canvas.setLineWidth(0.8)
    canvas.line(42, A4[1] - 36, A4[0] - 42, A4[1] - 36)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(HexColor("#7A1C1C"))
    canvas.drawString(42, A4[1] - 30, doc.guide_header_left)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#555555"))
    canvas.drawRightString(A4[0] - 42, A4[1] - 30, doc.guide_header_right)

    canvas.setStrokeColor(HexColor("#CCCCCC"))
    canvas.setLineWidth(0.5)
    canvas.line(42, 38, A4[0] - 42, 38)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#555555"))
    canvas.drawString(42, 25, f"Rome Archaeological & Culinary Corpus • {doc.filename_label}")
    canvas.drawRightString(A4[0] - 42, 25, f"Page {doc.page} of {PAGES_PER_PDF}")
    canvas.restoreState()


def build_historical_page_contents(stop, styles, total_pages):
    m = stop["monuments"]
    f = stop["figures"]
    s_name = stop["name"]

    pages = [
        # Page 1: Executive Overview & Topographical Setting
        [
            Paragraph(f"Stop {stop['stop_num']}: {s_name}", styles["DocSuperTitle"]),
            Paragraph(f"Historical, Archaeological & Cultural Field Guide • {stop['era']}", styles["DocSubtitle"]),
            Paragraph("1. Executive Historical Overview & Urban Topography", styles["PageHeaderTitle"]),
            Paragraph(stop["hist_overview"], styles["GuideBody"]),
            Paragraph("Topographical Context & Geomorphology", styles["SubSectionTitle"]),
            Paragraph(
                f"Located at <b>{stop['location']}</b> (Coordinates: {stop['coords']}), {s_name} occupies a pivotal "
                "zone within the ancient pomerial and Campus Martius/Forum basin network. Archaeological core sampling "
                "demonstrates how early Republican builders adapted to seasonal Tiber River flooding by raising tufa podiums "
                "and installing subterranean drainage channels connected to Rome's primary cloacae.",
                styles["GuideBody"]
            ),
            Paragraph(
                "<b>RAG Indexing Summary:</b> Document Type: Historical & Cultural Guide | Stop Number: "
                f"{stop['stop_num']} | Primary Site: {s_name} | Era: {stop['era']} | Key Monuments: "
                + ", ".join([x[0] for x in m[:4]]) + ".",
                styles["CalloutBox"]
            ),
            Paragraph("Chronological Stratigraphy Summary", styles["SubSectionTitle"]),
            Table(
                [
                    [Paragraph("Phase / Period", styles["TableHeader"]),
                     Paragraph("Key Monumental Intervention", styles["TableHeader"]),
                     Paragraph("Primary Building Materials", styles["TableHeader"])],
                    [Paragraph("Archaic / Early Republic", styles["TableCell"]),
                     Paragraph(f"Initial consecration and tufa altar foundations at {s_name}", styles["TableCell"]),
                     Paragraph("Cappellaccio & Grotta Oscura Tufa", styles["TableCell"])],
                    [Paragraph("Middle–Late Republic", styles["TableCell"]),
                     Paragraph(f"Expansion of {m[0][0]} and {m[1][0]} after military triumphs", styles["TableCell"]),
                     Paragraph("Monteverde Tufa, Travertine & Stucco", styles["TableCell"])],
                    [Paragraph("High Empire (Augustan–Severan)", styles["TableCell"]),
                     Paragraph("Marble revetment, raised travertine paving, and fire restorations", styles["TableCell"]),
                     Paragraph("Carrara, Pentelic & Polychrome Marbles", styles["TableCell"])]
                ],
                colWidths=[130, 230, 145],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#7A1C1C")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            )
        ],
        # Page 2: Origins, Foundation Myths & Early Republican Evolution
        [
            Paragraph(f"2. Origins, Votive Dedications & Republican Evolution", styles["PageHeaderTitle"]),
            Paragraph(
                f"During the Republican expansion of Rome across the Italian peninsula and the Mediterranean, {s_name} "
                "served as a canvas for aristocratic competition (nobilitas). Victorious generals (imperatores) vowed "
                "temples (vota) on the battlefield in exchange for divine favor, financing construction ex manubiis "
                "(from the spoils of war) upon their return to the capital.",
                styles["GuideBody"]
            ),
            Paragraph(f"Primary Focus: {m[0][0]} ({m[0][1]})", styles["SubSectionTitle"]),
            Paragraph(m[0][2], styles["GuideBody"]),
            Paragraph(f"Primary Focus: {m[1][0]} ({m[1][1]})", styles["SubSectionTitle"]),
            Paragraph(m[1][2], styles["GuideBody"]),
            Paragraph("Ritual Function & Triumphal Processions", styles["SubSectionTitle"]),
            Paragraph(
                f"Every temple precinct within {s_name} possessed a dies natalis (anniversary of its dedication) "
                "marked in the Fasti Antiates Maiores. Because Roman sacrificial ritual occurred outdoors under the open "
                "sky, monumental U-shaped altars with projecting wings were positioned directly at the foot of the frontal "
                "access stairs, aligning priest, victim, and cult statue along a single liturgical axis.",
                styles["GuideBody"]
            ),
            Paragraph(
                f"<b>Field Observation Note:</b> Examine the surviving base moldings around {m[0][0]}. Notice the distinct "
                "cyma reversa profile typical of Republican Italic podiums before Hellenistic Greek profiles became dominant "
                "following the conquests of Syracuse (212 BC) and Macedonia (146 BC).",
                styles["CalloutBox"]
            )
        ],
        # Page 3: Monumental Catalog Part II & Imperial Transformations
        [
            Paragraph("3. Monumental Catalog & Imperial Transformations", styles["PageHeaderTitle"]),
            Paragraph(
                f"As the Roman Republic gave way to the Principate under Augustus and later the Antonine and Severan dynasties, "
                f"{s_name} underwent profound architectural remodeling. Devastating urban fires—particularly those of 111 BC, "
                "AD 64, AD 80, and AD 191—compelled emperors to raise ground levels and encase older tufa structures in imported marble.",
                styles["GuideBody"]
            ),
            Paragraph(f"Monument Analysis: {m[2][0]} ({m[2][1]})", styles["SubSectionTitle"]),
            Paragraph(m[2][2], styles["GuideBody"]),
            Paragraph(f"Monument Analysis: {m[3][0]} ({m[3][1]})", styles["SubSectionTitle"]),
            Paragraph(m[3][2], styles["GuideBody"]),
            Paragraph(f"Monument Analysis: {m[4][0]} ({m[4][1]})", styles["SubSectionTitle"]),
            Paragraph(m[4][2], styles["GuideBody"]),
            Paragraph(
                "<b>Architectural Synthesis:</b> " + stop["arch_details"],
                styles["CalloutBox"]
            )
        ],
        # Page 4: Construction Engineering, Materials & Marble Provenance
        [
            Paragraph("4. Roman Engineering, Structural Mechanics & Lithic Provenance", styles["PageHeaderTitle"]),
            Paragraph(
                f"The monuments at {s_name} provide a textbook sequence of Roman structural engineering, illustrating the "
                "mastery of ashlar masonry (opus quadratum), concrete core construction (opus caementicium), brick facing "
                "(opus latericium), and polychrome geometric marble paving (opus sectile).",
                styles["GuideBody"]
            ),
            Paragraph("Lithic & Material Provenance Table", styles["SubSectionTitle"]),
            Table(
                [
                    [Paragraph("Material / Stone", styles["TableHeader"]),
                     Paragraph("Ancient Quarry Source", styles["TableHeader"]),
                     Paragraph("Structural / Decorative Application at Site", styles["TableHeader"])],
                    [Paragraph("Lapis Tiburtinus (Travertine)", styles["TableCell"]),
                     Paragraph("Tibur (Modern Tivoli)", styles["TableCell"]),
                     Paragraph("Load-bearing piers, column capitals, steps, and Imperial pavement slabs", styles["TableCell"])],
                    [Paragraph("Tufo Lionato / Monteverde", styles["TableCell"]),
                     Paragraph("Aniene Valley & Janiculum slopes", styles["TableCell"]),
                     Paragraph("Temple podium cores, Republican altar bases, and drainage channels", styles["TableCell"])],
                    [Paragraph("Marmor Lunense / Pentelicum", styles["TableCell"]),
                     Paragraph("Carrara (Italy) & Mt. Pentelicus (Attica)", styles["TableCell"]),
                     Paragraph("Corinthian entablatures, acrolithic cult statues, and carved relief panels", styles["TableCell"])],
                    [Paragraph("Pozzolana (Pulvis Puteolanus)", styles["TableCell"]),
                     Paragraph("Alban Hills & Campanian volcanic beds", styles["TableCell"]),
                     Paragraph("Hydraulic mortar binding opus caementicium vaults and foundations", styles["TableCell"])]
                ],
                colWidths=[135, 155, 215],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F3A52")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            ),
            Paragraph("Structural Load & Hydraulic Management", styles["SubSectionTitle"]),
            Paragraph(
                "Roman architects utilized relieving arches (archi di scarico) concealed within brick walls to channel "
                "vertical dead loads away from lintels and onto massive corner piers. Subsurface travertine gutters around "
                f"{s_name} captured rainwater from temple roofs, routing runoff directly into underlying collectors.",
                styles["GuideBody"]
            )
        ],
        # Page 5: Key Historical Figures & Political Drama
        [
            Paragraph("5. Key Historical Figures, Statesmen & Political Drama", styles["PageHeaderTitle"]),
            Paragraph(
                f"History at {s_name} was shaped by the ambitions, rivalries, and religious piety of Rome's most influential "
                "consuls, dictators, emperors, and architects. Below are the four primary historical protagonists linked directly "
                "to the surviving archaeological fabric of this stop:",
                styles["GuideBody"]
            ),
            Paragraph(f"• {f[0][0]}", styles["SubSectionTitle"]),
            Paragraph(f[0][1], styles["GuideBody"]),
            Paragraph(f"• {f[1][0]}", styles["SubSectionTitle"]),
            Paragraph(f[1][1], styles["GuideBody"]),
            Paragraph(f"• {f[2][0]}", styles["SubSectionTitle"]),
            Paragraph(f[2][1], styles["GuideBody"]),
            Paragraph(f"• {f[3][0]}", styles["SubSectionTitle"]),
            Paragraph(f[3][1], styles["GuideBody"]),
            Paragraph(
                "<b>Primary Ancient Literary Sources:</b> Suetonius (<i>De Vita Caesarum</i>), Plutarch (<i>Parallel Lives</i>), "
                "Livy (<i>Ab Urbe Condita</i>), Cassius Dio (<i>Roman History</i>), and Vitruvius (<i>De Architectura</i>) "
                f"all record direct eyewitness or archival accounts of the ceremonies and political crises at {s_name}.",
                styles["CalloutBox"]
            )
        ],
        # Page 6: Epigraphy, Inscriptions, Statuary & Numismatic Evidence
        [
            Paragraph("6. Epigraphy, Latin Inscriptions & Sculptural Finds", styles["PageHeaderTitle"]),
            Paragraph(
                "Latin epigraphy provides the chronological backbone for identifying temples and imperial restorations at "
                f"{s_name}. Monumental inscriptions were carved using V-cut trenches (litterae aureae) often fitted with "
                "gilded bronze letters fastened via lead-soldered tangs into sockets still visible on the stone architraves.",
                styles["GuideBody"]
            ),
            Paragraph("Corpus Inscriptionum Latinarum (CIL) & Sculptural Record", styles["SubSectionTitle"]),
            Paragraph(stop["inscriptions"], styles["GuideBody"]),
            Paragraph("Numismatic & Relief Iconography", styles["SubSectionTitle"]),
            Paragraph(
                f"Roman Republican denarii and Imperial sestertii frequently minted reverse dies depicting the facades of "
                f"monuments at {s_name}. These coins allow archaeologists to reconstruct lost pedimental sculptures, acroteria, "
                "and bronze grilles that vanished during late antique spoliation.",
                styles["GuideBody"]
            ),
            Paragraph(
                "<b>Epigraphic Reading Tip for Visitors:</b> Look closely at the spacing of interpuncts (triangular dots · "
                "between words) and the absence of 'U' (written as 'V') and 'J' (written as 'I'). Erasures where the stone "
                "surface sits slightly recessed indicate <i>damnatio memoriae</i> ordered by the Roman Senate.",
                styles["CalloutBox"]
            )
        ],
        # Page 7: Daily Life, Religious Rituals & Civic Spectacle
        [
            Paragraph("7. Daily Civic Life, Sacrificial Liturgy & Acoustic Space", styles["PageHeaderTitle"]),
            Paragraph(
                f"At its peak in the 1st and 2nd centuries AD, {s_name} was not a silent ruin of bare stone and brick, but "
                "a sensory kaleidoscope of painted stucco, fragrant frankincense smoke, bronze statuary gleaming in the sun, "
                "and crowds of citizens, senators, freedmen, and foreign envoys.",
                styles["GuideBody"]
            ),
            Paragraph("The Mechanics of Roman Public Sacrifice (Sacrificium)", styles["SubSectionTitle"]),
            Paragraph(
                "Public rites opened with the herald crying 'Favete linguis!' (Keep a reverent silence!) while flute players "
                "(tibicines) drowned out inauspicious street noises. The officiating magistrate, with his toga pulled over his "
                "head (capite velato), sprinkled salted spelt flour (mola salsa) and wine over the altar before the victimarius "
                "struck the sacrificial animal and haruspices inspected the entrails.",
                styles["GuideBody"]
            ),
            Paragraph("Commercial & Legal Rhythms Around the Precinct", styles["SubSectionTitle"]),
            Paragraph(
                f"Surrounding the sacred core of {s_name}, porticoes sheltered bankers (argentarii), bookbinders, scribes, "
                "and flower sellers weaving garlands for temple offerings. Marble game boards (tabulae lusoriae) scratched "
                "directly into the pavement steps by waiting clerks and loafers remain visible on site today.",
                styles["GuideBody"]
            )
        ],
        # Page 8: Medieval Post-Classical Survival, Spoliation & Excavations
        [
            Paragraph("8. Medieval Transformation, Renaissance Rediscovery & Modern Excavations", styles["PageHeaderTitle"]),
            Paragraph(
                f"Following the collapse of imperial administration in the West (5th–6th centuries AD), {s_name} entered a "
                "millennium-long phase of adaptive reuse. While exposed marble columns were frequently burned into slaked lime "
                "(calce) in medieval kilns (calcare), structures converted into Christian churches or baronial fortresses survived remarkably intact.",
                styles["GuideBody"]
            ),
            Paragraph("Christian Consecration & Baronial Fortifications", styles["SubSectionTitle"]),
            Paragraph(
                "During the 8th through 13th centuries, powerful Roman families—including the Frangipane, Pierleoni, Savelli, "
                f"and Conti—incorporated the stout Roman walls of {s_name} into fortified towers and diaconiae. Renaissance "
                "architects including Baldassarre Peruzzi, Antonio da Sangallo, and Andrea Palladio measured and sketched these "
                "ruins, transmitting their proportions directly into 16th-century European classicism.",
                styles["GuideBody"]
            ),
            Paragraph("19th–21st Century Archaeological Campaigns", styles["SubSectionTitle"]),
            Paragraph(
                "Systematic stratigraphic excavations led by Rodolfo Lanciani, Giacomo Boni, Antonio Muñoz, and the modern "
                "Sovrintendenza Capitolina ai Beni Culturali stripped away post-antique overburden, stabilized brick vaults "
                "with reversible titanium ties, and opened buried subterranean corridors to the public.",
                styles["GuideBody"]
            )
        ],
        # Page 9: Curated On-Site Viewing Route & Photography Guide
        [
            Paragraph("9. Step-by-Step On-Site Viewing Itinerary & Vantage Points", styles["PageHeaderTitle"]),
            Paragraph(
                f"To maximize your 45-to-60-minute visit at {s_name}, follow this sequential clockwise architectural circuit "
                "designed to trace the site from its earliest Republican foundations to its high Imperial climax:",
                styles["GuideBody"]
            ),
            Table(
                [
                    [Paragraph("Step", styles["TableHeader"]),
                     Paragraph("Vantage Point / Station", styles["TableHeader"]),
                     Paragraph("What to Look For (Key Visual Detail)", styles["TableHeader"])],
                    [Paragraph("01", styles["TableCell"]),
                     Paragraph(f"Primary Overview & {m[0][0]}", styles["TableCell"]),
                     Paragraph("Compare the archaic tufa ashlar blocks with the elevated imperial travertine pavement level.", styles["TableCell"])],
                    [Paragraph("02", styles["TableCell"]),
                     Paragraph(f"{m[1][0]} & Altar Precinct", styles["TableCell"]),
                     Paragraph("Inspect the U-shaped sacrificial altar moldings and surviving fluted column shafts.", styles["TableCell"])],
                    [Paragraph("03", styles["TableCell"]),
                     Paragraph(f"{m[2][0]} & {m[3][0]}", styles["TableCell"]),
                     Paragraph("Observe the transition to Hellenistic marble capitals and circular/pseudoperipteral layouts.", styles["TableCell"])],
                    [Paragraph("04", styles["TableCell"]),
                     Paragraph(f"{m[4][0]} & Epigraphic Zone", styles["TableCell"]),
                     Paragraph("Read the monumental Latin inscriptions and trace the Roman brick relieving arches.", styles["TableCell"])]
                ],
                colWidths=[40, 175, 290],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#7A1C1C")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            ),
            Paragraph("Golden Hour & Photography Guidance", styles["SubSectionTitle"]),
            Paragraph(
                f"Optimal raking sunlight strikes the travertine and tufa facades of {s_name} between 08:30–10:00 AM and "
                "again during late afternoon golden hour (16:30–18:00), bringing out deep chisel marks and relief shadows.",
                styles["GuideBody"]
            )
        ],
        # Page 10: Practical Visitor Logistics, Ticketing & Transit to Next Stop
        [
            Paragraph("10. Practical Visitor Logistics, Accessibility & Next-Stop Transit", styles["PageHeaderTitle"]),
            Paragraph(
                f"Use the reference sheet below when planning arrival times, ticketing, accessibility routes, and walking "
                f"transfers from <b>Stop {stop['stop_num']}: {s_name}</b> to the next destination on your Roman itinerary.",
                styles["GuideBody"]
            ),
            Table(
                [
                    [Paragraph("Logistic Category", styles["TableHeader"]),
                     Paragraph("Verified Visitor Information", styles["TableHeader"])],
                    [Paragraph("Exact Address & Zone", styles["TableCell"]),
                     Paragraph(f"{stop['location']} ({stop['coords']})", styles["TableCell"])],
                    [Paragraph("Recommended Visit Duration", styles["TableCell"]),
                     Paragraph("45–75 minutes (Perimeter viewing + interior archaeological walk)", styles["TableCell"])],
                    [Paragraph("Best Time of Day to Visit", styles["TableCell"]),
                     Paragraph("09:00 AM opening slot or 90 minutes prior to sunset to avoid tour bus peaks", styles["TableCell"])],
                    [Paragraph("Accessibility & Footwear", styles["TableCell"]),
                     Paragraph("Ancient uneven basalt (sampietrini/basoli) and travertine steps; sturdy walking shoes essential", styles["TableCell"])],
                    [Paragraph("Water & Rest Facilities", styles["TableCell"]),
                     Paragraph("Free potable cast-iron Roman Nasone drinking fountain located within 80 meters of the piazza", styles["TableCell"])]
                ],
                colWidths=[160, 345],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F3A52")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            ),
            Paragraph("Essential Glossary of Architectural Terms Used in This Guide", styles["SubSectionTitle"]),
            Paragraph(
                "• <b>Opus Caementicium:</b> Roman hydraulic concrete mixed from lime, pozzolana volcanic ash, and stone aggregate (caementa).<br/>"
                "• <b>Opus Quadratum:</b> Ashlar masonry of squared stone blocks laid in regular courses without mortar, clamped with iron/lead.<br/>"
                "• <b>Opus Sectile:</b> Luxury floor or wall decoration formed from precision-cut thin slabs of polychrome marble.<br/>"
                "• <b>Pomerium:</b> The sacred religious and legal boundary of the city of Rome within which weapons were forbidden.<br/>"
                "• <b>Damnatio Memoriae:</b> Official senatorial condemnation erasing a disgraced figure's name and likeness from monuments.",
                styles["GuideBody"]
            )
        ]
    ]
    return pages[:total_pages]


def build_culinary_page_contents(stop, styles, total_pages):
    v = stop["venues"]
    s_name = stop["name"]

    pages = [
        # Page 1: Culinary Landscape & Dining Matrix Overview
        [
            Paragraph(f"Stop {stop['stop_num']}: {s_name}", styles["DocSuperTitle"]),
            Paragraph(f"Curated Coffee, Bakeries, Gelato & Trattoria Guide • {stop['location']}", styles["DocSubtitle"]),
            Paragraph("1. Micro-Neighborhood Gastronomy & Quick-Reference Matrix", styles["PageHeaderTitle"]),
            Paragraph(
                f"Surrounding <b>{s_name}</b> lies one of Rome's richest gastronomic micro-districts. However, high monument "
                "foot traffic also attracts tourist-trap menus with frozen pasta and inflated service charges. This curated guide "
                "filters exclusively for historic roasteries, multi-generation bakeries, authentic Roman quinto quarto and pasta "
                "trattorias, and natural artisanal gelaterias within a 2-to-8-minute walk of the archaeological site.",
                styles["GuideBody"]
            ),
            Paragraph("Verified Top 8 Culinary Stops Near " + s_name, styles["SubSectionTitle"]),
            Table(
                [
                    [Paragraph("Venue Name", styles["TableHeader"]),
                     Paragraph("Category", styles["TableHeader"]),
                     Paragraph("Price", styles["TableHeader"]),
                     Paragraph("Signature Order", styles["TableHeader"])]
                ] + [
                    [Paragraph(f"<b>{item[0]}</b><br/>{item[1]}", styles["TableCell"]),
                     Paragraph(item[2], styles["TableCell"]),
                     Paragraph(item[3], styles["TableCell"]),
                     Paragraph(item[4], styles["TableCell"])]
                    for item in v[:6]
                ],
                colWidths=[145, 110, 45, 205],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#7A1C1C")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ])
            )
        ],
        # Page 2: Specialty Espresso Roasteries & Morning Pastry Culture
        [
            Paragraph("2. Historic Espresso Bars, Roasteries & Morning Cornetti", styles["PageHeaderTitle"]),
            Paragraph(
                f"Before or immediately after exploring {s_name}, experience genuine Roman bar ritual. In Rome, ordering "
                "at the counter (<i>al banco</i>) costs a fraction of table service (<i>al tavolo</i>) and places you shoulder-to-shoulder "
                "with locals grabbing a quick <i>caffè espresso</i> or <i>maritozzo con la panna</i>.",
                styles["GuideBody"]
            ),
            Paragraph(f"Featured Coffee & Bakery Stop: {v[2][0]} ({v[2][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Category:</b> {v[2][2]} | <b>Price Tier:</b> {v[2][3]} | <b>Hours:</b> {v[2][5]}<br/>"
                f"<b>What to Order:</b> {v[2][4]}",
                styles["GuideBody"]
            ),
            Paragraph(f"Featured Bakery / Café Stop: {v[0][0]} ({v[0][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Category:</b> {v[0][2]} | <b>Price Tier:</b> {v[0][3]} | <b>Hours:</b> {v[0][5]}<br/>"
                f"<b>What to Order:</b> {v[0][4]}",
                styles["GuideBody"]
            ),
            Paragraph(
                "<b>Roman Coffee Ordering Protocol:</b> Pay at the cashier (<i>la cassa</i>) first to receive your paper receipt "
                "(<i>lo scontrino</i>), then place the receipt on the brass bar counter with a €0.10–€0.20 coin if you want "
                "immediate attention during the morning rush. Ask for a glass of sparkling water (<i>acqua frizzante</i>) to cleanse your palate first.",
                styles["CalloutBox"]
            )
        ],
        # Page 3: Fast Casual Street Food, Pizza al Taglio & Forni
        [
            Paragraph("3. Artisanal Bakeries (Forni), Pizza al Taglio & Street Food", styles["PageHeaderTitle"]),
            Paragraph(
                f"If you want a high-speed, deeply authentic lunch between archaeological stops around {s_name}, bypass "
                "sit-down tourist menus in favor of a historic <i>forno</i> (bakery) or street-food counter specializing in "
                "72-hour fermented Roman pizza and fried rice croquettes (<i>supplì</i>).",
                styles["GuideBody"]
            ),
            Paragraph(f"Spotlight Street-Food / Bakery Venue: {v[3][0]} ({v[3][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Category:</b> {v[3][2]} | <b>Price Tier:</b> {v[3][3]} | <b>Hours:</b> {v[3][5]}<br/>"
                f"<b>Tasting Notes:</b> {v[3][4]}",
                styles["GuideBody"]
            ),
            Paragraph(f"Spotlight Casual Counter: {v[5][0]} ({v[5][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Category:</b> {v[5][2]} | <b>Price Tier:</b> {v[5][3]} | <b>Hours:</b> {v[5][5]}<br/>"
                f"<b>Tasting Notes:</b> {v[5][4]}",
                styles["GuideBody"]
            ),
            Paragraph("How Pizza al Taglio Works in Rome", styles["SubSectionTitle"]),
            Paragraph(
                "Point to the rectangular tray you want and show the baker with your hands how wide a strip to cut with "
                "their shears. The slice is weighed on a digital scale (<i>al chilo</i>), folded in half (<i>a libretto</i>) "
                "wrapped in butcher paper, and eaten warm while walking.",
                styles["GuideBody"]
            )
        ],
        # Page 4: Benchmark Sit-Down Roman Trattorias & Osterias
        [
            Paragraph("4. Benchmark Roman Trattorias & Historic Osterias", styles["PageHeaderTitle"]),
            Paragraph(
                f"For a full sit-down lunch or dinner near {s_name}, these vetted family-run trattorias execute the four "
                "foundational Roman pasta dishes—<i>Gricia, Cacio e Pepe, Carbonara, and Amatriciana</i>—using DOP Pecorino "
                "Romano and artisanal Lazio guanciale (never cream or pancetta).",
                styles["GuideBody"]
            ),
            Paragraph(f"Primary Trattoria Pick: {v[1][0]} ({v[1][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Style:</b> {v[1][2]} | <b>Price Tier:</b> {v[1][3]} | <b>Hours:</b> {v[1][5]}<br/>"
                f"<b>Must-Order Dishes:</b> {v[1][4]}",
                styles["GuideBody"]
            ),
            Paragraph(f"Secondary Trattoria Pick: {v[4][0]} ({v[4][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Style:</b> {v[4][2]} | <b>Price Tier:</b> {v[4][3]} | <b>Hours:</b> {v[4][5]}<br/>"
                f"<b>Must-Order Dishes:</b> {v[4][4]}",
                styles["GuideBody"]
            ),
            Paragraph(
                "<b>Reservation Strategy:</b> Top historic trattorias around the center book out 7–14 days ahead for "
                "the 20:00 dinner seating. If you do not have a booking, arrive at 12:15 PM sharp right before the doors "
                "unlock for lunch service to secure a walk-in table.",
                styles["CalloutBox"]
            )
        ],
        # Page 5: Contemporary Bistros, Wine Bars (Enoteche) & Aperitivo
        [
            Paragraph("5. Wine Bars (Enoteche), Craft Beer & Evening Aperitivo", styles["PageHeaderTitle"]),
            Paragraph(
                f"As the sun sets over the travertine ruins of {s_name}, the surrounding alleys transition to aperitivo hour "
                "(18:00–20:30). Skip generic spritz bars on main tourist squares and duck into these dedicated wine bars and "
                "contemporary bistros highlighting indigenous Lazio varietals like Cesanese del Piglio, Bellone, and Malvasia Puntinata.",
                styles["GuideBody"]
            ),
            Paragraph(f"Featured Evening / Aperitivo Venue: {v[6][0]} ({v[6][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Concept:</b> {v[6][2]} | <b>Price Tier:</b> {v[6][3]} | <b>Hours:</b> {v[6][5]}<br/>"
                f"<b>Highlights:</b> {v[6][4]}",
                styles["GuideBody"]
            ),
            Paragraph("Curated Lazio & Central Italian Wine Pairing Guide", styles["SubSectionTitle"]),
            Table(
                [
                    [Paragraph("Wine / Varietal", styles["TableHeader"]),
                     Paragraph("Region / DOCG", styles["TableHeader"]),
                     Paragraph("Ideal Roman Dish Pairing", styles["TableHeader"])],
                    [Paragraph("Frascati Superiore DOCG", styles["TableCell"]),
                     Paragraph("Castelli Romani (Volcanic soils)", styles["TableCell"]),
                     Paragraph("Carciofi alla Giudia, Supplì, and Cacio e Pepe", styles["TableCell"])],
                    [Paragraph("Cesanese del Piglio DOCG", styles["TableCell"]),
                     Paragraph("Ciociaria / Northern Frosinone", styles["TableCell"]),
                     Paragraph("Bucatini all'Amatriciana, Rigatoni alla Carbonara, and Roast Lamb", styles["TableCell"])],
                    [Paragraph("Bellone / Cacchione (Nettuno)", styles["TableCell"]),
                     Paragraph("Anzio & Coastal Lazio", styles["TableCell"]),
                     Paragraph("Spaghetti alla Gricia, Zucchini Blossoms with Anchovy & Mozzarella", styles["TableCell"])]
                ],
                colWidths=[145, 155, 205],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F3A52")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            )
        ],
        # Page 6: Artisanal Gelaterias, Dolci & How to Spot Fake Gelato
        [
            Paragraph("6. Artisanal Gelaterias, Roman Dolci & Quality Verification", styles["PageHeaderTitle"]),
            Paragraph(
                f"Few pleasures beat strolling past {s_name} in the evening with a cup or cone of authentic artisanal gelato. "
                "Use the profile below and our four-point visual inspection checklist to ensure you only eat slow-churned, "
                "all-natural gelato free of artificial emulsifiers and neon food coloring.",
                styles["GuideBody"]
            ),
            Paragraph(f"Featured Gelato / Dessert Stop: {v[7][0]} ({v[7][1]})", styles["SubSectionTitle"]),
            Paragraph(
                f"<b>Specialty:</b> {v[7][2]} | <b>Price Tier:</b> {v[7][3]} | <b>Hours:</b> {v[7][5]}<br/>"
                f"<b>Must-Try Flavors:</b> {v[7][4]}",
                styles["GuideBody"]
            ),
            Paragraph("4-Point Field Test: Real Artisanal Gelato vs. Industrial Tourist Gelato", styles["SubSectionTitle"]),
            Paragraph(
                "1. <b>Check the Pistachio & Banana Color:</b> Real Bronte pistachio gelato is a muted earthy sage-brown, never "
                "radioactive neon green; real banana is greyish-white, never bright yellow.<br/>"
                "2. <b>Inspect the Container Height:</b> Authentic gelato is dense and kept flat below the rim of steel cylindrical "
                "wells (<i>pozzetti</i>) to maintain temperature. Fluffy mountains piled high above the tray are whipped with vegetable fat.<br/>"
                "3. <b>Read the Ingredient Board:</b> By Italian law, gelaterias must display an ingredient book—look for fresh milk, "
                "cream, sugar, and seasonal fruit without hydrogenated oils or E-number stabilizers.<br/>"
                "4. <b>Say Yes to Panna:</b> Authentic Roman gelaterias offer a free dollop of unsweetened freshly whipped cream "
                "(<i>panna montata</i>) on top of your gelato.",
                styles["GuideBody"]
            )
        ],
        # Page 7: Deep Dive into Roman Culinary History & Signature Dishes
        [
            Paragraph("7. Anatomy of the Classic Roman Kitchen (Cucina Romana)", styles["PageHeaderTitle"]),
            Paragraph(
                f"The dishes served in the streets surrounding {s_name} descend from two distinct historical traditions: "
                "the pastoral shepherd cuisine of the Agro Romano and the historic Judeo-Roman kitchen (<i>Cucina Ebraico-Romanesca</i>), "
                "the oldest continuously practiced culinary tradition in Italy.",
                styles["GuideBody"]
            ),
            Paragraph("The Sacred Pasta Quartet of Rome", styles["SubSectionTitle"]),
            Paragraph(
                "• <b>Alla Gricia (400 AD+ pastoral roots):</b> Crispy rendered pork jowl (guanciale), freshly cracked black pepper, "
                "starchy pasta cooking water, and sharp aged Pecorino Romano—the ancestor of Amatriciana before New World tomatoes arrived.<br/>"
                "• <b>Cacio e Pepe:</b> An emulsion of toasted black peppercorns, starchy pasta water, and finely grated Pecorino Romano tossed with tonnarelli.<br/>"
                "• <b>All'Amatriciana:</b> Guanciale, San Marzano tomato passata, a touch of chili (peperoncino), white wine splash, and Pecorino with bucatini.<br/>"
                "• <b>Alla Carbonara:</b> Egg yolks, Pecorino Romano, crispy guanciale, and coarse black pepper emulsified off the heat into a silky golden sauce.",
                styles["GuideBody"]
            ),
            Paragraph("Judeo-Roman & Quinto Quarto Specialties", styles["SubSectionTitle"]),
            Paragraph(
                "Look for <i>Carciofi alla Giudia</i> (whole Romanesco cimarolo artichokes pressed and fried twice in olive oil until "
                "every leaf shatters like a potato chip) and <i>Coda alla Vaccinara</i> (oxtail braised for five hours with celery, tomatoes, "
                "pine nuts, raisins, and a pinch of bitter dark cocoa).",
                styles["GuideBody"]
            )
        ],
        # Page 8: Dietary Accommodations (Vegetarian, Vegan, Celiacs / Gluten-Free)
        [
            Paragraph("8. Dietary Guide: Vegetarian, Vegan & Gluten-Free (Senza Glutine)", styles["PageHeaderTitle"]),
            Paragraph(
                f"While traditional Roman cooking around {s_name} leans heavily on cured pork and sheep's cheese, Rome is "
                "exceptionally accommodating for vegetarian, vegan, and celiac (<i>celiachia</i>) travelers when you know "
                "which naturally compliant local dishes to order.",
                styles["GuideBody"]
            ),
            Paragraph("Naturally Vegetarian & Vegan Roman Classics", styles["SubSectionTitle"]),
            Paragraph(
                "• <b>Carciofi alla Romana:</b> Whole artichokes braised upside-down in olive oil, garlic, parsley, and wild mint (<i>mentuccia</i>)—100% vegan.<br/>"
                "• <b>Pizza Rossa & Pizza con Patate:</b> Traditional bakery red pizza brushed with tomato, oregano, and olive oil (no cheese).<br/>"
                "• <b>Cicoria Ripassata:</b> Wild field greens boiled and sautéed briskly in olive oil, garlic, and red chili flakes.<br/>"
                "• <b>Penne all'Arrabbiata:</b> Spicy garlic-and-tomato pasta; ask for it <i>senza pecorino</i> to make it strictly vegan.",
                styles["GuideBody"]
            ),
            Paragraph(
                "<b>Celiac / Gluten-Free Phrasebook (AIC Certified):</b> Italy tests all school children for celiac disease, "
                "making gluten awareness remarkably high. Say: <i>'Sono celiaco/a. Avete pasta senza glutine cotta in acqua "
                "separata?'</i> (I am celiac. Do you have gluten-free pasta cooked in separate water?).",
                styles["CalloutBox"]
            )
        ],
        # Page 9: Time-of-Day Culinary Pairing Itinerary Around This Stop
        [
            Paragraph("9. Time-of-Day Gastronomic Pairing Schedule", styles["PageHeaderTitle"]),
            Paragraph(
                f"Whether your visit to <b>Stop {stop['stop_num']}: {s_name}</b> falls in the early morning, midday, "
                "afternoon heat, or late evening, match your arrival slot with the exact venue schedule below:",
                styles["GuideBody"]
            ),
            Table(
                [
                    [Paragraph("Time Window", styles["TableHeader"]),
                     Paragraph("Recommended Venue", styles["TableHeader"]),
                     Paragraph("Optimal Culinary Pairing", styles["TableHeader"])],
                    [Paragraph("08:00 – 10:30 AM (Morning)", styles["TableCell"]),
                     Paragraph(f"{v[2][0]}", styles["TableCell"]),
                     Paragraph("Standing espresso or cappuccino at the counter paired with a warm pastry or maritozzo.", styles["TableCell"])],
                    [Paragraph("11:00 – 12:30 PM (Mid-Day Snack)", styles["TableCell"]),
                     Paragraph(f"{v[0][0]} / {v[5][0]}", styles["TableCell"]),
                     Paragraph("Warm folded slice of Pizza Rossa or gourmet stuffed Rosetta roll for walking fuel.", styles["TableCell"])],
                    [Paragraph("12:30 – 14:45 PM (Sit-Down Lunch)", styles["TableCell"]),
                     Paragraph(f"{v[1][0]} / {v[4][0]}", styles["TableCell"]),
                     Paragraph("Fried artichoke starter followed by Tonnarelli Cacio e Pepe or Rigatoni alla Carbonara.", styles["TableCell"])],
                    [Paragraph("16:00 – 18:00 PM (Afternoon Break)", styles["TableCell"]),
                     Paragraph(f"{v[7][0]} / {v[3][0]}", styles["TableCell"]),
                     Paragraph("Two-flavor artisanal gelato cup with fresh whipped cream or ricotta-sour cherry tart.", styles["TableCell"])],
                    [Paragraph("18:30 – 22:30 PM (Aperitivo & Dinner)", styles["TableCell"]),
                     Paragraph(f"{v[6][0]} / {v[4][0]}", styles["TableCell"]),
                     Paragraph("Lazio wine flight or craft beer followed by slow-braised Roman second-course meats.", styles["TableCell"])]
                ],
                colWidths=[115, 150, 240],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#7A1C1C")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            )
        ],
        # Page 10: Roman Dining Etiquette, Tipping, Bill Breakdown & Complete Directory
        [
            Paragraph("10. Roman Dining Etiquette, Bill Breakdown & Complete Venue Directory", styles["PageHeaderTitle"]),
            Paragraph(
                "Understanding Italian restaurant billing and etiquette around Rome's historic monuments prevents surprises "
                "and ensures smooth, welcoming service at every stop:",
                styles["GuideBody"]
            ),
            Paragraph(
                "• <b>Pane e Coperto (Bread & Cover Charge):</b> A standard legal charge of €1.50–€3.00 per person printed on the "
                "menu covering linen, breadbasket, and table setting.<br/>"
                "• <b>Servizio vs. Tipping (La Mancia):</b> Waitstaff in Italy are paid a full living wage. Tipping 15–20% is not "
                "customary; leaving €2–€5 in coins on the table for attentive service in a trattoria is warmly appreciated.<br/>"
                "• <b>Asking for the Bill:</b> Waiters consider bringing the check unasked to be rude. Catch their eye and say "
                "<i>'Il conto, per favore'</i> when you are ready to leave.",
                styles["GuideBody"]
            ),
            Paragraph(f"Complete Address & Hours Directory for Stop {stop['stop_num']} ({s_name})", styles["SubSectionTitle"]),
            Table(
                [
                    [Paragraph("#", styles["TableHeader"]),
                     Paragraph("Venue Name", styles["TableHeader"]),
                     Paragraph("Street Address", styles["TableHeader"]),
                     Paragraph("Operating Hours", styles["TableHeader"])]
                ] + [
                    [Paragraph(f"0{idx+1}", styles["TableCell"]),
                     Paragraph(f"<b>{item[0]}</b>", styles["TableCell"]),
                     Paragraph(item[1], styles["TableCell"]),
                     Paragraph(item[5], styles["TableCell"])]
                    for idx, item in enumerate(v)
                ],
                colWidths=[28, 155, 172, 150],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F3A52")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FAFAFA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ])
            )
        ]
    ]
    return pages[:total_pages]


def generate_pdf(filepath, filename_label, header_left, header_right, pages_flowables):
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=52,
        bottomMargin=50
    )
    doc.filename_label = filename_label
    doc.guide_header_left = header_left
    doc.guide_header_right = header_right

    story = []
    for idx, page_items in enumerate(pages_flowables):
        for item in page_items:
            story.append(item)
        if idx < len(pages_flowables) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)


def main():
    for d in OUTPUT_DIRS:
        os.makedirs(d, exist_ok=True)

    styles = get_styles()
    generated_files = []

    file_counter = 1
    for stop in STOPS_DATA:
        # 1. Historical & Cultural PDF
        hist_filename = f"{file_counter:02d}_Stop{stop['stop_num']}_{stop['slug']}_Historical_Cultural.pdf"
        hist_pages = build_historical_page_contents(stop, styles, PAGES_PER_PDF)
        primary_hist_path = os.path.join(OUTPUT_DIRS[0], hist_filename)

        generate_pdf(
            primary_hist_path,
            hist_filename,
            f"STOP {stop['stop_num']}: {stop['name'].upper()}",
            "HISTORICAL & CULTURAL GUIDE",
            hist_pages
        )
        shutil.copy2(primary_hist_path, os.path.join(OUTPUT_DIRS[1], hist_filename))
        generated_files.append(hist_filename)
        file_counter += 1

        # 2. Coffee & Restaurants PDF
        food_filename = f"{file_counter:02d}_Stop{stop['stop_num']}_{stop['slug']}_Coffee_Restaurants.pdf"
        food_pages = build_culinary_page_contents(stop, styles, PAGES_PER_PDF)
        primary_food_path = os.path.join(OUTPUT_DIRS[0], food_filename)

        generate_pdf(
            primary_food_path,
            food_filename,
            f"STOP {stop['stop_num']}: {stop['name'].upper()}",
            "COFFEE, BAKERIES & RESTAURANTS GUIDE",
            food_pages
        )
        shutil.copy2(primary_food_path, os.path.join(OUTPUT_DIRS[1], food_filename))
        generated_files.append(food_filename)
        file_counter += 1

    # Print Terminal Verification Table
    print("\n" + "=" * 98)
    print(f"{'ROMAN VISIT GUIDE RAG CORPUS — PDF VERIFICATION TABLE':^98}")
    print("=" * 98)
    print(f"{'#':<4} {'Filename':<55} {'./rag_corpus':<14} {'./public/rag_corpus':<20}")
    print("-" * 98)

    total_pages_dir1 = 0
    total_pages_dir2 = 0

    for idx, fname in enumerate(generated_files, start=1):
        p1 = os.path.join(OUTPUT_DIRS[0], fname)
        p2 = os.path.join(OUTPUT_DIRS[1], fname)
        c1 = len(PdfReader(p1).pages)
        c2 = len(PdfReader(p2).pages)
        total_pages_dir1 += c1
        total_pages_dir2 += c2
        print(f"{idx:02d}   {fname:<55} {str(c1) + ' pages':<14} {str(c2) + ' pages':<20}")

    print("-" * 98)
    print(f"{'TOTAL':<60} {str(total_pages_dir1) + ' pages':<14} {str(total_pages_dir2) + ' pages':<20}")
    print("=" * 98 + "\n")


if __name__ == "__main__":
    main()
