# Connections (SSH)

Une connexion dit **où** s'exécute ce que l'on lance : sur cet ordinateur, ou sur un serveur SSH.
Vue d'ensemble dans `specs/architecture.md`.
Ce que `ssh.exe` fait vraiment a été mesuré : voir « What `ssh.exe` does (measured) » dans `specs/architecture/transport.md`.
Les raisons des choix sont dans `specs/decisions.md` (2026-11-03) ; ce qui reste ouvert, dans `specs/open-questions.md`.

## What a connection is

Quatre choix indépendants, faits par session :

| Choix | Question | Valeurs |
|---|---|---|
| **Connexion** | Où ça s'exécute ? | Locale, ou un serveur SSH |
| Mode | Pipes ou terminal ? | CLI, TUI |
| Interpréteur | Quel shell local ? | Aucun, Cmd, PowerShell |
| Profil | Comment adapter l'application à ce qui tourne ? | préfixe de l'invite, variables, taille... |

- Ce n'est pas un profil : un profil adapte le comportement à une application, sur l'ordinateur ou sur un serveur.
  Ce n'est pas un interpréteur : le shell d'une connexion est celui du serveur.
- « Locale » est le choix par défaut : rien ne change pour ce qui existe.
- Une connexion se combine avec un profil, choisi avant ou après la connexion, comme avec un shell local.
  Les commandes du profil sont alors tapées dans le shell du serveur.
  Le programme du profil s'écrit par son nom de fichier, sans dossier ni extension (`core/config/profiles.py`, `program_name`) : un chemin Windows n'existe pas sur le serveur.
  Son interpréteur (Cmd, PowerShell) est ignoré, et « Lancer le programme » (F5) est grisé.
- C'est le concept `Transport` de `specs/architecture/transport.md` rendu visible : une connexion SSH est servie par un transport qui enveloppe `ConPtyTransport`.

## The connection file

- Un fichier JSON par connexion, dans le dossier `connections` des données de l'utilisateur, à côté de `profiles` : voir « Where the data lives » dans `specs/architecture/window.md`.
  Il est écrit comme un profil (écriture atomique, sauvegarde, fichier illisible mis de côté).
- Champs : le **nom** (celui du menu), la **cible**, et un **port** facultatif (clé `port`, `null` sans port).
  Une connexion n'a **pas de profil** : un profil de programme se choisit à part, dans le menu Profil (décidé le 2026-11-04) ; une clé `profile` écrite par une version plus ancienne est conservée comme toute clé inconnue, et ignorée.
- Le nom est celui du fichier (`connections\prod.json` est la connexion `prod`), jamais écrit dedans ; 20 caractères au plus (un nom de serveur est plus long qu'un nom de profil, limité à 10), et les autres règles sont celles d'un nom de profil : refusé vide, trop long, déjà pris (casse ignorée) ou contenant un caractère interdit dans un nom de fichier Windows.
- Les clés que cette version ne connaît pas sont conservées quand le fichier est réécrit ; un fichier illisible est mis de côté (`.corrupt`), sa sauvegarde est essayée, et l'utilisateur est prévenu.
- Une valeur d'un mauvais type est ignorée à la lecture, donc un port hors de 1 à 65535 (ou écrit entre guillemets) devient « pas de port ».
- La cible est un **alias** du `~/.ssh/config` de l'utilisateur, ou `utilisateur@hôte`.
  Avec un alias, `ssh` fournit seul l'utilisateur, le port, la clé et le saut (`ProxyJump`) ; sinon MiTerm-N5 passe l'hôte et le port.
- **Aucun secret** : ni mot de passe, ni phrase secrète, ni clé.
  Les clés et l'agent sont ceux du système ; un mot de passe est demandé à chaque connexion.
- MiTerm-N5 ne modifie jamais `~/.ssh/config` ni le `known_hosts` : ce sont les fichiers d'un autre programme, que l'on lit au plus.
- La cible est validée avant tout lancement (`target_problem`, `core/config/connections.py`) : vide (ou rien après le dernier `@`), un tiret au début de la cible **ou de l'hôte après le dernier `@`** (sinon `ssh` la prendrait pour une option), une espace ou une autre espace blanche, un caractère de contrôle ; le port est un entier de 1 à 65535.
  Elle est passée à `ssh` comme un argument à part, jamais dans une chaîne de commande.
- Une cible inutilisable écrite à la main dans un fichier n'empêche pas de lister la connexion (l'utilisateur doit pouvoir la corriger avec Modifier…) : un avertissement le dit à la lecture, et le lancement la refuse.
- Une connexion choisie ne se lance pas toute seule : rien ne s'exécute sans une action de l'utilisateur.

