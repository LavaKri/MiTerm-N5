# Open questions

Le seul endroit pour les questions et les améliorations.
Les autres documents contiennent ce qui est vrai ; les vérifications à faire avec un lecteur d'écran sont dans `specs/manual-checks.md`, les raisons des choix passés dans `specs/decisions.md`.

## Interface and accessibility (settled parts: `specs/interface.md`)

- Sons pour d'autres annonces que le bip de l'activité : pas dans la première version ; ils demandent des fichiers à livrer.

- **L'ordre entre stdout et stderr.** Deux tubes lus par deux threads : quand un programme écrit sur les deux presque en même temps, une ligne de l'un peut être lue après une ligne de l'autre écrite plus tard (vu avec `Progress`, où une barre sur stderr passait avant la ligne « Mode » écrite avant elle).
  Seule la fusion des deux flux dans un seul tube (comme `2>&1`) donnerait l'ordre d'écriture, mais elle ferait perdre le marquage « StdErr: » : une case « Fusion stdout/stderr » reste possible si l'ordre compte plus que la distinction.
- La recherche ignore la casse mais pas les accents (« e » ne trouve pas « é »), et n'a pas d'option pour les mots entiers ; à ajuster à l'usage.

## Profiles, titles, terminal analysis (see "Profiles" and "Titles" in `specs/interface.md`)

- **Une commande correspond-elle à un profil d'elle-même ?** Un profil (`git`) se choisit **à la main** dans le menu Profil : rien n'est appliqué automatiquement (décidé).
  Ouvert : quand le programme d'une commande lancée correspond à un profil (`git status` et le profil `git`), MiTerm-N5 doit-il (1) ne rien faire, (2) seulement annoncer « Profil git disponible », ou (3) l'appliquer et annoncer ce qu'il a changé ?
  L'appliquer écraserait une valeur que l'utilisateur a réglée à la main (TUI choisi, puis `git status` lancé en CLI) : pour l'éviter, une application automatique ne devrait jamais écraser un réglage manuel.
  Recommandé pour la première version : (1).
  Les commandes courantes d'un profil n'apparaissent dans la liste de l'historique que pendant qu'il est choisi.
- **Commandes tapées dans un shell** (Cmd, PowerShell, TUI) : le terminal les dessine lui-même, elles n'ont donc pas de marque `# `.
  Les lignes d'invite, déjà reconnues, pourraient servir de marques pour aller de commande en commande.
  À faire après la première fenêtre.
- **Les lignes d'un programme qui commencent par `#`** (commentaires, fichiers de configuration) sont des titres de niveau 1 comme les commandes.
  Si cela gêne, donner aux commandes un niveau propre.
- **Markdown au-delà des titres** (listes, tableaux, liens, blocs de code) : pas maintenant ; plus tard, facultatif par profil.
  Rare dans les commandes simples, fréquent dans les outils en ligne de commande d'IA et `gh`.
- **Activités du terminal** (progression, question, choix, erreur) : décidées (`specs/interface.md`, « Activities ») ; ce qui reste ouvert est plus bas, « Line analysis and activity ».
- **Curseur du terminal et curseur de texte** : « mettre le curseur de texte sur le curseur du terminal » est fait (Ctrl+G, `specs/interface.md`, « Terminal cursor »).
  « Mettre le curseur du terminal sur le curseur de texte » (flèches) est écarté le 2026-11-05 : trop limité pour servir (`specs/decisions.md`).

## Line analysis and activity (6f)

Ce qui est décidé est dans `specs/interface.md`, « Activities », et `specs/architecture/screen.md`, « Analysis of the output ».
- **Décidé le 2026-10-30.**
  Les éléments reconnus ne servent pas aux profils pour l'instant.
  Pas de couleurs : l'analyse lit le texte, pas les attributs de chaque cellule.
- **Attributs de cellule.** Un champ optionnel `marked_rows` de `ScreenUpdate` (les rangées qui contiennent du texte en vidéo inverse) n'est ajouté que si le texte ne suffit pas pour les choix ; il passerait par les tests de contrat du modèle d'écran.
  **Mesuré le 2026-10-30** (capture `reverse.vt`, `tests/core/screen/test_reverse_video.py`) : pyte donne l'attribut « inversé » de façon fiable avec la sortie de ConPTY, sur les cellules qui portent du texte et elles seules.
  Un programme qui écrit la vidéo inverse en VT (`Échap [7m`, aussi avec du gras ou une couleur) et un programme qui utilise l'attribut de l'API de console Windows (`COMMON_LVB_REVERSE_VIDEO`) sont vus de la même façon : ConPTY réécrit le second en `Échap [0;7m`.
  Deux limites à garder si `marked_rows` est ajouté : (1) un choix marqué seulement par deux couleurs (noir sur blanc) n'est pas de la vidéo inverse et ne serait pas trouvé ; (2) une vidéo inverse suivie d'un effacement jusqu'à la fin de la ligne couvre toute la rangée jusqu'au bord, donc il ne faut compter que les cellules qui portent du texte.
  **Pas vérifié** : ce que marquent les invites modernes. `gh auth login` (Go) marque l'item choisi par un glyphe `> ` en cyan, sans vidéo inverse : l'analyse de ligne le trouve par le glyphe. PowerShell désactive PSReadLine quand il détecte un lecteur d'écran, donc son menu de complétion n'a pas pu être observé. Les bibliothèques à vidéo inverse (`prompt_toolkit`, `inquirer`, `fzf`) restent à capturer.
