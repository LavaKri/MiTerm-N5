# Glossaire

Les concepts propres à MiTerm-N5, pour désigner les mêmes choses de la même façon.
Une entrée : le nom du code, le terme français, une définition.
Les entrées sont triées par nom du code.
Les mots courants (`disabled`, `buffer`, `prompt`...) n'y figurent pas.
Un concept nouveau s'ajoute ici avant d'être employé dans les specs.

- `activity`, activité.
  Un changement du texte de la sortie d'un programme, quel qu'il soit ; l'application ne le comprend pas, elle sait seulement qu'il a eu lieu.
- `ActivityWatch`, veille d'activité.
  Ce qui tient le drapeau d'activité, le vérifie à l'intervalle choisi et dit ce qu'il faut signaler (un bip, ou la ligne mise en forme d'un élément reconnu).
- `activity flag`, drapeau d'activité.
  Un booléen levé par chaque mise à jour de l'écran qui change du texte, et baissé à chaque vérification.
- `AnnouncementCenter`, centre d'annonces.
  Le seul point d'entrée des annonces, c'est-à-dire des messages dits au lecteur d'écran.
- `askpass program`, programme de saisie.
  Le petit exécutable que `ssh` appelle pour obtenir un mot de passe ou la confirmation d'une clé d'hôte (variable `SSH_ASKPASS`).
  Il transmet la question à l'application, qui la pose dans un dialogue natif, et rend la réponse à `ssh` ; appelé par `LocalCommand`, il dit aussi à l'application que la connexion est établie.
- `caret`, curseur de texte.
  La position dans le texte de la zone de sortie.
