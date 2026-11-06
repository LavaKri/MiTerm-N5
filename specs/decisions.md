# Decisions

La raison derrière les choix qui ne sont pas évidents à la lecture du code.
Une entrée par décision, la plus récente d'abord ; ce que fait le comportement reste dans le document de son sujet.
Une décision annulée n'est pas effacée : une nouvelle entrée le dit.

## 2026-11

- **Le curseur du terminal ne se place pas sur le curseur de texte ; seul le sens inverse existe (Ctrl+G, Alt+Début, Alt+Fin).** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* un terminal ne reçoit pas « mets le curseur ici » ; il faudrait envoyer des flèches au programme, ce qui ne marche que sur une ligne de saisie simple (`cmd`, bash, REPL) et échoue ailleurs : menus de sélection (les invites modernes cachent le curseur et marquent le choix par un glyphe ou une vidéo inverse), lignes repliées, curseur de texte dans la partie fixe ou l'historique, programmes en mode application (`ESC O D` au lieu de `ESC [ D`, que pyte ne suit pas : pas de `DECCKM`), PowerShell sans PSReadLine sous lecteur d'écran.
  Une commande qui n'agit que dans un cas étroit et annonce « impossible » le reste du temps coûte plus de doute qu'elle n'apporte ; les flèches du clavier restent la façon de déplacer le curseur d'un programme.
  À reprendre seulement si l'usage montre un cas fréquent.

- **La partie du présentateur de session qui parle d'une connexion est un mixin (`ConnectionPart`), pas un collaborateur à rappels.** Décidé le 2026-11-04.
  *Pourquoi :* `session_presenter.py` avait atteint 637 lignes (limite de 600) avec les connexions ; ouvrir une connexion, suivre ses pas et sa fin touchent l'état, l'exécution en cours, le flux de sortie et la vue, soit une vingtaine de rappels pour un objet à part, ce que l'entrée du 2026-11-03 sur `SessionChoices` déconseille.
  Le mixin déclare ce qu'il emprunte au présentateur (des annotations, vérifiées par mypy) ; ce qui n'a pas besoin de l'état est dans `connection_session.py`.
  Si le présentateur doit encore grandir, la suite reste l'objet de contexte partagé de cette entrée-là.
- **`announcements.py` (367 lignes) n'est pas découpé malgré les annonces ajoutées pour les connexions.** Constat du 2026-11-04.
  *Pourquoi :* il reste sous 400 lignes ; l'entrée du 2026-11-03 demandait de le découper si l'on y ajoutait encore des annonces, ce sera pour la prochaine catégorie.
- **Les connexions : une règle de grisage, pas de profil dans le fichier d'une connexion, Entrée ouvre la connexion, une partie de fin pour la ligne de déconnexion.** Décidé le 2026-11-04.
  *Pourquoi :* une connexion qui s'ouvre compte comme un programme qui tourne, donc Choix connexion, Ajouter, Modifier, Supprimer et Client SSH… se grisent par la règle qui existe déjà pour les profils ; avec une connexion choisie, tout est « sur le serveur », ce qui évite les cas croisés (un programme local lancé sans repasser par « Locale » n'existe pas).
  Le champ « profil » du fichier d'une connexion est retiré : il confondait deux idées (le serveur enregistré, et le profil de programme), et le menu Profil sait déjà s'appliquer avant ou après la connexion.
  Sur un serveur, le programme d'un profil s'écrit par son nom de fichier (`git` pour `C:\...\git.exe`), parce qu'un chemin Windows n'y existe pas ; F5 est grisé, car il taperait ce nom dans un shell dont on ne sait pas s'il attend.
  Entrée dans le champ ouvre la connexion et envoie la ligne tapée une fois connecté : l'utilisateur n'a pas à passer par le menu, et la mécanique (`Run.pending_line`) existe pour les shells locaux.
  La ligne « Déconnecté (code n). » va dans une **partie de fin** après la partie vivante (la partie fixe la mettrait au-dessus du dernier écran) ; Ctrl+Fin la lit, Alt+Fin s'arrête avant elle.
  Le `ssh.exe` se choisit dans un dialogue (comme PowerShell), pas seulement dans le fichier de réglages : l'utilisateur voit lequel est utilisé, et Git en apporte un autre.
- **Une case « Masquer le message » que l'utilisateur coche lui-même, plutôt qu'un masquage automatique.** Décidé le 2026-11-04.
  *Pourquoi :* aucun signal ne dit de façon fiable qu'un programme attend un secret.
  Le mode d'écho de la console (`ENABLE_ECHO_INPUT`) serait le signal d'un vrai terminal, mais sous Windows beaucoup de programmes lisent le mot de passe touche par touche sans le changer (`getpass` de Python, par `msvcrt.getwch`), et tout programme qui lit des touches brutes coupe aussi l'écho sans que ce soit un secret ; le lire exigerait en outre de s'attacher à la console du programme.
  Reconnaître le texte de la question (`password`, `passphrase`, `mot de passe`) est une devinette qui dépend de la langue et du programme : un faux négatif lit le secret à voix haute, un faux positif rend une commande illisible.
  La case est donc le choix de l'utilisateur, qui entend la question ; la devinette pourra seulement la *proposer* plus tard (`specs/open-questions.md`).
  La case se décoche après chaque envoi, parce que l'oublier masquerait la commande suivante, ce qui se remarque mal avec un lecteur d'écran.
  Le masque est celui de Windows (`EM_SETPASSWORDCHAR`) plutôt qu'un second champ : le texte, le curseur de texte et le focus ne bougent pas, et les lecteurs d'écran voient un champ protégé.