## How a connection is made

1. Le lanceur construit les arguments de `ssh.exe` (le module `core/transport/ssh_launch`, une petite dataclass `SshLaunch`) et le transport (`core/transport/ssh_transport`, `SshTransport`), qui enveloppe un `ConPtyTransport` et ajoute les états de connexion, le programme de saisie et le classement des erreurs.
   Le tube est servi par `core/transport/askpass_server` (le protocole et les threads) sur `core/transport/named_pipe` (les appels Windows et les droits) ; `core/transport/ssh_questions` dit quel dialogue une question demande.
2. **Quel `ssh.exe`** : celui de Windows, `%SystemRoot%\System32\OpenSSH\ssh.exe`, jamais le premier du `PATH` (celui de Git peut passer devant).
   Un réglage `ssh_path` global permet d'en choisir un autre.
   S'il manque, l'échec est annoncé (« Client OpenSSH introuvable »), comme un programme introuvable.
3. **Les options passées** (`SshLaunch.arguments`) : `-o PermitLocalCommand=yes`, `-o LocalCommand="<programme de saisie>" --connected` (le chemin entre guillemets, repris tel quel par `ssh`), `-o ConnectTimeout=15`, `-o ServerAliveInterval=15`, `-o ServerAliveCountMax=3` (une coupure est vue en 45 s au plus), puis `--` et la cible, après les options : même validée, la cible ne peut pas être prise pour une option.
   Le port s'ajoute par `-p`.
   Dans la version portable, `-o UserKnownHostsFile="<chemin>"` : entre guillemets, avec des barres obliques (`C:/dossier avec espace/known_hosts`), parce que la barre oblique inverse est un échappement dans les options de `ssh`.
   `SshLaunch` valide la cible et le port à sa création (`InvalidConnectionError`) : rien n'est construit avec une cible refusée.
   Sans commande distante : `ssh` ouvre le shell du serveur et demande un terminal parce que son entrée est une pseudo-console.
