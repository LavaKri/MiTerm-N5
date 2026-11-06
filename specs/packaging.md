# Packaging

MiTerm-N5 est distribué comme une application Windows construite avec PyInstaller.

- **Un dossier, pas un exe unique** (zippé pour la distribution).
  Un exe unique se décompresse dans un dossier temporaire à chaque démarrage, et chaque nouvelle session est un nouveau processus ; les exe uniques de PyInstaller sont aussi plus souvent signalés par les antivirus.
- **Fenêtré, sans console** : jamais de `print` ; le journal de diagnostic va dans un fichier.
  Les programmes en mode pipes démarrent sans fenêtre (`CREATE_NO_WINDOW`) ; ConPTY fonctionne sans console dans MiTerm-N5.
- **Nouvelle session** : démarre l'exe lui-même quand il est empaqueté (`is_packaged()`, `core/config/packaged.py`, qui lit `sys.frozen`), `python -m n5terminal` en développement.

## Build

`Built.bat`, à la racine, construit la distribution avec le Python de `.venv` :
1. il lit la version (`__version__`, `src/n5terminal/__init__.py`) ;
2. il efface `Dist` et `build`, puis lance PyInstaller sur `packaging/n5terminal.spec` (un dossier, fenêtré) ;
3. il copie `Help`, le dossier `licenses` et `THIRD-PARTY-NOTICES.md` à côté de l'exécutable (les profils de départ sont mis par le spec dans `_internal\StartProfil`) ;
4. il fait `Dist\MiTerm-N5-<version>.zip` (le dossier `MiTerm-N5` dedans).

Le résultat est `Dist\MiTerm-N5\MiTerm-N5.exe` et son dossier `_internal` (Python, wxPython, pywinpty, pyte en fichiers `.py`, les traductions `.mo` dans `n5terminal\locale`).
`Dist` et `build` ne sont pas versionnés.
Pour SSH, `_internal` contient un second exécutable de type console, `MiTerm-N5-askpass.exe` (le programme de saisie de `ssh`, `askpass.py`), construit avec le même `COLLECT` : il partage les bibliothèques d'`_internal` et ajoute très peu d'espace (`specs/architecture/connection.md`).
`COLLECT` met tout exécutable à la racine : le spec le construit avec `contents_directory="."` (il cherche ses bibliothèques dans son propre dossier, pas dans un `_internal` à côté de lui, sinon « Failed to load Python DLL »), et `Built.bat` le déplace dans `_internal`.
La racine ne garde que `MiTerm-N5.exe`, `Help`, `licenses` et les mentions ; `askpass_program_path()` (`core/transport/ssh_launch.py`) le cherche dans `_internal`.
**Mesuré le 2026-11-05** : appelé par un serveur de tube réel, avec le jeton, il rend la réponse sur la sortie standard avec le code 0 en 83 ms ; sans tube, il rend le code 2 en 0,16 s.
**Essayé à la main le 2026-11-05** avec l'application construite (version 0.3.0, avec un lecteur d'écran) : une connexion par mot de passe au serveur de test ouvre le shell Debian, sans autre fenêtre ni problème.
**Essayé le 2026-11-06** sur un PC sans Python : l'application et la connexion fonctionnent, et JAWS la lit comme NVDA (annonces, barre d'état).
Windows a montré l'avertissement SmartScreen (« Windows a protégé votre ordinateur », éditeur inconnu) : c'est celui d'un programme non signé qui vient d'ailleurs, il ne dit rien du contenu.
Il a été refusé à la main pour lancer l'application ; aucune détection de menace de Defender n'a été vue.
Pour qu'il disparaisse il faut une signature de code (ou du temps et de la réputation) : à décider avant de distribuer, non fait.

