# Aide de MiTerm-N5

## Description générale

MiTerm-N5 est une application de terminal, accessible avec un lecteur d'écran.
L'objectif n'est pas de fournir un terminal universel, mais plutôt :
- d'utiliser confortablement des applications en ligne de commande (CLI) ;
- de faciliter l'utilisation de programmes en mode terminal (TUI) ;
- de permettre le suivi d'une progression ou d'une mise à jour d'un résultat ;
- de pouvoir sélectionner et valider un choix au clavier ;
- de lire et parcourir librement la sortie des programmes, indépendamment de leur rythme d'affichage ;
- de conserver un historique, permettant de revenir sur les informations affichées précédemment.

## Session

Une session est un ensemble de paramètres définis dans la fenêtre de l'application.
Elle est limitée au lancement d'un seul programme à la fois, mais il est possible d'ouvrir plusieurs fenêtres d'application.

Avant de lancer un programme, vous choisissez son mode.
Le mode CLI convient à la plupart des commandes : le programme lit et écrit du texte.
Le mode TUI convient aux programmes qui ont besoin d'un vrai terminal : python, ssh, les mots de passe.
Le mode est choisi par l'utilisateur, jamais deviné.

Vous pouvez aussi sélectionner un interpréteur, Cmd ou PowerShell.
Un shell est toujours en mode TUI.

Le dossier de travail est celui où le programme démarre.
Vous pouvez le changer tant qu'aucun programme ne tourne.

## Profil

Un profil range les réglages d'un programme que vous utilisez souvent.
Il contient le programme, le mode, l'interpréteur, la taille du terminal et une liste de commandes courantes.
Avec un programme, les commandes courantes n'ont plus à le répéter : `status` suffit pour `git status`.
La liste dit seulement le nom du programme, et le champ de commande reçoit le chemin complet.

Vous choisissez un profil vous-même.
MiTerm-N5 n'en applique jamais un tout seul.
Sans profil choisi, la session est « Libre ».

Les commandes courantes d'un profil s'ajoutent à la liste des commandes tapées.
Elles peuvent contenir des variables, écrites entre accolades : `{name}`, `{source}`, `{destination}`, `{value1}`, `{value2}`, `{comment}`, `{ip}`, `{message}`.
Vous donnez leur valeur dans le dialogue des variables, et elles remplacent les accolades dans la liste.

Un profil `git` est fourni en exemple.
Vous pouvez ajouter, modifier et supprimer vos profils.
Chaque profil est un petit fichier : vous pouvez le copier sur une autre machine.

## Utilisation de l'application
La fenêtre a trois parties :
+ Une zone de sortie, en haut : on y lit ce que le programme écrit.
+ Une zone de commande, en bas : on y tape une commande, puis Entrée pour l'envoyer.
+ Une barre d'état, indiquant la ligne, la colonne et l'état du programme.

### Lancer et suivre un programme

Tapez la commande dans le champ de commande, puis Entrée.
Le focus passe automatiquement dans la zone de sortie, sur la ligne de la commande.
Pour envoyer d'autres commandes il faut retourner dans la zone de commande.
Certaines touches ou raccourcis clavier peuvent être envoyés directement au programme depuis cette zone.

La fin du programme est annoncée avec son code de sortie.

### Zone de commande

L'intitulé du champ de saisie indique comment est utilisé le texte :
- Commande : le texte est une commande. Au repos, il lance un programme ; dans un shell ouvert (Cmd, PowerShell) ou avec une connexion, il est envoyé dans le shell.
- Message : le texte est envoyé tel quel au programme qui tourne (une réponse à une question, par exemple).
- Le nom du profil (« Git ») : le texte devient les arguments du programme du profil, qui est lancé à l'envoi. Donc, un champ vide lance le programme seul.

Un historique des dernières commandes, ainsi que des commandes du profil, peut être invoqué depuis ce champ de saisie.

La case à cocher, pour masquer le texte saisi, se désactive automatiquement après un envoi.
Un texte masqué n'est pas mémorisé dans l'historique.

Le champ de saisie principal ne peut contenir qu'une seule ligne.
Pour envoyer plusieurs lignes, il faut utiliser la boîte de saisie multi-lignes.

### Zone de sortie

La sortie arrive en silence :
- Le texte ajouté ou modifié n'est pas annoncé ;
- ni le focus ni le curseur de texte ne sont changés ;
- vous lisez quand vous le décidez.
- les messages les plus anciens se trouvent en remontant dans le texte.

La lecture et la recherche de contenu se font avec les touches classiques.
Cependant, certaines fonctionnalités peuvent faciliter la consultation du contenu :
- les déplacements de titre en titre, notamment pour les profils CMD et PowerShell.
- une aide pour l'identification de certains éléments, tels que barre de progression, choix, liens, ...
- une lecture confortable, en limitant les textes redondants. Par défaut les invites de commandes courantes, mais vous pourrez ajouter d'autres motifs de détection.

La sortie des programmes en erreur commence par « StdErr: » : on la distingue par le texte, pas par la couleur.

#### Programmes interactifs

En mode TUI, vous pouvez envoyer au programme des touches que le champ de commande ne transmet pas : flèches, Échap, Tab, touches de fonction.
C'est utile pour les menus et les listes de choix.
Le menu Session propose ces touches, et vous pouvez leur donner un raccourci.

Le curseur du terminal est là où le programme attend votre saisie.

#### Les activités

Beaucoup de programmes écrivent des barres de progression, posent une question ou affichent un choix.
MiTerm-N5 reconnaît ces éléments dans les lignes de la sortie.
Il reconnaît les progressions, les questions, les choix et les erreurs.

