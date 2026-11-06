# Transports and launching programs

Le contrat `Transport` (préparé pour SSH), le transport ConPTY et la façon de lancer les programmes.
Vue d'ensemble dans `specs/architecture.md`.

## Transport (prepared for SSH)

SSH n'est pas une fonction immédiate mais viendra.
Le code est conçu dès maintenant pour lui ; aucun code ni aucune dépendance SSH n'est encore ajouté.

`core/` définit un `Protocol` `Transport`, implémenté par le transport local par pipes et le transport local ConPTY.
SSH sera une troisième implémentation.
Règles de conception :
- **Des octets, pas du texte.** Le décodage (UTF-8, page de code Windows) se fait au-dessus du transport.
- **Pousser, ne jamais bloquer.** Le transport remet les données reçues à un écouteur depuis son propre thread ; l'application poste vers l'interface avec `wx.CallAfter`.
- **Ordre des événements.** La fin du programme (`on_exit`, avec son code de sortie) est signalée dès qu'il se termine, éventuellement avant les dernières données.
  L'état `closed` vient en dernier, quand plus aucune donnée ne peut arriver : un processus que le programme a laissé tourner peut tenir sa sortie.
  Entre les deux, `write` est refusé et `close` arrête encore ce qui reste.
- **Cycle de vie explicite** : `connecting`, `authenticating`, `connected`, `closed`, `failed`.
  Annoncé à l'utilisateur (barre d'état, centre d'annonces).
- **Les identifiants et les clés d'hôte passent par un `Protocol` d'interaction séparé** (`TransportInteraction` : `ask_secret`, `confirm_host_key`, et `withdraw` pour fermer un dialogue resté ouvert) implémenté par un présentateur qui ouvre un dialogue natif accessible.
  Le transport ne lit jamais d'invites dans le flux de données.
  Les transports locaux ne l'appellent jamais.
- **Comment une connexion distante a fini** : le `Protocol` facultatif `ConnectionReport` (comme `ProcessCounter`, vérifié avec `isinstance`) donne `failure` (l'erreur, quand l'état est `failed`) et `cancelled` (l'utilisateur a annulé un dialogue, ce qui n'est pas une erreur).
- `resize(columns, rows)` et `close()` existent partout (sans effet pour les pipes).
- Aucune notion locale dans l'interface (PID, dossier de travail, environnement) : elles appartiennent aux paramètres de lancement propres à chaque transport (une petite dataclass par transport).
- Des erreurs typées dérivées de l'erreur de base du projet (`ConnectionFailedError`, `AuthenticationError`, `HostKeyError`), toutes annoncées.
- Un échec du démarrage sort de `start()` comme une `TransportError` (le plus souvent une `LaunchError`) et jamais comme une exception du système (`OSError`, `ValueError` pour un caractère nul dans un argument, erreur de `pywinpty`) : chaque transport convertit ce que sa bibliothèque peut lever.
  Le présentateur de session attrape toute `TransportError` au lancement, annonce l'échec et remet la session au repos ; sans cela, une exception imprévue la laisserait « en cours » sans programme, et plus rien ne pourrait être lancé.
- stderr est un second flux facultatif : seuls les pipes le séparent.
- Un faux transport (états, demande de mot de passe, fermeture inattendue) sert dans les tests ; si les présentateurs fonctionnent avec lui, SSH s'y branchera sans surprise.

Seul ce que les transports locaux utilisent vraiment entre dans l'interface ; le reste est documenté ici et ajouté avec SSH.

