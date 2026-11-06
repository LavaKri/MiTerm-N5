# Robustness: security, buffers, logs

## Security

- **Pas d'injection de commande.** Lancement direct sans shell (voir « Launching programs » dans `specs/architecture/transport.md`).
  La ligne tapée est découpée en programme et arguments, jamais concaténée avec une autre commande.
  Le futur réglage « interpréteur » sera un choix explicite de l'utilisateur.
- **Rien ne s'exécute implicitement.** Aucun programme n'est lancé au démarrage, depuis le fichier de réglages ou depuis la ligne de commande de MiTerm-N5, sans une action de l'utilisateur.
- **Secrets.** Le texte tapé n'entre jamais dans les journaux (il peut contenir un mot de passe).
  Aucun mot de passe stocké en clair.
  SSH : clés et agent du système, pas de stockage maison ; un mot de passe est demandé à chaque connexion, n'est ni enregistré ni journalisé, et ne reste en mémoire que le temps de la réponse.
- **Historique des lignes tapées.** Il garde, en mémoire seulement, toute ligne envoyée à un programme qui tourne, sauf un message masqué (une ligne tapée à un programme qui demande un mot de passe, sans la case « Masquer le message », y reste donc).
  **Une version future ne devra jamais l'enregistrer** (fichier, réglages, journal) : il peut contenir des informations sensibles.
  Il en va de même du brouillon de la saisie sur plusieurs lignes : en mémoire seulement, vidé à l'envoi.
- **Fichiers.** Les réglages et les journaux vivent dans le dossier de l'utilisateur (`platformdirs`), jamais dans un dossier partagé.
  Écriture atomique ; un fichier corrompu donne une erreur annoncée, pas un plantage.
- **Sortie non fiable.** La sortie d'un programme est du texte, jamais interprété.
  Les séquences d'échappement et les caractères de contrôle autres que le saut de ligne et la tabulation sont retirés ou neutralisés avant l'affichage, sinon un programme pourrait déformer l'affichage ou ce que dit le lecteur d'écran.
- **Processus enfants.** Le programme tourne dans un objet Job Windows (`core/transport/process_tree.py`).
  Un arrêt demandé par l'utilisateur termine tout l'arbre, même quand le programme lui-même est déjà terminé mais a laissé un enfant.
  Tant que le programme tourne, fermer le job tue ses processus : si MiTerm-N5 se termine ou plante, rien ne continue à tourner à l'insu de l'utilisateur.
  Une fois le programme terminé normalement, cette règle est levée : un processus qu'il a laissé volontairement (un éditeur ouvert par une commande) continue.
  Sans job (Windows l'a refusé), seul le programme est arrêté, et un avertissement est journalisé.
- **SSH** (`specs/architecture/connection.md`).
  Les clés d'hôte sont vérifiées par `ssh` ; un hôte inconnu est refusé sauf si l'utilisateur confirme dans un dialogue natif qui montre l'empreinte, et une clé modifiée est toujours refusée.
  La cible d'une connexion est validée (pas de tiret au début) et passée comme un argument à part, jamais dans une chaîne de commande.
  Le tube du programme de saisie est réservé à l'utilisateur courant par son descripteur de sécurité (même les administrateurs n'y entrent pas), refuse le réseau, ne peut pas être créé si son nom est pris, et demande un jeton aléatoire ; les variables qui le décrivent ne sont que dans l'environnement du processus `ssh`.
  Une connexion choisie ne se lance jamais toute seule.

## Output filter (contract)

Le filtre est défini par un contrat dans `src/n5terminal/core/screen/output_filter.py`, pour que la politique change sans toucher au code qui l'applique :
- `FilterRules` (données) : quels caractères de contrôle sont gardés (par défaut la tabulation et le saut de ligne), ce que signifie un retour chariot seul (`REPLACE_LINE` : garder le dernier état de la ligne, comme pour une barre de progression ; ou `NEW_LINE`), s'il faut retirer les séquences d'échappement, les contrôles C1, les marques de direction du texte (`U+202A` à `U+202E`, `U+2066` à `U+2069`) et les caractères de largeur nulle (`U+200B`, `U+FEFF`), et ce qui remplace un caractère retiré (`DROP` rien, ou `MARK` une marque visible).
- `OutputFilter` (`Protocol`) : `feed(text)` renvoie une liste de `FilteredChunk` et `finish()` renvoie ce qui est retenu.
  Le filtre garde un état entre les appels (une séquence ou un retour chariot coupé entre deux morceaux de texte) ; une instance par flux et par session.
- `FilteredChunk(text, replaces_current_line)` : du texte à ajouter, ou à mettre à la place de la dernière ligne inachevée.
- Toujours retiré : la séquence d'échappement entière (`ESC[31m` ne laisse rien, pas `[31m`), jamais seulement `ESC`.
  `CR LF` est un simple saut de ligne.
  Le caractère de remplacement `U+FFFD` (erreur de décodage) est gardé.