- **Le signal `connected` est le seul : pas de repli par le temps ni par la sortie, et on prévient sa perte.** Décidé le 2026-11-04.
  *Pourquoi :* `ssh` ignore l'échec de `LocalCommand` et ouvre le shell (mesuré), donc le signal peut se perdre sans rien dire ; mais une connexion par clé n'appelle le programme de saisie qu'une fois connectée, si bien qu'une authentification lente ne se distingue pas d'un signal perdu, et la sortie d'un serveur (une bannière avant l'authentification) peut contenir le texte qu'on voudrait y lire.
  On rend la perte improbable : le tube existe avant `ssh`, le programme de saisie est vérifié avant le lancement, `--connected` a un délai de 5 s (`ssh` l'attend avant d'ouvrir le shell), et une session qui finit en 0 sans `connected` est journalisée.
  Le prix : si le signal se perd, l'état reste à « Authentification… » et `write` est refusé ; l'utilisateur ferme la connexion.
- **Le programme de saisie abandonne au bout de 120 s (une question) ou 5 s (`--connected`), et une question posée pendant qu'une autre est ouverte retire la première.** Décidé le 2026-11-04.
  *Pourquoi :* sans délai, un dialogue oublié retient `ssh` pour toujours ; le programme qui abandonne laisse le dialogue à l'écran, et `ssh` rappelle alors (trois fois pour un mot de passe), ce qui ouvrirait un second dialogue par-dessus.
  Le transport retire donc l'ancien (`withdraw`), refuse la nouvelle question et compte une annulation.
- **Le tube du programme de saisie est réservé à l'utilisateur par son descripteur de sécurité, pas seulement par le jeton.** Décidé le 2026-11-04.
  *Pourquoi :* ce qui y passe est un mot de passe ; le descripteur par défaut d'un tube nommé laisse la lecture à tout le monde, et `multiprocessing.connection` ne permet pas d'en donner un.
  `named_pipe.py` appelle donc Windows directement (`CreateNamedPipeW` avec `D:P(A;;GA;;;<SID>)`, clients du réseau refusés, `FILE_FLAG_FIRST_PIPE_INSTANCE`) ; le jeton aléatoire est la deuxième barrière.
- **Le nom d'une connexion a 20 caractères au plus (10 pour un profil), et une cible inutilisable écrite à la main reste listée.** Décidé le 2026-11-04.
  *Pourquoi :* un nom de serveur (`serveur-prod-1`) dépasse vite 10 caractères ; les autres règles du nom (caractères interdits, noms réservés, casse) sont celles d'un fichier Windows, donc les mêmes que pour un profil (`name_problem` reçoit la longueur).
  Une cible refusée par `target_problem` (tiret au début, espace, rien) est listée avec un avertissement plutôt que sautée : sinon la connexion disparaîtrait du menu sans que l'utilisateur puisse la corriger avec Modifier…, et le lancement la refuse de toute façon.
  Le tiret est refusé aussi au début de l'hôte après le `@` (`admin@-oProxyCommand=…`), pour la même raison que celui du début de la cible.
- **Les connexions SSH ont leur menu, et leur état se dit à cinq endroits : barre d'état, annonce, sortie, titre de la fenêtre, informations sur la session.** Décidé le 2026-11-04.
  *Pourquoi :* le menu Connexion suit le menu Profil (choix, ajouter, modifier, supprimer), et « Se déconnecter » y double « Arrêter le programme » parce qu'on la cherche là.
  Le titre dit « sur SSH nom » à la place du dossier, avec « (non connecté) » à la fin, seule information d'état du titre (les étapes de la connexion restent dans la barre d'état et les annonces, pour que le titre ne change qu'à l'ouverture et à la fin) : le lecteur d'écran lit le titre quand la fenêtre reprend le focus, et c'est là qu'on apprend qu'une connexion s'est coupée.
  Un titre `# SSH nom` et une ligne « Vers … » sont écrits dans la sortie au lancement, contre la règle des modes terminal qui n'écrivent pas la commande : à la connexion la sortie est encore vide, sans rien à lire ni titre à atteindre, et le focus n'aurait nulle part où aller.
  Pas de quatrième champ dans la barre d'état : le lecteur d'écran le relirait à chaque passage pour peu d'information de plus.
  Les annonces de transition ont leur catégorie (« Connexion, état ») ; les erreurs restent dans « Échec de lancement », qu'on ne peut pas mettre sur « rien ».