SSH (décidé le 2026-11-03) : le `ssh.exe` du système, lancé dans le transport ConPTY, sans nouvelle dépendance ; il utilise le `~/.ssh/config`, les clés, l'agent et le `known_hosts` de l'utilisateur, et Windows le met à jour.
Le contrat d'interaction n'a pas besoin d'une bibliothèque : le programme `SSH_ASKPASS` fait passer le mot de passe et la clé d'hôte par des dialogues natifs, et `LocalCommand` signale la connexion établie.
La conception (fichier de connexion, programme de saisie, états, erreurs, session) est dans `specs/architecture/connection.md`.
Une bibliothèque SSH Python (paramiko ou asyncssh, compatibilité avec Python 3.14 à vérifier) ne serait envisagée que si ces mécanismes se révélaient insuffisants : elle demanderait une demande de pty distant (`pty-req`) qui alimente le même écran pyte, et le suivi de ses mises à jour de sécurité.

### What `ssh.exe` does (measured)

Mesuré le 2026-11-03 avec le `ssh.exe` de Windows (OpenSSH_for_Windows_9.5p2) contre un `sshd` de Debian dans WSL (port 2222), avec des programmes jetables et sans terminal.
- Avec `SSH_ASKPASS` et `SSH_ASKPASS_REQUIRE=force`, `ssh` n'a besoin d'aucun terminal : la confirmation de la clé d'hôte et le mot de passe passent tous deux par le programme indiqué.
  Ce doit être un exécutable : un fichier `.bat` coupe le message à son premier saut de ligne, parce qu'une ligne de commande Windows ne peut pas en contenir.
- Le texte arrive en un seul argument, sans variable `SSH_ASKPASS_PROMPT`.
  Pour la clé d'hôte, il tient sur quatre lignes et finit par `Are you sure you want to continue connecting (yes/no/[fingerprint])? ` ; la deuxième ligne donne l'empreinte (`ED25519 key fingerprint is SHA256:…`).
  Pour le mot de passe : `TestSSH@127.0.0.1's password: `.
- Le programme répond sur sa sortie standard.
  Une réponse qui n'est pas `yes`, `no` ou l'empreinte à la question de la clé d'hôte la fait reposer en boucle (`Please type 'yes', 'no' or the fingerprint: `) : pour arrêter `ssh`, le programme doit se terminer avec un code non nul.
- `LocalCommand` (avec `PermitLocalCommand=yes`) s'est exécuté après l'authentification et avant la commande distante : c'est un signal fiable pour l'état `connected`.
- L'avertissement « Warning: Permanently added … » est écrit sur la sortie d'erreur de `ssh`, pas par le programme de saisie.
- Le code de sortie de `ssh` est celui de la commande distante (`exit 7` donne 7) ; toute erreur de `ssh` donne 255.
- **Hôte inconnu refusé** (réponse `no`, ou le programme se termine avec un code non nul) : un seul appel, puis `Host key verification failed.` sur la sortie d'erreur, code 255.
- **Mot de passe faux** : le programme est rappelé avec le même texte, autant de fois que `NumberOfPasswordPrompts` le permet (3 par défaut), avec `Permission denied, please try again.` sur la sortie d'erreur entre deux ; puis `TestSSH@127.0.0.1: Permission denied (publickey,password).`, code 255.
- **Annulation au mot de passe** (le programme se termine avec un code non nul) : `ssh` ne s'arrête pas, il rappelle le programme jusqu'à la même limite.
  Pour qu'une annulation arrête tout de suite, le programme doit se souvenir de l'annulation et refuser sans ouvrir de dialogue, ou la connexion doit se faire avec `NumberOfPasswordPrompts=1`.
- **Clé d'hôte modifiée** : le programme n'est pas appelé.
  Le cadre d'avertissement `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` (une douzaine de lignes, avec l'empreinte reçue et la ligne fautive de `known_hosts`) est écrit sur la sortie d'erreur, puis `Host key verification failed.`, code 255.
