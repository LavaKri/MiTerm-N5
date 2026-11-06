# Screen model, output and titles

Des octets d'un programme au texte de la zone de sortie.
Vue d'ensemble dans `specs/architecture.md`.

## Screen model

`ScreenModel` (`core/screen/screen_model.py`) est le contrat entre les octets du terminal et la zone de sortie ; `PyteScreenModel` en est l'implémentation.
Les données qui le traversent sont simples (chaînes, nombres, booléens), si bien qu'un module natif peut le remplacer et passer les mêmes tests de contrat.
- `feed(bytes, stream)` décode l'UTF-8 de façon incrémentale (un octet invalide devient `U+FFFD`) et alimente pyte ; `resize(columns, rows)` ; `take_update()` renvoie un `ScreenUpdate` et l'oublie.
  `stream` dit de quel flux du transport viennent les octets : un terminal n'en a qu'un et les prend tous, les pipes les gardent séparés (`LineOutputModel`).
- `finish()` : plus aucune sortie ne viendra, le modèle lâche ce qu'il retenait (sans effet quand il ne retient rien) ; `take_update()` rend ensuite ce qui a été lâché.
- `application_cursor_keys` : le programme a-t-il demandé les flèches en mode application (DECCKM) ?
  Toujours faux pour les pipes.
- Ces trois points sont dans le contrat, donc dans les tests de contrat (`tests/fakes/screen_model_contract.py`) : un module natif ne peut pas les oublier.
  `ScreenPump` n'a plus à deviner ce qu'un modèle sait faire.
- `ScreenUpdate` : `fixed` (les lignes qui ont quitté l'écran depuis la dernière mise à jour, chacune une fois, dans l'ordre), `rows` (les lignes modifiées de la partie vivante, `replace_all` quand elle les contient toutes : première mise à jour, redimensionnement, ou plus de la moitié des lignes modifiées), `overflows`, la taille et le curseur.
  Les textes n'ont pas d'espaces en fin de ligne.
- **Lignes modifiées** : le `dirty` de pyte dit seulement quelles lignes regarder (chaque défilement les marque toutes) ; les lignes sont rendues et comparées à ce qui a été remis la dernière fois, si bien qu'une ligne inchangée n'est jamais signalée.
- **Lignes fixes** : une ligne est enregistrée quand l'écran défile avec le curseur sur la dernière ligne d'une région de défilement qui commence à la ligne 0.
  Effacer l'écran les conserve.
  Rien n'est supprimé dans le modèle : la limite de lignes gardées appartient à la zone de sortie.
- **Lignes repliées** (`continued`) : pyte replie dans `draw` en appelant `carriage_return` et `linefeed` ; la sous-classe sait qu'elle dessine et marque la ligne.
  La marque est gardée avec la largeur à laquelle la ligne s'est repliée, par numéro de ligne ; elle suit le défilement (`index`, `reverse_index`) et est supprimée par `insert_lines`, `delete_lines` et `reset`.
  **Elle survit à un élargissement de l'écran** (la ligne s'était bien terminée par un repli) : une invite repliée à 100 colonnes reste une seule ligne quand la taille automatique passe à 120.
  Une ligne effacée ou réécrite ensuite a une cellule vide là où elle se repliait, ce qui annule sa marque.
  Une ligne exactement aussi large que l'écran n'est pas continuée (pyte ne replie que quand le caractère suivant arrive).
  Limite connue : une ligne repliée dont le dernier caractère est une espace est lue comme non continuée.