- **Le présentateur de session reste au-dessus de 400 lignes (483, sous la limite de 600).** Constat du 2026-11-03.
  *Pourquoi :* sortir le suivi de l'exécution (`handle_state`, `handle_exit`, `_closed`) demanderait de passer l'état au nouveau fichier par des rappels (`get_state`, `set_state`, `say`), qui cachent qui possède l'état ; `SessionChoices` a déjà ce défaut.
  On a plutôt sorti les règles pures (`end_text`, `run_text`, `launch_failure`), découpé `_launch` en étapes nommées dans un ordre qui compte, et fait passer toute écriture dans le transport par une seule fonction (`_transmit`).
  Si le fichier doit encore grandir, la suite est un objet de contexte partagé (l'état, l'exécution en cours, le dossier, une seule méthode pour écrire l'état), pas des rappels ; l'API publique du présentateur ne change pas.
- **`Settings` écrit encore chaque champ à trois endroits (déclaration, lecture, `save`), gardés par des tests, sans table de champs.** Constat du 2026-11-03.
  *Pourquoi :* une table générique passerait par `setattr` avec des noms en chaînes, et mypy ne vérifierait plus ni les noms ni les types ; plusieurs champs (raccourcis, annonces, dossiers récents) ont leur propre logique.
  Les gardes sont `CHANGED_VALUES` (`tests/core/config/test_settings.py` : un champ ajouté doit y figurer, et chaque champ est écrit puis relu) et le test qui compare `LAUNCH_MODES` et `INTERPRETERS` aux énumérations (`settings.py` précède `session/` et ne peut pas les importer).
- **Les dépendances à Windows de `core/` sont connues et seront isolées au début du portage Linux, pas avant.** Constat du 2026-11-03.
  Ce sont `winpty` (`conpty_transport.py`), `ctypes` et l'objet Job (`process_tree.py`, aussi utilisé par le transport par pipes), `winreg` (`file_association.py`) et l'import en dur de `ConPtyTransport` par `ProcessLauncher`.
  *Pourquoi :* rien de cela ne se teste ici (ni machine Linux, ni lecteur d'écran Linux) ; des imports différés écrits maintenant ne seraient jamais exécutés et pourraient cacher une vraie erreur Windows.
  Au début du portage : une fabrique de transport par plateforme, `process_tree.py` derrière un `Protocol`, `file_association.py` derrière le `Protocol` `Registry` qui existe déjà.
- **`announcements.py` (338 lignes) et `main_menu.py` (363) ne sont pas découpés.** Constat du 2026-11-03.
  *Pourquoi :* la règle est « découper par raison de changer, pas par taille » (`specs/working-rules.md`) ; `main_menu.py` est un seul sujet, une fonction par menu.
  `announcements.py` mêle le vocabulaire (`Destination`, `Category`, `Announce`) et le mécanisme (`AnnouncementCenter`, récepteurs, bip) : on le découpera en deux fichiers si l'on y ajoute encore des annonces ou un autre récepteur (19 fichiers l'importent, tests compris).
  Pour `main_menu.py`, le menu Session est le premier à sortir quand le fichier approchera de 400 lignes.
- **La lecture de l'ancienne clé `display` des réglages et des profils est retirée.** Constat du 2026-11-03.
  *Pourquoi :* seules des versions de développement l'ont écrite (`terminal_view_only` la remplace depuis avant la 0.2.0), et aucun profil livré ne l'utilise.
  Un fichier de ce temps, jamais réenregistré depuis, est lu avec la valeur par défaut (la vue montre l'historique).

## 2026-10

- **L'application s'appelle MiTerm-N5 (« Mi » : moitié, à mi-chemin entre un lanceur et un terminal complet).**
  *Pourquoi :* « N5 » est un suffixe, parce que les autres applications de l'utilisateur ne doivent pas toutes commencer par « N5 » (la sélection par la première lettre y perdrait) ; et le mot « terminal » seul promettait un vrai terminal, avec le clavier envoyé directement.
  Le nom est écrit à un seul endroit du code (`APP_NAME`, `core/config/location.py`) ; l'identifiant de registre est `MiTermN5.LaunchFile` (un identifiant de type de fichier n'a pas de tiret).
  Le paquet Python `n5terminal`, l'extension `.n5term` et les fichiers `n5terminal.*` gardent leur nom : l'utilisateur ne les voit pas, ou seulement dans les fichiers qu'il écrit.
  Les dossiers de données ont changé de nom (`%APPDATA%\MiTerm-N5`) ; ceux de l'ancien nom ne sont pas repris.
- **Un profil a un programme facultatif ; la liste de Ctrl+Espace dit son nom seul, et le champ reçoit le chemin entier.**
  *Pourquoi :* ne pas répéter le programme dans chaque commande courante (`status` au lieu de `git status`), pouvoir viser un autre exécutable sans retaper son nom, et ne pas faire entendre un chemin long à chaque ligne de la liste.
  Le nom est celui du fichier sans dossier ni extension (`Git.exe` : « Git »).
  Le programme n'est pas vérifié à l'enregistrement (il peut être sur une autre machine) et les variables n'y sont pas remplacées.
  Un profil sans programme garde ses commandes complètes : les copies faites par une version plus ancienne marchent comme avant.
  Profil > Lancer le programme (F5) lance le programme seul, sans changer aucune valeur de la session.
- **Dans un fichier de lancement, la clé du profil est `profile`, sans alias français.**
  *Pourquoi :* les clés du fichier sont des identifiants techniques en anglais, comme les noms des variables (`name`, `source`) qui sont aussi ceux des `{variables}` des profils ; en traduire une seule aurait fait deux écritures pour un même fichier.
  Les avertissements de lecture du fichier, eux, sont dits dans la langue de l'application.
- **L'affichage plein écran (mode 5) et le clavier direct vers le programme sont abandonnés.**
  *Pourquoi :* les programmes plein écran (`vim`, `htop`) ne sont pas prévus pour un lecteur d'écran, et l'effort de lire une grille, de gérer l'écran alternatif et de partager le clavier n'aurait jamais donné un résultat à la hauteur.
  L'objectif devient de rendre faciles les éléments simples que les programmes écrivent en ligne : répondre à une question, faire un choix, suivre une barre de progression.
  Un programme plein écran reste lancé, et son écran est lu comme celui du mode 4 (ce que pyte montre), sans prise en charge propre.
  Cela annule « le clavier direct reste à concevoir » (mode étape, plus bas) et la section « Affichage plein écran » de `specs/open-questions.md`.
  La règle de la dernière vue ajoutée à l'historique n'est plus à revoir pour l'écran alternatif.
- **L'activité du terminal est un drapeau vérifié à intervalle fixe, et l'analyse est une fonction de ligne appelée à la demande ; la couche d'événements automatiques (`Recognizer`, `OutputAnalyzer`) est retirée.**
  *Pourquoi :* l'annonce automatique par reconnaisseurs demandait un état, une limite de fréquence par genre, des paliers, une clé par barre et une catégorie réglée par l'écoute, pour un résultat bavard ; un drapeau à intervalle fixe est prévisible, l'utilisateur règle la cadence (1 s par défaut) et la coupe d'un raccourci, et une barre qui stagne ne dit rien tant que le terminal ne change pas.
  Une fonction sans état qui lit une ligne se teste avec des chaînes, marche aussi en mode CLI, et sert à trois usages (annoncer la ligne d'une activité, la lire à la demande, lister les éléments d'un écran).
  Les éléments se reconnaissent par leur texte, pas par les attributs des cellules : pas de couleurs, et `marked_rows` n'est ajouté que si le texte ne suffit pas (`specs/open-questions.md`).
  Les flèches haut et bas restent la lecture native du texte brut : la lecture mise en forme est une commande à part, pour ne pas doubler ni couper celle du lecteur d'écran.
- **L'activité est signalée par défaut (« Messages ou bip »), avec un bip généré.**
  *Pourquoi :* l'utilisateur veut savoir qu'il se passe quelque chose, même minime, sans avoir à chercher.
  Cela annule « rien par défaut tant que les reconnaisseurs n'ont pas été écoutés » et « pas de son dans la première version » : un bip généré (`winsound.Beep`) ne demande aucun fichier à livrer, et un raccourci le coupe aussitôt.
  Le bip est court et joué depuis un thread de travail, parce que `winsound.Beep` bloque le thread qui l'appelle.
- **Les menus Affichage et Déplacement sont réunis en un menu Terminal, avec les sous-menus Déplacement et Activités.**
  *Pourquoi :* tout ce qui concerne le terminal (sa taille, sa vue, ses lignes, son curseur, ses activités) se trouve au même endroit, et l'effacement de la sortie y reste.
- **Envoyer depuis le champ de commande déplace le focus dans la zone de sortie.**
  *Pourquoi :* l'utilisateur lit ce que le programme répond ; après un lancement il est amené à la ligne de la commande, après un texte ou une touche il reste où il lisait.
  Cela annule la règle B (« lancer un programme ou envoyer une ligne garde le focus dans le champ »).
  Le prix : taper plusieurs lignes de suite demande un Tab pour revenir au champ.
- **La barre d'état a trois champs (ligne, état, colonne) et ne montre plus le dernier message ; le profil et le dossier sont dans le titre de la fenêtre ; le dossier d'une commande lancée est écrit sous son titre.**
  *Pourquoi :* le dernier message était déjà dit par le lecteur d'écran, et le lire en bas doublait la parole ; la colonne manquait pour lire une sortie en colonnes ; le profil et le dossier se lisent au moment où la fenêtre prend le focus.
  La ligne « Depuis C:\test\ » reste dans la sortie et l'export : elle dit où une commande a tourné, même après un changement de dossier.
  Elle n'est écrite que pour un lancement avec des tubes, parce qu'en mode terminal le programme dessine lui-même son écran ; le dossier est alors dans Session > Informations sur la session….
  Une ligne vide en bas de l'écran d'un programme terminé sans historique est laissée telle que le terminal l'a (décidé).
- **Quand un programme terminal finit sur un écran vide, sa dernière vue non vide passe dans l'historique.**
  *Pourquoi :* un programme plein écran (Codex, par exemple) efface l'écran en partant ; aucune ligne n'a défilé, donc la zone de sortie se vidait et le dernier résultat était perdu.
  Une règle à chaque effacement d'écran aurait déversé une image dans l'historique à chaque rafraîchissement de `top` ou de `htop` : la règle ne joue qu'à la fin du programme.
  Un écran qui garde du texte à la fin n'est pas touché.
  Si l'écran alternatif est géré un jour (`specs/open-questions.md`), la règle sera à revoir.
- **Les touches s'envoient une à une depuis un menu ou un raccourci (mode étape), avec seulement Maj+Échap et Maj+Entrée par défaut ; le clavier direct vers le programme reste à concevoir.**
  *Pourquoi :* il suffit pour les programmes interactifs légers (questions, listes), il garde le champ de commande et le focus où ils sont, et il prépare le clavier direct avec la même table de touches.
  Pas de raccourci par défaut pour les touches courantes (flèches, Ctrl+C) : ce sont déjà celles du champ de texte, et les règles des raccourcis existantes (Ctrl ou Alt obligatoire) évitent de casser la saisie.
  Maj+Échap et Maj+Entrée sont les deux exceptions voulues par l'utilisateur, car ni l'une ni l'autre ne gêne la saisie ; Maj+Échap est donc permis, alors que l'Échap seul reste réservé (il ferme les dialogues).
  La zone de sortie est un contrôle de texte riche en lecture seule : Windows y affiche son propre menu (clic droit, touche Application, Maj+F10) ; l'application prend ces trois gestes elle-même pour montrer le sien.
  Le menu Envoyer est dans le menu contextuel de la zone de sortie (avec Copier et Tout sélectionner), pas dans celui du champ de commande, qui garde Historique et ses commandes de texte natives (un menu à nous remplace le menu natif).
  L'envoi est annoncé une fois (« Envoie Échap. »), parce qu'un écran qui ne change pas ne dirait rien.

- **Le mode Develop (`--develop`) a son dossier `DevelopMode\` et écrit les profils dans `starter_profiles\` ; les valeurs par défaut des préférences restent dans le code.**
  *Pourquoi :* préparer ce qui est livré (profils de départ, catalogues, programmes de test) sans toucher au profil Windows du développeur, comme le fait le mode portable ; un fichier de valeurs par défaut séparé aurait ajouté une deuxième couche de valeurs par défaut, donc un doute sur ce que « Rétablir » rétablit en mode normal.
  Une copie d'un profil de départ déjà faite chez un utilisateur n'est pas remplacée (marqueur `.starters`).
  Voir « Where the data lives » dans `specs/architecture/window.md`.
- **Le dialogue Catalogues ne modifie que les traductions, jamais les identifiants, et n'a pas de catalogue anglais.**
  *Pourquoi :* l'identifiant anglais est la clé qui relie le code au catalogue ; le changer sans changer le code ferait perdre la traduction, et un catalogue anglais ajouterait un fichier dont le texte s'écarterait de celui du code.
  Un texte anglais se corrige dans le code.
  Les champs `{nom}` sont vérifiés à OK, sans afficher les drapeaux du catalogue : le nom du champ se reconnaît dans le message.
  Le fichier source de chaque message (sans numéro de ligne) est noté dans le `.pot` et, comme `pybabel update` le recopie, dans les `.po` : on laisse faire Babel plutôt que d'ajouter un outil pour les retirer.
- **« À propos » utilise la boîte de texte brut en lecture seule** (`Feedback.show_text`) plutôt qu'une boîte de message, plus facile à lire.

- **Le journal est au niveau `INFO` par défaut** (la spec disait `WARNING`).
  *Pourquoi :* l'utilisateur lance l'application par un raccourci, sans option, et un journal qui ne garde que les erreurs ne dit pas ce qui s'est passé juste avant.
  Le niveau `INFO` n'écrit que le démarrage, le nom des programmes lancés, l'état du transport et les codes de sortie, et la rotation (5 fichiers de 1 Mo) le borne ; le texte tapé, la sortie et les arguments n'y entrent jamais (les arguments seulement avec `DEBUG`).

- **La recherche ne revient pas au début, ne sélectionne rien et ignore la casse ; l'export est en UTF-8 avec des sauts de ligne Windows.** Le curseur de texte se place au début de l'occurrence et l'annonce lit la ligne.
  *Pourquoi :* le curseur de texte est la seule position que l'utilisateur lit avec son lecteur d'écran, et une sélection serait lue en plus de la ligne ; un retour silencieux au début ferait croire qu'une occurrence est nouvelle.
  Les sauts de ligne Windows parce que le bloc-notes et les outils de l'utilisateur les attendent.
  La recherche part du curseur de texte, qui reste à la fin tant qu'on ne l'a pas déplacé : depuis la fin, Rechercher le précédent (Maj+F3) atteint la dernière occurrence.
  Décidé par l'utilisateur de laisser ainsi, sans retour au début ni option de direction.
- **Deux modes de données : local (profil Windows, itinérant) et portable (dossier `data\` à côté de l'exécutable).** Le mode portable se choisit par un fichier vide `portable` à côté de l'exécutable, ou par `--data-folder`, qui l'emporte.
  *Pourquoi :* une clé USB ne doit laisser aucune trace de MiTerm-N5 sur le PC hôte, et un double-clic sans argument doit suffire.
  Les réglages sont itinérants parce qu'ils sont petits et suivent l'utilisateur ; le journal reste local.
  La détection automatique d'un disque amovible a été écartée : une clé peut se déclarer comme un disque fixe.
  Voir « Where the data lives » dans `specs/architecture/window.md`.
- **Les specs sont en français, `CLAUDE.md` compris ; le code, les commentaires et les docstrings restent en anglais.** Les noms qui existent dans le code restent tels quels entre accents graves.
  Les concepts propres au projet sont fixés dans `specs/glossaire.md`, trié par nom du code, sans test : une liste de mots à éviter ne serait jamais complète.
  *Pourquoi :* l'utilisateur lit les specs tous les jours et les lit mieux en français.
  Cela annule l'entrée « les documents restent en anglais ».
  `specs/working-rules.md`, copie du modèle de l'utilisateur, est traduit aussi.
- **Les titres de sections des specs restent en anglais ; le corps est en français.** *Pourquoi :* les docstrings du code (en anglais) citent ces titres (« Menus » dans `specs/interface.md`, par exemple), et mélanger deux langues dans le code surprend ; l'utilisateur lit sans peine de courts titres techniques, ses difficultés viennent des longs textes.
  `tests/test_specs.py` vérifie que chaque titre cité existe.
- **Les specs s'écrivent à raison d'une phrase par ligne.**
  *Pourquoi :* l'utilisateur les lit ligne par ligne avec un lecteur d'écran, et une coupure en plein milieu d'une phrase lit un fragment à chaque flèche Bas.
  Les diffs git ne montrent aussi que la phrase modifiée.
  `tests/test_specs.py` vérifie qu'une phrase n'est pas coupée en cours de ligne.
- **Le dossier `docs/` est devenu `specs/`.** *Pourquoi :* garder `docs/` pour de vrais documents (manuels, aide), et nommer ici ce que le dossier contient : des spécifications.
- **Le champ de commande ne prend pas Haut et Bas.** Ils restent les touches du champ de texte ; l'historique ne s'atteint que par la liste de Ctrl+Espace.
  *Pourquoi :* l'utilisateur ne veut pas que les flèches changent ce qui a été tapé.
  Retiré de `CommandHistory`, du présentateur et du champ.
- **Un raccourci reste écrit dans le texte de son item de menu**, grisé ou non.
  *Pourquoi :* l'utilisateur y lit le raccourci.
  La touche est aussi prise par la fenêtre avant le menu, donc une commande grisée peut annoncer pourquoi elle est refusée.
- **Annonces : options du fournisseur UI Automation `ServerSideProvider | UseComThreading` (0x22), hébergé par une fenêtre hors de vue, enfant du panneau.** *Pourquoi :* la première version utilisait la valeur 1 (côté client) et Windows ne livrait jamais les notifications, sans aucun message.
  Le schéma qui fonctionne est celui de `specs/architecture/window.md`.
- **Le premier plan est empêché puis repris à la fenêtre de console de la pseudo-console** : un verrou (`LockSetForegroundWindow`) pendant le démarrage du ConPTY, puis une garde qui regarde la fenêtre au premier plan (2026-11-03).
  *Pourquoi :* un programme qui demande à son terminal de restaurer sa fenêtre (`ESC [ 1 t`), et le démarrage d'un ConPTY lui-même, faisaient que Windows donnait le premier plan à la console cachée de ce processus, et rien n'y fonctionnait.
  La garde d'origine se fondait sur `IsActive()` de la fenêtre principale ; mesuré avec une vraie fenêtre, il reste vrai pendant que la console a le premier plan, donc elle n'agissait jamais pour un démarrage.
  Elle regarde maintenant la fenêtre qui tient le premier plan, et le verrou empêche le vol dans le cas courant (le programme qui démarre).
  Mesuré avec un journal de la fenêtre au premier plan, pas deviné.
  Le propriétaire de la pseudo-console (`ConptyReparentPseudoConsole`, comme Windows Terminal) n'est pas utilisable : pywinpty ne donne pas le handle de la pseudo-console.
- **La taille automatique du terminal part de 120 x 30**, pas de 80 x 24 (2026-11-03).
  *Pourquoi :* la ligne qui déclenche l'agrandissement est déjà écrite à l'ancienne largeur et reste repliée ; à 80 colonnes, une simple phrase d'aide (`wsl -l`, 99 caractères) était coupée au milieu d'un mot au début de chaque session.
  120 x 30 est la taille de départ de Windows Terminal (`initialCols` et `initialRows`, documentation de Microsoft), donc ce que les programmes écrivent pour lui y tient.
  La taille 80 x 24 reste un choix de la liste.
- **SSH : une connexion, qui n'est ni un profil ni un interpréteur** (2026-11-03).
  *Pourquoi :* un profil adapte l'application à un programme, que celui-ci tourne ici ou sur un serveur ; un interpréteur est un shell local.
  La connexion dit seulement où ça s'exécute, et se combine avec un profil choisi avant ou après (`specs/architecture/connection.md`).
- **SSH passe par le `ssh.exe` de Windows, pas par une bibliothèque Python** (2026-11-03).
  *Pourquoi :* Windows le met à jour, alors qu'une bibliothèque (et `cryptography`) demanderait de suivre ses failles et de publier une nouvelle version de l'application, ce que l'auteur ne veut pas s'imposer ; et il lit déjà le `~/.ssh/config`, les clés et l'agent.
  Mesuré : `SSH_ASKPASS` avec `SSH_ASKPASS_REQUIRE=force` fait passer la clé d'hôte et le mot de passe par un programme à nous, sans terminal, et `LocalCommand` dit quand la connexion est établie ; les dialogues natifs et les états exacts n'ont donc pas besoin d'une bibliothèque (`specs/architecture/transport.md`).
- **Les clés d'hôte restent dans le `known_hosts` de `ssh`, et MiTerm-N5 ne l'écrit pas** (2026-11-03).
  *Pourquoi :* c'est le fichier d'un autre programme, partagé par tous les outils SSH, que `ssh` réécrit (ajouts, hachage, `ssh-keygen -R`) ; il ne peut contenir que des hôtes et des clés.
  `ssh` y ajoute la clé de lui-même après le `yes` de l'utilisateur, mesuré.
  Version locale : le fichier du système.
  Version portable : `-o UserKnownHostsFile` vers un fichier de `data\`, pour ne rien écrire hors du dossier (au prix d'une confirmation de plus par serveur).
- **Une connexion est un petit fichier propre à MiTerm-N5, et les détails du serveur restent dans `~/.ssh/config`** (2026-11-03).
  *Pourquoi :* le fichier donne le nom du menu, la cible et un profil facultatif ; l'utilisateur, le port, la clé et le saut s'écrivent déjà dans `~/.ssh/config`, que la ligne de commande partage et que MiTerm-N5 ne modifie jamais.
  Les fichiers de connexion sont rangés avec les réglages, dans les versions locale et portable.
- **Le programme de saisie est un exécutable console à part, et un `.bat` ne convient pas** (2026-11-03).
  *Pourquoi :* `SSH_ASKPASS` ne prend qu'un chemin, et un `.bat` coupe le message à son premier saut de ligne, donc la question de la clé d'hôte (avec l'empreinte) arriverait tronquée, mesuré.
  En développement, il vient d'un point d'entrée de `pyproject.toml` ; empaqueté, d'un second exécutable du même dossier.
- **`core/` est découpé en `config`, `transport`, `screen`, `session`**, chacun ne dépendant que de ceux d'avant.
  *Pourquoi :* un dossier plat de 28 modules était difficile à lire et à charger en contexte.
- **La règle « les documents suivent le code, dans le même commit » est dans `CLAUDE.md`**, pas dans `working-rules.md`.
  *Pourquoi :* `CLAUDE.md` est chargé à chaque session, alors que `working-rules.md` n'est lu qu'à la demande.
- **Les specs sont vérifiées par un test** (`tests/test_specs.py`) : un fichier cité dans une spec doit exister.
  *Pourquoi :* un déplacement de fichiers avait laissé quatre documents périmés et seule une recherche l'avait vu.
- **`say(announce, **values)` garde des valeurs non typées, et un test lit le code pour vérifier chaque appel** (`tests/test_announcement_calls.py`).
  *Pourquoi :* les valeurs dépendent de l'annonce (`program`, `code`, `line`...) ; typer chaque appel demanderait une classe par annonce, pour un gain que le test donne déjà : un champ oublié se voit à l'exécution du test, pas quand l'utilisateur déclenche l'annonce.
  `SessionPresenter._set_state` n'a plus de `**changes` : il reçoit un état fait avec `dataclasses.replace`, dont mypy vérifie les champs.

## Earlier

- **Le mode (CLI ou TUI) est choisi par l'utilisateur avant le lancement**, jamais deviné.
  *Pourquoi :* aucun moyen de savoir si un programme a besoin d'un terminal, et relancer un programme qui s'est plaint l'exécuterait deux fois.
  Voir `specs/architecture.md`.
- **Les titres sont la navigation :** une commande lancée est écrite `# commande` (un titre de niveau 1), et les touches 1 à 6 et T vont de titre en titre (Maj pour reculer).
  Voir `specs/interface.md`.
- **L'historique des commandes en garde 20 par session et n'est pas un réglage.** *Pourquoi :* l'utilisateur a jugé 20 suffisant ; seule la limite de la sortie est un réglage.
- **Un profil se choisit à la main et rien n'est appliqué automatiquement.** L'utilisateur n'a jamais décidé qu'une commande applique un profil d'elle-même ; la question reste ouverte (`specs/open-questions.md`).
- **Grisé, jamais masqué :** une commande inutilisable est grisée et sa raison annoncée.
- **Un shell qui reste ouvert (Cmd ou PowerShell) est toujours en TUI.** Décidé par l'utilisateur le 2026-10-28 : Cmd aurait pu tourner sur des pipes, mais sans pseudo-console l'invite, la fin d'une commande et les programmes interactifs lancés dans le shell ne sont plus fiables.
  Voir `specs/architecture.md`.
- **Le préfixe de l'invite est un champ du profil, mis devant l'invite de l'utilisateur ; MiTerm-N5 ne devine pas l'invite et n'écrit rien sur l'ordinateur.** Décidé avec l'utilisateur le 2026-11-01.
  *Pourquoi :* sous Cmd et PowerShell, le shell écrit lui-même la commande après son invite, et la sortie est l'écran de l'émulateur, réécrit sans cesse : une ligne `# commande` ajoutée par MiTerm-N5 serait écrasée ou lue en double.
  Reconnaître l'invite cassait dès qu'elle est personnalisée.
  Faire écrire `# ` par le shell lui-même (variable `PROMPT` de Cmd pour le processus, fonction `prompt` de PowerShell passée à `-Command`) rend chaque ligne de commande un titre de niveau 1, sans fichier ni Registre touchés ; le préfixe s'ajoute devant l'invite de l'utilisateur au lieu de la remplacer.
  Le titre contient donc le dossier et la commande (`# C:\Dev> dir`), pas la commande seule comme en CLI.
  Voir « Interpreter » dans `specs/interface.md`.
- **Le PowerShell lancé est un réglage global, choisi par un item du menu Interpréteur, et le champ Programme d'un profil est grisé avec un shell.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* un seul interpréteur « PowerShell » (au lieu d'un par version) garde le menu court, et la version à lancer est une propriété de l'ordinateur plus que d'un profil ; le menu est plus près de l'interpréteur que les Préférences, et un dialogue réunit la liste des versions trouvées et un chemin à saisir.
  Windows PowerShell 5.1 reste le défaut (toujours présent) ; PowerShell 7 (`pwsh.exe`) est proposé s'il est trouvé, essayé le 2026-11-02 avec le préfixe de l'invite et la ligne tapée (PSReadLine y reste actif, l'émulateur le suit).
  Un shell reçoit des commandes complètes : un programme de profil n'y a pas de sens, le champ est grisé et la valeur écrite est gardée mais ignorée.
  Voir « Interpreter » dans `specs/interface.md`.
- **L'application démarre sur un profil (réglage `startup_profile` de l'onglet Général) ; l'onglet Démarrage des Préférences est supprimé.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* tout ce que l'onglet réglait (interpréteur, mode, taille, vue terminal, préfixe StdErr) fait partie d'un profil ; deux endroits pour les mêmes valeurs se contredisaient (un profil choisi remplaçait le démarrage).
  « Libre » reste le profil par défaut et le repli quand le profil de démarrage a disparu ou ne se lit pas.
  Les clés `launch_mode`, `interpreter`, `terminal_size`, `terminal_view_only` et `stderr_prefix` restent dans le fichier des réglages comme valeurs de départ de Libre, sans page pour les changer ; les retirer du code est possible plus tard.
  Voir « Preferences » dans `specs/interface.md`.
- **Avec un profil à programme, le champ de commande reçoit les arguments ; le type « les deux » devient « Shell » et ne s'offre qu'avec un interpréteur.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* le programme est déjà dans le profil, le retaper est inutile, et taper `-t ed25519` avec le profil `ssh-keygen` lançait un programme nommé `-t` ; Entrée sur un champ vide lance ainsi le programme, ce que F5 fait déjà.
  Le profil « Libre » sert à lancer autre chose ; un profil sans programme garde des commandes complètes (un enchaînement de programmes différents).
  L'étiquette du champ dit ce qu'il prend (« Commande », le nom du profil, « Message ») au lieu de « Commande » et « Entrée du programme » : on l'entend en revenant dans le champ.
  Le type « Shell » est le seul que le dialogue offre à un profil de shell (les commandes y sont toujours complètes et toujours listées) ; sans interpréteur, il n'y a que « lancement » et « programme ».
  Changer l'interpréteur, ou lire un ancien fichier, range les commandes dans les types offerts sans en perdre (`fit_uses`) ; le mot `both` des anciens fichiers se lit comme `shell`, et le fichier est réécrit avec `shell` à la prochaine écriture du profil.
  Les lignes d'historique restent entières ; avec un programme de profil, la liste de Ctrl+Espace n'en montre que les arguments, pour les lignes de ce programme.

- **Les items Libre, Locale, Définir les variables, Se connecter, Se déconnecter et Informations sur la session ont un raccourci par défaut ; Libre et Locale sont des items permanents de leur sous-menu.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* un item créé à l'ouverture du menu n'existe pas quand la touche est pressée menu fermé, donc son accélérateur ne pouvait pas marcher ; Libre et Locale sont créés une fois et seuls les profils et les connexions trouvés sont refaits.
  Les touches : F6, F7, Maj+F5, Maj+F6, Ctrl+D, Ctrl+I ; les touches de fonction suivent F5 (Lancer le programme), Ctrl+Alt est évité (c'est AltGr sur un clavier français).
  Deux commandes de plus (`CHOOSE_FREE_PROFILE`, `CHOOSE_LOCAL`) portent les règles de grisage de leur sous-menu, ce qui annonce la raison quand la touche est pressée programme en cours.
  « Se connecter » n'avait pas de raccourci par défaut (choix du 2026-11-04) : l'utilisateur en demande un.

- **La variable `{email}` s'appelle `{comment}`.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* dans le profil `ssh-keygen` c'est le commentaire `-C` de la clé, un texte libre (pas forcément une adresse) qui est copié en clair sur chaque serveur.
  Les anciens fichiers se lisent sans changement : `email` dans la liste des variables d'un profil, `{email}` dans ses commandes et la clé `email` d'un fichier de lancement valent `comment`, et le profil est réécrit avec le nouveau nom à son prochain enregistrement.

- **« Relancer la dernière commande » devient « Renvoyer la dernière commande », dans le menu Édition, et n'a plus de mémoire propre.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* il fait ce que font Ctrl+Espace puis Entrée sur la ligne sélectionnée à l'ouverture, donc il est disponible quand on peut envoyer une ligne avec le champ, en local comme avec une connexion, au repos comme pendant qu'un programme tourne, et il suit le profil choisi parce que la liste le suit.
  Il est à côté de « Historique » dans le menu Édition, parce que ce sont les mêmes lignes ; le raccourci (Ctrl+R) et son identifiant (`program.relaunch`) sont inchangés, pour ne pas perdre un raccourci déjà choisi.
  L'historique garde désormais toute ligne envoyée à un programme qui tourne, sauf un message masqué : l'entrée du 2026-11-02 ne gardait que celles d'un shell, de peur d'un mot de passe, mais l'utilisateur veut pouvoir renvoyer un message à son programme ; la case « Masquer le message » reste le moyen de ne rien garder.
  L'historique reste en mémoire : une version future ne doit pas l'enregistrer (`specs/robustness.md`, « Security »).

- **La recherche a une case « Expression régulière », décochée au départ, plutôt que de lire toute recherche comme une expression.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* la plupart des recherches sont du texte (`C:\Users`, `error (1)`) dont les caractères ont un sens en expression régulière, et une erreur de syntaxe silencieuse se repère mal avec un lecteur d'écran ; la case garde la recherche actuelle telle quelle et refuse une expression invalide dans la boîte, avec la raison dite.
  Les cases « Chercher vers le haut » et « Expression régulière » se rappellent leur dernier état jusqu'à la fin de l'application seulement, pas dans les réglages ; la direction ne sert que depuis la boîte, la sorte de texte est celle que F3 et Maj+F3 répètent.

- **Le profil de départ de PowerShell s'appelle `PowerShell`, plus `PWS`.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* le nom est lu par le lecteur d'écran (étiquette du champ, titre, menu) : `PWS` s'épelle, `PowerShell` se dit ; il tient dans les 10 caractères permis.
  Un utilisateur qui a déjà copié `PWS` le garde (un profil copié n'est jamais écrasé) et reçoit `PowerShell` en plus.

- **Plusieurs lignes se saisissent dans une boîte à part (Ctrl+M), pas dans le champ de commande, et partent en un seul bloc.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* un champ multiligne aurait pris Entrée et Maj+Entrée (déjà « Envoyer Entrée ») et rendu la lecture du champ moins directe ; la boîte laisse le champ tel qu'il est, avec Échap pour fermer et Tab jusqu'à Envoyer, sans case de masquage (un secret se tape dans le champ).
  Le bloc est envoyé en une écriture avec la fin de ligne du programme, comme un collage (essayé avec PowerShell 7, Windows PowerShell 5.1 et Cmd : `\r` marche, `\n` brouille PowerShell et colle les lignes de Cmd) ; Windows PowerShell sans PSReadLine, ce que PowerShell choisit quand un lecteur d'écran tourne, attend une ligne vide pour exécuter, donc une ligne vide est ajoutée pour PowerShell.
  L'historique garde le bloc avec ses vrais sauts de ligne et la liste le lit par sa première ligne et son nombre de lignes : un échappement (`\n`) est ambigu dans des chemins et des scripts, et se lirait « barre oblique inverse n ».
  Choisir un bloc dans la liste ouvre la boîte (le champ n'a qu'une ligne).
  Les titres de la sortie viennent des invites du shell, rien n'est codé pour eux.

- **Le nom d'un profil ou d'une connexion n'accepte qu'une liste de caractères, et le message nomme le caractère refusé.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* le nom est lu par le lecteur d'écran (étiquette du champ, titre, menu), et un caractère invisible, un accent séparé ou un symbole rare donne deux noms qui se lisent pareil ou une lecture incompréhensible ; une liste permise (lettres, chiffres, espace, `- _ . + # ( ) @`) est plus sûre qu'une liste d'interdits, et dire le caractère refusé évite de chercher.
  Les connexions ont la même liste (décidé le même jour) ; un profil ou une connexion ancien garde son nom tant qu'on ne le change pas.
  L'étiquette du champ de commande écrit le nom tel quel (`SetLabelText`) : un `&` d'un ancien nom n'y devient pas une touche d'accès.

- **La lecture confortable dit une ligne filtrée, par des filtres globaux gardés dans un dialogue à part, cherchés dans toute la ligne ; le premier qui trouve quelque chose est le seul appliqué.** Décidé avec l'utilisateur le 2026-11-05.
  *Pourquoi :* chaque commande d'un shell est précédée de son invite et du chemin courant, qu'il est pénible d'entendre ; la sortie reste la vérité (les flèches la lisent), donc seule l'annonce retire l'invite, par deux raccourcis (Ctrl+Alt+Haut et Bas) qui déplacent le curseur de la sortie et annoncent la ligne d'arrivée.
  Un champ « motif d'invite » dans chaque profil et chaque connexion aurait répété les mêmes motifs ; une liste globale à part, dans un dialogue (ajouter, modifier, supprimer, monter, descendre), sert à tous les shells, locaux ou distants, et l'ordre compte parce que le premier motif qui reconnaît la ligne gagne.
  Les motifs ne se fient pas au `# ` du préfixe de profil (un titre de texte peut commencer par `# `) : ils le permettent devant l'invite, sans l'exiger.
  Chaque motif a un remplacement (rien, un mot ou une partie de l'invite par ses groupes), pour qu'une invite longue se dise par un mot qui situe (« Debian ») au lieu d'être seulement retirée ; la fin d'une invite est une espace ou la fin de la ligne, parce que la sortie ne garde pas l'espace qui termine une ligne.
  Les filtres sont cherchés dans toute la ligne (le dialogue sert à retirer ou remplacer n'importe quel morceau, pas seulement une invite : décidé le 2026-11-05, les filtres de départ commencent donc par `^`) et le premier qui trouve quelque chose arrête la recherche : sans cascade, le résultat est celui de l'essai (F1), prévisible, jamais le fruit d'un remplacement qui en déclenche un autre.
  Chaque motif de la liste de départ dit un mot à la place de l'invite (« Commande », « Suite »), traduit dans la langue en cours quand la liste est utilisée : tant que l'utilisateur n'a pas enregistré sa liste, ses réglages n'en gardent aucune (`Settings.prompt_patterns` vaut `None`), pour qu'elle suive la langue ; « Rétablir les motifs de départ » remet les motifs de départ, mots compris, sans effacer les motifs que l'utilisateur a ajoutés.
  Le champ Résultat de l'essai n'interprète rien : il écrit la ligne comme elle serait annoncée.
  Une seconde case étend la lecture confortable aux déplacements par titres (les titres d'un shell sont ses lignes de commande, avec leur invite) ; les deux cases sont globales et décochées au départ.
  Les listes déjà enregistrées avec un motif de départ d'avant la fin de ligne sont remises au motif actuel au chargement, puisque l'utilisateur ne l'avait pas écrit ; un motif qu'il a écrit ou modifié n'est pas touché.
  La case « Inclure les mises en forme d'activités » est une pour tous les motifs, puisque la lecture confortable ne se fait que par ces deux raccourcis.
  Le même mécanisme de déplacement et d'annonce que « Aller au curseur du terminal » est réutilisé, qui n'est lu qu'une fois par NVDA.

- **Chaque commande courante d'un profil a un type (lancement, programme, les deux), choisi dans le dialogue de profil ; la liste de Ctrl+Espace filtre selon l'état de la session.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* le nom du programme est ajouté devant les commandes (`git push`), ce qui est faux pour une commande tapée dans un programme qui reste ouvert (`/select` dans Claude) ; un préfixe dans le texte (`> `) obligeait à retenir une syntaxe, une valeur par commande est dite par le dialogue et par la liste.
  Une commande sans type est une commande de lancement, pour que les anciens profils se lisent tels quels ; le type « Shell » (ancien « les deux », voir l'entrée du 2026-11-05) sert aux commandes d'un shell.
  L'historique reçoit le même type, sans « Shell » : la première ligne d'un shell est une ligne de lancement, les suivantes sont du programme.
  Voir « Common commands » dans `specs/interface.md`.
- **Les raccourcis des menus sont de vrais accélérateurs wx ; le crochet de la fenêtre ne fait plus qu'annoncer les refus.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* le menu affichait des raccourcis (F5) que la fenêtre ne liait pas, parce que deux listes tenues à la main pouvaient diverger ; avec un accélérateur, ce qui est affiché fonctionne.
  wx lit mal les noms français (« Maj » inconnu : il gardait la touche seule) : le catalogue `wxkeys`, au contexte « keyboard key » de `accelcmn.cpp`, lui donne nos noms (Maj, Début, Page suivante…) ; il est ajouté après celui de wx, qui cherche les derniers catalogues en premier.
  Un item grisé ignore sa touche en silence, ce qui n'est pas acceptable pour un lecteur d'écran : le crochet reste pour annoncer la raison et prendre la touche.
  Ctrl+Pause est Ctrl+Arrêt pour Windows : une entrée de plus dans le tableau de la fenêtre.
  L'historique des commandes (Ctrl+Espace) a un item dans le menu Édition, faute de quoi il n'aurait pas d'accélérateur ; le code du champ de commande qui prenait cette touche est retiré.
  Voir « Shortcuts » dans `specs/interface.md`.
- **Toute annonce appartient à une catégorie, désactivable ; douze catégories nommées « Session, … », « Sortie, … », etc.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* 27 annonces sur 47 étaient toujours dites, alors qu'un utilisateur de NVDA ou de JAWS peut vouloir les confier à un script ; les noms commencent par le même mot pour que la liste, triée par nom, les range ensemble.
  Le message « activité non signalée » est dans « Session, réglages » et non dans « Activité du terminal » : cette catégorie, mise à « Aucune », se tairait sur sa propre désactivation.
  « Échec de lancement » ne propose pas « Aucune annonce ». « Sortie exportée » n'est plus annoncée.
  Les catégories gardent leur identifiant (`folder`, `movement`, `movement_blocked`, `key_sent`) : seul le nom change ; `terminal_size` disparaît (un réglage enregistré est ignoré).
  Voir « Announcements » dans `specs/interface.md`.
- **« Identifier des activités » trouve les adresses web et mail ; un bouton copie l'élément choisi.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* une adresse affichée par un programme est à copier ou à atteindre, et la liste existait déjà pour les questions et les erreurs ; ouvrir l'adresse dans le navigateur a été refusé (une action sur l'ordinateur sans demande).
  La ligne de la liste est l'adresse seule, claire sans genre ; le bouton marche pour toutes les lignes, pas seulement les adresses ; la liste s'ouvre sur la dernière ligne qui n'est pas une adresse pour ne pas cacher la question qui attend.
  Recherche limitée aux dernières lignes (la hauteur du terminal), sans l'historique.
  Voir « Identifying activities » dans `specs/interface.md`.
- **Les raccourcis n'ont pas de limite de plus que les règles de la page Raccourcis ; un raccourci prend la touche au contrôle qui a le focus.** Décidé avec l'utilisateur le 2026-11-02.
  *Pourquoi :* l'idée d'interdire Ctrl+Début, Ctrl+Fin, Ctrl+flèches protégeait des déplacements du contrôle de texte, mais l'utilisateur choisit ses raccourcis et sait ce qu'il perd ; l'essai avec Alt+Bas a montré que l'application ne déplace pas le curseur (NVDA le déplace de son côté).
  Voir « Sending keys » dans `specs/interface.md`.
- **« Lancer le programme » (F5) reste disponible avec une connexion choisie et fermée ; il tape le nom de fichier du programme.** Décidé avec l'utilisateur le 2026-11-04.
  *Pourquoi :* la première règle grisait F5 comme les commandes qui parlent de cet ordinateur, mais sur un serveur le programme du profil s'écrit déjà par son nom (`git`), donc rien de local n'est lancé ; Entrée ouvre déjà la connexion et envoie la ligne.
  Ouverte, F5 est grisé : le shell du serveur n'est pas reconnu, on ne sait pas s'il attend une commande.
  Voir « Connections » dans `specs/interface.md`.
