# Manual checks

Ce que seule une personne avec un lecteur d'écran peut vérifier, étape par étape.
Les questions de conception sont dans `specs/open-questions.md` ; ici sont les vérifications faites et celles qui restent.
Une vérification est retirée quand elle est réglée, et ce qu'elle a décidé est écrit là où le comportement est décrit.

Méthode : lancer `Start.bat` avec le lecteur d'écran actif.

## Steps 6a and 6b (window, announcements)

À vérifier :
- Si un raccourci vers un item de menu **grisé** atteint la fenêtre et annonce pourquoi il est refusé (essayer Ctrl+Pause sans programme en cours).
  Le raccourci reste écrit dans le texte du menu ; si l'accélérateur avale la touche, trouver un autre moyen de garder les deux.
- Si un message est prononcé **une seule fois** et ne cache pas la ligne en cours de lecture (la notification demande « importante, la plus récente » : une nouvelle remplace celle qui attend).
- Si la fenêtre cachée des annonces apparaît dans la navigation objet de NVDA (une fenêtre appelée « MiTerm-N5 »), et si Tab l'atteint jamais (il ne doit pas).
- Les tests de la fenêtre qui font tourner une vraie boucle d'événements affichent « Windows fatal exception: code 0x8001010d » (`RPC_E_CANTCALLOUT_ININPUTSYNCCALL`, une erreur COM de première chance : `faulthandler` la rapporte, COM l'attrape) ; ils réussissent.
  Elle vient d'un lecteur d'écran allumé, pas de l'application (`specs/testing.md`, « Screen reader during the tests »).
  Constaté le 2026-11-03 : elle s'affiche aussi avec `tests/ui/test_feedback_dialogs.py` seul, dans le nettoyage qui suit le test du dialogue de texte (`Feedback.show_text`, qui crée un champ `TE_RICH2`).
  Elle n'est donc pas propre aux tests avec de vrais programmes : elle apparaît quand la boucle d'événements tourne après la création d'un champ `TE_RICH2`.
  La cause n'est pas trouvée ; ne pas désactiver `faulthandler` de pytest, qui perdrait aussi les vrais vidages en cas de plantage.
  Une fenêtre wx nue qui ne contient qu'un contrôle `TE_RICH2` la provoque ; le même contrôle sans `TE_RICH2` non ; elle apparaît aussi quand la sortie des annonces est désactivée ; 50 notifications UI Automation de suite réussissent pendant qu'elle se produit.
  Pas encore vérifié : qu'elle disparaisse quand aucun lecteur d'écran ne tourne.
  À vérifier avec la vraie fenêtre : qu'elle ne se voie pas sous forme de retard ou d'une annonce manquante.

## Foreground after a launch

Mesuré le 2026-11-03 avec une fenêtre de test au premier plan : le verrou empêche la console cachée de prendre le premier plan, et la garde le reprend sans le verrou.
- Avec NVDA, lancer une commande dans le profil PowerShell (par exemple `wsl -l`) : le focus reste dans l'application, le raccourci qui lit le titre de la fenêtre dit « MiTerm-N5 » et non « pythonw », Tab fonctionne, sans Alt+Tab.
- Le faire plusieurs fois de suite, et aussi avec un programme TUI qui demande la restauration de sa fenêtre (Codex).
- Si le focus se perd quand même : lire le dossier des journaux (Aide > Ouvrir le dossier des journaux) ; « The foreground could not be taken back » dit quelle fenêtre le tient.

## Shortcuts as menu accelerators

