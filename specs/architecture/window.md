# The window and the services around it

La couche wx, les raccourcis, les annonces, la langue et les réglages.
Vue d'ensemble dans `specs/architecture.md`.

## The window (`ui/`)

Seulement la mise en page et le câblage.
`MainWindow` (`ui/main_window.py`) crée, dans l'ordre de la touche Tab, le champ de commande et son bouton (`command_panel.py`), puis la zone de sortie (`output_area.py`), les menus (`main_menu.py`, `menus.py` : items gardés par commande et grisés d'après l'ensemble des commandes activées du présentateur, choix à boutons radio cochés d'après l'état réel), et `Feedback` (`feedback.py` : la barre d'état de trois champs, les dialogues, le centre d'annonces, et l'enregistrement des réglages, dont l'échec est montré à l'utilisateur sans arrêter l'application).
`WxSessionView` implémente `SessionView` sur ces widgets ; `WindowActions` (`actions.py`) est ce que font les commandes (dialogues, nouvelle session, copie, liste de l'historique, touches de titres) une fois que le présentateur les a acceptées ou a dit pourquoi non.
Elle ne fait que le câblage : le menu Profil est `ProfileActions` (`profile_actions.py`, qui lit les profils par `ProfileCatalog`, `presenters/profile_catalog.py`), le menu Develop est `DevelopActions` (`develop_actions.py`, qui sait quels programmes de test il y a et comment en lancer un par `presenters/develop_programs.py`), les commandes qui changent un réglage (Préférences, choix du PowerShell, bascule du signal d'activité) sont `SettingsActions` (`settings_actions.py`, qui enregistre les réglages par `Feedback.save_settings`), et le texte de « Informations sur la session » est fait par `presenters/session_report.py`.
Où l'application tourne (dossier des données donné en argument, dossier des profils, association des fichiers, dossier des journaux, dossier du mode Develop, lieu des données) est un seul objet, `AppContext` (`core/config/app_context.py`), que le point d'entrée fait avec `AppContext.from_location` et donne à `MainWindow` ; une fenêtre sans contexte (les tests) n'a ni profils, ni association, ni mode Develop, ni dossier d'aide (`help_folder`, le dossier `Help` à côté de l'application ; `HelpActions` dans `ui/help_actions.py`).
`OutputCommands` (`output_commands.py`) fait l'export, la recherche, la lecture d'une ligne mise en forme (`presenters/line_reader.py`) et les déplacements du sous-menu Déplacement du menu Terminal (vers le curseur du terminal, la première et la dernière ligne du terminal) : les dialogues de `Feedback` (`save_file`, `ask_text`), le curseur de texte et le focus ; l'écriture du fichier est dans `core/session/output_export.py`, la recherche dans `presenters/output_search.py`.
La fermeture de la fenêtre (`MainWindow._on_close`) demande confirmation quand un programme tourne : un « Non » garde la fenêtre et le programme.
Un « Oui », ou l'absence de programme, arrête le programme, enregistre les réglages et libère le récepteur d'annonces.
Une seconde fermeture reçue avant que wx ait détruit la fenêtre est ignorée.
La copie d'une adresse ou d'un élément (`OutputCommands._copy`) dit « Rien n'a été copié » quand le presse-papiers, que tout l'ordinateur partage, ne s'ouvre pas ou refuse le texte.
- **Zone de sortie** : un contrôle `TE_MULTILINE | TE_RICH2` en lecture seule.
  `OutputText` garde le texte et transforme une mise à jour en la plus petite modification (ce qui est commun au début et à la fin n'est pas remplacé) plus l'endroit où va le curseur de texte ; le contrôle l'applique dans `Freeze` / `Thaw`, en convertissant les index en UTF-16 (`core/screen/titles.py`).
- **Raccourcis** : affichés dans les textes de menu (pour que les accélérateurs existent) et aussi pris par un `EVT_CHAR_HOOK` sur la fenêtre, qui transforme une touche en commande (`shortcut_keys.py`, `core/session/command_shortcuts.py`) et interroge le présentateur : un raccourci vers une commande grisée annonce donc pourquoi elle est refusée.
  Ctrl+Pause arrive comme Ctrl+Break (`WXK_CANCEL`).
- **Minuteur** : 50 ms, appelle `presenter.tick()`, où la veille d'activité compare l'horloge à l'intervalle choisi (pas de minuteur à part).
  Un `wx.Timer` se déclenche dans `MainLoop` mais pas sous `wx.Yield` ; les tests de la fenêtre utilisent une vraie boucle (`tests/fakes/wx_loop.py`).
- **Garde de premier plan** (`ui/foreground_guard.py` ; les décisions sont dans `core/transport/foreground.py`) : la fenêtre de console cachée (`ConsoleWindowClass`) de la pseudo-console appartient à ce processus.
  Quand Windows lui donne le premier plan, rien n'y fonctionne, Tab ne fait rien, le lecteur d'écran dit « pythonw » et seul Alt+Tab ramène à la fenêtre principale.
  Cela arrive environ 60 ms après le démarrage d'un programme, même avec PowerShell seul (mesuré avec une vraie fenêtre au premier plan), et quand un programme demande à son terminal de restaurer sa fenêtre (Codex envoie `ESC [ 1 t`).
  Deux moyens :
  - le **verrou du premier plan** (`hold_foreground`, `LockSetForegroundWindow`) est posé juste avant le démarrage du ConPTY et levé 0,4 s plus tard ; il empêche le vol, mesuré avec la même fenêtre ;
  - la garde regarde, à chaque tick du minuteur, **quelle fenêtre a le premier plan** : pendant que la console l'a, `wx` répond encore que la fenêtre principale est active (`IsActive()` reste vrai, aucun événement d'activation n'arrive, mesuré), donc l'état d'activation ne dit rien.
  Quand une fenêtre de l'application (la principale ou un dialogue) avait le premier plan au tick précédent et que la console de ce processus l'a maintenant, la garde le rend à la fenêtre principale : elle lève le verrou, appelle `SetForegroundWindow`, et si Windows refuse, rattache l'entrée du fil à celui qui tient le premier plan (`AttachThreadInput`) avant de réessayer.
  Elle réessaie pendant une seconde, puis journalise le succès (INFO) ou l'échec (WARNING, avec la fenêtre qui tient le premier plan).
  Elle n'agit jamais quand une autre application a le premier plan.
- **Nouvelle session** : un nouveau processus (`core/session/new_session.py`), `--folder` donne son dossier de travail.
- **Démarrage** (`__main__.py`) : réglages, langue (gettext et `wx.Locale`), un fichier de journal dans le dossier des journaux de l'utilisateur (`core/config/logging_setup.py`, niveau `--log-level`, `INFO` par défaut, pas de console), la fenêtre.
- **Traductions** : `babel.cfg`, `src/n5terminal/locale/n5terminal.pot`, `fr/LC_MESSAGES/n5terminal` `.po` et `.mo`.
  Après un changement de textes : `pybabel extract -F babel.cfg -k N_ --add-location=file -o src/n5terminal/locale/n5terminal.pot .`, `pybabel update -i src/n5terminal/locale/n5terminal.pot -d src/n5terminal/locale -D n5terminal --no-fuzzy-matching`, traduire, `pybabel compile -d src/n5terminal/locale -D n5terminal`, puis `python tools/make_wx_keys.py` (le catalogue `wxkeys` des noms de touches de wx, fait à partir du précédent ; un test vérifie qu'ils ne divergent pas).
  Le fichier source de chaque message (sans numéro de ligne) est noté dans le `.pot`, pour les catégories du dialogue Catalogues (`specs/interface.md`, « Catalogs »), et `pybabel update` le recopie dans les `.po` ; le dialogue lit les catégories dans le `.pot`.
  Un test vérifie que chaque texte est traduit et garde ses champs nommés.

## Shortcuts, announcements, language, settings

- **Raccourcis** (`core/config/shortcuts.py`) : un raccourci est un texte (`Ctrl+Shift+O`), validé et normalisé dans `core/` (règles dans « Shortcuts » de `specs/interface.md`) ; une liste de commandes configurables avec leur valeur par défaut ; les réglages ne stockent que les différences.
  Quand les Préférences changent un raccourci, `MainWindow.refresh_shortcuts` réécrit le texte des items de menu (`MenuBuilder.refresh_shortcuts`) et recalcule les touches prises par `EVT_CHAR_HOOK`, sans redémarrage.
  La conversion d'un événement clavier wx vers ce texte et la page des Préférences appartiennent à `ui/`.
- **Annonces** (`core/config/announcements.py`, `core/config/screen_reader.py`) : des messages `Announce`, des `Category` avec une `Destination`, et `AnnouncementCenter`, le seul point d'entrée ; un `MessageSink` fait l'envoi.
  Le récepteur pour Windows (`ui/message_sinks.py`, `UiaMessageSink`) lève des notifications UI Automation (genre « autre », « importante, la plus récente ») sur une fenêtre d'un pixel, hors de vue, enfant du panneau (pas de la barre d'état, dont les lecteurs d'écran lisent les enfants avec elle), jamais focalisable et hors de l'ordre de Tab (`ui/uia_provider.py`, écrit avec `ctypes` : aucune API propre à un éditeur, pas de MSAA).
  Le fournisseur s'accroche à la procédure de la fenêtre (`SetWindowSubclass`), répond à `WM_GETOBJECT` par un petit objet `IRawElementProviderSimple` (côté serveur, appelé sur notre thread ; un élément texte, un contrôle et un élément de contenu, nommé d'après le dernier texte dit) et lève toujours l'événement, sans demander si un client écoute.
  Les options doivent être `ServerSideProvider | UseComThreading` (0x22) : la valeur 1 est *côté client* et a rendu la première version muette.
  `Feedback.apply_screen_reader_output` construit le récepteur à partir du réglage une fois le panneau créé (les Préférences le rappelleront) ; s'il ne peut pas être créé, l'utilisateur en est informé une fois et les annonces ne vont nulle part.
  Un fournisseur n'est jamais libéré (UI Automation le lâche tard).
  `RecordingMessageSink` sert aux tests (`tests/fakes/recording_sinks.py`, comme `RecordingBeeper`).
  Le bip de l'activité passe par le même centre : la destination « bip » appelle un `Beeper` (un `Protocol`, `winsound.Beep` pour Windows), qui joue un son de 30 à 50 ms depuis un thread de travail, parce que `winsound.Beep` bloque le thread qui l'appelle ; un faux `Beeper` sert aux tests.
  Ce thread ne touche pas à wx.
- **Langues** (`n5terminal/i18n`) : gettext, français par défaut, identifiants de messages en anglais ; `install` active une langue ; les textes propres à wx la suivent (`wx.Locale`, dans `ui/`).
  Les catalogues sont construits avec Babel.
- **Réglages** (`core/config/settings.py`, `core/config/jsonstore.py`) : un fichier JSON, dont l'emplacement dépend du mode local ou portable (section suivante).
  Écrit de façon atomique (fichier temporaire, puis remplacement), la dernière bonne version gardée en `.bak` ; un fichier abîmé est mis de côté en `.corrupt`, la sauvegarde est essayée, et l'utilisateur en est informé.
  Les valeurs invalides sont ignorées une à une.

## Where the data lives

Deux modes d'utilisation, choisis au démarrage (`core/config/location.py`, `DataLocation`).
Le reste du code ne connaît les chemins que par cet objet ; les tests lui donnent un dossier temporaire.

- **Local** : l'application est un dossier sur le disque ou installée.
  Les réglages (`settings.json`), les profils (`profiles\`) et les connexions SSH (`connections\`) sont dans le profil Windows de l'utilisateur, en itinérant : `%APPDATA%\MiTerm-N5\`.
  Les clés d'hôte sont dans le `known_hosts` de `ssh`, dans le profil Windows (`%USERPROFILE%\.ssh\`) : MiTerm-N5 n'y touche pas.
  Le journal (`n5terminal.log`) reste sur le PC : `%LOCALAPPDATA%\MiTerm-N5\Logs\`.
- **Portable** : pour une clé USB, sans trace de MiTerm-N5 sur le PC hôte.
  Tout est dans un dossier `data\` à côté de l'exécutable : `data\settings.json`, `data\profiles\`, `data\connections\`, `data\logs\n5terminal.log`.
  Les clés d'hôte SSH y ont leur propre fichier, `data\known_hosts`, que `ssh` reçoit par `-o UserKnownHostsFile` ; le `known_hosts` du système n'est pas écrit.
- **Develop** : pour préparer ce qui est livré (`--develop`, voir le mode Develop dans `specs/glossaire.md`).
  Les réglages et le journal sont dans le dossier `DevelopMode\` à côté de l'application (`DevelopMode\settings.json`, `DevelopMode\logs\n5terminal.log`), comme en mode portable ; rien n'est écrit dans le profil Windows ni dans le registre.
  Les profils ajoutés, modifiés et supprimés sont ceux du dossier `starter_profiles\` de l'application, c'est-à-dire ceux qui sont livrés ; les profils de départ ne sont donc pas copiés.
  Les connexions SSH et leur fichier de clés d'hôte sont dans `DevelopMode\connections\` et `DevelopMode\known_hosts`, comme en mode portable.
  Le journal démarre au niveau `DEBUG`, sauf si `--log-level` est donné.
  Une nouvelle session reçoit `--develop`.
- **Choix du mode** : l'option `--develop` d'abord, puis l'option `--data-folder DOSSIER` (tout est alors dans ce dossier, qui n'a pas besoin d'être `data\`) ; sinon la présence d'un fichier vide nommé `portable` à côté de l'exécutable (le dossier du dépôt en développement) ; sinon le mode local.
  Un double-clic sur l'exécutable de la clé suffit donc, et le mode voyage avec le dossier.
- **Nouvelle session** : elle retrouve le fichier `portable` d'elle-même ; seule l'option `--data-folder` lui est transmise.
- **Ce que le mode portable garantit** : MiTerm-N5 n'écrit rien en dehors de son dossier (ni réglages, ni profils, ni journal, ni fichier temporaire) et n'utilise pas le registre.
  Avec une connexion SSH, `ssh` lit sans y écrire le `~/.ssh/config`, les clés et l'agent du PC hôte.
  Il ne peut pas empêcher Windows de noter le lancement d'un programme (Prefetch, programmes récents, journaux d'événements), ni les programmes lancés dans MiTerm-N5 de laisser leurs propres traces.
- **Dossier non inscriptible** (clé verrouillée en écriture) : le journal est alors désactivé, et les réglages ne s'enregistrent pas, ce que l'utilisateur apprend par l'erreur annoncée à l'enregistrement.
  MiTerm-N5 ne se rabat jamais sur le disque du PC hôte.

## Screen reader notes

- Les modes 1 à 4 donnent du texte linéaire, affiché dans un contrôle de texte natif en lecture seule, que NVDA et JAWS lisent.
- Le mode 5 n'a pas de prise en charge propre : son écran est montré comme celui du mode 4 (`specs/decisions.md`).
- Ce qui aide à suivre un programme (détection d'activité, ligne mise en forme, identification) travaille sur les lignes du texte, dans tous les modes (`specs/interface.md`, « Activities »).
