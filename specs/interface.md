# Interface

Première étape (CLI avec pipes).
Une fenêtre = une session (voir « Sessions » dans `specs/architecture/session.md`).
Pas d'onglets.

## Main window

De haut en bas :

1. **Barre de menus** (libellés français, par `_()` ; les identifiants de messages sont en anglais), voir « Menus » ci-dessous.
2. **Zone de sortie** : un contrôle de texte multiligne en lecture seule qui remplit toute la partie haute de la fenêtre.
   Elle affiche la sortie du programme (stdout et stderr, dans l'ordre d'arrivée).
   Chaque ligne de stderr commence par « StdErr: » (une fois, même pour une barre de progression réécrite ; une ligne vide n'est pas marquée), pour qu'on la distingue par le texte et non par la place ou la couleur.
   Le mot est un nom technique, comme Cmd : il n'est pas traduit, et il est gardé dans l'export.
   La case « Préfixe StdErr » (cochée par défaut) du dialogue de profil retire la marque ; un profil choisi remplace la valeur de la session, comme le mode.
   Les deux flux sont lus par deux threads : l'ordre entre eux n'est pas celui de l'écriture quand le programme écrit sur les deux presque en même temps (`specs/open-questions.md`).
3. **Zone de commande**, en bas, sur toute la largeur de la fenêtre :
   - un champ de texte d'une ligne, pleine largeur (la commande à envoyer) ;
   - à côté, une case à cocher « Masquer le message » (voir « What the command field sends ») et un bouton « Envoyer ».
4. **Barre d'état** de trois champs (voir « Focus and caret ») :
   - la ligne du curseur de texte (« Ligne 12 sur 340 ») ;
   - l'état de la session (pour un programme local : l'état du transport, voir « Transport » dans `specs/architecture/transport.md`) ;
   - la colonne du curseur de texte (« Colonne 3 sur 80 »).
   Le **titre de la fenêtre** dit le profil et le dossier de travail, ou la connexion SSH (voir « Session information »).

## Menus