- Avec NVDA, en français : chaque raccourci écrit dans un menu fonctionne (F1, F3, Maj+F3, F4, F5, Maj+F5, F6, Maj+F6, F7, Ctrl+D, Ctrl+I, Ctrl+R, Ctrl+Espace, Alt+Début…) et les noms sont ceux de l'application (Maj, Début, Entrée), pas ceux de wx (Majuscule, Dossier personnel).
- Un raccourci d'un item grisé annonce sa raison et ne fait rien d'autre (Maj+Entrée sans programme ne valide pas le champ de commande).
- Ctrl+Pause arrête le programme (Windows l'envoie comme Ctrl+Arrêt).
- Un raccourci d'envoi (Alt+Bas pour « Envoyer Flèche bas », donné dans Préférences > Raccourcis) envoie la touche au programme sans déplacer le curseur de texte de la zone de sortie ; si le curseur bouge, vérifier d'abord avec NVDA suspendu (c'est lui qui le déplace).

## Step 6d (export, search, dropped lines)

- Fichier > Exporter la sortie… (Ctrl+S) : le titre du dialogue, lu à l'ouverture, parle des secrets ; le focus est sur le champ du nom, qui propose `sortie.txt` ; après Entrée, rien n'est annoncé (la boîte de sélection de fichier suffit), et le focus revient où il était.
- Le fichier s'ouvre dans le bloc-notes avec ses accents et ses lignes.
- Édition > Rechercher dans la sortie… (Ctrl+F) depuis le champ de commande : la boîte annonce son champ « Mot à rechercher » ; un mot absent dit « Pas d'occurrence suivante » et le focus reste dans le champ de commande.
- Avec le curseur de texte remis au début de la sortie (Ctrl+Début dans la zone de sortie), un mot présent met le focus dans la zone de sortie, et la ligne est lue **une seule fois** (pas la ligne puis le mot).
- F3 et Maj+F3 avancent et reculent d'une occurrence ; sans mot cherché, ils ouvrent la boîte.
- Depuis la fin (cas habituel), Ctrl+F ne trouve rien et Maj+F3 atteint la dernière occurrence (décidé, `specs/decisions.md`) : vérifier que le message est clair à l'écoute.
- Un flot long (par exemple 20 000 lignes avec la limite à 1 000) : le message sur la limite est dit une fois, sans couvrir la lecture en cours.

## Step 6g (terminal cursor)

- Terminal > Déplacement > Aller au curseur du terminal (Ctrl+G), avec un shell Cmd ou PowerShell à son invite : le focus va dans la zone de sortie, le curseur de texte est derrière l'invite, et la ligne est lue une seule fois.
- Terminal > Vue terminal seule, annoncée cochée ou non cochée : cocher puis décocher, le curseur de texte reste sur la bonne ligne.
- Vue terminal seule décochée, lancer Codex puis le quitter : la zone de sortie garde sa dernière vue, que l'on lit avec les flèches.
- Les trois items du sous-menu Déplacement restent actifs dans les deux vues, et le menu Terminal est annoncé entre Profil et Aide (Develop, en mode Develop, est entre Terminal et Aide).
- Alt+Début et Alt+Fin, depuis le champ de commande puis depuis la zone de sortie : le focus va dans la zone de sortie, la ligne est lue une seule fois, et la touche n'ouvre aucun menu (Alt seul ne doit rien déclencher).
- Dans un programme qui cache son curseur (invite moderne), voir où Ctrl+G met le curseur de texte.

## Develop mode

- Lancer avec `--develop` : le menu Develop est entre Terminal et Aide, absent sans l'option.
- Develop > Programmes de test : le sous-menu liste les fichiers de `DevelopMode\testprograms\`, ou « (aucun) » grisé.
- Develop > Catalogues… : le focus arrive sur la liste ; Gauche et Droite changent le contenu des lignes sans perdre la ligne, le lecteur d'écran lit la nouvelle ligne ; le champ est lu avec son étiquette (« Message » ou « Message en français ») et dit lecture seule pour les identifiants.
- Retirer un champ `{nom}` d'une traduction : OK refuse et le message d'erreur est lu.
- « À propos » : la zone de texte est lue à l'ouverture.

## Sending keys

- Menu contextuel du champ de commande (touche Application, puis Maj+F10) : le focus reste dans le champ, le menu lit Historique, Saisie sur plusieurs lignes…, Couper, Copier, Coller, Tout sélectionner (Saisie sur plusieurs lignes… ouvre la boîte) ; Échap le ferme et le focus revient au champ.
- Menu contextuel de la zone de sortie : Copier, Tout sélectionner, Envoyer ; Échap le ferme et le focus revient à la zone.
- Maj+Échap et Maj+Entrée envoient Échap et Entrée à un programme TUI (avec `Commands`), et annoncent « Envoie … » ; sans programme TUI, Maj+Entrée dit pourquoi au lieu d'envoyer la ligne.
- Session > Envoyer une touche et le même sous-menu du menu contextuel : grisés sans programme, ou avec un programme en mode CLI ; actifs avec un programme en mode TUI.
- Avec `Commands` en TUI (Develop > Programmes de test) : chaque touche envoyée est nommée par le programme, et l'annonce « Envoie … » est lue une seule fois.
- Les flèches avec un programme qui demande le mode application (`Échap [ ? 1 h`) arrivent sous la forme `Échap O A`.
- Préférences > Raccourcis : le choix « Commandes à afficher » (Principal, Envoi de touche) est lu ; donner Ctrl+Alt+touche à une touche envoyée ne gêne pas le lecteur d'écran.

## Status bar, title and session information

- La barre d'état lit trois champs dans l'ordre : « Ligne 3 sur 40 », l'état, « Colonne 5 sur 80 ». Avec un programme TUI, le total des colonnes est la largeur de l'écran ; avec un programme CLI, la longueur de la ligne.
- Le titre de la fenêtre dit « MiTerm-N5 : profil libre dans … » à l'ouverture de la fenêtre (Alt+Tab) ; il change avec le profil et avec le dossier.
- Une commande lancée en CLI se lit en deux lignes : « # commande » puis « Depuis C:\dossier\ » ; le texte envoyé à un programme en cours n'en a pas.
- Session > Informations sur la session… : la boîte lit une ligne par information, avec le chemin complet du dossier et le type de session (normal, portable, develop).

## Focus after sending

- Lancer une commande en CLI (Entrée dans le champ) : le focus passe dans la zone de sortie et le lecteur d'écran lit la ligne `# commande`.
- Envoyer du texte à un programme en cours, ou une touche : le focus passe dans la zone de sortie, le curseur de texte ne bouge pas, et le lecteur d'écran lit la ligne du curseur.
- Tab depuis la zone de sortie ramène au champ de commande.

## Hiding a message

Avec un programme qui demande un secret (`python -c "import getpass; getpass.getpass()"`, ou le profil `PowerShell` et la commande qui ajoute une clé à un serveur).
- Au repos, la case « Masquer le message » est grisée : Tab passe du champ au bouton Envoyer. Pendant un programme, Tab passe du champ à la case, puis au bouton.
- Cocher la case : le lecteur d'écran dit « coché ». Revenir dans le champ (Maj+Tab) et taper : les lettres ne sont **pas** lues (ni dites « étoile » une à une, à voir), et le champ est annoncé comme protégé ou « mot de passe ».
- Entrée : le secret est envoyé, le focus passe dans la zone de sortie, la case est décochée (Tab, Tab pour le vérifier) et le champ est de nouveau lisible pour la commande suivante.
- Avec un programme servi par des tubes, la sortie dit `> (message masqué)` et jamais le secret ; Ctrl+Espace ne le propose pas.
- Cocher la case avec du texte déjà tapé le masque aussitôt ; la décocher le montre de nouveau.

## Starter profiles

- Au premier démarrage, le menu Profil > Choix profil propose `git`; le choisir puis Ctrl+Espace liste les six commandes, écrites sans le programme (« Git status » se lit, `status` s'écrit).
- Avec le profil `git` : le champ s'appelle « git » (le nom du profil) ; `status` puis Entrée lance `git status` (la sortie écrit `# Git`) ; un champ vide lance `git` seul.
  Pendant l'exécution le champ s'appelle « Message » ; avec `CMD` ou le profil Libre, « Commande ».
- Édition > Saisie sur plusieurs lignes… (Ctrl+M depuis le champ de commande) : la boîte annonce son titre et son champ « Lignes à envoyer », Entrée fait une nouvelle ligne, Tab atteint « Envoyer », Échap ferme sans envoyer ; Ctrl+M ne fait pas Entrée dans le champ.
  Avec le profil `PowerShell`, envoyer une boucle `foreach` sur plusieurs lignes : elle s'exécute en un titre ; la liste de Ctrl+Espace la lit « première ligne (N lignes) » et la choisir rouvre la boîte.
- Lecture confortable (Terminal > Lecture confortable > Filtrage de ligne…) : dans la sortie d'un shell PowerShell puis Cmd, Ctrl+Alt+Haut et Ctrl+Alt+Bas annoncent la ligne filtrée (« Commande dir » pour `C:\chemin>dir`), une seule fois (le curseur arrive sur la ligne, mais NVDA ne la relit pas entière) ; avec une connexion, sans `utilisateur@hôte:~$ ` ; NVDA ne prend pas Ctrl+Alt+flèches pour sa navigation de tableau ni Windows pour une rotation de l'écran.
  Dans la boîte d'un motif, taper une ligne d'essai puis F1 depuis un autre champ : la ligne telle qu'elle serait annoncée est dite ; Tab atteint le champ « Résultat (F1 pour entendre) » et le texte s'y lit.
  Avec une invite `utilisateur@hôte:~$` sans commande, la ligne est annoncée « invite » (ou par le remplacement du motif).
  Avec « Lecture confortable pour les déplacements par titres » cochée, T et les touches 1 à 6 annoncent le titre d'une commande sans son invite.
  Terminal > Lecture confortable > Filtrage de ligne… : la liste est lue dans son ordre, Monter et Descendre changent l'ordre, « Inclure la mise en forme » ajoute « Question : … » à la ligne annoncée.
- Rechercher dans la sortie… (Ctrl+F) : le champ s'appelle « Recherche du texte » et les cases « Chercher vers le haut » et « Expression régulière » se lisent comme des cases ; une expression invalide est refusée avec sa raison ; F3 et Maj+F3 répètent la recherche comme la dernière faite depuis la boîte.
- Le dialogue de profil de `CMD` n'offre que le type « Shell » ; passer l'interpréteur à « Aucun » offre « Commande de lancement » et « Commande du programme », sans perdre de commande.
- Profil > Définir les variables… propose « Source » et « Message » ; après les avoir remplies, la liste montre `git add fichier.txt` et `git commit -m "mon message"`.
- Supprimer `git` puis relancer : il ne revient pas.
- Le profil `ssh-keygen` (mode Develop, ou après un nouveau démarrage) : `-t ed25519 -C "{comment}"` crée une clé dans un dossier d'essai (le répondre à « Enter file in which to save the key » avec un chemin d'essai, jamais le `.ssh` réel) ; les questions de la phrase secrète se lisent et se répondent avec la case « Masquer le message ».
- Profil `PowerShell` : les trois commandes de clés d'un serveur, **écrites mais jamais exécutées** (un essai automatique a été refusé le 2026-11-04 : il modifiait `authorized_keys`).
  À essayer à la main sur le serveur de test : donner `{name}` = `TestSSH` et `{ip}` = `127.0.0.1 -p 2222` (les options de `ssh` peuvent suivre l'adresse).
  Points à vérifier : les guillemets passent par PowerShell 5.1 et par PowerShell 7 (`'\r'`, `'{value1}d'`) ; la clé ajoutée n'a pas de `^M` en fin de ligne (`cat -A ~/.ssh/authorized_keys`) ; elle est listée avec son numéro de ligne, puis retirée par ce numéro ; `authorized_keys.bak` existe ensuite ; une valeur de `{value1}` non remplie échoue sans rien modifier.

## Logs

- Aide > Ouvrir le dossier des journaux : l'explorateur s'ouvre sur le dossier, et le focus y passe ; sans journal, la boîte le dit et le focus revient où il était.
- Lancer sans option : le fichier contient le démarrage, la version, un lancement de programme et sa fin, et aucun texte tapé ni sortie de programme.

## SSH

**Le serveur de test** est un `sshd` dans Debian sous WSL 2, mis en place le 2026-11-03 ; à refaire sur une autre machine :
1. `wsl --install -d Debian --no-launch` (administrateur ; un redémarrage si WSL n'était pas activé, puis relancer la commande), vérifier avec `wsl -l -v` (Debian, version 2).
2. En `root`, par `wsl -d Debian -u root -- commande` (sous Git Bash, préfixer `MSYS_NO_PATHCONV=1` : il transforme `/bin/bash` en chemin Windows) :
   - `apt-get update`, puis `apt-get install -y openssh-server` ;
   - `useradd -m -s /bin/bash TestSSH`, puis un mot de passe de test choisi (`chpasswd`) ;
   - un fichier `/etc/ssh/sshd_config.d/10-miterm-test.conf` avec `Port 2222`, `ListenAddress 127.0.0.1` et `PasswordAuthentication yes` ;
   - `sshd -t`, puis `systemctl restart ssh`.
3. **WSL arrête la distribution dès qu'aucun processus n'y est attaché**, et `sshd` avec elle (« Connection refused »).
   Garder ouverte, dans une autre session de MiTerm-N5, la commande `wsl -d Debian -u root -- sleep infinity` ; un processus lancé en arrière-plan par un outil ne survit pas à la fin de son tour.
4. Essai : `ssh -p 2222 TestSSH@127.0.0.1`.
   Pour tout arrêter : `wsl --shutdown`.

**Avant que la connexion existe**, essayé à la main sur ce serveur le 2026-11-03 (`ssh.exe` dialogue dans le terminal, sans dialogue de MiTerm-N5) : la connexion et l'authentification fonctionnent dans une seconde instance de MiTerm-N5 ; ce que NVDA lit n'a pas été noté.

**Essayé à la main le 2026-11-04** contre ce serveur (sans noter ce que lit le lecteur d'écran) : les dialogues de la clé d'hôte et du mot de passe, le refus d'un mot de passe, Se déconnecter et Ctrl+Pause, le grisage du menu, la case « Masquer le message », puis la connexion par clé (clé créée avec le profil `ssh-keygen`, posée avec la commande d'ajout de `PowerShell`) : « Debian » se connecte sans dialogue de mot de passe.
Rappels : `sshd` coupe une connexion qui ne s'authentifie pas en 120 s (`LoginGraceTime`), donc taper le mot de passe vite ; le profil `PowerShell` veut `ip` = `127.0.0.1 -p 2222` pour ce serveur ; la commande de suppression de `PowerShell` demande `value1` (le numéro de ligne de `cat -n`), sinon elle part avec `{value1}`.

**À vérifier, la connexion étant construite** :
- Se connecter depuis le menu Connexion : « Connexion… », « Authentification… » puis « Connecté à… » sont annoncés, sans répétition.
- La question de la clé d'hôte : le dialogue s'ouvre avec le focus dans le texte, qui se lit ligne par ligne avec l'empreinte ; « Annuler » est le bouton par défaut ; « Faire confiance et continuer » enregistre la clé (une seconde connexion ne la redemande pas).
- Le mot de passe : le champ est masqué, son nom reprend la question ; un mauvais mot de passe rouvre le dialogue, et Annuler arrête sans le rouvrir.
- Une clé d'hôte modifiée (changer la ligne de `known_hosts` du serveur) : l'erreur est annoncée comme telle, et le cadre de `ssh` est lisible dans la sortie.
- Un délai dépassé, une connexion refusée : annoncés comme une erreur de connexion, avec le texte de `ssh` dans la sortie.
- Le menu Connexion se lit dans l'ordre Choix connexion, Se connecter, Se déconnecter, Ajouter…, Modifier…, Supprimer, Client SSH… ; les items grisés disent leur raison.
- Les dialogues de `ssh` : le titre dit « Connexion à prod » (« Connexion prod : mot de passe » pour le mot de passe) et la première ligne la cible et le port ; la clé d'hôte se lit ligne par ligne (l'empreinte est sur la deuxième) et « Annuler » est le bouton par défaut ; le mot de passe se tape dans un champ que le lecteur d'écran ne lit pas.
- Ctrl+Fin atteint la ligne « Déconnecté (code n). » après l'écran du serveur, Alt+Fin s'arrête avant elle.
- Informations sur la session : les lignes Connexion, Cible, État de la connexion (avec « depuis 12 min »), Client OpenSSH.
- Entrée dans le champ avec une connexion choisie l'ouvre ; la ligne tapée part une fois connecté.
- La sortie à la connexion : le focus est sur `# SSH nom`, la ligne « Vers … » se lit dessous, et la touche 1 ou T atteint ce titre.
- Le titre de la fenêtre dit « … sur SSH nom (non connecté) » avant et après la connexion, et « … sur SSH nom » une fois connecté (Alt+Tab pour l'entendre).
- Dans le shell du serveur : le focus suit les règles de « Focus and caret », Ctrl+Pause ferme la connexion, `exit` aussi (« Déconnecté (code 0) » annoncé et écrit à la fin de la sortie), et un profil choisi avant ou après tape ses commandes dans le shell du serveur.
- La coupure du réseau (arrêter `sshd` brutalement) est annoncée en 45 s au plus, y compris quand la fenêtre n'a pas le focus ; au retour par Alt+Tab, le titre dit « (non connecté) ».
- L'exécutable de saisie ne fait apparaître aucune fenêtre et le focus ne bouge pas.
  Mesuré le 2026-11-04 avec `n5terminal-askpass.exe` (surveillance des fenêtres visibles et du premier plan) ; à refaire avec `MiTerm-N5-askpass.exe` une fois empaqueté.

## Data modes (local and portable)

À essayer à la main, à la première version empaquetée :
- Mode local : les réglages sont dans `%APPDATA%\MiTerm-N5\settings.json`, le journal dans `%LOCALAPPDATA%\MiTerm-N5\Logs\`.
- Mode portable : avec le fichier `portable` à côté de l'exécutable sur une clé, rien n'est écrit dans `%APPDATA%` ni `%LOCALAPPDATA%` après un tour complet (démarrage, changement de dossier, nouvelle session, fermeture).
- Une clé verrouillée en écriture : l'application démarre, et dit à la fermeture que les réglages n'ont pas pu être enregistrés.

## Preferences, page General

- Fichier > Préférences… s'ouvre, le focus est sur l'onglet Général, que le lecteur d'écran annonce.
- Tab entre dans la page : la langue, puis les lignes conservées, puis la case « Maximiser la fenêtre au démarrage » (annoncée cochée ou non cochée), puis le bouton d'association, puis les boutons OK et Annuler ; chaque champ est annoncé avec son nom.
- Décocher la case, valider, relancer : la fenêtre s'ouvre à sa taille normale ; cochée, elle s'ouvre maximisée.
- Entrée valide, Échap annule, et le focus revient où il était.
- Changer le nombre de lignes s'applique aussitôt ; changer la langue le dit, et ne s'applique qu'au prochain démarrage.

## Preferences, page Announcements

- Ctrl+Tab (ou Ctrl+Page suivante) passe de l'onglet Général à l'onglet Annonces, et le nom de l'onglet est annoncé.
- La « Sortie des annonces » est le premier champ de la page.
- La liste est lue ligne par ligne, par exemple « Session, réglages, Message », dans l'ordre alphabétique.
- Changer la destination sous la liste met la ligne à jour, et la liste garde sa position.
- Après OK, une annonce de la catégorie changée va bien à la nouvelle destination (par exemple « Aucune annonce » : plus rien n'est dit pour cette catégorie).

## Preferences, page Shortcuts

- La liste est lue ligne par ligne, par exemple « Arrêter le programme, Ctrl+Pause ».
- Le champ sous la liste annonce le raccourci de la commande choisie, et lire son nom suffit à savoir qu'on y appuie sur une touche.
- Appuyer sur une combinaison la donne à la commande, et la ligne de la liste suit.
- Un raccourci refusé fait dire pourquoi ; Tab quitte le champ dans tous les cas.
- Après OK, le menu affiche le nouveau raccourci, et la touche fait bien la commande, sans redémarrage.