**Essayé le 2026-11-05** (`Built.bat`, version 0.2.0, PyInstaller 6.22.3) : la construction réussit, le dossier fait 84 Mo et le zip 30 Mo.
`Dist\MiTerm-N5\MiTerm-N5.exe --data-folder <dossier>` démarre, reste ouvert, copie les profils de départ dans `profiles\` et écrit son journal (« starts (portable data) »).
Les avertissements de PyInstaller sont ceux de `OpenConsole.exe` (`ext-ms-win-uiacore-l1-1-*.dll`, des ensembles d'API du système) et `tzdata` introuvable (importation facultative).
Pas encore fait : l'usage de la fenêtre construite avec un lecteur d'écran, une machine sans Python, un antivirus.

## Self-contained folder

Le dossier `DevelopMode` (mode Develop, `specs/architecture/window.md`) n'est pas livré ; le mode Develop prépare ce qui l'est (`starter_profiles`, livré sous le nom `StartProfil`, catalogues, `Help`).
Les profils de départ sont livrés dans `_internal\StartProfil` (`starter_profiles` est leur nom dans le dépôt, et celui du mode Develop) ; `Help` reste à côté de l'exécutable.
Le dossier `Help` est livré à côté de l'exécutable avec les pages `Fr.html` et `En.html` (`specs/interface.md`, « Help ») ; les sources `.md` peuvent l'être aussi.
Le dossier sert aussi de version portable : un fichier vide `portable` à côté de l'exécutable fait ranger les données dans `data\` du même dossier (voir « Where the data lives » dans `specs/architecture/window.md`).
Le fichier n'est pas livré : l'utilisateur le crée pour une clé USB.

Le dossier contient l'exe, l'interpréteur Python, wxPython et wxWidgets, chaque bibliothèque (pywinpty et ses fichiers, pyte) et notre code ; `vcruntime140.dll` vient avec Python et est copiée.
Rien n'est installé sur la machine de l'utilisateur.
Un futur module Rust est un `.pyd` compilé (`.so` sous Linux) copié comme les autres bibliothèques, sans runtime Rust.

Linux, plus tard : le dossier est construit sous Linux (PyInstaller ne fait pas de construction croisée) ; la bibliothèque C et une partie de GTK restent celles du système, comme pour toute application Linux (à vérifier pour wxPython).

## pywinpty

Le paquet installé (3.1.0) contient, en plus de son module compilé `_winpty.cp314-win_amd64.pyd` : `conpty.dll` et `OpenConsole.exe` (un ConPTY livré avec Windows Terminal), `winpty.dll` et `winpty-agent.exe` (l'ancien moteur winpty).
Son README ne les mentionne pas.
PyInstaller n'a aucun hook pour pywinpty (aucun dans pyinstaller-hooks-contrib) : le spec doit collecter tout le paquet (`collect_all("winpty")`), sinon l'exe échoue quand un programme démarre en mode terminal. pywinpty fournit des déclarations de types (`_winpty.pyi`) ; on peut le retirer des modules ignorés par mypy.

## Licenses

- pywinpty : MIT (copyright Spyder IDE).
- pyte : LGPL v3 (métadonnées du paquet) : l'utilisateur doit pouvoir le remplacer.
  Garder pyte en fichiers séparés dans le dossier, pas dans l'archive interne de PyInstaller.
- wcwidth (une dépendance de pyte) : MIT (métadonnées du paquet, version 0.9.4).
- wxPython : wxWindows Library License. platformdirs : MIT.
- Un fichier de mentions des composants tiers accompagne l'application : `THIRD-PARTY-NOTICES.md` à la racine du dépôt (bilingue, le nom, la version et la licence de chaque composant livré, et la façon de remplacer pyte), avec le texte de chaque licence dans `licenses/`.
  Les deux sont copiés à côté de l'exécutable par `Built.bat`.
  Les textes viennent des paquets installés ; à refaire quand une version change.
  OpenConsole.exe (dans pywinpty) est de Microsoft (MIT) ; PyInstaller n'est pas livré, mais sa licence (GPL avec exception) est rappelée.
  Babel est livré parce que `core/config/catalogs.py` l'importe ; c'est une dépendance normale dans `pyproject.toml` (décidé le 2026-11-06), pas seulement de développement.

## Early packaging test

Fait, juste après le modèle d'écran du terminal.
`tools/check_packaging.py` construit `packaging/smoke.spec` (PyInstaller 6.22, un dossier, fenêtré) à partir de `packaging/smoke.py`, exécute l'exécutable et lit les rapports qu'il écrit dans des fichiers (un programme fenêtré n'a pas de console).
Le programme de test ouvre une fenêtre wx, exécute `cmd /c echo` sous ConPTY et lit le résultat à travers `PyteScreenModel`, vérifie les fichiers de pywinpty et ceux de pyte, démarre une nouvelle session de lui-même (`--child`, `sys.executable` une fois figé), et écrit son journal dans un fichier.
Résultat : **réussi**, un dossier de 51 Mo.
- `collect_all("winpty")` apporte `conpty.dll`, `OpenConsole.exe`, `winpty.dll`, `winpty-agent.exe` et le module compilé.
  Filtrer `winpty.tests`, sinon pytest entre aussi (5 Mo de plus).
  PyInstaller avertit que `OpenConsole.exe` a besoin de `ext-ms-win-uiacore-l1-1-*.dll` : des ensembles d'API du système, rien à embarquer ; le programme a tourné sans problème.
- `module_collection_mode={"pyte": "py"}` laisse pyte en fichiers `.py` dans `_internal/pyte/`, hors de l'archive (LGPL : remplaçable par l'utilisateur).
- Fenêtré : `sys.stdout` vaut `None`, donc rien ne doit faire de `print` ; le fichier de journal est écrit.
- Une nouvelle session est l'exécutable relancé ; le parent et l'enfant tournent côte à côte.
- Pas encore testé : l'avis d'un antivirus, une machine sans Python, une seconde version de Windows, l'application réelle et ses traductions.
  À refaire avec le vrai point d'entrée quand il existera.
