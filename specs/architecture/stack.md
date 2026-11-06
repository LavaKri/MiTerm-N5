# Stack: language strategy, libraries, experiments

Pourquoi Python d'abord, quelles bibliothèques, et ce que l'expérience ConPTY a montré.
Vue d'ensemble dans `specs/architecture.md`.

## Language strategy

- **Tout en Python + wxPython d'abord**, livré dans un dossier autonome : l'application démarre depuis un exécutable et tout ce dont elle a besoin est dans son dossier (voir `specs/packaging.md`).
- **Modules remplaçables** : chaque partie importante est un contrat (`Protocol`) avec des tests de contrat que toute implémentation doit passer.
  Les données qui traversent un contrat restent simples (octets, chaînes, nombres, listes de lignes), jamais des objets d'une bibliothèque, pour qu'un autre langage puisse prendre la place.
- **Modules Rust, prévus pour la version 2** (réactivité sur les PC modestes), là où une mesure montre que Python ne suffit pas (PyO3, construit avec maturin, livré sous forme de `.pyd` dans le dossier, aucun runtime à installer).
  Ce qu'ils amélioreraient :
  - **Modèle d'écran du terminal** (premier candidat) : `alacritty_terminal` à la place de pyte ; vitesse native, GIL relâché pendant l'émulation (l'interface n'est plus ralentie pendant un flot de sortie, même sur une machine modeste), Apache 2.0 au lieu de LGPL.
  - **Filtre de sortie** (`OutputFilter`) : vitesse native sur les grosses sorties de pipes, GIL relâché.
  - **Décodage et découpage** des grosses sorties (UTF-8, lignes) pour les mêmes raisons, si la mesure le justifie.
  - Les transports attendent surtout des entrées-sorties et y gagnent peu.
- **Python sans GIL** (3.14t) n'est pas disponible pour nous : wxPython n'a pas de build sans GIL.
- **Linux plus tard** : wxPython tourne sur Linux (GTK) ; `Transport` permet déjà un transport `pty`.

Choix écartés :
- C# : pas d'émulateur de terminal mûr.
- C++ avec wxWidgets : notre propre code exposé aux erreurs de mémoire et de threads.
- Rust avec wxDragon : la liaison wxWidgets est trop jeune.
- Rust avec winsafe : Windows seulement.
- Interfaces dessinées avec AccessKit (egui, Slint, Iced) : accessibilité du texte pas assez sûre.
- Tauri : interface web, pas de contrôles natifs.
- Qt : contrôles dessinés par Qt, pas natifs.
- libvterm : pas de liaison Python.

## Libraries

- **Pipes** : `subprocess` (bibliothèque standard).
- **ConPTY** : `pywinpty` (wheel disponible pour Python 3.14), qui enveloppe l'API de pseudo-console de Windows et se rabat sur winpty sur un vieux Windows.
- **Émulation de terminal** : `pyte`.
  Pas d'émulateur maison.
  - Il est derrière le contrat `ScreenModel` (`core/screen/screen_model.py`) et son implémentation `PyteScreenModel` (`core/screen/pyte_screen_model.py`), voir `specs/architecture/screen.md`.
  - pyte 0.8.2 (dernière version, novembre 2023) ne gère **pas** l'écran alternatif (`?1047`/`?1049`), les modes souris ni le collage entre crochets (bracketed paste) ; les modes privés inconnus sont acceptés et ignorés.
    L'écran alternatif n'est plus visé (`specs/decisions.md`) ; si un jour il l'était, il faudrait dériver `Screen` et surcharger `set_mode` / `reset_mode` pour ajouter un second tampon.
  - Le journal des lignes qui quittent l'écran est le nôtre (une surcharge de `index()`), pas `HistoryScreen` : son historique est une `deque` bornée qui perd les vieilles lignes en silence et ne peut pas être remise morceau par morceau, et elle enveloppe chaque événement.
- libvterm a été examiné et écarté : pas de liaison Python utilisable sur PyPI, une bibliothèque native à compiler et à embarquer.

## ConPTY experiment (mode 4)

`tools/capture_conpty.py` lance de vrais programmes sous ConPTY (80 x 24) et enregistre ce que pywinpty renvoie dans `tests/data/captures/*.vt` ; `tools/replay_captures.py` les rejoue dans un `HistoryScreen` de pyte.
Programmes : `cmd /c echo`, 60 lignes, une ligne de 200 caractères, une barre de progression avec retours chariot, des couleurs, des accents, le REPL de Python 3.14, une session interactive de `cmd`, `ssh` sans arguments.
Résultats :
- **pyte suffit pour le mode 4.** Chaque capture se rejoue exactement vers le texte attendu : aucun doublon, aucun caractère parasite.
  La barre de progression garde son dernier état, les 60 lignes sont toutes dans l'historique.
- **Un écran pyte est nécessaire, pas seulement un filtre.** Le REPL de Python redessine toute la ligne, avec couleurs et déplacements du curseur, à chaque touche tapée ; `cmd` fait écho de la commande tapée avec des positions de curseur absolues (`ESC[4;30H`).
  Retirer les séquences seules donnerait du bruit.
- **Séquences de démarrage de ConPTY** : `ESC[1t`, `ESC[c` (une demande des attributs du terminal, laissée sans réponse sans dommage), `ESC[?1004h` (événements de focus), `ESC[?9001h` (mode d'entrée win32). pyte les ignore.
  Les titres de fenêtre arrivent en OSC 0 (`ESC]0;titre ESC\`).
- **Fins de ligne** : `\r\n` ; un `\r` seul reste un retour chariot.
- **Lignes longues** : envoyées entières ; pyte les replie à la largeur de l'écran (voir `specs/open-questions.md`).
- **Écho** : le programme ou la console fait lui-même l'écho de ce qui est tapé.
- **pywinpty** : utiliser le `winpty.PTY` de bas niveau (`spawn`, `read`, `write`, `set_size`, `isalive`, `get_exitstatus`, `pid`).
  `PtyProcess` relaie la sortie par une socket TCP locale, ce qui n'est pas nécessaire.
  `PTY.read` renvoie une `str` (déjà décodée), pas des octets : le transport ConPTY la ré-encode en UTF-8, ce qui garde un seul contrat d'octets pour tous les transports.
  `ssh` a donné son code de sortie (255) correctement.