Trois fonctions s'appuient sur cette reconnaissance.
Lire la ligne avec mise en forme dit la ligne du curseur de texte de façon plus claire : « Téléchargement, 60 % ».
Identifier des activités liste ce qui est reconnu à l'écran, et vous emmène sur la ligne choisie.
Signaler les activités vous prévient quand la sortie change.

Le signal d'activité se règle dans les Préférences, à la page Annonces.
Par défaut, MiTerm-N5 vérifie chaque seconde si la sortie a changé.
Si la ligne du curseur est un élément reconnu, il la dit.
Sinon, il joue un bip, pour signaler un changement.
Si le bip vous gêne, coupez le signal avec un raccourci.

### Barre d'état et annonces

MiTerm-N5 n'annonce que ce qui compte : début et fin d'un programme, erreurs, commandes refusées.
Vous pouvez choisir, pour chaque catégorie, si elle est dite, ignorée ou montrée dans une boîte de dialogue.

La barre d'état a trois champs d'informations :
- Position de la ligne
- état de fonctionnement
- Position de la colonne

## Connexion

Une connexion définit où s'exécute ce que vous lancez : sur cet ordinateur, ou sur un serveur.
- « Locale » est le choix par défaut : les programmes tournent sur cet ordinateur.
- Les autres choix sont des connexions à des serveurs.
Quand une connexion est choisie, toutes les commandes sont envoyées à son serveur.
Le dossier de travail, l'interpréteur et le mode ne seront donc plus disponibles.
L'envoi d'une commande ouvre automatiquement une connexion.

### SSH

MiTerm-N5 utilise par défaut le programme ssh.exe d'OpenSSH, livré avec Windows.
L'authentification peut se faire de deux façons.
+ Par mot de passe : une boîte de dialogue indique le serveur et demande le mot de passe, dans un champ masqué.
+ Par clé : ssh trouve votre clé tout seul et ne pose aucune question.

À la première connexion à un serveur, ssh en montre l'empreinte et demande si vous lui faites confiance.
Annuler un dialogue n'est pas une erreur : la connexion s'arrête, simplement.
MiTerm-N5 ne garde aucun mot de passe et ne copie aucune clé.

Où sont les clés :
- La clé du serveur, celle que vous avez acceptée, est écrite par ssh dans le fichier `known_hosts` du dossier `.ssh` de votre profil Windows (`%USERPROFILE%\.ssh\known_hosts`).
  En mode portable, elle est dans le fichier `data\known_hosts`, à côté de l'application.
- Votre clé privée est un fichier du même dossier `.ssh`, par exemple `id_ed25519`, à côté de sa clé publique `id_ed25519.pub`, celle que l'on copie sur le serveur.
  Ne partagez jamais la clé privée.
  Le profil `ssh-keygen` peut aider à la créer.

## Limites d'utilisation

- MiTerm-N5 fonctionne seulement sous Windows.

- Il ne lance pas les programmes graphiques, qui ouvrent leur propre fenêtre.
- Il ne prend pas en charge les programmes plein écran comme `vim` ou `htop`.
Ils se lancent, mais leur écran n'est pas lu comme une grille.
Le clavier ne leur est pas transmis directement.

- La sortie a une limite de lignes, définissable dans les Préférences.
Les plus anciennes lignes sont abandonnées, et MiTerm-N5 vous le dit.

- L'export peut contenir des secrets : relisez-le avant de le partager.

- Une ligne plus longue que l'écran est lue comme plusieurs lignes, comme dans un terminal ordinaire.
MiTerm-N5 agrandit alors la taille du terminal si vous avez choisi la taille automatique.

- La reconnaissance des activités lit le texte, pas les couleurs.
Elle peut se tromper ou ne rien voir.
Un mot de passe que l'on tape n'écrit rien : la question reste reconnue après la réponse.

- Un programme lancé garde les droits de l'utilisateur.
MiTerm-N5 ne protège pas contre une commande dangereuse.

## Fichier de lancement (.n5term)

Un fichier portant l'extension `.n5term` ouvre une session déjà réglée.
Il suffit de le passer à l'application, ou de double-cliquer dessus, après une association.
Le bouton d'association des Préférences, page Général, fait ouvrir ces fichiers par MiTerm-N5.

C'est un fichier texte, une clé et sa valeur par ligne.
Les lignes qui commencent par `;` ou `#` sont des commentaires.

La clé obligatoire :
- `profile` : le nom du profil à choisir.

Les autres clés possibles sont :
- `WorkingPath` : le dossier de travail ;
- le nom d'une variable du profil (`name`, `source`, `comment`, `message`…) : sa valeur.

Exemple :
```
profile = git
WorkingPath = C:\Projets\mon-projet
source = origin
```

Sans définir de valeur pour `WorkingPath`, la session démarre dans le dossier du fichier.
Un chemin relatif se lit à partir de ce dossier.

Le fichier ne lance aucune commande.

## Mode local et mode portable

En mode local, MiTerm-N5 range ses données dans votre profil Windows.
Les réglages et les profils sont dans `%APPDATA%\MiTerm-N5`.
Le journal est dans `%LOCALAPPDATA%\MiTerm-N5\Logs`.

Le mode portable convient à une clé USB.
Il ne laisse aucune trace sur l'ordinateur hôte.
Réglages, profils et journal sont dans un dossier `data`, à côté de l'exécutable.

Pour passer en mode portable, placez un fichier vide nommé `portable` à côté de l'exécutable.
On peut aussi spécifier un dossier de données avec l'option `--data-folder`.