- **Débordements** (`overflows`) : l'excédent d'une ligne repliée (les caractères au-delà de la largeur de l'écran) est signalé une fois que le programme quitte la ligne (retour chariot, saut de ligne, déplacement du curseur), pas pendant qu'elle s'écrit.
- **Taille automatique** : `AutoSizePolicy` (`core/screen/terminal_size.py`) prend les `overflows` et dit quand passer à la taille standard suivante.
  L'appliquer ensemble à ConPTY et au modèle est le travail du présentateur de session.

## Output of the pipe modes

`LineOutputModel` (`core/screen/line_output_model.py`) est un modèle d'écran d'une seule ligne, pour que les pipes suivent le même chemin que le terminal (`ScreenPump`, `DisplayExchange`, `ScreenUpdate`) : les lignes terminées forment la partie fixe, la ligne en cours d'écriture est la partie vivante.
Il décode chaque flux avec `StreamDecoder` (`core/transport/stream_decoder.py` : UTF-8, puis pour le reste du flux la page de code de la console, `cp850` par défaut, quand les octets ne sont pas de l'UTF-8) et le filtre avec `DefaultOutputFilter` ; la sortie standard et l'erreur standard écrivent dans l'ordre d'arrivée, et une ligne n'est jamais partagée entre les deux (la ligne inachevée est fermée quand l'autre flux écrit).
Une ligne plus longue que le maximum (10 000 caractères, à décider) est coupée et les morceaux sont marqués `continued`.
Il peut être appelé sans danger depuis les deux threads de lecture.
Limite connue : quand un flux réécrit sa ligne (une barre de progression) après que l'autre a écrit, la réécriture apparaît comme une nouvelle ligne.

## Terminal size

Le terminal (MiTerm-N5) fixe la taille et le programme s'y adapte ; on ne peut pas compter sur un programme pour la choisir.
L'utilisateur choisit une taille standard ou le mode automatique (voir « Terminal size » dans `specs/interface.md`) ; le mode automatique démarre à **120 x 30** et ne fait que grandir.
La même taille est appliquée à ConPTY (`PTY.set_size`) et à l'écran pyte, créé **avant** le démarrage du programme pour qu'aucune sortie ne soit perdue.
Un redimensionnement met à jour les deux.
Un décalage déforme l'affichage, puisque des positions de curseur n'existeraient pas dans l'écran virtuel.

pyte replie une ligne plus longue que l'écran (autowrap, DECAWM), comme le fait un vrai terminal, et ne s'en souvient pas.
Pour rejoindre les lignes repliées et détecter les débordements, une sous-classe de `Screen` marque une ligne comme continuée quand le repli se produit pendant l'écriture du texte (et non sur un retour chariot envoyé par le programme).

## Titles, command marks, size

- **Titres** (`core/screen/titles.py`, `presenters/title_navigation.py`) : la sortie est lue comme du Markdown (`markdown-it-py`, blocs de code ignorés) ; `parse_titles`, `next_title`, `previous_title` travaillent sur le texte avec des sauts de ligne `\n`, et `to_utf16` / `from_utf16` convertissent vers les positions d'un champ de texte Windows (un caractère hors du plan de base compte pour deux).
  `TitleNavigator.go` trouve le titre depuis le curseur de texte, l'annonce (`MOVED_TITLE` dans la catégorie « Sortie, déplacement et lecture » : rien, message ou lire la ligne ; `NO_NEXT_TITLE`... dans « Sortie, pas ou plus d'éléments ») et renvoie où le curseur de texte va.
  La fenêtre garde sa propre copie du texte avec des sauts de ligne `\n`, puisqu'un contrôle de texte Windows compte `\r\n` différemment.
- **Marques** : le présentateur écrit une commande lancée `# commande` (`LAUNCH_PREFIX`, un titre de niveau 1, atteint avec la touche 1) et une ligne envoyée à un programme en cours `> texte` (`SEND_PREFIX`).
- **Taille** (`core/screen/terminal_size.py`) : `SizeChoice` contient ce que l'utilisateur a choisi, une taille standard ou l'automatique, et `AutoSizePolicy` fait grandir l'automatique.
- **Limites** : l'historique des commandes en garde 20 par session (`CommandHistory`, ce n'est pas un réglage) ; la sortie garde `Settings.output_limit` lignes (10 000 par défaut, entre 1 000 et 100 000).

## Analysis of the output

