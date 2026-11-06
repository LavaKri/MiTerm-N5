# MiTerm-N5

Application de terminal adaptée aux lecteurs d'écran (wxPython).

Ce projet est autonome : il ne doit ni référencer, ni importer, ni dépendre d'aucun autre projet.

Les specs vivent dans `specs/` (en français ; les titres de sections restent en anglais, le code les cite).
**Nouvelle session : lire `specs/roadmap.md`, puis seulement le fichier du sujet que l'on touche.** `architecture.md` est la vue d'ensemble et renvoie à `architecture/` (un fichier par sujet : stack, transport, connection, screen, session, window).
Les autres : `interface.md` (ce que voit l'utilisateur), `robustness.md` (sécurité, tampons, threads, journaux), `testing.md` (fausses implémentations, simulateurs), `decisions.md` (pourquoi un choix a été fait), `manual-checks.md` (ce qui reste à écouter avec un lecteur d'écran), `packaging.md`, `open-questions.md` (le seul endroit des questions), `glossaire.md` (les mots du projet), `working-rules.md` (comment le code est organisé ; **le suivre**).

**Les specs suivent le code, dans le même commit.** Un changement de comportement, de décision ou de place d'un fichier met à jour la spec de son sujet avant de proposer le commit (une raison qui mérite d'être gardée va dans `decisions.md`).
`glossaire.md` fixe les concepts propres au projet ; un concept nouveau y est ajouté d'abord.
`tests/test_specs.py` échoue quand une spec cite un fichier ou une section qui n'existe plus ; rien ne vérifie le sens, donc relire la spec que l'on touche.
**Format des specs : une phrase par ligne**, sans coupure forcée en cours de phrase (l'utilisateur lit ligne par ligne avec un lecteur d'écran) ; un item de liste commence sur sa ligne et ses phrases suivantes sont indentées.
Dans le texte, on écrit le terme français ; le nom du code, entre accents graves, sert quand on parle du code lui-même (classe, fichier, fonction).

## Stack
- Python 3.14, wxPython 4.3 (contrôles natifs, pour la prise en charge des lecteurs d'écran), platformdirs, markdown-it-py (jetons Markdown rendus dans des contrôles natifs), pywinpty (pseudo-console ConPTY), pyte (émulation de terminal).
- Outils de développement : ruff, mypy, pytest, pytest-cov, Babel (gettext), PyInstaller.
- Pas d'uv.
  Environnement virtuel : `.venv/` (créé avec `--system-site-packages`, wxPython vient de l'installation de base).

## Commands (PowerShell, from repo root)
- Installation (une fois) : `python -m venv .venv --system-site-packages`, puis `.venv\Scripts\python.exe -m pip install -e .[dev]`
- Lancer : `Start.bat` (ou `.venv\Scripts\python.exe -m n5terminal`) ; en mode Develop : `DevelopStart.bat` (ou l'option `--develop`)
- Tests (ciblés d'abord) : `.venv\Scripts\python.exe -m pytest tests/core/test_x.py`, `-k nom`, `-m unit`, `--lf`
- Vérification complète, en quatre commandes séparées (jamais enchaînées) : `.venv\Scripts\python.exe -m pytest`, puis `.venv\Scripts\python.exe -m ruff check`, `.venv\Scripts\python.exe -m ruff format --check`, `.venv\Scripts\python.exe -m mypy src tests`

## Layout
Modèle-Vue-Présentateur :
- `src/n5terminal/core/` : le modèle : logique, fichiers.
  **N'importe jamais `wx`.** Sous-paquets, chacun ne dépendant que de ceux d'avant : `config/` (réglages, raccourcis, annonces), `transport/` (comment on atteint un programme), `screen/` (modèles de sortie, filtre, titres), `session/` (état, lanceur, historique) ; `errors.py` à la racine.
- `src/n5terminal/presenters/` : la logique d'un écran.
  **N'importe jamais `wx`.** Parle à sa vue par un `Protocol` ; testé avec une fausse vue.
- `src/n5terminal/ui/` : fenêtres, dialogues et vues wx ; mince, sans logique métier.
- `tests/` reflète `src/n5terminal/`.
  Marqueurs : `unit`, `ui`, `slow`.
- `__version__` dans `src/n5terminal/__init__.py` est le seul endroit du numéro de version.

## Rules
- **Ne jamais commiter sans demander à l'utilisateur.** Proposer le message et attendre son accord.
- **Ne jamais utiliser de sous-agents** (ni l'outil Agent, ni les agents Explore/Plan) : faire toute la recherche et le travail directement avec les autres outils.
- **Ne jamais enchaîner de commandes shell.** Une commande par appel d'outil : pas de `;`, `&&`, `||`, `&`, pas de pipes utilisés pour enchaîner des commandes, pas de `cd x && ...`.
  Lancer les commandes indépendantes en appels d'outils parallèles et les dépendantes l'une après l'autre.
- Code, commentaires, docstrings : anglais.
  Specs : français, sauf les titres de sections (anglais).
  Langue par défaut de l'interface : français ; chaque chaîne visible passe par `_()` ; pas de concaténation de chaînes (utiliser `str.format` avec des champs nommés).
- Annotations de types complètes ; mypy strict sur `core/` et `presenters/`.
  `@dataclass(slots=True)`, `Protocol` pour les contrats, `pathlib.Path`, encodages de fichiers explicites.
- Exceptions spécifiques dérivées d'une erreur de base du projet ; jamais de `except` nu ni d'erreur avalée.
  Les erreurs visibles par l'utilisateur sont annoncées.
- Ruff (longueur de ligne 100, sans tolérance), mypy et pytest doivent passer avant de proposer un commit.
- Ne lancer que les tests nécessaires pendant le travail ; la suite complète, ruff et mypy une seule fois, juste avant de proposer un commit.
- Seul le thread principal touche wx : les threads de travail postent vers l'interface avec `wx.CallAfter`.
- Taille des fichiers (`specs/working-rules.md`) : un fichier dépasse rarement 400 lignes, jamais 600 ; vérifier les fichiers touchés et les découper avant de proposer un commit.

## Accessibility (non-negotiable)
- Tout est utilisable au clavier seul ; nom accessible sur chaque contrôle ; focus initial défini dans chaque dialogue.
- Aucun changement de focus inattendu, aucune information transmise par la couleur seule.
- Natif d'abord : s'appuyer sur les contrôles natifs, la barre d'état et les boîtes de message.
  Toute parole supplémentaire passe par un centre d'annonces (notifications UI Automation sous Windows ; pas de MSAA, pas d'API propre à un éditeur).
- Vérifié à la main avec NVDA et JAWS à chaque étape.
