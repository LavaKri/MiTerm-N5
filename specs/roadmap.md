# Roadmap

Où en est le projet et ce qui vient ensuite.
**Nouvelle session : commencer ici.** Le détail de ce qui existe est dans les documents nommés ci-dessous et dans l'historique git, pas ici.
Les questions sont seulement dans `specs/open-questions.md`.

## Decisions taken

- Python 3.14, wxPython (contrôles natifs, prise en charge des lecteurs d'écran) ; ruff, mypy, pytest, Babel, PyInstaller.
  Pas d'uv.
  Tout en Python d'abord, dans un dossier autonome ; un module d'écran en Rust est prévu pour la **version 2** (`specs/architecture/stack.md`).
- CLI (pipes) et TUI (pseudo-console + pyte), **choisis par l'utilisateur avant le lancement** ; un shell qui reste ouvert est toujours en TUI (`specs/architecture.md`).
- Une interface `Transport` conçue pour SSH, qui viendra plus tard.
  Pas d'émulateur de terminal maison.
- Une fenêtre = une session = un processus, pas d'onglets (`specs/architecture/session.md`).
- Lancement direct (sans shell) par défaut, un sélecteur de dossier de travail, un Cmd ou PowerShell facultatif qui reste ouvert.
- Un seul modèle de sortie pour tous les modes : une partie fixe et une partie vivante, mises à jour en silence avec le curseur de texte conservé (`specs/interface.md`).
- Menus grisés, jamais masqués ; un seul centre d'annonces ; français par défaut (`specs/interface.md`, `specs/architecture/window.md`).
- Une commande lancée est écrite `# commande`, un titre de niveau 1 ; les touches 1 à 6 et T vont de titre en titre.
  Les profils se choisissent à la main, un fichier chacun (`specs/interface.md`).
- Pas d'affichage plein écran ni de clavier direct vers le programme : l'objectif est de faciliter les éléments simples écrits en ligne (une question, un choix, une barre de progression) par la détection d'activité, la lecture d'une ligne mise en forme et l'identification des activités (`specs/interface.md`, « Activities » ; `specs/decisions.md`).
- Règles du code : `specs/working-rules.md`.
  Un écart est consigné là où il est décidé.

## Done

| Étape | Où elle est décrite |
|---|---|
| Fondations : dépôt, chaîne d'outils, specs, test d'empaquetage précoce (dossier de 51 Mo) | `specs/packaging.md` |
| Transports : `PipeTransport`, `ConPtyTransport`, objet Job, vrai lanceur | `specs/architecture/transport.md` |
| Sortie : filtre, décodeur, modèle d'écran sur pyte, modèle des pipes, point d'échange, test de charge | `specs/architecture/screen.md`, `specs/robustness.md` |
| Session : état et règles des commandes, présentateur, détection de l'invite du shell, mode CLI / TUI | `specs/architecture/session.md` |
| Réglages, raccourcis, annonces, langue | `specs/architecture/window.md` |
| **6a, la fenêtre principale** : faite | `specs/architecture/window.md`, `specs/interface.md` |
| **6b, annonces par UI Automation** (et le garde de premier plan) : faite | `specs/architecture/window.md` |
| **6c, Préférences** : les pages Général (langue, limite de la sortie, profil de démarrage), Annonces (sortie et destinations) et Raccourcis ; les profils ne sont pas dans les Préférences : faites | `specs/interface.md`, « Preferences » |
| **6e, profils** : le cœur (un fichier chacun, les variables et leur remplacement), le menu Profil (choix, suppression), le dialogue Ajouter / Modifier et Définir les variables…, le fichier de lancement `.n5term` passé en argument (profil, variables, dossier de travail) et le bouton d'association de Préférences > Général : faits | `specs/interface.md`, « Profiles » |
| **6d, export et recherche, lignes abandonnées**, **6g** (l'autre direction est écartée, `specs/decisions.md`) : faites | `specs/interface.md`, « Search in the output » ; `specs/robustness.md`, « Export » |
| **Profils de départ** (dossier `starter_profiles`, profil `git` de programme `git`, variables `source`, `message`) | `specs/interface.md`, « Starter profiles » |
| **Journal** : rotation, `--log-level` (`INFO` par défaut), Aide > Ouvrir le dossier des journaux | `specs/robustness.md`, « Logs » |
| **Mode Develop** (`--develop`) : dossier `DevelopMode`, journal `DEBUG`, profils de départ, menu Develop (Catalogues, Programmes de test), « À propos » en zone de texte : faits ; programme de test `DevelopMode/testprograms/Commands.py` fait, les autres sont à définir | `specs/interface.md`, « Catalogs » ; `specs/architecture/window.md` |
| **Envoi de touches** (mode étape) : menu Session > Envoyer une touche, menu contextuel de la zone de sortie, raccourcis modifiables (Maj+Échap et Maj+Entrée par défaut), annonce « Envoie … », filtre de la page Raccourcis : faits | `specs/interface.md`, « Sending keys » |
| **Barre d'état et titre** : trois champs (ligne, état, colonne), profil et dossier dans le titre de la fenêtre, ligne « Depuis … » sous une commande lancée en CLI, Session > Informations sur la session… : faits | `specs/interface.md`, « Status bar », « Session information » |
| **Focus après un envoi** : un lancement met le focus dans la zone de sortie sur la ligne de la commande, un texte ou une touche l'y met sans toucher au curseur de texte : fait | `specs/interface.md`, « Focus and caret » (règle B) |
| **6f, activités du terminal** (menu Terminal, F4, Maj+F4, Ctrl+B, bip) : faites ; la conception est dans `specs/decisions.md` (2026-10-30) et les restes sont écartés | `specs/interface.md`, « Activities » ; `specs/open-questions.md`, « Line analysis and activity » |
| **Aide** (Aide > Ouvrir l'aide, F1, dossier `Help` avec `Fr.md`, `En.md` et leurs pages HTML, Develop > Convertir l'aide en HTML) : faite | `specs/interface.md`, « Help » |
| **Programme d'un profil** (champ Programme, liste de Ctrl+Espace qui dit le nom seul, Profil > Lancer le programme, F5) : fait | `specs/interface.md`, « Profiles », « Profile menu » |
| **Préfixe de l'invite** (champ du profil, `# ` dans les profils de départ Cmd et PowerShell : chaque ligne de commande d'un shell ouvert devient un titre, atteint par les touches 1 et T) : fait | `specs/interface.md`, « Interpreter », « Profile dialog » |
| **Sélection du PowerShell** (menu Session > Interpréteur, réglage global `powershell_path`, liste des PowerShell 7 trouvés ou chemin saisi) et champ Programme d'un profil grisé avec un shell : fait | `specs/interface.md`, « Interpreter », « Profile dialog » |
| **Profil de démarrage** (liste « Profil de démarrage » de Préférences > Général, repli sur Libre) à la place de l'onglet Démarrage : fait | `specs/interface.md`, « Preferences », « Profiles » |
| **Nom MiTerm-N5**, version 0.3.0, `CHANGELOG.md`, `Built.bat` (dossier `Dist` et zip avec la version) | `specs/packaging.md`, `specs/decisions.md` |
| **Premier plan** : le verrou pendant le démarrage du ConPTY et la garde qui regarde la fenêtre au premier plan (la console cachée ne prend plus le focus à la fenêtre principale) : faits, vérifiés avec une fenêtre de test dans l'application | `specs/architecture/window.md`, « Garde de premier plan » ; `specs/decisions.md` |
| **Taille automatique** du terminal : démarre à 120 x 30 (Windows Terminal) | `specs/interface.md`, « Terminal size » |
| **SSH, conception** : ce que fait le `ssh.exe` de Windows (mesuré avec un serveur de test dans WSL), la connexion, le programme de saisie, les clés d'hôte, les erreurs, la session, l'interface (menu Connexion, état dit à cinq endroits) | `specs/architecture/connection.md`, `specs/architecture/transport.md` |
| **SSH, connexions** : fichier d'une connexion, programme de saisie, tube réservé à l'utilisateur, `SshTransport`, présentateur, dialogues (clé d'hôte, mot de passe, connexion, client SSH), menu Connexion, partie de fin, titre et barre d'état : faits, testés avec un faux `ssh` et mesurés avec le vrai `ssh.exe` | `specs/architecture/connection.md`, `specs/interface.md`, « Connections » |
| **Message masqué** : la case « Masquer le message » (champ de mot de passe de Windows, jamais gardé ni écrit dans la sortie), et les profils `ssh-keygen` et `PowerShell` (commandes de clés) : faits ; les commandes de clés de `PowerShell` : ajouter et lister essayées le 2026-11-04 (la connexion par clé marche), supprimer pas encore ; propositions en attente dans `specs/open-questions.md`, « Profile program in the command field » | `specs/interface.md`, « What the command field sends », « Starter profiles » ; `specs/decisions.md` (2026-11-04) |

L'organisation des tests : `specs/testing.md`.

## Accepted limits

- Un enfant démarré entre le lancement du programme et son affectation au job échappe au job.
  La fenêtre dure quelques microsecondes, alors qu'un programme met des millisecondes à démarrer : aucun cas réel n'est connu.
  La fermer demanderait de démarrer le programme suspendu avec des appels Windows directs, que `subprocess` ne permet pas ; le coût est disproportionné.

## Next

**État pour une nouvelle session** : tout ce qui est écrit ci-dessus est commité ; ruff, mypy et pytest passent (avec un lecteur d'écran allumé, pytest peut écrire une exception COM de première chance `0x8001010d`, qui ne fait rien échouer : `specs/testing.md`).
Le mode Develop se lance par `DevelopStart.bat` (`--develop`) ; ses programmes de test sont dans `DevelopMode/testprograms/` (`Commands`, `Cadence`, `Progress`, `Selection`, `Questions`, `Addresses`, l'en-tête commun dans `DevelopMode/testprograms/_common.py`).

**Idées en attente, non décidées** :
- d'autres programmes de test : progression sur une ligne (retour chariot), plantage ou code d'erreur, sortie en couleurs ;
- la ligne « Depuis … » en mode terminal (aujourd'hui seulement en CLI).

Ce qui reste, chaque étape vérifiée à la main et commitée (le reste de 6a à 6g est dans « Done ») :
- **6h** l'empaquetage avec le vrai point d'entrée : `Built.bat` construit le dossier et le zip (fait, `specs/packaging.md`, « Build ») ; fait aussi : `MiTerm-N5-askpass.exe`, le fichier de mentions des composants tiers et l'essai de l'exécutable sur cette machine ; essayé aussi, le 2026-11-06, sur un PC sans Python, avec JAWS et NVDA : tout fonctionne ; Windows y montre l'avertissement SmartScreen (programme non signé), dont la suite (signature de code ou non) reste à décider.

**SSH, ce qui reste** (`specs/architecture/connection.md`, « Order of work ») : la version portable sur une machine sans dossier `.ssh`.
La page d'aide en anglais est faite, le `known_hosts` de la version portable est mesuré (étape 7), et une connexion par mot de passe est essayée dans l'application construite (`MiTerm-N5-askpass.exe`, 2026-11-05).
La donnée `Connection` et son fichier sont faits (`core/config/connections.py`, étape 1) ; le point d'entrée `n5terminal-askpass` (`askpass.py`, le client du tube) est fait et mesuré avec `ssh.exe` sous la pseudo-console, sans fenêtre (étape 2).
`SshLaunch` (`core/transport/ssh_launch.py`, les arguments et l'environnement de `ssh`) et le classement des erreurs (`core/transport/ssh_errors.py`) sont faits et mesurés avec le vrai `ssh.exe` (étape 3).
Le tube (`named_pipe.py`, `askpass_server.py`, réservé à l'utilisateur) et `SshTransport` avec ses états (`ssh_transport.py`) sont faits, testés avec un faux `ssh` (`tests/fakes/program_ssh.py`) et mesurés avec le vrai `ssh.exe` (étape 4).
Le présentateur de la connexion, ses dialogues, le menu Connexion, la partie de fin de la sortie, le choix du `ssh.exe` et les lignes de « Informations sur la session » sont faits, essayés à la main le 2026-11-04 (voir `specs/manual-checks.md`, « SSH ») (étape 5).
Le serveur de test (`sshd` dans Debian sous WSL, port 2222, utilisateur `TestSSH`) est décrit dans `specs/manual-checks.md`, « SSH » ; il faut le garder allumé pendant les essais.
Les questions ouvertes sont dans `specs/open-questions.md`, « SSH connections ».

Ensuite : Linux (un transport `pty`, une construction Linux) ; **version 2** : le module d'écran en Rust (alacritty_terminal, PyO3, maturin) qui passe les mêmes tests de contrat.