Sept menus, et un huitième en mode Develop.
Les items qui ne s'appliquent pas à l'état de la session sont **désactivés (grisés), jamais masqués** : un lecteur d'écran dit « indisponible », la liste des items reste la même, et l'utilisateur ne se demande pas si un item existe.
Choisir une commande refusée par son raccourci annonce pourquoi (par exemple « Indisponible pendant qu'un programme tourne. »).

- **Fichier** : Nouvelle session, Dossier de travail…, Dossiers récents (sous-menu), Exporter la sortie…, Préférences…, Quitter.
- **Édition** : Copier, Tout sélectionner, Rechercher dans la sortie…, Rechercher le suivant, Rechercher le précédent, Historique (Ctrl+Espace), Renvoyer la dernière commande (Ctrl+R), Saisie sur plusieurs lignes… (Ctrl+M).
- **Session** : Arrêter le programme, Mode (sous-menu, un seul choix : « CLI, texte simple » et « TUI, terminal interactif »), Interpréteur (sous-menu : un choix parmi Aucun, Cmd, PowerShell, puis « Sélection du PowerShell… »), Envoyer une touche (sous-menu, voir « Sending keys »), Informations sur la session… (voir « Session information »).
- **Profil** : Choix profil (sous-menu à un seul choix : Libre et les profils), Lancer le programme (F5), Ajouter…, Modifier…, Supprimer, Définir les variables… (voir « Profiles »).
- **Connexion**, entre Profil et Terminal : Choix connexion (sous-menu à choix unique : Locale, puis les connexions par ordre alphabétique), Se connecter, Se déconnecter, puis, après un séparateur, Ajouter…, Modifier…, Supprimer, et Client SSH… (voir « Connections »).
- **Terminal** : Taille du terminal (sous-menu, un seul choix : 80 x 24, 100 x 30, 120 x 30, 132 x 43, 160 x 50, 200 x 60, Automatique), Vue terminal seule (une case à cocher, décochée par défaut ; seulement pour les modes terminal 4 et 5 ; voir « Terminal display »), Déplacement (sous-menu : Aller au curseur du terminal, Aller à la première ligne du terminal, Aller à la dernière ligne du terminal ; voir « Terminal cursor »), Activités (sous-menu : Lire la ligne avec mise en forme, Identifier des activités…, Signaler les activités, une case à cocher ; voir « Activities »), Lecture confortable (sous-menu : Ligne précédente, avec filtrage, Ligne suivante, avec filtrage, Filtrage de ligne… ; voir « Comfortable reading »), puis, après un séparateur, Effacer la sortie.
  Le sous-menu Activités contient Lire la ligne avec mise en forme, Identifier des activités… et Signaler les activités (une case à cocher).
- **Aide** : Ouvrir l'aide (F1, voir « Help »), Ouvrir le dossier des journaux, À propos.
  « Ouvrir le dossier des journaux » montre le dossier du fichier de journal dans l'explorateur (voir « Logs » dans `specs/robustness.md`) ; sans journal, une boîte de message le dit.
  « À propos » ouvre une boîte de dialogue avec une zone de texte brut en lecture seule (focus initial dessus) et un bouton OK, plus facile à lire qu'une boîte de message.
- **Develop**, entre Terminal et Aide, **seulement en mode Develop** (`--develop`, voir `specs/architecture/window.md`, « Where the data lives ») : Catalogues…, Programmes de test (sous-menu), Convertir l'aide en HTML (voir « Help »).
  Le sous-menu liste, à chaque ouverture, les fichiers `.py` du dossier `DevelopMode\testprograms\` ; en choisir un le lance comme une commande tapée, avec le Python qui fait tourner l'application.
  L'application tourne sous `pythonw.exe` (sans console) ; le programme est lancé avec le `python.exe` du même dossier, sinon il n'a ni entrée ni sortie et se termine aussitôt.
  Un fichier dont le nom commence par un tiret bas (le fichier `DevelopMode/testprograms/_common.py`) n'est pas un programme : il est ce que les programmes partagent, et le menu ne le liste pas.
  Tout programme de test commence par son nom en titre de niveau 1, puis une ligne qui dit le mode détecté (CLI avec des tubes, TUI avec une console).
  `DevelopMode/testprograms/Commands.py` affiche ensuite, sans fin, affiche une invite (titre de niveau 2) et le texte ou le nom de la touche reçue avec ses codes ; Ctrl+D (TUI) ou la fin de l'entrée (CLI) le termine.
  `DevelopMode/testprograms/Cadence.py` écrit 60 lignes, une toutes les 0,5 s, vidées aussitôt ; chaque ligne commence par son numéro (« 07/60 ») puis dit toujours les mêmes fruits ; une dernière ligne donne la durée réelle.
  Il teste la sortie qui arrive pendant la lecture, sans déplacer le curseur de texte.
  `DevelopMode/testprograms/Progress.py` teste les barres de progression réécrites sur place, selon le mode détecté.
  - En CLI, trois barres de 20 s à la suite, réécrites avec un retour chariot : « Téléchargement » sur la sortie d'erreur, « Vérification » sur la sortie standard entre deux lignes de texte, « Installation » sur la sortie standard sans saut de ligne à la fin (le programme finit sur 100 %).
  - En TUI, l'écran est effacé puis dessiné par positionnement du curseur : une barre sur la première ligne pendant 30 s, puis, après une pause de 3 s, deux barres sur les deux premières lignes, la plus lente en 30 s et l'autre en 20 s.
    Le curseur du terminal reste sous les barres.
  En TUI, l'application n'envoie aujourd'hui que du texte suivi de `\r` : l'envoi de touches reste à concevoir.
  `DevelopMode/testprograms/Selection.py` (TUI seulement) fait choisir dans trois listes, avec les flèches, Page précédente et suivante, Début et Fin, puis Entrée : un marqueur `>` sur la ligne choisie ; aucun marqueur, le curseur du terminal étant sur la ligne choisie ; une liste de trente lignes dont huit se voient, avec un compteur « 3/30 ».
  `DevelopMode/testprograms/Questions.py` pose quatre questions, en CLI comme en TUI : oui ou non avec un défaut (`[O/n]`) ; un mot de passe (rien ne s'affiche en TUI, le programme dit seulement combien de caractères il a reçus) ; des choix numérotés avec une erreur et une nouvelle question pour une réponse hors liste ; une question dont la ligne n'est pas terminée (« Votre nom : »).
  `DevelopMode/testprograms/Addresses.py` écrit des adresses web (seules, dans une phrase, entre parenthèses, sans protocole, deux sur une ligne), des adresses mail (seules, avec `+` et points, deux sur une ligne, une dans une adresse web), des pièges qui n'en sont pas (`utilisateur@machine`, `git@github.com:utilisateur/depot.git`, des versions), puis la question `Continuer ? [O/n]` avec une adresse mail écrite **en dessous** ; dans « Identifier des activités », la liste doit s'ouvrir sur la question.
  Le titre de niveau 1 de la commande lancée (mode tubes) ne donne que le nom du fichier (« Progress.py »), pas la ligne de commande entière ; l'historique des commandes garde la ligne entière.
  Sans fichier, le sous-menu contient l'item grisé « (aucun) ».
  Grisé pendant qu'un programme tourne.
  Catalogues… ouvre le dialogue décrit dans « Catalogs ».

- **Mode** : la désignation est le sigle, CLI ou TUI ; « texte simple » et « terminal interactif » sont des indications, répétées dans le texte d'aide de chaque choix (« CLI : le programme lit et écrit du texte, pour la plupart des commandes » / « TUI : le programme croit être dans une vraie console, pour python, ssh, les mots de passe et les shells »).
  CLI par défaut.
  Désactivé pendant qu'un programme tourne, et avec un shell (toujours TUI, annoncé).
  Voir « Choosing the mode » dans `specs/architecture.md`.
- **Nouvelle session** démarre une nouvelle instance de l'application (voir « Sessions » dans `specs/architecture/session.md`), dans le dossier de travail de la session courante.
- **Dossier de travail** et **Dossiers récents** fixent le dossier du prochain lancement.
  Quand l'interpréteur est un shell qui reste ouvert (Cmd, PowerShell) et attend à son invite, ils changent aussi le dossier de ce shell : MiTerm-N5 tape la commande à sa place, en une fois, quelle que soit la profondeur (`cd /d "C:\Premier\SRC"` pour Cmd, `Set-Location -LiteralPath 'C:\Premier\SRC'` pour PowerShell), et la ligne apparaît dans la sortie comme n'importe quelle ligne tapée.
  L'item est désactivé tant qu'un programme occupe le shell, sinon la commande serait envoyée à ce programme comme du texte.
- **Historique des commandes** : pas d'item de menu.
  Un raccourci (Ctrl+Espace, comme les suggestions d'un éditeur de code) ouvre une liste des commandes déjà tapées, choisies avec les flèches.
  Haut et Bas ne sont pas pris par le champ (décidé) : l'historique n'est atteint que par cette liste.
- **Passer du champ de commande à la zone de sortie** se fait avec Tab (pas de raccourci).
- Pas dans la première version : l'encodage, le dossier de travail et l'environnement dans un profil, les onglets.
  SSH vient ensuite, par les connexions (voir « Connections »).
  La page des Préférences contient la langue, les raccourcis et les annonces.

### Shortcuts

Propositions, toutes modifiables dans Préférences > Raccourcis (une liste des commandes, un champ où l'on appuie sur le nouveau raccourci, des boutons « par défaut » et « aucun ») : Nouvelle session Ctrl+N, Dossier de travail Ctrl+O, Exporter Ctrl+S, Arrêter le programme **Ctrl+Pause** (Ctrl+C reste « copier » dans le champ de commande), Relancer Ctrl+R, Effacer Ctrl+L, Historique des commandes Ctrl+Espace, Rechercher Ctrl+F, Suivant F3, Précédent Maj+F3, Aller au curseur du terminal Ctrl+G, Aller à la première et à la dernière ligne du terminal **Alt+Début** et **Alt+Fin** (Ctrl+Début et Ctrl+Fin restent ceux du contrôle de texte), Lire la ligne avec mise en forme **F4**, Identifier des activités **Maj+F4**, Signaler les activités **Ctrl+B** (B comme bip), Ouvrir l'aide **F1**, Lancer le programme du profil **F5**, Choisir le profil libre **Maj+F5**, Définir les variables **Ctrl+D** (D comme définir), Se connecter **F6**, Choisir la connexion locale **Maj+F6**, Se déconnecter **F7** (comme Arrêter le programme pendant une connexion), Informations sur la session **Ctrl+I**, Saisie sur plusieurs lignes **Ctrl+M**, Ligne précédente et Ligne suivante, avec filtrage **Ctrl+Alt+Haut** et **Ctrl+Alt+Bas**.
Les touches de fonction vont ensemble : F5 le programme du profil, F6 la connexion, F7 la déconnexion, et Maj sur F5 et F6 choisit l'élément qui ne dépend d'aucun fichier (Libre, Locale).
Libre et Locale restent dans leur sous-menu en permanence (les profils et les connexions trouvés les suivent) pour que leur raccourci marche menu fermé.
Règles (`core/config/shortcuts.py`) : Ctrl ou Alt est obligatoire (une simple lettre bloquerait la saisie) sauf pour une touche de fonction ; Tab et Inser (la touche des lecteurs d'écran) sont refusées, et Échap sauf avec Maj seule ; les raccourcis des commandes standard (presse-papiers, quitter, les touches d'accès des menus) ne peuvent pas être réutilisés ; deux commandes ne peuvent pas partager le même.
Un raccourci invalide dans le fichier de réglages est ignoré.
Les raccourcis sont enregistrés avec les noms de touches anglais (`Alt+Home`), mais **montrés et lus avec les noms de la langue** : les textes des menus et la page Raccourcis des Préférences disent `Alt+Début`, `Maj+Échap`, `Ctrl+Page suivante`, parce qu'une voix française lit « Home » comme « dossier personnel » (`display_shortcut`, `core/config/shortcuts.py`).
Le raccourci d'un item de menu en est l'**accélérateur** : c'est wx qui exécute l'item quand on appuie sur la touche, comme un clic, donc un raccourci affiché fonctionne toujours.
wx lit et écrit les noms de touches avec ses propres traductions (« Majuscule+Entrée », « Alt+Dossier personnel ») : le catalogue `wxkeys` (`locale/<langue>/LC_MESSAGES/wxkeys.mo`, fait par `tools/make_wx_keys.py` à partir du catalogue de l'application) lui donne les nôtres, dans le contexte « keyboard key » qu'il cherche.
Sans lui, avec wx en français, « Maj+Entrée » devenait la touche Entrée seule, prise par le menu avant le champ de commande.
Ctrl+Pause arrive de Windows comme Ctrl+Arrêt (`WXK_CANCEL`) : la fenêtre ajoute cette touche à son tableau d'accélérateurs pour les items dont la touche est Pause.
Le crochet de la fenêtre (`MainWindow._on_char_hook`) ne fait plus que dire pourquoi une touche ne fait rien : l'accélérateur d'un item grisé est ignoré en silence, et la touche irait au contrôle (Maj+Entrée validerait le champ de commande).
Si la commande de la touche est disponible, le crochet la laisse au menu ; sinon il annonce la raison et prend la touche.

### Announcements

Toute parole supplémentaire passe par un seul centre d'annonces (`core/config/announcements.py`).
Chaque message est un membre de `Announce` et **appartient à une catégorie** dont l'utilisateur choisit la destination dans Préférences > Annonces : rien, un message, une boîte de dialogue ou la ligne (les choix qu'une catégorie accepte diffèrent), pour qu'un script du lecteur d'écran puisse prendre le relais.
Il y en a treize :
- **État du programme** : démarrage, fin, arrêt, processus resté actif.
- **Session, réglages** : dossier de travail, PowerShell, activité signalée ou non (ce dernier message n'est pas dans « Activité du terminal » : désactivée, cette catégorie ne dirait même pas qu'elle l'est).
- **Session, changement** : taille du terminal, lignes supprimées, lignes perdues.
- **Sortie, déplacement et lecture** : titres, curseur du terminal, début et fin de l'émulateur (rien, message ou lire la ligne).
- **Sortie, pas ou plus d'éléments** : plus de titre suivant ou précédent, aucun élément reconnu.
- **Sortie, lire la ligne** : « Lire la ligne avec mise en forme » (F4) ; rien, message (la ligne mise en forme, par défaut) ou lire la ligne (la ligne telle qu'elle est).
- **Sortie, touches envoyées** : « Envoie {touche}. ».
- **Recherche atteinte** et **Recherche sans résultat** (deux catégories : leurs destinations diffèrent, la seconde accepte une boîte de dialogue).
- **Activité du terminal** (voir « Activities »).
- **Connexion, état** : « Connexion… », « Authentification… », « Connecté à prod. », « Déconnecté (code 255). », « Connexion annulée. » (voir « Connection state »).
- **Commande impossible** : les commandes non disponibles avec leur raison, l'historique vide, rien envoyé, l'aide introuvable ou non ouverte (rien ou message).
- **Échec de lancement** : programme, PowerShell ou dossier introuvable, lancement impossible (message ou boîte de dialogue, jamais « rien » : une erreur ne se supprime pas).
Aucune annonce n'est hors catégorie (un test le vérifie).
La sortie exportée n'est pas annoncée : la boîte de sélection de fichier suffit.
Un message n'est pas écrit dans la barre d'état : il est seulement dit.
La sortie se choisit dans les Préférences : notification UI Automation (Windows, par défaut) ou aucune.
Si la sortie échoue, l'utilisateur en est informé une fois et le centre se rabat sur aucune.

Ce qui est annoncé par défaut : le début et la fin d'un programme avec son code de sortie, un processus resté actif, les erreurs et les commandes refusées, et l'activité du terminal (voir « Activities »).
La sortie n'est **pas** lue automatiquement : elle s'ajoute en silence et l'utilisateur s'y déplace.
Le seul son est le bip de l'activité, généré par l'application (aucun fichier de son n'est livré).
La catégorie « Activité du terminal » a deux destinations qui lui sont propres : « Messages ou bip » (par défaut) et « Messages ».

### Status bar

Trois champs.
- Ligne : « Ligne 12 sur 340 », la ligne du curseur de texte et le nombre de lignes du texte.
  Le total s'adapte à l'affichage : avec historique il compte tout le texte, sans historique seulement les lignes de l'émulateur.
- État : « Prêt », « En cours : ping », « Terminé (code 0) », « Processus enfant actif ».
  Il ne dit pas le profil, que dit le titre de la fenêtre.
  Avec une connexion SSH, il dit l'état de la connexion (voir « Connections »).
- Colonne : « Colonne 3 sur 80 », la colonne du curseur de texte.
  Le total est la largeur de l'écran du terminal pour un programme servi par une pseudo-console, et la longueur de la ligne avec les tubes (où il n'y a pas de largeur).
- Les messages annoncés ne sont pas écrits dans la barre d'état (le texte d'aide d'un item de menu n'y apparaît pas non plus).

### Interpreter

« Aucun » lance le programme directement.
« Cmd » et « PowerShell » ouvrent un shell qui reste ouvert sous les modes terminal (4 et 5), et chaque commande y est tapée : c'est le seul cas où `cd` a un effet durable, et aucun shell n'est relancé pour chaque ligne.
Ne change que sans programme en cours.

Le **préfixe de l'invite** du profil choisi (vide par défaut) est écrit devant l'invite du shell, pour que chaque ligne de commande, par exemple `# C:\Dev> dir`, soit un titre de niveau 1 que les touches 1 et T atteignent.
- Cmd : MiTerm-N5 met le préfixe devant la variable d'environnement `PROMPT` que l'utilisateur a déjà (`$P$G` s'il n'en a pas), pour le processus du shell seulement.
- PowerShell : le shell est lancé avec `-NoExit -Command` et une fonction `prompt` qui appelle celle que l'utilisateur a déjà (son profil `$PROFILE` est chargé avant) et la fait précéder du préfixe.
- Rien n'est écrit dans le Registre, dans les variables de l'utilisateur ni dans son profil PowerShell ; la personnalisation de l'utilisateur est conservée.
- L'invite en attente et une ligne validée vide sont aussi des titres.
- Si l'utilisateur change son invite dans la session (`prompt ...`), le préfixe disparaît jusqu'au prochain lancement du shell.
- La reconnaissance d'un shell à son invite (« Dossier de travail ») attend le préfixe au début de la ligne.

**Sélection du PowerShell…** (dernier item du sous-menu Interpréteur) choisit quel PowerShell lance l'interpréteur « PowerShell » ; c'est un réglage global (clé `powershell_path` de `settings.json`, vide = Windows PowerShell, `powershell.exe`).
- Le dialogue a une liste « Version de PowerShell » : Windows PowerShell (par défaut), puis chaque PowerShell 7 ou plus récent trouvé sur l'ordinateur (dans le `PATH`, y compris celui du Microsoft Store, et dans `%ProgramFiles%\PowerShell\*`), puis « Autre… ».
- « Autre… » active le champ « Chemin de PowerShell » et le bouton « Parcourir… » (grisés pour les autres choix) ; OK est refusé, avec « Veuillez sélectionner un PowerShell valide. », tant que ce chemin n'est pas un `.exe` existant.
- Le focus initial est dans la liste.
- Disponible quand aucun programme ne tourne, même si un profil est choisi (le réglage est global, il ne fait pas partie du profil) ; le changement est annoncé (« PowerShell : … ») et s'applique au prochain lancement du shell.
- Si le chemin enregistré n'existe plus, le lancement du shell annonce « Veuillez sélectionner un PowerShell valide. Introuvable : chemin. ».
- Le code est dans `core/session/powershells.py` (la détection, sans rien lancer), `presenters/powershell_choice.py` (le brouillon) et `ui/powershell_dialog.py`.

### Language

Français par défaut, anglais disponible ; choisi dans les Préférences, appliqué au prochain démarrage.
Chaque chaîne visible passe par gettext (`_()`), les identifiants de messages sont en anglais.
Les textes de wxWidgets lui-même (boutons standard, dialogues standard) suivent la même langue.

## Focus and caret

Quatre règles.
Toute nouvelle fonction en suit une ou ajoute son cas ici.
- **A.
  Un dialogue se ferme : le focus revient où il était** (`Feedback.modal` affiche chaque dialogue et message).
- **B.
  Démarrage, nouvelle session : le focus est sur le champ de commande.** Envoyer depuis le champ (Entrée ou le bouton) le vide, puis déplace le focus dans la zone de sortie :
  - une commande qui lance un programme (programme, `cmd` ou shell) met le curseur de texte au début de la commande écrite dans la sortie (la ligne `# commande`) ; en mode terminal, où la commande n'est pas écrite, au début de la partie émulateur ;
  - du texte envoyé à un programme en cours, ou une touche envoyée, met le focus dans la zone de sortie **sans toucher au curseur de texte** ;
  - une commande ou un envoi refusé (programme introuvable, entrée non lue) laisse le focus dans le champ.
  Pour taper la ligne suivante, Tab ramène au champ de commande (la zone de sortie est la dernière de l'ordre de Tab).
- **C.
  L'arrivée de sortie ne déplace jamais le focus ni le curseur de texte.** Le changement du texte est le plus petit possible (`presenters/output_text.py`) ; un curseur de texte à l'intérieur de ce qui est réécrit reste sur la même ligne et la même colonne, ou va au début de la ligne quand cette colonne n'existe plus ; un curseur de texte ailleurs ne bouge pas.
  Un utilisateur qui se déplace dans le texte déplace le curseur et le focus volontairement : les touches 1 à 6 et T (titres), une recherche qui trouve (le focus va dans la zone de sortie), Entrée sur un élément du dialogue « Identifier des activités… » (le focus va dans la zone de sortie), la liste de l'historique (Ctrl+Espace met le focus dans le champ).
  « Lire la ligne avec mise en forme » et l'activité signalée ne déplacent ni le focus ni le curseur de texte.
- **D.
  « Effacer la sortie », « Arrêter le programme » et les changements des menus laissent le focus où il est.**

Ordre de Tab : champ de commande, case « Masquer le message » (grisée, donc sautée, tant qu'aucun programme ne tourne), bouton Envoyer, zone de sortie.
L'étiquette d'un contrôle est créée juste avant lui, pour qu'un lecteur d'écran les associe ; l'étiquette du champ suit l'état (« Commande », le nom du profil, « Message » ; voir « Command field and program of a profile »).

La barre d'état a **trois champs** : la ligne du curseur de texte (« Ligne 12 sur 340 »), l'état de la session et la colonne du curseur de texte (« Colonne 3 sur 80 »).
Le texte d'aide d'un item de menu n'y est pas affiché.

## Titles: going from command to command

Une commande lancée en mode CLI est écrite dans la sortie `# commande`, un titre Markdown de niveau 1 ; ce qui est envoyé à un programme en cours reste `> texte`.
Dans la **zone de sortie**, les touches **1 à 6** vont au titre suivant de ce niveau et **T** au titre suivant de n'importe quel niveau ; **Maj** avec la touche va au précédent (ni Ctrl, ni Alt).
Le focus est dans la zone de sortie, le curseur de texte va au titre, et une annonce le dit (catégorie « Sortie, déplacement et lecture » : rien, message, ou lire la ligne).
À la fin : « Pas de titre suivant » (catégorie « Sortie, pas ou plus d'éléments »).
Les titres du Markdown propre aux programmes s'atteignent de la même façon.
Le menu contextuel de la zone de sortie a les items « Titre précédent (1 à 6) » (Maj+T) et « Titre suivant (1 à 6) » (T) : ils font la même commande que la touche T (une seule route : la touche et l'item passent par la commande, donc par la même règle), vont au titre de n'importe quel niveau et affichent cette touche (les chiffres de 1 à 6, pour un niveau précis, ne sont qu'évoqués dans le texte).
Sans sortie, la commande est refusée et la raison annoncée (« La sortie est vide. ») : l'item est grisé, et la touche dit la même chose au lieu de « Pas de titre suivant ».
Dans le **champ de commande**, **Ctrl+Espace** ouvre la liste des commandes (historique de la session, de la plus ancienne à la plus récente, puis les commandes courantes du profil choisi).
La liste dépend de l'état de la session (voir « Common commands »).
La dernière commande tapée est sélectionnée à l'ouverture : Haut lit les plus anciennes, Bas atteint aussitôt les commandes du profil.
Sans historique, c'est la première ligne qui est sélectionnée.
L'historique des commandes en garde 20 par session (ce n'est pas un réglage) ; une commande déjà dans l'historique (du même type) n'est pas répétée : l'ancienne place est supprimée et la commande devient la plus récente (`dir`, `cd`, `dir` donne `cd`, `dir`) ; une commande d'un profil, une fois lancée ou envoyée, entre dans l'historique comme n'importe quelle commande tapée ; la sortie garde 10 000 lignes par défaut (un réglage).

## Search in the output

**Rechercher dans la sortie…** (Ctrl+F) ouvre une boîte avec le champ **« Recherche du texte »** et deux cases à cocher, **« Chercher vers le haut »** et **« Expression régulière »** ; le dernier texte cherché y est proposé (sélectionné), les cases reprennent leur dernier état (gardé jusqu'à la fin de l'application, jamais enregistré), Entrée valide, Échap annule, et un texte vide ne cherche rien.
La recherche part du curseur de texte de la zone de sortie et va vers la fin ; une occurrence qui commence sur le curseur de texte compte.
Avec la case cochée, elle va vers le haut et prend la dernière occurrence qui commence avant le curseur de texte.
La case de la direction ne sert que depuis cette boîte : Rechercher le suivant et Rechercher le précédent gardent leur sens.
Avec « Expression régulière », le texte est une expression régulière (la casse reste ignorée) ; une expression qui n'est pas valable est refusée dans la boîte, avec la raison dite, et la boîte reste ouverte.
Rechercher le suivant et le précédent cherchent ensuite le même texte de la même façon (en expression régulière si la dernière recherche l'était).
**Rechercher le suivant** (F3) et **Rechercher le précédent** (Maj+F3) répètent avec le même mot, à partir du curseur de texte : le suivant passe l'occurrence où l'on est, le précédent prend la dernière qui commence avant le curseur de texte.
Tant qu'aucun mot n'a été cherché, les deux ouvrent la boîte comme Rechercher.
La casse est ignorée, le texte est simple tant que la case « Expression régulière » n'est pas cochée (les caractères `.`, `(`, `$`, `\` ne sont alors que ce qu'ils sont), et deux occurrences qui se chevauchent comptent chacune ; avec une expression régulière, chaque endroit où elle peut commencer à correspondre compte, et un texte trouvé vide ne compte pas.
Il n'y a pas de retour au début : au-delà de la dernière occurrence, il n'y en a plus.
- Une occurrence trouvée : le focus va dans la zone de sortie et le curseur de texte se place au début de l'occurrence, sans rien sélectionner.
  L'annonce lit la ligne qui la contient (catégorie « Recherche atteinte » : rien ou un message).
- Rien trouvé : « Pas d'occurrence suivante de « mot ». » ou « Pas d'occurrence précédente de « mot ». » (catégorie « Recherche sans résultat » : rien, un message, ou une boîte de dialogue), et le focus comme le curseur de texte ne bougent pas.
- Tant que l'utilisateur n'a pas déplacé le curseur de texte, il reste à la fin de ce qui arrive : depuis la fin, Rechercher ne trouve rien après lui, et Rechercher le précédent atteint la dernière occurrence (décidé, voir `specs/decisions.md`).
- Les trois commandes sont grisées tant que la sortie est vide, avec la raison annoncée.
- Le code est dans `core/screen/text_search.py` (trouver), `presenters/output_search.py` (le mot et l'annonce) et `ui/output_commands.py` (la boîte et le curseur de texte).

## Profiles

Un profil est un fichier JSON (`profiles/git.json` dans le dossier des données, voir « Where the data lives » dans `specs/architecture/window.md`, écrit de façon atomique comme les réglages, clés inconnues conservées) dont le nom est celui du fichier et n'y est pas écrit (en général le programme, `git`), avec : le programme (facultatif, clé `program`), le mode, l'interpréteur, la taille de l'émulateur, l'affichage avec ou sans historique, les variables qu'il utilise (voir ci-dessous) et une liste de commandes courantes (`status`, `commit -m "{message}"`... avec un programme ; `git status`... sans).
Pas de dossier pour l'instant ; d'autres éléments pourront venir.
Un fichier illisible est mis de côté (`.corrupt`) et signalé à l'utilisateur ; les autres profils restent listés.
Le code est dans `core/config/profiles.py`.
Les Préférences n'ont pas d'onglet Profils : un profil se gère entièrement depuis le menu **Profil**.
Le profil de démarrage (Préférences > Général, voir « Preferences ») est choisi au lancement de l'application, sans annonce.

### Starter profiles

L'application livre des profils de départ dans le dossier `starter_profiles` de son dossier (la racine du dépôt en développement) ou, une fois empaquetée, dans `_internal\StartProfil` (à côté de l'exécutable, comme `Help`), un fichier `.json` chacun, au même format qu'un profil.
Au démarrage, chaque profil de départ jamais proposé est copié dans le dossier des profils de l'utilisateur, sauf si l'utilisateur a déjà un profil de ce nom.
Les noms déjà proposés sont écrits dans le fichier `.starters` du dossier des profils : un profil supprimé ne revient pas, un profil modifié n'est jamais écrasé, et un profil de départ ajouté par une version ultérieure est proposé une fois.
Le mode portable copie dans son dossier `data\profiles`, rien ailleurs.
Une erreur de copie est dite dans la boîte des profils illisibles.
Le profil `git` a pour programme `git` (commandes `status`, `diff`, `add {source}`, `commit -m "{message}"`, `pull`, `push`…).
Une copie du profil `git` faite par une version plus ancienne, sans programme, garde ses commandes complètes (`git status`) et marche comme avant.
Les autres profils livrés sont ceux du dossier `starter_profiles` (Cmd, PowerShell, Python, Node, npm, pip…) ; un profil modifié ou déjà copié n'est jamais écrasé, donc une commande ajoutée à un profil livré n'arrive pas dans la copie qu'un utilisateur a déjà.
- **`ssh-keygen`** : programme `ssh-keygen` (celui d'OpenSSH pour Windows), mode TUI parce qu'il pose des questions (emplacement, phrase secrète).
  Ses commandes de base : créer une clé `ed25519` (`-t ed25519 -C "{comment}"`, ou dans le fichier `{source}`) ou `rsa` de 4096 bits, afficher l'empreinte d'une clé (`-l -f "{source}"`), changer sa phrase secrète (`-p -f "{source}"`), retrouver sa clé publique (`-y -f "{source}"`), chercher ou retirer un serveur de `known_hosts` (`-F {name}`, `-R {name}`).
  Les variables sont `{name}` (un nom d'hôte), `{source}` (le fichier de la clé) et `{comment}` (le commentaire de la clé, un texte libre copié en clair sur chaque serveur).
- **`PowerShell`** gagne trois commandes pour les clés d'un serveur Linux (`{name}` est l'utilisateur, `{ip}` l'adresse, `{value1}` un numéro de ligne) : ajouter la clé publique `id_ed25519.pub` à `~/.ssh/authorized_keys` (en corrigeant les fins de ligne de PowerShell), lister ce fichier avec les numéros de ligne (`cat -n`), retirer la ligne de ce numéro (`sed -i.bak '{value1}d'`, qui garde une copie `authorized_keys.bak`).
  Le mot de passe du serveur est demandé par `ssh` dans le terminal : la case « Masquer le message » sert à le taper.
Le code est dans `core/config/starter_profiles.py`.

### Profile menu

- **Choix profil** : un sous-menu à un seul choix, « Libre » d'abord, puis les profils par ordre alphabétique.
  Le choisir remplace aussitôt le mode, l'interpréteur, la taille et l'affichage de la session par ceux du profil, **sans annonce** ; l'utilisateur peut ensuite changer la taille et l'affichage (**la dernière action gagne**, rien n'est écrit dans le profil).
  Désactivé tant qu'un programme tourne ou qu'un shell est ouvert, comme Mode et Interpréteur.
- **Lancer le programme** (F5) lance le programme du profil choisi, seul, comme si le champ de commande, vide, était validé (voir « Command field and program of a profile ») : la sortie écrit `# Git` (le nom du programme, sans dossier ni extension) et le focus suit la règle B.
  Avec un shell qui reste ouvert et attend à son invite, le programme y est tapé comme n'importe quelle commande.
  Il ne change aucune valeur de la session (mode, interpréteur, taille : ceux du profil sont déjà appliqués).
  Grisé, avec la raison annoncée, sans profil choisi (« Aucun profil n'est choisi. »), avec un profil sans programme (« Le profil choisi n'a pas de programme. ») et pendant qu'un programme tourne.
- **Libre** est le choix de départ par défaut : au lancement de l'application, ses valeurs sont celles du fichier des réglages (`launch_mode`, `interpreter`, `terminal_size`, `terminal_view_only`, `stderr_prefix` : CLI, Aucun, Automatique, avec historique, préfixe StdErr, tant que le fichier n'a pas été modifié à la main ; il n'y a plus de page pour les changer).
  Le choisir plus tard ne change aucune valeur (les valeurs en cours restent) ; les commandes courantes de l'ancien profil quittent la liste.
- **Ajouter…**, **Modifier…**, **Supprimer** : Ajouter est toujours actif ; Modifier et Supprimer sont grisés avec « Libre ».
  Supprimer demande une confirmation ; supprimer le profil choisi ramène à « Libre » sans changer les valeurs.
  Modifier le profil choisi réapplique ses valeurs à la session dès la validation.
- **Définir les variables…** : grisé si le profil choisi n'utilise aucune variable (la raison est annoncée) ; possible aussi pendant qu'un programme tourne, puisqu'il ne change que les commandes de la liste.
  Ses valeurs suivent le renommage du profil et disparaissent avec sa suppression.
- Pendant qu'un profil est choisi, **Mode** et les trois choix de **Interpréteur** du menu Session sont grisés (« Sélection du PowerShell… » reste actif) ; **Taille du terminal** et **Vue terminal seule** du menu Terminal restent actifs.
- Le profil actif est dit par le titre de la fenêtre, jamais par une annonce.
- Rien n'est appliqué automatiquement (voir `specs/open-questions.md`).
- Au lancement, l'application démarre toujours en « Libre » (le dernier profil n'est pas mémorisé), sauf si un fichier de lancement dit autrement (voir « Launch file »).

### Profile dialog

Ajouter et Modifier ouvrent le même dialogue : les valeurs sont celles du profil, ou les valeurs en cours de la session pour Ajouter.
Entrée valide, Échap annule ; les fichiers `profiles/<nom>.json` sont écrits à la validation.
- **Nom** : 10 caractères au plus, que le champ de saisie impose ; refusé vide, trop long, déjà pris (casse ignorée), ou contenant un caractère hors de la liste permise ; une boîte de message dit pourquoi.
  La liste permise : les lettres (accentuées comprises) et les chiffres, l'espace, et les signes `- _ . + # ( ) @`.
  Le message nomme le premier caractère refusé (« Le caractère & n'est pas permis dans un nom… ») ; un caractère invisible est dit par son nom (« zero width space »).
  Un nom ne commence ni ne finit par une espace, ne finit pas par un point et n'est pas un nom réservé de Windows (`con`, `nul`, `com1`…), puisque c'est le nom du fichier du profil.
  Le texte saisi est mis en une seule forme pour les lettres accentuées (une lettre et son accent séparé deviennent la lettre accentuée), pour que deux noms qui se lisent pareil ne soient pas deux fichiers.
  Un profil écrit avant cette liste garde son nom tant qu'on ne le change pas.
- **Programme** : un champ de texte, juste sous le nom ; un nom (`git`) ou un chemin (`C:\Program Files\Git\bin\git.exe`), vide pour un profil dont les commandes sont complètes.
  Il est grisé quand l'interpréteur est Cmd ou PowerShell : leurs commandes sont tapées dans le shell, complètes.
  La valeur déjà écrite reste dans le fichier du profil, mais elle est ignorée tant qu'un shell est choisi : pas de programme devant les commandes de la liste de Ctrl+Espace, et « Lancer le programme » (F5) grisé.
  Rien n'est vérifié à l'enregistrement : le programme peut être sur une autre machine, et un programme introuvable est dit au lancement.
  Les variables n'y sont pas remplacées.
- **Interpréteur**, **Mode**, **Taille du terminal** : trois listes déroulantes ; le mode est grisé quand un shell est choisi (toujours en TUI).
- **Préfixe de l'invite** : un champ de texte, juste sous l'interpréteur, grisé quand l'interpréteur est « Aucun » (clé `prompt_prefix`, vide par défaut ; voir « Interpreter »).
  Il est enregistré tel qu'il est écrit, espace finale comprise.
- **Vue terminal seule** et **Préfixe StdErr** : deux cases à cocher (la seconde est cochée par défaut ; voir « Terminal display » et l'en-tête de la sortie).
- **Variables** : une liste à sélection multiple, une ligne par variable (« Nom, {name} »), où le profil choisit celles qu'il utilise.
- **Type de commande** : une liste déroulante juste avant la liste des commandes.
  Sans interpréteur, elle a deux choix : « Commande de lancement » (le choix de départ) et « Commande du programme ».
  Avec un interpréteur (Cmd, PowerShell), elle n'a qu'un choix, « Shell » : les commandes d'un shell sont complètes d'elles-mêmes, et la liste de Ctrl+Espace les montre toujours.
  Changer l'interpréteur déplace les commandes vers les types que le nouvel interpréteur offre, sans en perdre : vers un shell, toutes deviennent « Shell » ; vers « Aucun », les commandes « Shell » rejoignent les deux autres types.
  Elle filtre la liste des commandes courantes : la liste ne montre que les commandes du type choisi, et Ajouter et Modifier travaillent sur ce type.
  À l'ouverture, la liste montre le premier type qui a des commandes.
- **Commandes courantes** : une liste avec les boutons « Ajouter une commande… », « Modifier la commande… » (aussi par un double clic sur la ligne) et « Supprimer la commande » ; Ajouter et Modifier ouvrent une boîte à un champ, une commande vide est refusée.
  Ajouter ou Modifier **refuse** une commande déjà dans la liste du même type (le même texte exactement) : une boîte de message le dit (« Cette commande est déjà dans la liste. ») et la ligne existante est sélectionnée ; le même texte reste permis dans un autre type.
  La liste est **toujours en ordre alphabétique** (la casse est ignorée) : une commande ajoutée ou modifiée prend sa place et reste sélectionnée.
  Le fichier du profil est écrit dans le même ordre, et lu de même, donc la liste de Ctrl+Espace (après l'historique) est triée aussi ; les fichiers des profils de départ sont livrés triés.
- Le titre dit s'il s'agit d'un nouveau profil ou de la modification de l'un d'eux, et le focus initial est dans le champ Nom.
- Ajouter choisit le nouveau profil dès qu'il est écrit (sauf si un programme tourne : il est écrit, mais pas choisi) ; Modifier le profil choisi le choisit de nouveau, donc ses nouvelles valeurs s'appliquent aussitôt (le renommer renomme son fichier).
- Le code est dans `presenters/profile_editor.py` (le brouillon) et `ui/profile_dialog.py`.

### Profile variables

Huit variables, remplaçables dans les commandes courantes d'un profil : `{name}`, `{source}`, `{destination}`, `{value1}`, `{value2}`, `{comment}`, `{ip}`, `{message}` (la casse est ignorée à la lecture : `{IP}` est `{ip}`).
Elles n'ont pas de sens fixe : `{name}` peut être un nom de projet ou d'identifiant, par exemple ; `{message}` sert au message d'un commit, `{ip}` à une adresse de machine.
Seuls ces huit noms sont remplacés ; toute autre accolade (`HEAD@{1}`, un bloc PowerShell) reste telle quelle.
**Définir les variables…** ouvre un dialogue dynamique : un champ de saisie par variable que le profil utilise, avec son libellé, sans contrôle de la valeur saisie.
Chaque profil a ses valeurs, gardées en mémoire le temps de la session seulement.
Avant d'afficher la liste de Ctrl+Espace, chaque variable qui a une valeur est remplacée dans les commandes courantes (de tous les types), à chaque endroit où elle apparaît ; une variable sans valeur reste écrite telle quelle, sans alerte à l'envoi.
### Common commands

Chaque commande courante a un **type** (clé `use` dans le fichier) :
- **lancement** (`launch`) : les arguments du programme du profil, pour le lancer (`push` pour `git push`) ; sans programme dans le profil, une commande complète ;
- **programme** (`program`) : tapée dans le programme une fois lancé, telle quelle (`/select` dans Claude) ;
- **shell** (`shell`) : une commande d'un shell, complète d'elle-même, au repos comme shell ouvert (les anciens fichiers disent `both`, qui se lit de même).
Dans le fichier, une commande de lancement reste un simple texte (les fichiers des versions précédentes se lisent sans changement : une commande sans type est une commande de lancement) ; les autres sont `{"text": "/select", "use": "program"}`.
Un profil avec un interpréteur n'a que des commandes « Shell » ; un profil sans interpréteur n'en a pas : à la lecture, les commandes sont rangées dans les types que le profil offre, sans en perdre.
La liste de **Ctrl+Espace** montre l'historique du même type que l'état, puis les commandes du profil de ce type :
- sans programme en cours : les lignes lancées (l'historique de lancement) puis les commandes de lancement et « Shell » du profil ;
- avec un programme qui tourne : les lignes qu'on lui a tapées (l'historique du programme) puis les commandes du programme et « Shell » du profil.
La première ligne tapée pour démarrer un shell est une ligne de lancement ; les suivantes sont des lignes du programme.

Si le profil a un programme, une ligne de la liste dit seulement le nom du programme, sans dossier ni extension, puis la commande (« Git status » pour `C:\Program Files\Git\bin\Git.exe` et `status`), parce qu'un chemin entier est long à entendre.
Choisir la ligne écrit dans le champ de commande les arguments seuls (`status`), puisque le champ ne reçoit plus le programme (voir « Command field and program of a profile »).
Les lignes d'historique suivent la même règle : avec un programme de profil, la liste ne montre que les lignes lancées avec ce programme, écrites comme leurs arguments ; celles d'un autre programme se retrouvent avec le profil « Libre ».

### Command field and program of a profile

Avec un profil à programme (un interpréteur « Aucun » et un programme renseigné), rien qui tourne et pas de connexion choisie, **le texte du champ de commande est les arguments du programme** : `status` lance `git status`, et la sortie écrit `# Git`.
Un champ vide lance le programme seul, comme F5.
Le profil « Libre », un profil de shell, un profil sans programme et une connexion choisie gardent la ligne de commande entière ; ce qui est envoyé à un programme qui tourne ne change pas.
Pour lancer un autre programme, on choisit « Libre ».
« Renvoyer la dernière commande » (menu Édition, Ctrl+R) fait ce que font Ctrl+Espace puis Entrée sur la ligne sélectionnée à l'ouverture de la liste : il envoie la dernière ligne de l'historique de la vue en cours, avec le programme du profil devant s'il y en a un.
Il est disponible dans les mêmes conditions qu'Entrée dans le champ : au repos avec une commande de lancement, avec une connexion choisie (il ouvre la connexion et tape la ligne), et pendant qu'un programme tourne (il lui renvoie le dernier message tapé).
Il est grisé quand la liste n'a aucune ligne d'historique pour le moment, et pendant la fin d'un programme dont un processus enfant écrit encore.
Il n'y a pas de confirmation : l'utilisateur sait ce qu'il renvoie.
L'**étiquette du champ**, qui est aussi son nom accessible, dit ce qu'il prend :
- « Commande » : profil Libre, de shell ou sans programme au repos ; un shell prêt à recevoir une commande ; une connexion, fermée ou ouverte ;
- le nom du profil (« git », tel que l'utilisateur l'a écrit) : profil à programme, rien ne tourne ; le texte est les arguments de son programme ;
- « Message » : un programme qui tourne et qui n'est pas un shell prêt (la case « Masquer le message » est alors disponible).

### Multi-line input

Le champ de commande est une ligne.
Pour envoyer plusieurs lignes d'un coup (un script PowerShell, une boucle, un here-string), **Édition > Saisie sur plusieurs lignes…** (Ctrl+M) ouvre une boîte de texte ; le champ de commande n'est pas modifié.
- La boîte a un champ de texte multiligne (« Lignes à envoyer ») et un seul bouton, **Envoyer**.
  Entrée fait une nouvelle ligne, Tab va au bouton, **Échap ferme la boîte sans rien envoyer** (il n'y a pas de bouton Annuler).
  Le focus initial est dans le texte, le curseur à la fin.
- Elle s'ouvre sur le texte du champ de commande, ou sur les lignes gardées la dernière fois qu'on l'a fermée avec Échap (le **brouillon**, gardé en mémoire seulement, vidé à l'envoi, jamais enregistré).
- La commande est disponible quand Entrée dans le champ le serait : au repos, avec une connexion choisie, ou pendant qu'un programme tourne ; elle est grisée pendant la fin d'un programme dont un processus enfant écrit encore.
- Il n'y a pas de case « Masquer le message » dans cette boîte : un message secret se tape dans le champ de commande.
- **Envoyer** envoie le texte comme Entrée dans le champ le ferait, en un seul **bloc** :
  - à un programme ou un shell qui tourne, les lignes sont écrites en une fois, séparées par la fin de ligne du programme (retour chariot sous terminal, saut de ligne en pipes) ; c'est ce que ferait un collage dans un terminal ;
  - à un shell à lancer (Cmd, PowerShell), le shell est lancé et le bloc lui est envoyé quand son invite est prête ;
  - avec une connexion fermée, la connexion s'ouvre puis le bloc est tapé dans le shell du serveur ;
  - avec le programme d'un profil, le bloc est ses arguments : un saut de ligne ne sépare pas les arguments (seuls l'espace et la tabulation le font), il en fait partie, ce qui donne un argument sur plusieurs lignes entre guillemets (`commit -m "ligne 1` puis `ligne 2"`).
  Pour PowerShell, une ligne vide est ajoutée à la fin : sans PSReadLine (que PowerShell désactive quand un lecteur d'écran tourne) il attend une ligne vide pour exécuter ce qu'il a reçu.
- Le bloc est **une seule entrée de l'historique**, avec ses vrais sauts de ligne (pas d'échappement : `\n` existe dans des chemins et des scripts).
  La liste de Ctrl+Espace le lit comme sa première ligne, coupée à 50 caractères (avec « … »), puis son nombre de lignes : « foreach ($i in 1..3) { (4 lignes) ».
  **Choisir un bloc dans la liste ouvre la boîte** sur ce bloc, au lieu de l'écrire dans le champ qui n'a qu'une ligne ; « Renvoyer la dernière commande » envoie le bloc directement.
- Les titres de la sortie viennent des invites du shell : avec PowerShell, une instruction sur plusieurs lignes n'a l'invite que sur sa première ligne, donc un seul titre ; deux instructions séparées en ont chacune un (essayé le 2026-11-05 avec PowerShell 7, Windows PowerShell 5.1 et Cmd).
- En mode pipes, la sortie répète le bloc sous la forme `> première ligne` suivie des autres lignes.

### Comfortable reading

Dans la sortie d'un shell, chaque commande envoyée est précédée de son invite, avec le chemin courant : l'entendre à chaque ligne est pénible.
La **lecture confortable** dit une ligne **avec filtrage** : un morceau de texte en est retiré ou remplacé par un mot, n'importe où dans la ligne ; la sortie ne change pas et les flèches Haut et Bas lisent toujours la vérité.
- **Ctrl+Alt+Haut** et **Ctrl+Alt+Bas** (modifiables dans Préférences > Raccourcis ; Terminal > Lecture confortable > « Ligne précédente, avec filtrage » et « Ligne suivante, avec filtrage ») déplacent le curseur de texte de la sortie d'une ligne vers le haut ou vers le bas, comme les flèches, et annoncent la ligne d'arrivée filtrée.
  Du curseur en ligne 3, Ctrl+Alt+Bas va en ligne 4 et l'annonce.
  Au début ou à la fin du texte, « Pas de ligne précédente. » ou « Pas de ligne suivante. » est dit, et rien ne bouge.
  Le focus passe dans la zone de sortie, comme pour Aller au curseur du terminal ; la commande est grisée tant qu'il n'y a pas de sortie.
- **Les filtres** sont des expressions régulières **cherchées dans toute la ligne**, dans l'ordre de la liste.
  **Le premier filtre qui trouve quelque chose est le seul appliqué**, et une seule fois : aucun remplacement ne se suit en cascade, donc le résultat est prévisible et le même dans l'essai du dialogue (F1) et à la lecture.
  Un filtre qui doit trouver son texte au début de la ligne commence par `^` ; un filtre qui trouve un texte vide, ou qui n'est pas une expression régulière valable, est sauté.
- Chaque filtre a un **remplacement**, ce qui est dit à la place du texte trouvé : rien (le défaut, le texte est simplement retiré), un mot (« Debian » pour l'invite d'un serveur, ce qui dit où l'on est), ou une partie du texte trouvé par les groupes de l'expression (`\1` ou `\g<nom>` : `sur \g<hote>`).
  La ligne annoncée est ce qui précède le texte trouvé, le remplacement, puis ce qui suit, séparés par une espace ; une ligne dont il ne reste rien est annoncée « vide ».
  Un remplacement qui nomme un groupe que le filtre n'a pas est refusé à l'enregistrement, avec la raison dite.
- Une ligne qu'aucun filtre ne touche est annoncée entière.
- **La liste de départ** retire les invites de Cmd (`^C:\chemin>`), PowerShell (`^PS C:\chemin> `), PowerShell `>> ` (ligne de suite d'un bloc), bash (`^utilisateur@hôte:chemin$ ` ou `#`, avec un `(venv) ` facultatif devant) et zsh (`^utilisateur@hôte dossier % `), et dit à la place « Commande » (« Suite » pour `>> `).
  La fin d'une invite est une espace ou la fin de la ligne : le texte de la sortie ne garde pas l'espace qui termine une ligne, donc une invite où rien n'est tapé (`utilisateur@hôte:~$`) est reconnue aussi.
  Les filtres de départ ne se fient pas au `# ` du préfixe d'invite d'un profil : ils l'acceptent devant l'invite, sans l'exiger, et un titre de texte qui commence par `# ` n'est pas pris pour une invite, parce que le filtre demande aussi la forme de l'invite elle-même.
  Les invites personnalisées (thèmes, `starship`, invites sur plusieurs lignes) ne sont pas reconnues tant que l'utilisateur n'ajoute pas son filtre.
- **Terminal > Lecture confortable > Filtrage de ligne…** ouvre le dialogue des filtres :
  - une liste, dans l'ordre où les filtres sont essayés, et les boutons « Ajouter un filtre… », « Modifier le filtre… » (aussi par un double clic), « Supprimer le filtre », « Monter », « Descendre » et « Rétablir les filtres de départ » (les filtres de départ qui sont dans la liste, trouvés par leur nom, redeviennent ce qu'ils étaient à leur place, ceux qui manquent sont ajoutés à la fin, et les filtres que l'utilisateur a ajoutés ne sont pas touchés) ;
  - la case à cocher **« Inclure les mises en forme d'activités »**, cochée au départ, une pour tous les filtres : la ligne annoncée garde la mise en forme que la touche Lire la ligne (F4) ajoute (« Question : … », une progression) ; sans elle, la ligne est annoncée filtrée et rien d'autre ;
  - la case à cocher **« Lecture confortable pour les déplacements par titres »** : les touches 1 à 6 et T (et Maj) annoncent alors le titre atteint filtré, par les mêmes filtres ; le texte de la sortie ne change pas, et la case est décochée au départ ;
  - l'ajout et la modification ouvrent une boîte avec le nom, le motif, le remplacement, une ligne d'essai et son résultat, un texte en lecture seule de plusieurs lignes qui écrit seulement la ligne telle qu'elle serait annoncée avec ce filtre (la ligne elle-même s'il n'y trouve rien), sans phrase d'explication, comme toute zone à lire (« Résultat (F1 pour entendre) ») ; **F1**, depuis n'importe quel contrôle de la boîte, annonce le résultat (« Rien à essayer pour l'instant. » quand il est vide) ; le nom ne peut pas être vide ni déjà pris (la casse ignorée) et le motif doit être une expression régulière valable, sinon une boîte de message le dit.
  Les filtres et les cases sont gardés dans les réglages ; une liste vidée reste vide.
- La destination de l'annonce suit celle des messages de déplacement (Préférences > Annonces).

### Launch file

L'application accepte en argument un chemin de fichier (`n5terminal projet.n5term`), sans option.
Le fichier fixe le profil, les valeurs de ses variables et le dossier de travail de la session ; il remplace le profil de démarrage et le dernier dossier récent.
C'est un fichier `.ini` en UTF-8, une clé et sa valeur par ligne (`clé = valeur`), sans en-tête de section obligatoire (un en-tête reste accepté) ; les lignes commençant par `;` ou `#` sont des commentaires, et le signe `%` n'a pas de sens particulier.
Les clés sont celles des variables (`name`, `source`, `destination`, `value1`, `value2`, `comment`, `ip`, `message`, les accolades étant acceptées : `{name}`), `profile` (le nom du profil ; la clé est en anglais, comme les autres, et seule celle-là est lue) et `WorkingPath` (le dossier de travail) ; la casse est ignorée et une clé inconnue est ignorée.
```
profile = git
WorkingPath = C:\Projets\mon-projet
name = dev
source = origin
```
- Le profil nommé est choisi au démarrage, comme par le menu Profil (sans annonce), et les variables du fichier sont les valeurs de ce profil pour la session.
  Si le profil n'existe pas, une boîte de message le dit et on reste en « Libre » ; des variables sans clé `profile` sont ignorées, avec un avertissement.
  Les avertissements et les erreurs de lecture sont dits dans la langue de l'application.
- Sans `WorkingPath`, la session démarre dans le dossier du fichier ; un `WorkingPath` relatif se lit à partir de ce dossier.
  Un dossier qui n'existe pas donne un avertissement et le comportement habituel (dernier dossier récent).
  Le dossier donné par `--folder` l'emporte sur `WorkingPath`.
- Le fichier n'exécute rien : il ne lance aucune commande.
- Un fichier illisible (introuvable, mal formé) est signalé par une boîte de message et l'application démarre sans lui.
- « Nouvelle session » ne transmet pas le fichier : la nouvelle session est « Libre ».
- L'extension du fichier est `.n5term`.
  Le bouton « Associer » de Préférences > Général fait ouvrir ces fichiers par MiTerm-N5 (voir « Preferences »).
- Le code est dans `core/config/launch_file.py`.

## Sending keys

Un programme servi par une pseudo-console (mode TUI) lit des touches, pas seulement des lignes : flèches, Échap, Tab, Ctrl+C, touches de fonction.
Le champ de commande n'envoie que du texte, suivi de `\r` ; une touche qui n'est pas du texte s'envoie par un menu ou par un raccourci.
Ce « mode étape » suffit pour les programmes interactifs légers (questions, listes à choisir, REPL) ; le clavier envoyé directement au programme reste à concevoir.

- **Les touches** (une commande chacune, `core/config/keys.py`) :
  - Navigation : flèches haut, bas, droite, gauche, Début, Fin, Page précédente, Page suivante.
  - Édition : Entrée, Tab, Maj+Tab, Échap, Espace, Retour arrière, Suppression.
  - Contrôle : Ctrl+C (interrompre), Ctrl+D (fin de saisie), Ctrl+Z (suspendre), Ctrl+L (redessiner).
  - Touches de fonction : F1 à F12.
- **Le raccourci prend la touche.** Une touche à raccourci (par exemple Alt+Bas pour « Envoyer Flèche bas ») n'arrive plus au contrôle qui a le focus : elle envoie la touche au programme, ou, si c'est impossible, annonce pourquoi.
  Le curseur de texte de la zone de sortie ne bouge donc pas (vérifié avec de vraies frappes, en français et en anglais) ; si le curseur bouge malgré tout, c'est NVDA qui le déplace avec ses propres commandes.
  Il n'y a pas de limite de plus sur les raccourcis (Ctrl+Début, Ctrl+Fin, Ctrl+flèches…) : l'utilisateur choisit, et un raccourci qu'il donne à une commande remplace la touche du contrôle.
- **Octets envoyés** : ceux d'un clavier de terminal (séquences VT ; Entrée est `\r`, Retour arrière `\x7f`).
  Les flèches, Début et Fin changent de forme quand le programme a demandé le mode « touches du curseur en mode application » (`Échap O A` au lieu de `Échap [ A`) : l'émulateur le sait, l'envoi en tient compte.
  Ctrl+C envoyé est un octet pour le programme, pas l'arrêt du programme (Arrêter le programme, Ctrl+Pause, le fait).
- **Où les trouver** : Session > Envoyer une touche (sous-menus par groupe) et le menu contextuel de la zone de sortie (touche Application, Maj+F10, clic droit) : Copier, Tout sélectionner (les commandes natives du contrôle), puis Envoyer.
  Le menu contextuel du champ de commande est : Historique (avec son raccourci, Ctrl+Espace), Saisie sur plusieurs lignes… (Ctrl+M), puis Couper, Copier, Coller, Tout sélectionner (les commandes natives du champ, qu'un menu à nous remplacerait).
- **Disponibilité** : seulement pendant un programme servi par une pseudo-console.
  Sinon les items sont grisés, et un raccourci annonce pourquoi : « Aucun programme en cours. », « Seulement pour les programmes qui utilisent un terminal. ».
- **Raccourcis** : chaque touche a une commande « Envoyer … » dans Préférences > Raccourcis (groupe « Envoi de touche »), **sans raccourci par défaut**, sauf Maj+Échap pour « Échap » et Maj+Entrée pour « Entrée ».
  Les mêmes règles s'appliquent qu'aux autres commandes : Ctrl ou Alt obligatoire (sauf F1 à F12 et Maj+Entrée), pas Tab ni Insertion, Échap seulement avec Maj, pas les raccourcis fixes (Ctrl+C reste « copier »).
  Un conseil vaut pour tout le groupe : choisir une combinaison avec Ctrl ou Alt qui ne gêne pas le lecteur d'écran, à vérifier à l'écoute.
- **Annonce** : une seule, « Envoie Échap. », de la catégorie « Sortie, touches envoyées » (message par défaut, rien possible dans Préférences > Annonces), hors de la barre d'état.
- **Focus** : l'envoi met le focus dans la zone de sortie sans toucher au curseur de texte (règle B de « Focus and caret »).

## Session information

Le **titre de la fenêtre** est « MiTerm-N5 : profil libre dans Dev » : le profil (« profil libre », ou le nom du profil choisi) et le dernier nom du dossier de travail.
Il suit le choix du profil et celui du dossier.
Avec une connexion SSH choisie, « dans Dev » est remplacé par « sur SSH » et le nom de la connexion : « MiTerm-N5 : profil libre sur SSH prod ».
Tant que la connexion n'est pas ouverte (avant de se connecter, pendant la connexion, après la fin), « (non connecté) » termine le titre : « MiTerm-N5 : profil libre sur SSH prod (non connecté) ».
« (non connecté) » est la seule information d'état du titre, et le seul suffixe : ni « Connexion… » ni « Authentification… » (ils sont dans la barre d'état), et rien une fois connecté.
Le titre n'a donc que deux formes, et ne change qu'à l'ouverture et à la fin de la connexion.
Le lecteur d'écran lit le titre quand la fenêtre reprend le focus (Alt+Tab) : l'utilisateur y apprend qu'une connexion s'est coupée pendant qu'il était ailleurs.

Session > Informations sur la session… ouvre la boîte de texte brut en lecture seule (focus sur le texte, OK ferme), une ligne « Nom : valeur » par information :
- le dossier de travail (chemin complet) ;
- le type de session : normal (données dans le profil Windows), portable (données à côté de l'application) ou develop (voir « Where the data lives » dans `specs/architecture/window.md`) ;
- le profil, le programme en cours, la fin du dernier programme ;
- avec une connexion SSH choisie : son nom, sa cible (avec le port), son état et, une fois connecté, depuis combien de temps (« connecté depuis 12 min ») ;
- le mode (CLI ou TUI), l'interpréteur, la taille du terminal, l'affichage du terminal (avec historique ou émulateur seul), les lignes de la sortie sur la limite ;
- le fichier des réglages, le dossier des profils, le dossier des connexions, le client OpenSSH (le `ssh.exe` de Windows, ou celui du réglage `ssh_path`) et le fichier du journal ;
- la version.

## Catalogs

Le mode Develop (`--develop`) a un dialogue, Develop > Catalogues…, qui modifie légèrement les textes traduits de l'application.
Il ne crée pas de message et ne change jamais un identifiant de message (le texte anglais du code) : seules les traductions se modifient.
Un texte anglais se corrige donc dans le code.

Le dialogue a, dans l'ordre de Tab : une liste déroulante « Catégorie », une liste « Messages » à une seule colonne, un champ de saisie, OK, Annuler.
Le focus initial est sur la liste.

- **Catégories** : Tous, Non traduits, Menus, Préférences, Annonces, Dialogues, Autres.
  La catégorie vient du fichier source qui utilise le message, noté dans `n5terminal.pot` (voir `specs/architecture/window.md`) ; un message utilisé par plusieurs fichiers est dans chacune de leurs catégories.
  La liste est faite quand on choisit la catégorie : un message qui devient traduit ne quitte pas « Non traduits » sous le curseur.
- **Liste** : une ligne montre soit l'identifiant du message, soit sa traduction dans une langue.
  Une ligne s'arrête au premier saut de ligne du message ou à 50 caractères ; dans ce cas « ... Extrait de message » est ajouté à la suite.
  Le texte complet est dans le champ de saisie.
  Gauche et Droite changent ce que montrent les lignes : avec une seule langue, Gauche montre les identifiants et Droite le français ; Haut et Bas sont ceux d'une liste.
  La ligne sélectionnée ne change pas quand on change de contenu.
- **Champ de saisie** : il contient le texte de la ligne sélectionnée.
  Son étiquette est « Message » quand la liste montre les identifiants (le champ est alors en lecture seule), « Message en français » quand elle montre le français.
  En vue de langue, chaque modification est reportée aussitôt dans le catalogue en mémoire ; la liste est remise à jour au changement de vue.
  Un message d'une seule ligne reste d'une seule ligne.
- **OK** vérifie que chaque traduction modifiée garde les mêmes champs `{nom}` que son identifiant (sinon le programme échouerait en affichant le message) ; si ce n'est pas le cas, le dialogue reste ouvert, une boîte de message dit quels champs sont attendus, et le message fautif est sélectionné dans la liste « Tous ».
  Sinon les fichiers `.po` modifiés sont écrits (fichier temporaire, puis remplacement) et leur `.mo` recompilé ; la langue change au prochain démarrage.
  Annuler ne change aucun fichier.

## Preferences

Fichier > Préférences… ouvre une boîte de dialogue à onglets, dans cet ordre : Général, Raccourcis, Annonces.
À l'ouverture, le focus est sur l'onglet Général, pour que l'utilisateur entende où il est avant d'entrer dans une page.
Entrée valide (OK), Échap annule.
Chaque champ a un nom accessible, et son étiquette est juste avant lui.
OK enregistre aussitôt dans le fichier des réglages ; si l'enregistrement échoue, l'erreur est annoncée.

- **Général** : la langue (Français ou English, appliquée au prochain démarrage et dite à l'utilisateur), le profil de démarrage et le nombre de lignes conservées dans la sortie (de 1 000 à 100 000, appliqué aussitôt).
  La liste déroulante « Profil de démarrage » propose « Libre » (le choix par défaut) puis tous les profils ; le profil choisi est celui sur lequel l'application démarre (clé `startup_profile`, vide = Libre), lu au prochain démarrage.
  Le repli est toujours Libre : si le profil n'existe plus ou ne peut pas être lu, l'application démarre sur Libre et une boîte de message le dit (« Le profil de démarrage … n'existe pas. »).
  Dans la liste, un profil disparu est montré comme « Libre » mais son nom n'est effacé que si l'utilisateur choisit autre chose.
  Un fichier de lancement qui nomme un profil l'emporte sur le profil de démarrage.
  Une case à cocher « Maximiser la fenêtre au démarrage », cochée par défaut, fait ouvrir la fenêtre principale maximisée ; elle est lue au prochain démarrage.
  Chaque langue est écrite dans sa propre langue.
  Un bouton « Associer les fichiers .n5term à MiTerm-N5 » (ou « Supprimer l'association des fichiers .n5term » quand elle existe) fait ouvrir les fichiers de lancement par un double clic ; il agit aussitôt, sans attendre OK, et une boîte de message dit ce qui a été fait ou pourquoi cela a échoué.
  L'association est écrite pour l'utilisateur Windows seulement (`HKEY_CURRENT_USER\Software\Classes`, sans droits d'administrateur) ; la supprimer retire tout ce qui a été écrit, et l'association d'un autre programme n'est pas touchée.
  En mode portable, rien n'est écrit : le bouton reste activable (un bouton grisé n'est pas atteint par Tab) et dit, au clic, que c'est indisponible parce que cela laisserait une trace sur l'ordinateur.
- **Raccourcis** : en haut, un choix « Commandes à afficher » (liste déroulante : Principal, Envoi de touche) ; dessous, une liste d'une ligne par commande configurable du groupe choisi, qui dit la commande puis son raccourci (« Arrêter le programme, Ctrl+Pause » ; « Envoyer Échap, aucun »).
  Sous la liste, un champ en lecture seule montre le raccourci de la commande choisie ; y appuyer sur une combinaison la donne à la commande.
  Tab quitte toujours le champ.
  Un raccourci refusé (touche réservée, raccourci d'une commande standard, déjà pris, mal formé) n'est pas donné, et une boîte de message dit pourquoi, en nommant la commande qui l'a déjà.
  Deux boutons : « Rétablir le raccourci par défaut » (refusé si une autre commande l'a pris) et « Aucun raccourci ».
  Appliqué aussitôt aux menus et au clavier.
- **Annonces** : en haut, la « Sortie des annonces » (UI Automation ou aucune, appliquée aussitôt).
  Dessous, une liste d'une ligne par catégorie, qui dit la catégorie puis sa destination (« Session, réglages, Message »), rien ne dépend de colonnes.
  Les catégories sont dans l'ordre alphabétique de leur nom, accents et casse ignorés.
  Sous la liste, un choix « Destination » ne propose que ce que la catégorie accepte, et changer la destination met la ligne à jour.
  Appliqué aussitôt.
  Dessous encore, deux champs de l'activité du terminal : « Intervalle de vérification de l'activité (en secondes) » (de 1 à 10, 1 par défaut) et la case « Annonce d'activité seulement dans la zone de sortie » (cochée par défaut).
- Les profils ne sont pas dans les Préférences (voir « Profiles »).

## What the command field sends

Un champ et un bouton ; le comportement dépend de l'état de la session.

| État | « Envoyer » (ou Entrée) |
|---|---|
| Aucun programme en cours | Le texte est une **ligne de commande** (programme et arguments), qui est lancée |
| Programme en cours | Le texte est écrit sur le **stdin** du programme, suivi d'un saut de ligne |

- Le nom accessible du champ change avec l'état : « Commande » au repos, le nom du profil avec un profil à programme, « Message » pendant l'exécution d'un programme (voir « Command field and program of a profile »).
  Le bouton garde son libellé « Envoyer ».
- Le champ d'état de la barre d'état affiche « Prêt » ou « En cours : nom du programme ».
  La fin d'un programme est annoncée avec son code de sortie dès qu'elle se produit.
- Un programme peut se terminer pendant qu'un processus qu'il a démarré écrit encore dans la sortie.
  La barre d'état affiche alors « Processus enfant actif », sa sortie continue d'apparaître, et le champ reste dans son état « Message » : pas de nouvelle commande tant que cette sortie n'est pas finie ou que l'utilisateur ne l'a pas arrêtée, pour que les sorties de deux programmes ne se mélangent jamais.
  Envoyer une ligne dans cet état est refusé avec un message annoncé, puisque le programme qui la lirait est terminé.
- Entrée envoie, puis le champ est vidé.
  Une ligne vide est ignorée au repos et envoyée quand un programme tourne (un simple saut de ligne sert souvent à continuer).
- **La case « Masquer le message »**, entre le champ et le bouton, sert à taper un secret (le mot de passe ou la phrase secrète qu'un programme demande) : l'utilisateur la coche au bon moment, quand il entend la question.
  - Cochée, le champ devient un champ de mot de passe de Windows (`EM_SETPASSWORDCHAR`, `hidden_text.py`) : il montre des `*`, le lecteur d'écran ne lit pas les lettres tapées parce que le style `ES_PASSWORD` le marque comme protégé, et Windows refuse d'en copier le texte.
    Le texte et le curseur de texte sont conservés : cocher ou décocher change seulement l'affichage.
  - Elle ne vaut que pour **le texte envoyé à un programme qui tourne** : au repos, la ligne est une commande de lancement, jamais un secret, et la case est grisée (donc sautée par Tab) et décochée.
  - Le message masqué est envoyé comme les autres, mais **jamais gardé** : il n'entre ni dans l'historique, ni dans « Renvoyer la dernière commande », ni dans un journal.
    Avec les pipes, la sortie écrit `> (message masqué)` à la place de la ligne, pour que la session se lise toujours comme un journal.
  - Elle se **décoche toute seule** après chaque envoi (et à la fin du programme) : le message suivant n'est pas masqué par oubli, ce qui rendrait une commande illisible.
    L'utilisateur la recoche pour le secret suivant.
  - Ni annonce ni raccourci : l'état de la case est lu par le lecteur d'écran comme celui de toute case à cocher.
    Un raccourci modifiable dans Préférences > Raccourcis reste possible plus tard.
- Une commande lancée avec des tubes (CLI) est écrite `# commande` puis, dessous, une ligne « Depuis C:\test\ » qui dit le dossier de travail (avec un séparateur final).
  Cette ligne n'est écrite que pour un lancement, pas pour le texte envoyé à un programme en cours, et pas en mode terminal, où le programme dessine son écran.
- La ligne envoyée est répétée dans la zone de sortie avec un préfixe (`> commande`), pour que la session se lise comme un journal complet.
  Avec les pipes, le programme ne fait pas l'écho de son entrée.
- Un seul historique, partagé par les deux états, atteint par la liste de Ctrl+Espace.
  Il garde toute ligne envoyée à un programme qui tourne, sauf un message masqué : un mot de passe tapé sans la case « Masquer le message » y reste donc, en mémoire, jusqu'à la fin de la session.
- Une saisie masquée par le programme (mots de passe) est impossible avec les pipes : c'est une raison d'être des modes terminal (4, 5).
  La case « Masquer le message » masque, elle, ce que l'utilisateur tape dans le champ, dans tous les modes.
- Lancement direct (sans shell) : `.exe`, `.bat` et `.cmd` fonctionnent ; les commandes internes de `cmd` (`dir`, `cd`, `echo`, `copy`), les pipes (`|`) et les redirections (`>`) non, tant que le réglage d'interpréteur n'existe pas.
  Un programme introuvable donne une erreur claire et annoncée (« Programme introuvable : dir. »).
- Arrêter un programme : une commande de menu et un raccourci (Ctrl+Pause), pas Ctrl+C dans le champ de commande, où il reste « copier ».

## Help

L'aide est une page par langue dans le dossier `Help`, à côté de l'application : `Fr.html` et `En.html`, faites à partir de `Fr.md` et `En.md` qui sont les sources.
**Aide > Ouvrir l'aide** (F1) ouvre dans le navigateur par défaut la page de la langue de l'application (réglage « Langue »).
- Sans la page de cette langue, la page `En.html` est ouverte.
- Sans aucune page, ou si le navigateur ne s'ouvre pas, un message le dit (« Le fichier d'aide Fr.html est introuvable. »).
- L'item est toujours disponible, et le focus passe au navigateur, comme pour tout programme ouvert depuis l'application.

**Develop > Convertir l'aide en HTML** (mode Develop seulement) écrit une page `.html` à côté de chaque fichier `.md` du dossier `Help`, puis dit combien de pages ont été écrites ; une erreur (dossier absent, aucun fichier `.md`, fichier illisible) est montrée dans une boîte de message.
La page est la plus simple possible, sans style ni script : le type de document, la langue (`lang`), le jeu de caractères (pour les accents), un titre (le premier titre du texte, que le lecteur d'écran lit à l'ouverture) et le texte converti en HTML.
Le code est dans `core/config/help.py` et `ui/help_actions.py`.

## Activities

Trois fonctions aident à suivre un programme sans relire la sortie sans cesse : la détection d'activité, la lecture d'une ligne avec mise en forme, et l'identification des activités de l'écran.
Elles sont dans le menu Terminal > Activités.
Elles lisent des lignes de texte, pas la grille d'un programme plein écran (`specs/decisions.md`).
Elles ne changent jamais le texte de la sortie, et seule l'identification déplace le curseur de texte et le focus, quand l'utilisateur le demande.
Le fonctionnement est dans `specs/architecture/screen.md`, « Analysis of the output ».

### Recognized elements

Une ligne reconnue donne un texte mis en forme, plus court et plus clair que la ligne brute :
- progression : « Téléchargement, 60 % » (le libellé qui précède la barre, puis la valeur ; sans libellé, « 60 % ») ;
- question : « Question : Écraser ? Réponse par défaut : non », « Question : Password » ;
- choix : « Red, sélectionné » (un marqueur), « Tests, cochée » (une case), « Option 2, Beta » (une option numérotée) pour une ligne, et « Choix, 5 options, sélectionné : Option B » pour un menu entier (dans la liste de l'identification) ;
- erreur : « Erreur : Access is denied. », « Avertissement : using the default ».

Les mots exacts sont à régler à l'écoute (`specs/open-questions.md`, « Line analysis and activity »).
Une ligne où rien n'est reconnu est lue nettoyée de son décor (cadres, suites de `#` ou de `=`), jamais brute.

### Activity detection

Un drapeau d'activité est levé à chaque mise à jour de l'écran qui change du texte de la sortie, dans n'importe quel mode.
Une ligne réécrite avec le même texte ne change rien, et l'écho de ce que l'utilisateur vient d'envoyer (dans les 300 ms) n'est pas une activité.
- À chaque **intervalle** (1 s par défaut, de 1 à 10 s), la veille regarde le drapeau et le baisse.
  La cadence est fixe : il n'y a pas d'annonce immédiate au premier changement.
- Si le drapeau était levé, et que le focus est dans la zone de sortie quand la case « seulement dans la zone de sortie » est cochée, la veille regarde la ligne du curseur de texte de la zone de sortie :
  - un élément reconnu : le texte mis en forme est annoncé (« Téléchargement, 60 % ») ;
  - sinon, avec « Messages ou bip » : un bip ;
  - sinon, avec « Messages » : rien.
- Si le focus n'est pas dans la zone de sortie (case cochée), rien n'est signalé, et le drapeau est quand même baissé pour qu'aucun bip n'arrive au retour du focus.
- Il n'y a aucune mémoire de la dernière valeur dite : une barre qui avance est redite à chaque intervalle, et une barre qui stagne est redite avec la **même valeur** tant que le terminal change ailleurs.
  Si le terminal ne change plus du tout (la barre stagne seule pendant dix secondes), il n'y a ni annonce ni bip.
- Le drapeau est baissé quand un programme démarre ou finit ; le message de fin existe déjà.
- Une roue qui tourne ou une horloge donnent une activité permanente : l'utilisateur coupe la détection avec « Signaler les activités » (Ctrl+B).
- La catégorie « Aucune » ne signale rien.

**Signaler les activités** est une case à cocher du menu, cochée tant que la catégorie n'est pas « Aucune ».
La décocher met la catégorie à « Aucune » et la recocher rétablit le dernier choix non vide (« Messages ou bip » à défaut), mémorisé dans les réglages.
Le raccourci dit toujours « Activité signalée » ou « Activité non signalée ».
Il n'y a ainsi qu'un seul interrupteur.

### Reading a line

Les flèches Haut et Bas ne sont pas touchées : la lecture est celle du lecteur d'écran, le texte brut de la ligne.
**Lire la ligne avec mise en forme** (F4) lit la ligne du curseur de texte de la zone de sortie, quel que soit le focus : « Téléchargement, 60 % », « Option B, sélectionné ».
Elle ne déplace ni le curseur de texte ni le focus.
Quand le curseur du terminal est **dans le texte** de la ligne lue (pas derrière, comme après une invite) et que la ligne ne montre rien d'autre, la ligne est l'item choisi d'une liste qui ne marque son choix que par le curseur : « Green, sélectionné ».
Un curseur derrière le texte attend une réponse, il ne marque rien.
Grisée tant que la sortie est vide.

### Identifying activities

**Identifier des activités…** (Maj+F4) liste ce qui est reconnu dans les dernières lignes de la sortie, autant que la hauteur du terminal choisi.
- La liste est faite de phrases complètes, une par élément, avec le texte et la position séparés par des virgules (rien ne dépend de colonnes) : « Progression, Téléchargement, 60 %, ligne 12 », « Question : Écraser ? Réponse par défaut : non, ligne 14 », « Erreur : disque plein, ligne 20 ».
  Une progression et un choix commencent par leur genre ; une question et une erreur le portent déjà dans leur texte.
- Les lignes d'un menu de choix qui se suivent sont un seul élément : « Choix, 3 options, sélectionné : Beta, ligne 5 » (la ligne de l'item choisi, sinon la première) ; une ligne de choix seule se dit « Choix, Red, sélectionné, ligne 3 ».
  Une liste dont les lignes ne se suivent pas, ou qui ne marque son choix que par le curseur du terminal, donne un élément par ligne reconnue.
- Les **adresses web** (`http://`, `https://`, `www.`) et les **adresses mail** écrites dans ces lignes sont aussi des éléments, un par adresse (une ligne peut en avoir plusieurs, ou en mêler avec une erreur) ; la ligne de la liste est **l'adresse seule**, sans genre ni numéro de ligne.
  La ponctuation de la phrase autour n'en fait pas partie (`(voir https://a.fr/x).` donne `https://a.fr/x`), `user@hôte` sans point et `git@github.com:user/dépôt` ne sont pas des adresses mail, et une commande lancée (`# …`) n'est pas cherchée.
  Limite connue : une adresse repliée sur deux lignes du terminal est vue en deux morceaux.
- Les éléments sont dans l'ordre du texte, et le **dernier qui n'est pas une adresse** est sélectionné à l'ouverture : c'est en général la question qui attend, qu'une adresse écrite plus bas ne doit pas masquer.
- Le bouton **« Copier dans le presse-papiers »** copie l'élément sélectionné, pour toutes les lignes : l'adresse telle quelle, ou le texte dit de l'élément (« Progression, Téléchargement, 60 % »).
  Le dialogue reste ouvert, et la copie est annoncée (« Copié dans le presse-papiers. », catégorie « Session, changement »).
  Le presse-papiers appartient à tout l'ordinateur : si un autre programme le tient, ou s'il refuse le texte, rien n'est copié et l'annonce le dit (« Rien n'a été copié : le presse-papiers n'est pas disponible. », catégorie « Commande impossible »).
- Entrée ferme le dialogue, met le curseur de texte au début de l'élément (pour une adresse, au début de l'adresse dans sa ligne) et le focus dans la zone de sortie.
  Échap ferme sans rien changer, et le focus revient où il était.
- Rien de reconnu : pas de dialogue, un message « Aucun élément reconnu. » toujours dit.
- Focus initial sur la liste, qui a un nom accessible.
- Grisé tant que la sortie est vide.

## Terminal display (modes 4 and 5)

La zone de sortie montre ce que montre le terminal, **en direct** (choix A) : chaque changement de l'écran pyte met à jour le texte.
Ce qui aide à suivre un programme sans tout relire (activité, ligne mise en forme, éléments reconnus) est dans « Activities ».
- **Mise à jour silencieuse.** Changer le contenu d'un contrôle de texte natif est silencieux, même quand il a le focus.
  Avec le focus dans la zone de sortie, le curseur de texte est remis où il était (même ligne, même colonne), ou au début de la ligne quand cette colonne n'existe plus.
  Pour l'instant l'utilisateur se déplace pour entendre une ligne et découvrir ce qui s'est passé.
- **Deux vues** (un réglage, la case « Vue terminal seule » du menu Terminal, décochée par défaut) :
  - **Vue terminal seule** (cochée) : la zone de sortie contient exactement les lignes du terminal (par exemple 24), donc Page précédente et Page suivante atteignent le haut et le bas d'un coup.
  - **Avec historique** (décochée) : les lignes qui ont quitté l'écran viennent d'abord, puis les lignes du terminal, tant que le terminal a des lignes.
    Quand le programme se termine sur un écran vide (un programme plein écran qui efface l'écran en partant), la dernière vue qui avait du texte est ajoutée à l'historique ; un écran qui garde du texte n'est pas touché (voir `specs/decisions.md`).
    La vue terminal seule n'a pas d'historique, donc rien n'y est ajouté.
    La partie émulateur n'est pas marquée dans le texte : MiTerm-N5 sait où elle commence et finit, et des raccourcis clavier y mènent (à choisir).
    Le total de la ligne dans la barre d'état s'adapte : il compte tout le texte avec historique, les lignes de l'émulateur sans.
- Pas d'écho local : le terminal affiche lui-même ce qui est tapé.

### One model for every mode: a fixed part and a live part

La zone de sortie est faite d'une **partie fixe**, qui ne fait que grandir (des lignes qui ne changeront plus), suivie d'une **partie vivante**, remplacée en bloc quand elle change.
- Mode pipes : la partie vivante est la dernière ligne inachevée (une barre de progression qui se réécrit).
- Mode terminal : la partie vivante est l'émulateur (toutes ses lignes) ; les lignes qui quittent l'écran vont à la partie fixe (avec historique) ou sont abandonnées (affichage émulateur).

La vue a une seule opération : ajouter ces lignes à la partie fixe, et voici la nouvelle partie vivante.
Le présentateur a un seul chemin pour tous les transports, et sait toujours où la partie vivante commence et finit.

**Mise à jour sélective de la partie vivante.** La mise à jour ne porte que les lignes modifiées (numéro de ligne et texte, d'après l'ensemble `dirty` de pyte), pour qu'une sélection ou le curseur de texte ailleurs soit laissé tranquille et que les lignes modifiées soient connues pour de futures annonces.
Un remplacement complet reste pour le redimensionnement, l'écran alternatif, l'effacement, ou quand la plupart des lignes ont changé.
En mode pipes la partie vivante est une ligne : les deux se confondent.

### Terminal cursor

**Aller au curseur du terminal** (menu Terminal > Déplacement, Ctrl+G) met le curseur de texte de la zone de sortie sur le curseur du terminal, c'est-à-dire là où le programme attend ce qu'on tape (derrière l'invite, par exemple).
Le focus va dans la zone de sortie, et l'annonce lit la ligne du curseur du terminal (catégorie « Sortie, déplacement et lecture » : rien, un message, ou la ligne ; « Curseur du terminal : » puis la ligne, ou « vide » quand elle l'est).
- La colonne reste dans la ligne : une ligne perd ses blancs de fin, donc un curseur du terminal derrière l'invite `C:\>` (et son espace) est placé à la fin de `C:\>`.
- Un curseur du terminal sur une ligne qui n'est pas montrée (les lignes vides à la fin, avec historique) est placé à la fin du texte.
- En mode pipes, le curseur du terminal est la fin de la dernière ligne inachevée.
- Grisée tant que la sortie est vide.
- Seul le sens « curseur du terminal vers curseur de texte » existe, et jamais automatiquement ; l'autre sens est écarté (`specs/decisions.md`).
- Le code est dans `OutputText.terminal_cursor_index` (`presenters/output_text.py`) et `ui/output_commands.py`.

**Aller à la première ligne du terminal** (Alt+Début) et **Aller à la dernière ligne du terminal** (Alt+Fin), dans le même menu, mettent le curseur de texte au début et à la fin de la partie vivante (Ctrl+Début et Ctrl+Fin restent ceux du contrôle de texte, pour tout le texte).
Le focus va dans la zone de sortie, et l'annonce lit la ligne (« Début de l'émulateur : » ou « Fin de l'émulateur : » puis la ligne, même catégorie que le curseur du terminal).
- Le début est le premier caractère de la première ligne de l'émulateur ; la fin est la fin du texte, c'est-à-dire de la dernière ligne montrée (avec historique, les lignes vides à la fin ne sont pas dans le texte).
- Elles restent actives en vue terminal seule, où elles font doublon avec Ctrl+Début et Ctrl+Fin : un item qui disparaît ou se grise selon la vue ferait douter qu'il existe.
- Ctrl+G aussi reste actif dans les deux vues : le curseur du terminal est celui de l'émulateur, il existe avec ou sans historique, et c'est avec l'historique qu'il est le plus utile (il ramène du haut d'une longue sortie à l'invite).
- Grisées tant que la sortie est vide, et pendant un programme qui n'utilise pas de terminal (« Seulement pour les programmes qui utilisent un terminal. ») ; sans programme en cours, elles atteignent la partie vivante de la dernière sortie.
- Quand la ligne qui chevauche la partie fixe et l'émulateur sera rejointe (`specs/open-questions.md`), le début ira au début de cette ligne logique.

### Terminal size

- L'utilisateur choisit parmi les **tailles standard** 80 x 24, 100 x 30, 120 x 30, 132 x 43, 160 x 50, 200 x 60, ou **automatique**.
- **Automatique** part de 120 x 30, la taille de départ de Windows Terminal, et ne peut que **grandir**, d'une taille standard à la fois, sur un débordement significatif : une ligne repliée de plus de 2 caractères vue deux fois, ou de plus de 10 caractères une fois (un ou deux caractères en trop peuvent être une erreur d'affichage du programme).
  Ces valeurs sont un début, à ajuster à l'usage.
  Les lignes déjà affichées restent telles quelles ; ce qui suit en profite.
  La pseudo-console et l'écran pyte sont redimensionnés ensemble, et le programme en est informé.
- **Les lignes repliées sont affichées comme les affiche un terminal standard** : une ligne plus longue que l'écran se lit comme plusieurs lignes.
  Les rejoindre est une question ouverte (`specs/open-questions.md`).
- **Débordement** : pas annoncé pour l'instant ; la session le garde comme un état (une ligne était plus longue que l'écran), que l'interface pourra montrer plus tard.

## Connections

La conception et les mesures sont dans `specs/architecture/connection.md`.
Une **connexion** dit où s'exécute ce que l'on lance : cet ordinateur (« Locale », le choix par défaut) ou un serveur SSH.
Avec une connexion choisie, tout s'exécute sur le serveur : on ne lance pas de programme local sans repasser par « Locale ».
- Le menu **Connexion**, entre Profil et Terminal, fonctionne comme le menu Profil : **Choix connexion** (un sous-menu à choix unique : Locale d'abord, puis les connexions par ordre alphabétique, un fichier chacune), **Se connecter**, **Se déconnecter**, puis, après un séparateur, **Ajouter…**, **Modifier…**, **Supprimer**, et **Client SSH…**.
  « Se connecter » n'a pas de raccourci par défaut, l'utilisateur lui en donne un dans Préférences > Raccourcis.
  « Se déconnecter » fait la même chose que « Arrêter le programme » (Ctrl+Pause) pendant une connexion : on la trouve là où on la cherche.
- Les items sont grisés avec leur raison annoncée, par une seule règle : **tant qu'une connexion s'ouvre ou est ouverte, on ne la change pas** (comme on ne change pas le profil pendant qu'un programme tourne).
  - Choix connexion, Ajouter, Modifier, Supprimer et Client SSH… : grisés dès que la connexion s'ouvre (la connexion en cours d'ouverture compte comme un programme qui tourne) ;
  - Modifier et Supprimer : grisés aussi avec « Locale » ;
  - Se connecter : grisé avec « Locale » et quand une connexion s'ouvre ou est ouverte ;
  - Se déconnecter : grisé tant qu'aucune connexion ne s'ouvre ni n'est ouverte.
- Avec une connexion choisie, les commandes qui parlent de cet ordinateur sont grisées, avec « Indisponible avec une connexion. » : Dossier de travail, Dossiers récents, Interpréteur (et Sélection du PowerShell), Mode, Relancer la dernière commande et les programmes de test.
  « Lancer le programme » (F5) reste disponible tant que la connexion est fermée : voir plus bas.
  Un seul fait compte pour toutes : une connexion est choisie (`SessionState.connection`).
- Le dialogue Ajouter / Modifier : le nom (20 caractères au plus, avec la même liste de caractères que le nom d'un profil, voir « Profile dialog »), la cible (un alias du `~/.ssh/config` ou `utilisateur@hôte`) et le port facultatif.
  Aucun mot de passe n'y est écrit.
  Une connexion n'a pas de profil : le profil (git, Cmd…) se choisit dans le menu Profil, avant ou après la connexion.
- **Entrée dans le champ de commande**, avec une connexion choisie et fermée, **ouvre la connexion** : l'utilisateur n'a pas à passer par le menu.
  Le texte tapé est envoyé au serveur une fois connecté, comme la ligne tapée à un shell local ; une ligne vide ne fait que se connecter.
- Les dialogues de `ssh` disent toujours où l'on se connecte : leur titre est « Connexion à prod » (« Connexion prod : mot de passe » pour la question d'un mot de passe, que le lecteur d'écran lit à l'ouverture), et leur texte donne la cible et le port.
  - Le mot de passe (ou la phrase secrète, ou un code) : le serveur, la consigne « Saisissez le mot de passe ou la réponse demandée par le serveur ; elle reste masquée. », la question de `ssh`, puis un champ masqué, OK et Annuler.
  - La clé d'hôte d'un serveur inconnu : le texte de `ssh` avec l'empreinte, un champ en lecture seule atteint par Tab, « Faire confiance et continuer » et « Annuler » (par défaut).
  - Une connexion par clé ne pose aucune question, donc n'ouvre aucun dialogue : l'état se lit dans la barre d'état et dans la sortie.
- **Client SSH…** ouvre un dialogue, sur le modèle de « Sélection du PowerShell… » : une liste (l'OpenSSH de Windows, par défaut ; ceux trouvés ailleurs, comme celui de Git ; « Autre… » avec un chemin) qui dit le `ssh.exe` utilisé.
  C'est un réglage global (clé `ssh_path` de `settings.json`, vide : celui de Windows).
  Seul l'OpenSSH de Windows est mesuré : le dialogue dit que les autres ne sont pas essayés.
- La session ouvre le shell du serveur, en TUI ; les commandes du profil sont tapées dans ce shell.
  Sur un serveur, **le programme d'un profil s'écrit par son nom de fichier**, sans dossier ni extension (`C:\Program Files\Git\bin\git.exe` devient `git`) : un chemin Windows n'existe pas sur le serveur.
  L'interpréteur d'un profil de shell local (Cmd, PowerShell) est ignoré.
  **Lancer le programme** (F5) fait de même : avec une connexion fermée, il l'ouvre puis tape le nom du programme du profil (`git`) dans le shell du serveur.
  Une fois la connexion ouverte, il est grisé (« Indisponible pendant qu'un programme tourne. ») : le shell du serveur n'est pas reconnu, donc on ne sait pas s'il attend une commande ; les commandes du profil restent dans la liste de Ctrl+Espace.
- Arrêter le programme (Ctrl+Pause) ferme la connexion.
- « Nouvelle session » démarre en « Locale », sans hériter de la connexion choisie.

### Connection state

L'état de la connexion se dit à cinq endroits, du plus permanent au plus ponctuel :
- **La barre d'état** (champ du milieu) : « Connexion… », « Authentification… », « Connecté à prod », « Déconnecté (code 255) ».
  C'est la référence quand l'utilisateur la consulte.
- **Une annonce à chaque changement d'état** : la catégorie « Connexion, état » (rien ou message, message par défaut), avec les mêmes textes, une fois chacun, et « Connexion annulée. » quand l'utilisateur annule un dialogue.
  Une coupure vue par `ssh` (45 s au plus) se dit ainsi, même quand la fenêtre n'a pas le focus.
  Une erreur (connexion impossible, authentification refusée, clé d'hôte) est de la catégorie « Échec de lancement » : message ou dialogue, jamais « rien », avec sa cause.
- **La sortie** : « Se connecter » écrit dans la partie fixe, comme une commande lancée, un titre de niveau 1 `# SSH prod` puis une ligne « Vers utilisateur@hôte:22 » (la cible du fichier de la connexion, avec le port s'il y en a un), sur le modèle de « Depuis ».
  Sans ces lignes la sortie serait vide à la connexion : tant que le serveur n'a rien écrit, il n'y a rien à lire ni à atteindre.
  Le titre est atteint par les touches 1 et T, et le focus comme le curseur de texte suivent la règle B de « Focus and caret » (au début du titre).
  À la fin de la connexion, une ligne « Déconnecté (code 255). » est écrite dans la **partie de fin** de la sortie, après la partie vivante (l'écran du serveur) : Ctrl+Fin y mène, et Alt+Fin s'arrête avant elle, à la fin de la partie vivante.
  La partie de fin disparaît avec la partie vivante quand la sortie suivante (une nouvelle connexion, un programme local) la remplace.
  C'est une exception à la règle des modes terminal, qui n'écrivent pas la commande : à la connexion la sortie est encore vide, et ces lignes donnent quelque chose à lire et un endroit où mettre le focus.
- **Le titre de la fenêtre** : « sur SSH prod », puis « (non connecté) » tant que la connexion n'est pas ouverte (voir « Session information »).
- **Session > Informations sur la session…** : le nom, la cible, l'état et la durée, à la demande.

Pas de quatrième champ dans la barre d'état : un lecteur d'écran le relirait à chaque passage pour peu d'information de plus.

## Accessibility

- Chaque contrôle a un nom accessible (zone de sortie, champ de commande, bouton Envoyer).
- Focus initial : le champ de commande.
  La zone de sortie ne vole jamais le focus quand du texte arrive.
- Tout est atteignable au clavier seul (ordre de Tab : champ de commande, case « Masquer le message », bouton Envoyer, zone de sortie).
- Les changements d'état (état de la connexion, fin du programme avec son code de sortie) sont affichés dans la barre d'état et annoncés par le centre d'annonces, pas par la couleur seule.
- Tout est lu et annoncé correctement par un lecteur d'écran.

## Not decided yet

Voir `specs/open-questions.md` : ce qui est annoncé et quand, les raccourcis clavier de la partie émulateur, le format de la barre d'état.