Ce que l'utilisateur voit est dans `specs/interface.md`, « Activities » ; la raison du choix est dans `specs/decisions.md`.
Deux pièces, qui ne font que regarder : elles ne changent jamais le texte de la sortie, le curseur de texte ni le focus.
**État** : l'analyse de ligne, la lecture d'une ligne (F4), l'identification des activités (Maj+F4) et la détection d'activité sont faites (`specs/roadmap.md`, 6f).
- **L'identification** (`core/screen/screen_elements.py`, `find_elements`) donne chaque ligne des dernières lignes de la sortie (la hauteur du terminal choisi) à l'analyse de ligne, avec le curseur du terminal, et fait un seul élément (`FoundElement`) des lignes de choix qui se suivent.
  `ui/output_commands.py` (`identify_activities`) montre la liste avec la liste de choix de `Feedback` (`choose`), le dernier élément sélectionné, puis met le curseur de texte et le focus sur la ligne choisie.
- **Les adresses** (`core/screen/addresses.py`, `find_addresses`, sans `wx` ni temps) : le texte d'une ligne donne ses adresses web (`http://`, `https://`, `www.`) et ses adresses mail, chacune avec sa place dans la ligne (`Address`).
  Une ligne peut en avoir plusieurs, alors que l'analyse de ligne n'en tire qu'un élément : `find_elements` appelle les deux, sauf pour une commande lancée (`# `) et, en mode tubes, une ligne envoyée (`> `).
  Les signes de la phrase autour sont retirés de la fin d'une adresse web (`.`, `,`, `;`, `:`, `!`, `?`, guillemets, crochets, et une parenthèse fermante sans ouvrante).
  Ne sont pas des adresses mail : une adresse écrite dans une adresse web, `user@hôte` sans point, et `git@github.com:user/dépôt`.
  Ce que voit l'utilisateur est dans `specs/interface.md`, « Activities ».
- **L'analyse de ligne** (`core/screen/line_analysis.py`, sans `wx` ni temps) : `analyze_line(texte, selection_marks=True)` reçoit le texte d'une ligne et rend un `LineElement` ou rien.
  Un élément a un genre (`ElementKind`, liste fermée : progression, question, choix, erreur, adresse web, adresse mail), le texte mis en forme qui s'en lit (traduit avec `_()`) et une valeur (le pourcentage d'une progression).
  Les deux genres d'adresse ne sont jamais rendus par `analyze_line` mais par `find_addresses` (le point suivant).
  `clean_line` rend la ligne nettoyée de son décor (cadres, suites de quatre signes `#`, `=`, `-`, `_`, `*`, `~` ou `.`, crochets vides), et `read_line` rend l'élément ou, à défaut, la ligne nettoyée : c'est ce que dit F4.
  Elle travaille sur le texte tel qu'il est dans la zone de sortie, donc de la même façon en mode CLI et en mode terminal.
  Elle laisse de côté une commande lancée (`# `) et retire « StdErr: » ; `> ` est la marque d'un choix en mode terminal, et celle d'une ligne envoyée en mode tubes (`selection_marks` faux), où la ligne n'est pas analysée.
  Les marques de l'application, `LAUNCH_PREFIX` et `SEND_PREFIX`, sont définies dans ce module.
  Seuls des chaînes et des nombres la traversent, pour qu'un module natif puisse aussi la faire.
  `presenters/line_reader.py` (`LineReader`) la dit par le centre d'annonces (`Announce.LINE_READ`, toujours dite) ; `ui/output_commands.py` lui donne la ligne du curseur de texte.