- **Délai dépassé** (`ConnectTimeout=3`) : `ssh: connect to host … port 2222: Connection timed out`, code 255, programme non appelé.
- **Connexion refusée** : le texte dépend du cas, `ssh: connect to host … Connection refused` ou `banner exchange: Connection to UNKNOWN port -1: Connection refused` ; code 255, programme non appelé.
- **Dans la pseudo-console du projet** (`ConPtyTransport`, 120 x 30), avec `SSH_ASKPASS` et `SSH_ASKPASS_REQUIRE=force` dans l'environnement du lancement : mêmes appels (clé d'hôte puis mot de passe), rien de ces questions n'apparaît dans le terminal.
  Le terminal reçoit seulement l'avertissement « Warning: Permanently added … », la sortie distante et, en session interactive, la bannière, l'invite de `bash` et « Connection to … closed. ».
  Les états du transport sont `connecting`, `connected` (au lancement du processus) puis `closed`, avec le code de sortie 0 ; `LocalCommand` s'est exécuté (son marqueur est écrit) dans les deux variantes.
- **Avec le vrai programme de saisie** (`n5terminal-askpass.exe`, celui de pip, mesuré le 2026-11-04 : `ssh.exe` lancé dans le `ConPtyTransport` du projet, 120 x 30, contre le même `sshd`, avec un serveur de tube de test) :
  - la clé d'hôte inconnue puis le mot de passe passent par le tube, et la réponse revient par la sortie standard ; rien de ces questions n'apparaît dans le terminal, **aucune fenêtre visible n'est créée** (surveillée toutes les 20 ms) et le premier plan ne change pas ;
  - un mot de passe faux donne trois appels, à 3 s d'écart : le délai est celui du serveur après un échec, pas celui du programme ;
  - une clé d'hôte refusée (`refused`, code 1) donne un seul appel, `Host key verification failed.` et le code 255 ;
  - `LocalCommand` reçoit l'environnement de `ssh` (le tube et le jeton) et s'exécute après l'authentification, **même quand l'exécutable est dans un dossier dont le nom contient une espace**, avec `-o LocalCommand="chemin" --connected` passé par `subprocess.list2cmdline` (le guillemet est repris tel quel par `ssh`) ;
  - un appel du programme (lanceur de pip, Python, le tube) dure environ 60 ms.
- **Quand `LocalCommand` échoue** (mesuré le 2026-11-04, connexion par clé, `ssh.exe` dans le `ConPtyTransport`) :
  - un programme qui se termine avec 1, puis avec 3 : `ssh` **ignore le code**, ouvre le shell et se termine avec 0 à la fin de la session ; aucun avertissement ;
  - un programme introuvable : même résultat, plus la ligne d'erreur de `cmd.exe` dans le terminal (« Le chemin d'accès spécifié est introuvable. ») : `ssh` lance `LocalCommand` par `cmd.exe /c`, et ce que le programme écrit sur la console va dans le flux du terminal ;
  - un programme lent (4 s) : **`ssh` l'attend** avant d'ouvrir la session (le shell apparaît après 4,3 s) ; un signal perdu ne coupe donc rien, mais un programme qui ne se termine pas retient la session.
  - Le signal `connected` peut donc se perdre sans que rien le dise, et un `--connected` bloqué retient le shell.