4. **L'environnement de `ssh` seulement** (pas celui de MiTerm-N5, et `ssh` ne le transmet pas au serveur) : `SSH_ASKPASS` (le programme de saisie), `SSH_ASKPASS_REQUIRE=force`, le nom du tube et un jeton aléatoire.
5. **Les états**, annoncés comme ceux de tout transport (ceux du `ConPtyTransport` enveloppé ne comptent pas : il se dit « connecté » dès que `ssh` démarre) :
   - `connecting` : au début de `start`, avant même que le tube existe ;
   - `authenticating` : le premier appel du programme de saisie (une connexion par clé n'en a pas) ;
   - `connected` : le signal de `LocalCommand`, après l'authentification et avant la session ; **c'est le seul signal** (voir « The lost signal ») ;
   - `closed` : `ssh` s'est terminé et sa dernière sortie est remise, avec son code (celui de la commande distante, ou 255 pour une erreur de `ssh`) ; `on_exit` vient dès que `ssh` se termine, `closed` après ;
   - `failed` : `ssh` s'est terminé avant `connected` avec une erreur que `classify_ssh_end` reconnaît, ou `start` a échoué.
   Le transport dit comment il a fini par deux propriétés (le `Protocol` `ConnectionReport`, `core/transport/transport.py`) : `failure` (l'erreur, pour `failed`) et `cancelled` (l'utilisateur a annulé un dialogue : l'état est `closed`, sans erreur, et l'interface annonce « Connexion annulée. »).
   `write` est refusé (`TransportClosedError`) tant que l'état n'est pas `connected`.
6. **Le contrat d'interaction** (voir `specs/architecture/transport.md`, `TransportInteraction`) est implémenté par le présentateur : `confirm_host_key(texte) -> bool`, `ask_secret(question) -> str | None` (`None` : l'utilisateur a annulé) et `withdraw()` (fermer le dialogue encore ouvert : sa question n'attend plus de réponse).
   Le transport les appelle depuis son thread et attend la réponse ; le présentateur ouvre le dialogue dans le thread de l'interface (`wx.CallAfter`), sans jamais le bloquer.
   `withdraw` est appelé quand l'utilisateur ferme la connexion pendant un dialogue, quand `ssh` se termine pendant un dialogue (le programme de saisie a abandonné au bout de son délai) et quand `ssh` pose une seconde question alors que la première est encore ouverte ; l'implémentation le traite comme une annulation.
7. **Au démarrage** (`SshTransport.start`), dans cet ordre : le programme de saisie existe (sinon `AskpassNotFoundError`, un `ProgramNotFoundError`, rien n'est créé) ; le tube est créé (`NamedPipeError` si le nom est déjà pris) ; `ssh` est lancé (`ProgramNotFoundError` si `ssh.exe` manque, le tube est alors fermé).
   Le tube existe donc avant `ssh` : le programme de saisie ne peut pas arriver sur un tube absent.

### The askpass program

- `SSH_ASKPASS` demande un exécutable, sans argument : un script ou un `.bat` ne convient pas (un `.bat` coupe le message à son premier saut de ligne).
  Le programme est **un exécutable de type console** (pour que sa sortie standard arrive à `ssh` ; sous la pseudo-console, il n'ouvre aucune fenêtre), qui appelle le module `n5terminal.askpass`.
- **En développement** : un point d'entrée `[project.scripts]` de `pyproject.toml` (`n5terminal-askpass`) fait créer `.venv\Scripts\n5terminal-askpass.exe` par `pip install -e .[dev]`, comme `n5terminal.exe` existe déjà pour `[project.gui-scripts]`.
- **Empaqueté** : un second exécutable, `MiTerm-N5-askpass.exe`, dans `_internal` avec les bibliothèques de l'application (un seul `COLLECT` de PyInstaller, puis `Built.bat` le déplace : `specs/packaging.md`, « Build ») : il ajoute très peu au dossier.
- **Ses deux rôles** : appelé avec une question en argument, il la transmet ; appelé avec `--connected`, il signale la connexion.
- **Le module** : `askpass.py`, à la racine du paquet (hors des couches) et **limité à la bibliothèque standard**, parce que `ssh` le relance à chaque question ; le client du tube est `run`, `exchange` et `open_pipe`.
- **L'environnement** : l'application pose `N5_ASKPASS_PIPE` (le nom complet du tube) et `N5_ASKPASS_TOKEN` (le jeton) dans l'environnement de `ssh` seulement ; `LocalCommand` les reçoit de `ssh`.
  Sans l'un des deux, ou sans argument, le programme se termine avec le code 2 sans rien envoyer.
- **Le tube** : l'application ouvre un tube nommé `\\.\pipe\n5terminal-askpass-<hasard>`, réservé à l'utilisateur courant, et accepte un échange court par appel (un thread par appel : une question qui attend l'utilisateur n'arrête pas le tube).
  Il est réservé par son descripteur de sécurité (`D:P(A;;GA;;;<SID de l'utilisateur>)`, pas même les administrateurs) ; il refuse les clients venus du réseau (`PIPE_REJECT_REMOTE_CLIENTS`) ; il est créé avec `FILE_FLAG_FIRST_PIPE_INSTANCE`, qui échoue si le nom est déjà pris ; une nouvelle instance attend dès qu'un client est connecté, pour que le nom ne soit jamais libre.
  Une ligne de plus de 64 Kio, ou qui n'est pas une requête, est abandonnée : la connexion est fermée sans réponse.
  Le programme envoie une ligne JSON UTF-8 : `{"token": …, "event": "ask" ou "connected", "text": la question}`.
  L'application répond par une ligne : `{"answer": "…"}` à une question, `{"ok": true}` à `connected`, `{"refused": true}` quand l'utilisateur annule.
  Un jeton faux est ignoré (refusé sans ouvrir de dialogue).
  Si l'application ne répond pas ou se ferme, le programme se termine avec un code non nul, ce qui arrête la demande.
- **Le résultat pour `ssh`** : la réponse est écrite en UTF-8 sur la sortie standard, suivie d'un saut de ligne, et rien d'autre, ni sur la sortie d'erreur ; le code de sortie est 0 (réponse donnée, ou `connected` reconnu), 1 (refusé) ou 2 (application introuvable, réponse absente ou incomprise).
  `ssh` ignore le code de `LocalCommand` (mesuré, `specs/architecture/transport.md`).
- **Ses délais** : le programme a une minuterie qui le termine avec le code 2 : 120 s pour une question (l'utilisateur cherche son mot de passe), 5 s pour `--connected` (`ssh` attend la fin de `LocalCommand` avant d'ouvrir le shell, mesuré : un tube qui ne répond plus ne doit pas retenir la session).
- **Le tube occupé** : entre deux appels, le tube n'a un instant aucune instance libre ; `FileIO` le dit par `errno` 22 (pas de `winerror`).
  Le programme attend alors une instance (`WaitNamedPipe`, 100 ms) et réessaie jusqu'à 6 fois ; un tube qui n'existe pas n'est pas attendu.
- **Une réponse refusée** (code de sortie non nul) fait arrêter `ssh` sur une clé d'hôte, mais **pas** sur un mot de passe : `ssh` rappelle alors le programme jusqu'à `NumberOfPasswordPrompts` (3).
  Le transport se souvient donc de l'annulation et refuse les appels suivants sans ouvrir de dialogue (mesuré avec le vrai `ssh.exe` : un seul dialogue, fin en 0,7 s ; trois mots de passe faux : trois dialogues, 9 s, le délai du serveur).
- **Une seconde question pendant qu'une est ouverte** : le programme qui a posé la première a abandonné (sa minuterie) et `ssh` rappelle.
  Le transport retire le vieux dialogue (`withdraw`), refuse la nouvelle question et compte l'annulation.
  Une réponse qui arrive quand le programme n'attend plus est jetée (`reply_lost`) et compte aussi pour une annulation.
- Le texte qu'il reçoit n'entre jamais dans un journal : les journaux du tube disent l'événement (`ask`, `connected`), jamais son texte (un test le vérifie).

### The lost signal

`ssh` ignore l'échec de `LocalCommand` et ouvre le shell quand même (`specs/architecture/transport.md`) : le signal `connected` peut se perdre sans que rien le dise.
Il n'y a **pas de repli par le temps ni par la sortie** : une connexion par clé n'appelle le programme de saisie qu'une fois connectée, donc une authentification lente ne se distingue pas d'un signal perdu, et la sortie d'un serveur (une bannière) peut contenir n'importe quel texte.
On prévient la perte : le tube existe avant `ssh` et le programme de saisie est vérifié avant le lancement.
Une session qui se termine sans `connected` avec le code 0 est journalisée (niveau `WARNING`, sans texte secret) : un bogue serait visible.
Tant que le signal manque, `write` reste refusé et l'état reste `authenticating` ou `connecting` ; l'utilisateur ferme la connexion avec Ctrl+Pause.

### Which dialog for which question

La question arrive en anglais (`ssh` n'est pas traduit) ; on la reconnaît par son texte :
- se termine par `(yes/no/[fingerprint])? ` ou commence par `Please type 'yes', 'no' or the fingerprint` : une **clé d'hôte** ;
- se termine par `password: ` ou commence par `Enter passphrase for key` : un **secret** ;
- toute autre question (un second facteur, par exemple `Verification code: `) : un secret aussi, saisi masqué.

Les dialogues sont natifs, avec un nom accessible et un focus initial :
- **Clé d'hôte** : le texte complet de `ssh` (la deuxième ligne donne l'empreinte) dans un champ en lecture seule, atteint par Tab et copiable ; deux boutons « Faire confiance et continuer » et « Annuler », le second par défaut.
- **Secret** : une étiquette qui reprend la question, un champ masqué, « OK » et « Annuler ».
- Annuler un dialogue annonce « Connexion annulée. », pas une erreur.

### Host keys

- C'est `ssh` qui écrit la clé dans le `known_hosts`, après la réponse `yes` de l'utilisateur (« Permanently added… »).
  MiTerm-N5 relaie seulement la réponse.
- **Version locale** : le `known_hosts` du système, sans option.
- **Version portable** (et mode Develop) : `-o UserKnownHostsFile=<dossier des données>\known_hosts`, pour ne rien écrire hors du dossier.
  Un serveur connu du système y redemande une confirmation, une fois.
- Une clé modifiée est refusée par `ssh` seul, sans appeler le programme de saisie, avec un grand cadre sur la sortie d'erreur ; elle est annoncée comme une erreur de clé d'hôte.
  Effacer la ligne fautive (`ssh-keygen -R`) reste à faire à la main.

### Errors

`ssh` termine avec 255 pour toute erreur, et son message n'est que du texte du terminal.
Une fonction pure de `core/transport` (`classify_ssh_end`, `ssh_errors.py`) classe la fin du texte (les 4096 derniers caractères reçus) avec le code, d'après les textes mesurés ; elle rend l'erreur (`AuthenticationError`, `HostKeyError` ou `ConnectionFailedError`, toutes des `SshConnectionError`, avec la ligne qui dit pourquoi dans `detail`) ou rien :
- `Permission denied` : `AuthenticationError` ;
- `REMOTE HOST IDENTIFICATION HAS CHANGED` ou `Host key verification failed` : `HostKeyError`, sauf quand l'utilisateur vient de refuser lui-même la clé (alors « Clé d'hôte refusée. », pas une erreur) ;
- `Connection timed out`, `Connection refused`, `banner exchange`, `Could not resolve hostname`, `No route to host` : `ConnectionFailedError` ;
- tout autre 255 : `ConnectionFailedError` avec la dernière ligne du texte.
Un code autre que 255 (celui de la commande distante), ou une annulation de l'utilisateur (le paramètre `user_cancelled`), ne donne pas d'erreur.
La fonction ne vaut que pour un `ssh` qui s'est terminé **avant** `connected` : une fois le shell du serveur ouvert, un « Permission denied » écrit par une commande distante ne dit pas pourquoi `ssh` s'arrête.
Les séquences d'échappement de la pseudo-console sont retirées, et les motifs se cherchent dans le texte sans ses sauts de ligne, pour qu'une ligne coupée par la console soit reconnue.
Les messages du système que `ssh` cite sont dans la langue de Windows et leurs accents sont écrits en octal (`Hôte inconnu.` arrive `H\364te inconnu.`, mesuré) : la fonction les remet avec la page de code de Windows, pour que l'annonce se lise.
Le texte reste dans la zone de sortie ; l'erreur est en plus annoncée.

## What the session does

Première version : **ouvrir le shell du serveur**, toujours en TUI.
- Le menu **Connexion**, entre Profil et Terminal : Choix connexion (un sous-menu à choix unique, Locale et les connexions, comme Profil > Choix profil), **Se connecter**, **Se déconnecter** (la même commande que « Arrêter le programme » pendant une connexion), Ajouter…, Modifier…, Supprimer, Client SSH….
  Les raccourcis par défaut sont F6 (Se connecter), F7 (Se déconnecter) et Maj+F6 (Locale), modifiables dans Préférences > Raccourcis ; F5 ne change pas.
  Les règles de grisage sont dans `specs/interface.md`, « Connections ».
- Les commandes qui parlent de cet ordinateur, grisées avec « Indisponible avec une connexion. » : le dossier de travail, les dossiers récents, l'interpréteur, le mode.
  « Lancer le programme » (F5) n'en fait pas partie : avec une connexion fermée il l'ouvre puis tape le nom de fichier du programme du profil dans le shell du serveur ; ouverte, il est grisé (le shell du serveur n'est pas reconnu).
- **Entrée dans le champ de commande**, au repos avec une connexion choisie, ouvre la connexion ; le texte tapé est envoyé une fois connecté (la même mécanique que la ligne tapée à un shell local, `Run.pending_line`).
- La connexion est une **exécution** de la session comme une autre (`Run`) : même `Run`, même flux de sortie, mêmes états ; seul le lanceur change (il rend un `SshTransport` et un modèle d'écran de terminal).
  Tant qu'elle existe, la phase est « en cours » : toutes les règles de grisage « tant qu'un programme tourne » valent sans cas particulier.
- Pendant la session, « Arrêter le programme » (Ctrl+Pause) ferme la connexion ; fermer la fenêtre demande confirmation, comme pour un programme en cours.
- **Où l'état se dit** (détail dans `specs/interface.md`, « Connection state ») :
  - la barre d'état : « Connexion… », « Authentification… », « Connecté à <nom> », « Déconnecté (code n) » ;
  - une annonce par changement d'état, de la catégorie « Connexion, état » ; les erreurs sont de la catégorie « Échec de lancement » ;
  - la sortie : un titre `# SSH <nom>` et une ligne « Vers <cible> » écrits au lancement, une ligne « Déconnecté (code n). » dans la partie de fin ;
  - le titre de la fenêtre : « sur SSH <nom> » à la place du dossier, avec « (non connecté) » à la fin tant que l'état n'est pas `connected` ;
  - Session > Informations sur la session… : le nom, la cible, l'état, la durée.
- Le focus suit les règles de `specs/interface.md`, « Focus and caret » : au lancement de la connexion, dans la zone de sortie, sur le titre `# SSH <nom>` (règle B) ; le texte qui arrive ensuite du serveur ne déplace ni le focus ni le curseur de texte (règle C).
- Le préfixe d'invite d'un profil est ignoré avec une connexion (il agit par l'environnement du shell local).

## Not in the first version

- Une commande tapée au repos qui s'exécute sur le serveur (`ssh serveur commande`).
- Un dossier de travail distant, et la reconnaissance de l'invite d'un shell distant (celle de `core/session/shell_prompt` est faite pour Cmd et PowerShell).
- Le préfixe d'invite sur le serveur (envoyer une ligne `PS1=...` à l'ouverture).
- Une empreinte attendue dans le fichier de la connexion ; effacer une clé modifiée depuis l'application ; les saisies de second facteur à vérifier.

## Order of work

1. Les specs (ce document), puis la donnée `Connection` et son fichier (`core/config`), avec les tests des fichiers abîmés et de la validation de la cible.
2. Le point d'entrée `n5terminal-askpass` : vérifier à la main qu'un exécutable console, lancé par `ssh.exe`, rend sa réponse sur la sortie standard, sans fenêtre, sous la pseudo-console du projet.
3. `SshLaunch` (arguments, environnement) et la fonction de classement des erreurs, testées avec les textes mesurés.
4. Le tube et le programme de saisie, puis `SshTransport` et ses états, testés avec un faux `ssh` (voir plus bas).
   **Fait** (2026-11-04) : `named_pipe`, `askpass_server`, `ssh_questions`, `ssh_transport` ; le contrat d'interaction est défini (`TransportInteraction`), pas encore implémenté.
5. Le présentateur qui implémente le contrat d'interaction ; les dialogues ; le menu Connexion, les annonces, la barre d'état, le titre, les règles de commandes grisées.
   **Fait** (2026-11-04) : `presenters/connection_part.py` (ouvrir, suivre, fermer ; un mixin du présentateur de session), `connection_session.py` (le choix, la fin, l'échec du démarrage), `connection_interaction.py` (du thread du transport à la fenêtre), `connection_catalog.py`, `connection_editor.py`, `ssh_choice.py` ; `ui/connection_menu.py`, `connection_actions.py`, `connection_dialog.py`, `connection_prompts.py`, `ssh_dialog.py` et `program_dialog.py` (commun avec PowerShell) ; la partie de fin (`ScreenUpdate.closing`, `OutputText`) ; le réglage `ssh_path` ; le `known_hosts` des versions portable et develop (`known_hosts_file`).
   Reste de cette étape : la page d'aide en anglais.
6. Vérifications à la main contre le serveur de test (`specs/manual-checks.md`, « SSH »).
7. La version portable : le `known_hosts` de `data\`.

## Tests

- Un **faux `ssh`** (`tests/fakes/program_ssh.py`, lancé avec `sys.executable` par `SshLaunch.program_arguments`) joue les scénarios mesurés : clé d'hôte inconnue, mot de passe, mauvais mot de passe, annulation, clé modifiée, délai, refus, connexion coupée, code de sortie distant, signal perdu.
  Le scénario est dans le nom d'hôte (`fake@hostkey.password`, les mots séparés par des points).
  Il appelle le vrai programme de saisie (`n5terminal-askpass.exe`, de `pip install -e .`) comme `ssh` le fait (le texte en argument, la réponse sur la sortie standard), puis `LocalCommand` par un shell.
  Cela teste le vrai tube, le vrai transport et le vrai programme de saisie sans réseau.
- Le tube se teste seul (`tests/core/transport/test_askpass_server.py`) avec le vrai programme de saisie comme client : le jeton, les lignes mal formées, les droits (un descripteur qui ne nomme pas l'utilisateur lui ferme le tube), le nom déjà pris, la fermeture.
- Une **fausse interaction** (`tests/fakes/fake_interaction.py`) donne les réponses de l'utilisateur et sait garder un dialogue ouvert (`hold`) ; `withdraw` le ferme comme une annulation.
- Les présentateurs sont testés avec cette fausse interaction et le faux transport, qui sait déjà jouer `authenticating`.
- Un vrai serveur ne sert qu'aux vérifications à la main : un `sshd` dans Debian sous WSL (`specs/manual-checks.md`, « SSH »).