- **Les genres** se reconnaissent au texte seul, sans couleur ni attribut de cellule :
  - progression : un pourcentage de 0 à 100 (`50 %`, `50%`, `12,5 %`), une fraction avec une unité (`4,2/12 MB`, `11.0/11.0 kB`) ou entre crochets (`[3/10]`), une barre entre crochets avec au moins un signe plein (`[####....]` : le pourcentage se calcule), une suite de blocs (`━━━━`, sans valeur) ; le libellé qui précède est gardé ;
  - question : `[Y/n]`, `[o/N]` (la lettre en majuscule est la réponse par défaut), `(yes/no)`, `[1-3]`, une ligne de mot de passe (`Password:`), `Press any key`, `--More--`, une ligne qui finit par `?` (la fonction ne connaît pas le curseur du terminal, donc une ligne qui finit par `:` seule ne suffit pas) ; une question à laquelle la réponse est écrite sur la ligne n'en est plus une ;
  - choix sans marqueur : `cursor_on_text` (la fonction ne voit pas le curseur, l'appelant le dit : `cursor_is_on_line_text` dans `core/screen/text_search.py`) fait d'une ligne qui ne montre rien d'autre l'item sélectionné ; vu avec `Selection` ;
  - choix : un marqueur de sélection (`>`, `*`, `❯`, en mode terminal seulement), une case (`[x]`, `[ ]`, `(*)`), une option numérotée (`1)`, `[1]` ; pas `1.`, qui est une étape de texte) ;
  - erreur : une ligne qui commence par `error:`, `fatal:`, `failed:`, `warning:` (ou `[ERROR]`), `Traceback`, une exception Python (`ValueError: …`), ou qui contient `Access is denied`, `command not found` et leurs semblables ; un avertissement se dit « Avertissement ».
  La liste est un début, à ajuster sur des captures de vrais programmes (`specs/open-questions.md`, « Line analysis and activity »).
  Un choix marqué seulement par la vidéo inverse n'est pas trouvé : `marked_rows` dans `ScreenUpdate` n'est ajouté que si le texte ne suffit pas.
- **La veille d'activité** (`presenters/activity_watch.py`, `ActivityWatch`) : le drapeau d'activité et l'heure de la dernière vérification.
  `note` le lève après chaque mise à jour qui change du texte (`_show_output` du présentateur), `sent` fait ignorer l'écho de ce que l'utilisateur vient d'envoyer (0,3 s), `reset` l'oublie quand un programme démarre, et `check(maintenant, intervalle)` le baisse et dit s'il était levé, une fois par intervalle.
  Elle lit l'heure qu'on lui donne, donc elle se teste sans attendre ; elle ne reçoit ni texte ni écran.
- **Le signal** (`presenters/activity_signal.py`, `ActivitySignal`) décide à chaque tick (`SessionPresenter.tick`) ce que l'utilisateur entend : rien sans programme, ni quand la catégorie « Activité du terminal » est à « Aucune », ni avec le focus hors de la zone de sortie quand la case le demande ; sinon il prend la ligne du curseur de texte (`SessionView.caret_line`), l'analyse, dit l'élément (`Announce.ACTIVITY`) ou, avec « Messages ou bip », joue un bip (`AnnouncementCenter.beep`).
  Le centre d'annonces connaît le `Beeper` (`NullBeeper` par défaut, `RecordingBeeper` des tests, dans `tests/fakes/recording_sinks.py`) ; celui de Windows est `ui/beeper.py` (`WinsoundBeeper`).
  Les réglages sont `activity_interval`, `activity_only_in_output` et `activity_last_choice` de `Settings` ; `Settings.toggle_activity` fait Ctrl+B.
- **Le rejeu** (`tests/fakes/capture_replay.py`, `tools/replay_screens.py`) : les octets d'une capture de `tests/data/captures` sont donnés au modèle d'écran par petits morceaux (un morceau par tick, 50 ms simulées) ; l'outil, lancé avec le Python de `.venv` (`tools/replay_screens.py [--chunk 256] [nom ...]`), imprime une ligne par fait : les lignes qui ont quitté l'écran et les rangées modifiées à chaque pas.
  Il écrit après chaque ligne l'élément que l'analyse de ligne y reconnaît (` -> PROGRESS 'Downloading, 40 %'`), ce qui permet d'essayer une règle sur de vraies captures.
  Les tests de l'analyse de ligne rejouent les captures avec la même fonction (`replay`, `tests/core/screen/test_line_analysis_captures.py`).
  Les captures de l'analyse se refont avec `tools/capture_conpty.py` : `bar_cr`, `two_bars`, `questions`, `numbered_menu`, `glyph_menu`, `errors`, `pip_dry_run` (`pip install --dry-run`) et `winget_search`, qui n'installent rien.
- **Plus tard, peut-être** : un champ optionnel `marked_rows` (les rangées qui contiennent du texte en vidéo inverse) dans `ScreenUpdate`.
  La mesure est faite : pyte lit la vidéo inverse de ConPTY de façon fiable, mais un programme qui marque son choix par un glyphe ou une couleur n'est pas trouvé par ce champ (`specs/open-questions.md`, « Line analysis and activity »).