- Par défaut : `DROP`, puisqu'une marque visible serait lue à voix haute par le lecteur d'écran.
- L'implémentation est `DefaultOutputFilter` (`core/screen/default_output_filter.py`), testée cas par cas.
  Un retour chariot revient au début de la ligne et ce qui suit l'écrase, comme dans un terminal (`abcdef\rxy` affiche `xycdef`).
  Une séquence inachevée de plus de 4096 caractères est abandonnée.

## Buffers

**Threads pour l'affichage.** Trois étapes :
1. Le thread du transport lit la sortie et la donne aussitôt au décodeur et au filtre (pipes) ou à pyte (terminal), sur ce même thread.
   Quand pyte prend du retard, la lecture ralentit et ConPTY retient la sortie : un frein naturel, aucune donnée perdue.
2. Un point d'échange entre ce thread et l'interface : les lignes qui vont à la partie fixe s'accumulent (toutes remises, dans la limite de lignes) ; pour la partie vivante, seuls le dernier état et l'ensemble des lignes modifiées sont gardés (les états intermédiaires sont sautés).
   Un verrou court, aucun travail effectué pendant qu'il est tenu.
3. Le thread de l'interface prend ce qui s'est accumulé toutes les 50 à 100 ms et met à jour le contrôle de texte ; il n'exécute jamais pyte.

Seul le thread du transport touche l'écran pyte ; l'interface reçoit des copies figées (des chaînes).
Précautions contre le GIL (pyte en Python pur fait concurrence au thread de l'interface pendant un flot) : la sortie est donnée par blocs bornés (par exemple 16 Ko), ce qui laisse l'interface tourner entre deux blocs ; un test de charge (un programme simulé qui écrit plusieurs mégaoctets) mesure le temps de pyte et la plus longue attente de l'interface.
Si le résultat est mauvais, l'émulation passe dans un processus séparé derrière le même point d'échange (qui ne porte déjà que des copies figées) ; plus difficile dans un exe empaqueté, donc seulement si la mesure le justifie.

**Implémentation** (`core/screen/display_exchange.py`) : `DisplayExchange` fusionne les `ScreenUpdate` publiés par le thread qui alimente (les lignes fixes s'accumulent jusqu'à une limite, les plus anciennes abandonnées et comptées dans `DisplayBatch.dropped_lines` ; une ligne garde son dernier état ; un remplacement reste un remplacement et contient alors toutes les lignes) et les remet à l'interface en un seul `take()`, qui renvoie `None` quand rien n'est arrivé.
Le verrou couvre quelques affectations ; les tuples sont construits en dehors.
`ScreenPump` coupe la sortie en blocs de 16 Ko, alimente le modèle et publie après chaque bloc ; `resize` peut venir d'un autre thread.

**Mesure** (`tools/load_screen.py`, 4 Mo, morceaux de 4 Ko, une machine, un thread qui tient lieu d'interface et se réveille toutes les 50 ms ; ce n'est pas une vraie boucle wx) :
- pyte met environ 5 s pour 4 Mo : **0,8 à 1 Mo/s** (lignes simples, lignes colorées, redessins plein écran, pareil).
  Le plus long bloc donné : 6 ms.
- Le thread de l'interface se réveille **13 ms en retard en moyenne, 22 ms au plus** pendant que pyte tourne (0,3 ms et 0,6 ms seul) : l'attente du GIL.
  Aucun gel, rien de perdu, aucune ligne abandonnée.
- La taille des blocs ne change rien à cette attente (2 Ko ou 16 Ko) ; l'intervalle de changement de thread change un peu (1 ms au lieu de 5 ms : 8 ms en moyenne, 17 ms au plus).
- Conclusion pour l'instant : l'interface reste réactive ; la limite est le débit (un déversement de 50 Mo prendrait environ une minute à émuler, la pseudo-console retenant la sortie entre-temps).
  La version 1 reste en Python ; un module d'écran en Rust est prévu pour la version 2, pour gagner en réactivité sur les PC modestes (voir `specs/roadmap.md`).

- **Lecture.** Un thread de lecture par flux (stdout, stderr), lectures par blocs (4 à 64 Ko), jamais sur le thread de l'interface.
  Les données atteignent l'interface par `wx.CallAfter`.
- **Débit.** Les mises à jour sont groupées (par exemple un lot toutes les 50 à 100 ms), pas un `CallAfter` par ligne, pour qu'un programme qui écrit très vite ne gèle pas l'interface.
- **Taille de la zone de sortie.** Limitée en lignes (défaut à décider, ajustable).
  Au-delà de la limite, les plus anciennes lignes sont abandonnées et l'utilisateur en est informé une fois.
  Sans limite, `ping -t` ou un gros journal consommerait toute la mémoire.
  Le message (« La sortie ne garde que les 10 000 dernières lignes : les plus anciennes sont abandonnées. ») est dit une fois par sortie, et de nouveau si la sortie est effacée puis dépasse encore la limite.
  Il fait partie des messages toujours dits, sans catégorie à régler.
  La zone de sortie dit combien de lignes la limite a retirées (`OutputArea.show`) et le présentateur décide de l'annonce (`SessionPresenter._report_dropped`).
- **Lignes très longues.** Coupées à une longueur maximale (défaut à décider).
- **Décodage.** Décodeur incrémental : un caractère UTF-8 coupé entre deux blocs n'est pas corrompu.
- **Entrée.** Écrite sur stdin depuis un thread dédié avec une file bornée, pour que l'interface ne se bloque pas quand le programme ne lit pas.
- **Contre-pression.** Si l'interface prend du retard, une file bornée retient les données ; au-delà de la limite, les plus anciennes sont abandonnées, avec un message.
  Le point d'échange compte ces lignes (`DisplayBatch.dropped_lines`) et le message (« 5 lignes de sortie ont été perdues : elles sont arrivées plus vite que la fenêtre ne pouvait les montrer. ») est dit chaque fois, puisque ces lignes ne sont ni dans la zone de sortie ni dans l'export.

## Logs

- **Journal de diagnostic de l'application** (`logging`) :
  - Fichier dans le dossier de données de l'utilisateur, avec rotation par taille (par exemple 5 fichiers de 1 Mo).
  - Niveau fixé par `--log-level` (`DEBUG`, `INFO`, `WARNING`, `ERROR`), `INFO` par défaut, `DEBUG` en mode Develop (`--develop`).
  - Y entrent : le démarrage et la version, le lancement d'un programme (son nom), l'état du transport, la fin d'un programme avec son code (au niveau `INFO`), les échecs de lancement, les erreurs et exceptions avec leur trace.
    Le déroulement de la session est donc dans le journal sans option à passer ; `--log-level WARNING` ne garde que les avertissements et les erreurs, `DEBUG` ajoute les arguments des commandes.
    Les erreurs montrées à l'utilisateur (`Feedback.show_error`) sont aussi journalisées, pas seulement annoncées.
  - Au niveau `DEBUG`, chaque commande reçue (son nom, `Command: HISTORY`) et chaque boîte modale ouverte puis fermée (`Dialog opened: SecretDialog`, `Dialog closed: SecretDialog (5100)`) sont écrites : un arrêt sans exception laisse ainsi la dernière action dans le journal.
  - En mode Develop seulement, `faulthandler` écrit la pile Python de tous les threads dans `faulthandler.log`, à côté du journal, quand le processus meurt d'une erreur native (une telle fin ne lève aucune exception Python, donc le journal n'en dit rien).
    Le fichier ne contient que des noms de fonctions et de fichiers, jamais de valeurs ; il est gardé d'un démarrage à l'autre et recommencé au-delà de 1 Mo.
    Avec un lecteur d'écran allumé il reçoit aussi des erreurs système bénignes que Windows gère lui-même (`0x8001010d`) : c'est pourquoi il n'est pas activé pour les utilisateurs.
  - Le code est dans `core/config/logging_setup.py`, la rotation est faite par `RotatingFileHandler` (5 fichiers de 1 Mo : le courant et quatre anciens).
  - Un dossier non inscriptible ne donne aucun journal, sans erreur ni autre emplacement.
  - Le menu Aide > Ouvrir le dossier des journaux l'ouvre dans l'explorateur ; il n'y a pas de visionneuse dans l'application.
  - N'y entrent **jamais** : le texte tapé, la sortie des programmes, les arguments de la commande lancée (ils peuvent contenir des secrets).
    Le nom du programme est journalisé, ses arguments seulement à un niveau `DEBUG` explicite.
