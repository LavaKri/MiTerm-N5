# Session, state and presenter

Une fenêtre, une session ; l'état qui décide des commandes disponibles ; le présentateur qui pilote la fenêtre.
Vue d'ensemble dans `specs/architecture.md`.

## Sessions

**Une fenêtre = une session = un processus.** Pas d'onglets.
Une « nouvelle session » démarre une nouvelle instance de l'application, pour qu'un plantage ou une fermeture n'emporte jamais les autres sessions.
(Un programme lancé par MiTerm-N5 est un processus enfant et ne peut pas faire planter MiTerm-N5 ; l'isolement protège contre un défaut de MiTerm-N5, de wx ou du code natif de pywinpty, et contre la fermeture de l'application qui tuerait tous les programmes en cours.)
- Une session est un objet (`SessionPresenter`, avec le lancement en cours, `Run`), pas un état global, pour que les onglets restent possibles plus tard.
- Pas de mécanisme d'instance unique.
- Fichier de réglages : écriture atomique (fichier temporaire, puis remplacement), le dernier écrivain gagne, lu au démarrage seulement.
  **Écart décidé par rapport à `specs/working-rules.md`** (« une seule instance écrit les fichiers d'un utilisateur ») : plusieurs instances peuvent écrire, puisque les écritures sont atomiques et rares et que perdre un dossier récent est sans gravité.
- Confirmation (dialogue natif) avant de fermer pendant qu'un programme tourne.
- Pas de journal de session (voir « Export » dans `specs/robustness.md`) ; le titre de la fenêtre identifie la session.
- La sortie est gardée après la fin du programme et le code de sortie est annoncé.

## State of the session and available commands

Un seul modèle d'état, dans `core/session/session_state.py`, sans `wx`, décide de ce que l'interface propose :
- `SessionState`, une dataclass figée : la phase (au repos, en cours, programme terminé avec un enfant encore actif), le mode (pipes, ligne, plein écran), l'interpréteur (aucun, Cmd, PowerShell), si un shell qui reste ouvert attend à son invite, s'il y a de la sortie, s'il y a une ligne à renvoyer.
  Seul le présentateur de session le modifie, à partir des événements du transport et de ses propres actions.
- Chaque commande (`CommandId`) a une `Rule` : un `available(state) -> bool` pur et l'annonce qui dit pourquoi elle est refusée.
  `command_states(state)` renvoie l'ensemble des commandes activées et `refusal(command, state)` la raison ; les deux sont testés sans aucune fenêtre, un état à la fois.
  En bref : un changement de dossier demande aucun programme, ou un shell à son invite ; l'interpréteur ne change que sans programme ; « Arrêter » demande un programme ou un enfant resté en cours ; les commandes sur la sortie demandent de la sortie ; le mode d'affichage ne s'applique qu'à un programme en terminal (ou à aucun pour l'instant).
- Le présentateur donne cet ensemble à la vue (`set_commands_enabled`), qui active ou **désactive** (jamais ne masque) les items de menu, les boutons et les raccourcis d'après lui : un seul chemin, donc un item de menu, son raccourci et son bouton sont toujours d'accord.
  Une commande refusée est annoncée avec sa raison.
- Rien n'est partagé entre sessions : chaque fenêtre est un processus (voir plus haut).
  Seul le fichier de réglages (dossiers récents, raccourcis...) l'est, lu au démarrage.
- On ne sait pas avec certitude si un shell attend à son invite : pour Cmd et PowerShell, on peut le deviner d'après l'arbre des processus (aucun enfant sous le shell).
  À vérifier par l'expérience avant de s'y fier (`specs/open-questions.md`).

## The session presenter

`presenters/session_presenter.py`, `SessionPresenter`, testé avec une fausse vue (`presenters/session_view.py`, `SessionView`) et le faux transport.
Il reçoit ses dépendances dans un `SessionServices` (lanceur, réglages, centre d'annonces, `post`, horloge) ; les données d'un lancement (`Run`), l'écouteur de son transport et `SessionServices` sont dans `presenters/session_run.py`.
Les règles qui ne demandent pas le présentateur sont des fonctions à part, testées seules : `launch_failure` (`session_run.py`) choisit l'annonce d'un démarrage qui échoue, `end_text` et `run_text` (`session_info.py`) font le texte de fin et le texte d'état de la barre d'état.
Trois sujets qui ont leur propre état sont dans leur fichier, et le présentateur les tient :
- `presenters/output_flow.py`, `OutputFlow` : le chemin de la sortie depuis le point d'échange jusqu'à la fenêtre, les lignes que la session écrit elle-même (l'écho `# commande` et `> texte`), et les annonces de lignes perdues ou abandonnées.
- `presenters/session_display.py`, `SessionDisplay` : ce que la fenêtre montre de l'état (choix des menus, commandes activées, mode du champ, état, titre), donné seulement quand cela change.
- `presenters/session_choices.py`, `SessionChoices` (`presenter._choices`) : ce que l'utilisateur choisit pour le prochain programme (interpréteur, PowerShell, mode, profil, taille) et les valeurs qui ne sont pas dans l'état (taille, marque de la sortie d'erreur, préfixe de l'invite) ; le présentateur garde les mêmes méthodes publiques et leur délègue.
- `presenters/profile_values.py`, `ProfileValues` (`presenter.profile_values`) : le profil choisi et les valeurs données aux variables de chaque profil pour la session.
- **Un seul chemin pour tous les transports.** `Launcher.launch(...)` (`core/session/launcher.py`) renvoie un transport pas encore démarré, son mode et le modèle d'écran qui le sert (`LineOutputModel` pour les pipes, `PyteScreenModel` pour un terminal).
  Le thread du transport alimente un `ScreenPump` qui publie vers le `DisplayExchange` de la session ; la fenêtre appelle `tick()` toutes les 50 à 100 ms et le présentateur lui remet le lot (`show_output`).
  Les événements qui changent l'état (état, sortie) sont remis au thread de l'interface par `post` ; les événements d'un lancement terminé sont ignorés.
- **Le champ de commande** a deux états : aucun programme, le texte est une ligne de commande (découpée avec les règles de Windows, lancée dans le dossier de travail) ou, avec le programme d'un profil, ses arguments (`SessionPresenter._launch_from_field` met le programme devant, `ProfileValues.takes_arguments`) ; un programme tourne, le texte lui est envoyé avec `\n` (pipes) ou `\r` (terminal).
  Les pipes font l'écho de la ligne `> texte` dans la sortie, un terminal non (il fait l'écho lui-même).
  Une ligne vide est ignorée au repos et envoyée quand un programme tourne.
  Après la fin du programme, mais tant qu'un processus qu'il a démarré écrit encore, rien n'est envoyé et l'utilisateur en est informé.
- **Lancer une commande** (`SessionPresenter._launch`) suit des étapes dans un ordre qui compte : la demande de lancement, la mémorisation de la commande, l'écho `# commande` (pipes seulement), le suivi de l'exécution (état « en cours »), puis le démarrage du transport.
  L'écho passe avant le démarrage, pour que la première sortie du programme ne puisse pas le précéder (un test le fixe).
  `OutputFlow.echo` dit combien de lignes il écrit, et la vue place le curseur de texte d'après ce nombre.
  Un démarrage qui échoue est annoncé par `launch_failure`, et la session redevient prête.
- **Écrire dans le transport** passe par une seule fonction (`_transmit`) pour le texte et pour les touches : un transport fermé et une file d'entrée pleine sont annoncés au même endroit.
- **Historique.** Les commandes lancées, et toutes les lignes envoyées à un programme qui tourne, sont gardées, sauf un message masqué.
  « Renvoyer la dernière commande » (`CommandId.RESEND`) envoie la dernière ligne de la vue de l'historique, comme Ctrl+Espace puis Entrée ; `SessionState.has_history` dit s'il y en a une, et `SessionPresenter._refresh` le tient à jour.
- **Fin d'un programme.** La sortie est annoncée aussitôt ; si le transport n'est pas fermé une seconde plus tard (`CHILD_GRACE`), « un processus démarré par le programme tourne encore » est dit et la barre d'état l'indique.
  Quand le transport est fermé, le modèle lâche ce qu'il retenait et la session est prête ; l'état affiche « Terminé (code n) ».
- **Interpréteur.** Avec un shell, le shell est le programme (démarré une fois) ; la première ligne tapée y est écrite dès qu'il est connecté.
  « Dossier de travail » y tape `cd` seulement quand le shell attend à son invite (paragraphe suivant).
- **Un shell à son invite** (`core/session/shell_prompt.py`, `presenters/prompt_watch.py`, mesuré avec `tools/probe_shell_prompt.py`).
  Deux signaux qui **doivent concorder**, sinon le shell compte comme occupé (la réponse sûre) : (1) l'objet Job du shell contient **un** processus (`ProcessTree.active_processes`, exposé par `ConPtyTransport.active_processes` ; un programme lancé par le shell en fait deux ou plus) ; (2) la ligne du curseur, reconstituée à partir des lignes marquées `continued` (un dossier profond replie l'invite sur plusieurs lignes), ressemble à l'invite de ce shell (`C:\...>` pour Cmd, `PS C:\...>` pour PowerShell).
  Un seul signal est faux : les `pause` et `set /p` de Cmd, les `Read-Host` et `Start-Sleep` de PowerShell attendent avec un seul processus ; et un programme qui vient de démarrer peut encore laisser l'ancienne invite à l'écran.
  Une ligne écrite dans le shell le rend occupé aussitôt, jusqu'à ce que le shell affiche quelque chose de nouveau.
  Limites : une invite personnalisée n'est pas reconnue (l'item reste désactivé) ; une commande interne en attente dont le texte ressemble à une invite serait prise pour une invite.
  Avec un préfixe d'invite, la ligne du curseur doit commencer par le préfixe avec lequel le shell a été lancé (`Run.prompt_prefix`), le reste étant l'invite par défaut.
- **PowerShell choisi.** `shell_command(..., powershell_path)` remplace `powershell.exe` par le chemin du réglage `powershell_path` (`Settings`) ; `LaunchRequest.powershell_path` le porte jusqu'à `build_run`.
  `SessionChoices.set_powershell_path` (par `SessionPresenter.set_powershell_path`) applique la règle `CommandId.SELECT_POWERSHELL` (aucun programme) et annonce le choix ; un `ProgramNotFoundError` du shell PowerShell avec un chemin choisi dit `POWERSHELL_NOT_FOUND`.
  Un profil avec un shell n'a pas de programme : `has_program` est faux et `ProfileValues.program()` est vide.
- **Préfixe de l'invite** (`core/session/shell.py`).
  `shell_command(interpreter, prompt_prefix)` ajoute à PowerShell `-NoExit -Command` et une fonction `prompt` qui appelle l'ancienne ; `shell_environment(...)` donne à Cmd un environnement dont `PROMPT` est précédé du préfixe (`None` sans préfixe : l'environnement est hérité).
  `build_run` les passe au lanceur (`Launcher.launch(..., options=LaunchOptions(mark_stderr, environment))`) ; le préfixe vient du profil choisi (`SessionPresenter.select_profile`), vide sans profil.
- **Taille.** Lancé à la taille choisie ou à 120 x 30 en automatique ; `AutoSizePolicy` reçoit les `overflows` de chaque lot et une croissance redimensionne ensemble le modèle et la pseudo-console.
  Les pipes ne se redimensionnent jamais.