- `closing part`, partie de fin.
  Les lignes de la sortie qui viennent après la partie vivante (« Déconnecté (code 255). » à la fin d'une connexion) ; elles disparaissent avec la partie vivante, quand la sortie suivante la remplace.
- `CommandPanel`, champ de commande.
  Le champ de texte d'une ligne où l'on tape, avec son bouton Envoyer.
- `connection`, connexion.
  L'endroit où s'exécute ce que l'on lance : cet ordinateur (connexion locale) ou un serveur SSH.
  Un fichier JSON par connexion (nom, cible, port facultatif) ; à ne pas confondre avec un profil (comment adapter l'application à un programme) ni avec un interpréteur (quel shell local).
  Avec une connexion choisie, tout s'exécute sur le serveur : on ne lance pas de programme local sans repasser par « Locale ».
- `cursor`, curseur du terminal.
  La position du curseur dans l'écran émulé, à ne pas confondre avec le curseur de texte.
- `develop mode`, mode Develop.
  Un état de l'application, activé par `--develop`, qui sert à préparer ce qui est livré : profils de départ, catalogues de messages, programmes de test.
  Ses réglages et son journal sont dans le dossier `DevelopMode` à côté de l'application.
- `DisplayExchange`, point d'échange.
  L'endroit où le thread du transport remet ses mises à jour à l'interface.
- `fixed part`, partie fixe.
  Les lignes de la sortie qui ne changeront plus.
- `dropped lines`, lignes abandonnées.
  Les plus anciennes lignes de la sortie, retirées parce que la limite de lignes est dépassée, ou perdues parce que la fenêtre n'a pas suivi ; l'utilisateur en est informé.
- `ForegroundGuard`, garde de premier plan.
  Le code qui reprend le premier plan à la console de la pseudo-console.
- `foreground lock`, verrou du premier plan.
  L'interdiction de changer la fenêtre au premier plan, posée juste avant le démarrage d'une pseudo-console et levée 0,4 s plus tard (`hold_foreground`).
- `free profile`, profil Libre.
  Le choix « Libre » du menu Profil : aucun fichier de profil, les valeurs des réglages au lancement de l'application, puis les valeurs en cours ; c'est le profil de démarrage par défaut.
- `host key`, clé d'hôte.
  La clé publique qui identifie un serveur SSH, et son empreinte.
  `ssh` la mémorise dans son `known_hosts` après la confirmation de l'utilisateur ; MiTerm-N5 ne lit ni n'écrit ce fichier.
- `launch file`, fichier de lancement.
  Un fichier de configuration passé en argument à l'application, qui fixe le profil, les valeurs des variables et le dossier de travail de la session.
- `line analysis`, analyse de ligne.
  Une fonction qui regarde le texte d'une seule ligne et dit si c'est un élément reconnu ; sans état, elle ne connaît ni l'écran ni le temps.
- `LineElement`, élément reconnu.
  Ce que l'analyse de ligne trouve : un genre (progression, question, choix, erreur) et le texte mis en forme qui s'en lit (« Téléchargement, 60 % »).
- `live part`, partie vivante.
  La fin de la sortie, remplacée quand elle change.
- `MessageSink`, récepteur de messages.
  Ce qui envoie réellement une annonce au lecteur d'écran.
- `OutputArea`, zone de sortie.
  Le contrôle de texte en lecture seule qui montre la sortie.
- `Profile`, profil.
  Un fichier JSON (programme, mode, interpréteur, préfixe de l'invite, taille, affichage, variables utilisées, commandes courantes) que l'utilisateur choisit à la main.
- `prompt prefix`, préfixe de l'invite.
  Le texte (`# ` dans les profils de départ Cmd et PowerShell) que MiTerm-N5 fait écrire devant l'invite d'un shell qui reste ouvert, pour que chaque ligne de commande soit un titre Markdown de niveau 1 et que les touches 1 et T aillent de commande en commande.
  Il s'ajoute devant l'invite de l'utilisateur, pour cette session seulement, et ne s'écrit nulle part sur l'ordinateur.
- `powershell_path`, PowerShell choisi.
  Le chemin de l'exécutable que l'interpréteur « PowerShell » lance (vide : Windows PowerShell, `powershell.exe`) ; un réglage global, choisi par « Sélection du PowerShell… ».
- `CommandUse`, type de commande.
  Ce à quoi sert une commande courante d'un profil : lancement (les arguments du programme du profil), programme (tapée dans le programme qui tourne) ou shell (complète, pour un profil de shell) ; une commande sans type est une commande de lancement.
- `ProfileVariable`, variable de profil.
  Un nom entre accolades (`{source}`) écrit dans les commandes courantes d'un profil et remplacé par la valeur que l'utilisateur a saisie ; à ne pas confondre avec une variable d'environnement.
- `SentKey`, touche envoyée.
  Une touche ou combinaison de touches (flèche, Échap, Tab, Ctrl+C, F5…) que l'utilisateur envoie au programme depuis le menu ou par un raccourci, sous forme des octets qu'un clavier de terminal enverrait.
  Elle n'a de sens que pour un programme servi par une pseudo-console.
- `application cursor keys`, touches du curseur en mode application.
  Un mode que le programme demande à l'émulateur (DECCKM) : les flèches, Début et Fin s'envoient alors avec `Échap O` au lieu de `Échap [`.
- `PromptPattern`, filtre de ligne (d'abord un motif d'invite).
  Un nom, une expression régulière cherchée dans une ligne de la sortie (`^C:\chemin>`, `utilisateur@hôte:~$ `, une date) et un remplacement dit à la place du texte trouvé ; la lecture confortable applique le premier filtre qui trouve quelque chose, et lui seul.
- `block`, bloc.
  Une commande de plusieurs lignes, envoyée d'un coup (Édition > Saisie sur plusieurs lignes…) et gardée comme une seule entrée de l'historique ; ses lignes sont séparées par `\n` dans le texte et par la fin de ligne du programme à l'envoi.
- `starter profile`, profil de départ.
  Un profil livré avec l'application, copié une fois chez l'utilisateur.
- `ScreenModel`, modèle d'écran.
  Le contrat entre les octets du terminal et la zone de sortie.