- **Ce que les captures ont montré** (`pip install --dry-run`, `winget search`, programmes simples) : pip n'écrit pas de barre pour un petit fichier (sa ligne `Downloading … (1.7 kB)` n'est pas une progression) ; la table de winget n'est rien à reconnaître ; une barre réécrite par un retour chariot donne une ligne qui monte de 0 à 100 %.
- **Écarté le 2026-10-31** (l'étape 6f est faite), à reprendre seulement si l'usage le demande :
  - les coches en symboles (`✔`, `☑`, `◉`) ;
  - une question repliée sur deux lignes, et un menu sans marqueur dont le choix n'est marqué que par le curseur (un élément par ligne reconnue) ;
  - un mot de passe qui reste reconnu après la réponse (il n'écrit rien sur la ligne) ;
  - F4 qui dit « sélectionné » sur une ligne où le curseur du terminal est dans le texte, même hors liste, et un curseur caché qui n'est pas vu ;
  - une commande « lire la dernière activité » et un signal de silence (« plus de sortie depuis N s »).

## Robustness (see `specs/robustness.md`)

- Limites par défaut : lignes gardées dans la zone de sortie (10 000 ?), longueur d'une ligne (10 000 caractères ?), taille et nombre de fichiers de journal en rotation (5 x 1 Mo ?).
- Caractères de contrôle dans la sortie : les retirer, ou les remplacer par une marque visible ?

## Against `specs/working-rules.md`

- **Des listes sans colonnes.** Les règles veulent l'information d'une liste dans le texte de chaque ligne, séparée par des virgules, rien ne dépendant de colonnes.
  La liste des raccourcis des Préférences doit être construite ainsi (une liste de lignes comme « Arrêter le programme, Ctrl+Pause »), pas comme un tableau.

## Project frame

- Licence : pyte est sous LGPL v3 (voir `specs/packaging.md`) ; GPL-3.0 est compatible.

## Terminal display (see "Terminal display" in `specs/interface.md`)

- Où l'état de débordement est montré, si tant est qu'il le soit.
- **Rejoindre les lignes repliées** (pour l'instant MiTerm-N5 se comporte comme un terminal standard et ne les rejoint pas).
  - Le problème : le terminal replie une ligne plus longue que l'écran.
    Un programme écrit 80 « A », 80 « b » et 40 « c » sur un écran de 80 colonnes : la grille contient trois lignes, et le lecteur d'écran lit trois lignes, la deuxième commençant au milieu de ce que le programme a écrit.
    L'export garde des sauts de ligne que le programme n'a jamais écrits.
  - L'idée : une préférence (case à cocher) qui montre une telle ligne comme la seule ligne que le programme a écrite.
    Le modèle d'écran marque déjà une ligne `continued` quand le terminal l'a repliée en dessinant du texte ; l'affichage joint une ligne à la suivante quand elle est marquée.
  - Le cas délicat : la ligne chevauche l'historique et l'écran (la ligne des « A » est sortie de l'écran, les lignes « b » et « c » y sont encore).
    Règle : pas de saut de ligne entre la partie fixe et la partie vivante quand la dernière ligne fixe est marquée continuée ; la partie vivante commence alors au milieu d'une ligne de texte, et le raccourci vers le début de l'émulateur va au début de cette ligne logique.

## SSH connections (see `specs/architecture/connection.md`)

- **Les questions de second facteur** (`Verification code: `) arrivent-elles par le programme de saisie, et sous quelle forme ? À mesurer avec un serveur qui l'exige.
- **Le préfixe d'invite sur le serveur** : envoyer une ligne `PS1=...` à l'ouverture du shell (visible dans la sortie et dans l'historique du serveur) ou y renoncer.
- **La reconnaissance de l'invite d'un shell distant** (pour les commandes qui demandent un shell à son invite) et un dossier de travail distant.
- **Version portable** : `-o UserKnownHostsFile` vers `data\known_hosts` est confirmé (`specs/architecture/transport.md`, « What `ssh.exe` does (measured) ») ; reste à essayer `ssh` sur une machine dont le dossier `.ssh` n'existe pas.


## Profile program in the command field


## Hiding a secret (see `specs/decisions.md`, 2026-11-04)

- **Proposer la case « Masquer le message » quand la dernière ligne de la sortie ressemble à une demande de secret** (`password`, `passphrase`, `mot de passe`, `PIN`…).
  Proposer veut dire cocher la case et le dire (« Saisie masquée proposée »), jamais masquer sans que l'utilisateur puisse le défaire.
  À essayer à l'usage : trop de faux positifs ou de faux négatifs la rendrait pénible.
- **Lire le mode d'écho de la console du programme** (s'y attacher avec `AttachConsole`) : jamais essayé, jugé peu fiable (voir la décision).

## To check by experiment

- Quel ConPTY pywinpty utilise : le `conpty.dll` / `OpenConsole.exe` qu'il livre, ou celui de Windows.
  Les captures ont été faites avec celui qu'il utilise.
- Une invite personnalisée (un thème, `prompt $G`) n'est pas reconnue comme invite, donc l'item « Dossier de travail » reste désactivé dans ce shell : un réglage devrait-il laisser l'utilisateur donner un motif pour elle ?
- Si `ESC[3J` (effacer l'historique de défilement, peut-être envoyé par `cls`) atteint pyte, et quoi en faire (vider la partie fixe, ou la garder).
- Ce qui manque à pyte avec la sortie de ConPTY pour les caractères larges (l'écran alternatif n'est plus visé, `specs/decisions.md`).
- Plus tard : compatibilité de paramiko ou asyncssh avec Python 3.14.