- **Les arguments de `SshLaunch`** (mesurés le 2026-11-04, même montage, connexion par clé) : `--` avant la cible est accepté ; `-o UserKnownHostsFile="C:/…/dossier avec espace/known_hosts"` écrit la clé dans ce fichier ; le tout passe par `subprocess.list2cmdline` et revient identique par `CommandLineToArgvW` (testé).
- **Le `known_hosts` de la version portable** (mesuré le 2026-11-05, `ssh.exe` 9.5 contre le serveur de test) : avec `-o UserKnownHostsFile="…/data/known_hosts"`, `ssh` écrit la clé dans ce fichier (« Permanently added… ») et ne touche pas au `known_hosts` du système (date inchangée).
  Le dossier du fichier doit exister : sinon `ssh` dit `Failed to add the host to the list of known hosts` et continue sans mémoriser la clé.
  En portable ce dossier existe toujours au lancement, puisque le journal est écrit dans `data\logs\` (`core/config/logging_setup.py`).
  `ssh` ne lit pas `USERPROFILE` (il interroge Windows pour le profil), donc l'absence du dossier `.ssh` n'a pas pu être essayée sans le retirer ; les clés d'identité absentes ne sont que des lignes de débogage (`type -1`) et la connexion se poursuit.
- **Les erreurs**, sorties réelles de `ssh` dans la pseudo-console, classées par `classify_ssh_end` : port fermé (`banner exchange: Connection to UNKNOWN port -1: Connection refused`), nom inconnu (`ssh: Could not resolve hostname nohost.invalid: H\364te inconnu.`, l'accent en octal), mauvais mot de passe (`Permission denied (publickey,password).`), clé modifiée (`REMOTE HOST IDENTIFICATION HAS CHANGED`) et délai dépassé (`Connection timed out`), tous avec le code 255.
- Les messages d'erreur de `ssh` (délai, refus, clé modifiée) ne passent donc que par le terminal : pour les annoncer comme des erreurs de connexion, il faudra les reconnaître par leur texte (anglais, non traduit) et par le code 255.

## ConPTY transport

`core/transport/conpty_transport.py`, `ConPtyTransport` avec `ConPtyLaunch` (arguments, dossier, environnement, colonnes, lignes ; 80 x 24 par défaut, la même taille va à l'écran pyte).
- Un seul thread, la pompe, possède la pseudo-console : il applique un redimensionnement en attente, écrit l'entrée en file, lit la sortie (lectures non bloquantes, une pause de 10 ms au repos) et surveille la fin du programme.
  Un seul flux (`Stream.OUTPUT`), qui porte des séquences VT.
- Entrée : une ligne tapée se termine par un **retour chariot** (`\r`) dans un terminal, pas un saut de ligne : le présentateur envoie `\r` à ce transport et `\n` au transport par pipes.
  Le terminal fait l'écho de ce qui est tapé (pas d'écho local) ; un mot de passe lu par le programme n'est pas affiché.
- Fin : `on_exit` avec le code de sortie dès que le programme se termine, puis la sortie est vidée jusqu'à un silence de 0,2 s, puis `closed`.
  Lâcher la pseudo-console la ferme : les processus que le programme a laissés attachés sont fermés avec elle (contrairement au mode pipes, où ils peuvent continuer à écrire).
- L'objet de pywinpty, qui n'a pas de types, est décrit par le `Protocol` `PseudoConsole` du même fichier (`pid`, `isalive`, `get_exitstatus`, `set_size`, `write`, `read`) : mypy vérifie ce que la pompe en utilise.
- Avant le démarrage, `_spawn` pose le verrou du premier plan (`core/transport/foreground.py`, `hold_foreground`) : sans lui, la console cachée de la pseudo-console prend le premier plan à la fenêtre principale (`specs/architecture/window.md`, « Garde de premier plan »).
- Même objet Job que le transport par pipes (`hold_process_tree`, `keep_children`, `terminate_tree` dans `core/transport/process_tree.py`) : un arrêt termine tout l'arbre.

## Launching programs

- **Lancement direct** (`prog arguments`, sans shell) d'abord : prévisible, sans surprise de guillemets, le code de sortie est celui du programme.
  La ligne tapée est découpée avec les règles des programmes Windows (`core/transport/command_line.py`), pour que le programme reçoive ce que l'utilisateur a tapé.
- Possible plus tard : un réglage « interpréteur » à trois valeurs (aucun, `cmd`, PowerShell), par défaut aucun, donnant accès aux pipes, aux redirections, aux alias et aux commandes internes (`dir`, `cd`).
- Sans shell, un **sélecteur de dossier de travail** est nécessaire (un dialogue natif de choix de dossier, avec un nom accessible), puisque `cd` n'est pas disponible.
- Environnement hérité de MiTerm-N5 ; des ajouts par profil sont possibles plus tard.
- Encodage : décoder en UTF-8, avec repli sur la page de code de la console Windows (`cp850` ou `cp1252`) ; un réglage par profil, puisque les vieux programmes n'utilisent pas UTF-8.
