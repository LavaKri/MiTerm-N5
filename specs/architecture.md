# Architecture

MiTerm-N5 lance des programmes en ligne de commande et affiche leur sortie dans des contrôles wx natifs, pour qu'elle soit utilisable avec un lecteur d'écran.
Les couches (Modèle-Vue-Présentateur) sont décrites dans `CLAUDE.md`.

## Where to read what

Les couches (Modèle-Vue-Présentateur) et les règles du code sont dans `CLAUDE.md`.
Un fichier par sujet, à lire quand on y touche :

| Sujet | Fichier | Code |
|---|---|---|
| Pourquoi Python d'abord, bibliothèques, l'expérience ConPTY, stratégie de langage | `architecture/stack.md` | |
| Contrat `Transport` (prêt pour SSH), transport ConPTY, lancement des programmes | `architecture/transport.md` | `core/transport/transport.py`, `pipe_transport.py`, `conpty_transport.py` ; `core/session/launcher.py` |
| Connexion SSH : le fichier d'une connexion, `ssh.exe` et le programme de saisie, clés d'hôte, erreurs, ce que fait la session | `architecture/connection.md` | `core/config/connections`, `askpass` (le client du tube), `core/transport/ssh_launch`, `core/transport/ssh_errors`, `core/transport/ssh_questions`, `core/transport/named_pipe`, `core/transport/askpass_server`, `core/transport/ssh_transport` |
| Modèle d'écran, sortie des pipes, titres, marques, taille du terminal, analyse de ligne et éléments reconnus (activités, adresses) | `architecture/screen.md` | `core/screen/screen_model.py`, `pyte_screen_model.py`, `line_output_model.py`, `titles.py`, `terminal_size.py`, `line_analysis.py`, `screen_elements.py`, `addresses.py` |
| Session, état des commandes, présentateur, invite du shell | `architecture/session.md` | `core/session/session_state.py`, `presenters/` |
| La fenêtre, raccourcis, annonces, langue, réglages | `architecture/window.md` | `ui/`, `core/config/shortcuts.py`, `announcements.py`, `settings.py` |

Ailleurs : ce que voit l'utilisateur `interface.md`, sécurité et tampons `robustness.md`, tests `testing.md`, empaquetage `packaging.md`, prochaines étapes `roadmap.md`, questions `open-questions.md`, raisons des choix passés `decisions.md`, vérifications à faire avec un lecteur d'écran `manual-checks.md`, mots du projet `glossaire.md`.

## Vocabulary

Chaque programme que lance MiTerm-N5 est un programme console (sous-système CUI).
Les programmes graphiques ouvrent leurs propres fenêtres, ne peuvent pas être hébergés par des pipes ou ConPTY, et sont hors périmètre.
Les programmes diffèrent par leur usage de la console, et nous nommons les modes d'après le **mécanisme** qui les sert :

| Nom | Modes | Mécanisme | Ce que l'on obtient |
|---|---|---|---|
| CLI (pipes) | 1 à 3 | `subprocess` avec des pipes stdin, stdout, stderr | Texte linéaire, stdout et stderr séparés, code de sortie |
| TUI, orienté lignes | 4 | ConPTY (pywinpty) + pyte, lecture des lignes | Texte linéaire |
| TUI, plein écran | 5 | ConPTY (pywinpty) + pyte, sans prise en charge propre | Ce que pyte montre |

Les modes :
1. Exécuter une fois, lire stdout, stderr et le code de sortie.
2. Flux continu : lire la sortie ligne par ligne pendant que le programme tourne (thread de lecture, annulation).
3. Dialogue par lignes : le programme demande, l'utilisateur répond sur stdin.
4. Le programme a besoin d'un vrai terminal (REPL, invite de mot de passe de `ssh`, couleurs seulement sur un tty) mais sa sortie reste par lignes.
5. Programme plein écran (`vim`, `less`, `htop`) : redessine l'écran avec positionnement du curseur.

« TUI » dans ce projet est le nom de l'infrastructure (terminal virtuel).
À proprement parler, seul le mode 5 a un affichage plein écran.
Le mode 5 n'a pas de prise en charge propre : l'application ne lit pas sa grille, ne gère pas l'écran alternatif et n'envoie pas le clavier directement (`specs/decisions.md`).
Son écran est montré comme celui du mode 4, ce que pyte en rend.

**Ce que voit l'utilisateur : deux désignations, CLI et TUI.** Le menu Session > Mode propose **CLI** (indication « texte simple » : pipes) et **TUI** (indication « terminal interactif » : pseudo-console).
La désignation est le sigle ; l'indication ne fait que l'expliquer.
« CUI » garde son sens général ci-dessus (tout programme console).
Les numéros 1 à 5 restent la classification interne des programmes : CLI couvre 1 à 3, TUI couvre 4 et 5 (affichage par lignes ou plein écran, distingués automatiquement, pas choisis).

Un protocole structuré sur stdin/stdout (JSON, JSON-RPC, comme `claude -p --output-format stream-json`, LSP, MCP) est une variante du mode CLI : les mêmes pipes, avec un décodeur de protocole par-dessus.
Pas dans les premières étapes.

## Choosing the mode

Il n'y a aucun moyen fiable de savoir à l'avance si un programme a besoin d'un terminal, et relancer un programme qui s'est plaint l'exécuterait deux fois (un premier lancement a pu écrire ou envoyer quelque chose).
Donc **l'utilisateur choisit avant le lancement** (décidé) : menu Session > Mode, CLI par défaut.
- **CLI** : les pipes et le `LineOutputModel` d'une ligne.
  **TUI** : un ConPTY à la taille du terminal et `PyteScreenModel`.
  `LaunchMode` (`core/session/session_state.py`) contient le choix, le lanceur construit en conséquence (`Launcher.launch(..., launch_mode=...)`).
- Un shell qui reste ouvert (interpréteur Cmd ou PowerShell) est toujours en TUI : l'item est désactivé et le dit.
  Il est aussi désactivé pendant qu'un programme tourne.
  Le choix est conservé quand on abandonne le shell.
- Plus tard : une liste de programmes connus pour avoir besoin d'un terminal (`vim`, `less`, `htop`, `nano`, `top`, `ssh`, `python` sans arguments) pourra *proposer* le TUI, et un profil pourra mémoriser le mode par programme.
  Un programme qui se plaint de l'absence de terminal est annoncé (« ce programme semble avoir besoin d'un terminal ») avec une proposition de le relancer en TUI, jamais relancé en silence.
- Dans le TUI, le passage à l'affichage plein écran se fait à la première séquence d'écran alternatif ou d'adressage du curseur (de simples couleurs ne prouvent rien), et peut se reproduire pendant que le programme tourne (`git commit` ouvre `vim`).
  Pas choisi par l'utilisateur.