- **Pas de journal de session.** La conversation n'est pas écrite sur le disque au fil de l'eau.

## Export

À la place d'un journal de session, le menu « Fichier » a un item d'**export** (par exemple « Exporter la sortie… ») qui enregistre le contenu de la zone de sortie dans un fichier texte choisi avec un dialogue d'enregistrement natif (UTF-8).
- Il exporte ce que contient la zone de sortie, donc les lignes abandonnées par la limite de taille ne sont pas dans le fichier.
- Le fichier peut contenir des secrets tapés ou affichés pendant la session ; le dialogue le dit, dans son titre, que le lecteur d'écran lit à l'ouverture.
- Fait seulement à la demande de l'utilisateur, jamais automatiquement.
- Le dialogue s'ouvre dans le dossier de travail de la session et propose `sortie.txt` ; il demande avant de remplacer un fichier.
- Le fichier est en UTF-8, avec des sauts de ligne Windows, et sa dernière ligne se termine par un saut de ligne.
- Après l'écriture, « Sortie exportée vers sortie.txt. » est dit (le nom du fichier, pas son chemin).
  Si le fichier ne peut pas être écrit, une boîte d'erreur dit pourquoi (`ExportError`).
- La commande est grisée tant que la sortie est vide.
- Le code est dans `core/session/output_export.py` (l'écriture) et `ui/output_commands.py` (le dialogue).
