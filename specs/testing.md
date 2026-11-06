# Testing

## Tools and markers

pytest et pytest-cov.
`tests/` reflète `src/n5terminal/` ; `tests/fakes/` contient ce que les tests partagent (importé comme `fakes.*`, voir `pythonpath` dans `pyproject.toml`).
Marqueurs :
- `unit` : logique pure, rapide.
- `slow` : de vrais processus (les programmes simulés ci-dessous).
- `ui` : une fenêtre créée dans une `wx.App` de test.

Des tests ciblés pendant le travail ; la suite complète, ruff et mypy une fois, avant de proposer un commit.
La couverture est mesurée avec pytest-cov, sans seuil au début.

## By layer

| Couche | Genre | Comment |
|---|---|---|
| Logique de `core/` (filtre, décodeur, tampons) | `unit` | Cas par cas : séquence coupée entre deux morceaux, retour chariot, UTF-8 coupé, ligne longue, limite de lignes |
| Transports de `core/` | `slow` | Le vrai transport exécute un programme simulé (ci-dessous) |
| `presenters/` | `unit` | Fausse vue et faux transport ; pas de `wx`, pas de processus |
| `ui/` | `ui` | Noms accessibles, ordre de Tab, focus initial. Contrôles légers |

`tests/test_layers.py` vérifie que `core/` et `presenters/` n'importent jamais `wx`.
Il vérifie aussi que les couches ne dépendent que vers le bas : `core/` n'importe ni `presenters/` ni `ui/`, `presenters/` n'importe pas `ui/`.
Dans `core/`, chaque sous-paquet n'importe que ceux qui le précèdent (`config`, `transport`, `screen`, `session`), et `errors.py` n'en importe aucun.
Les imports relatifs sont interdits, parce qu'ils échapperaient à ces vérifications.
`tests/test_announcement_calls.py` lit le code et vérifie que chaque appel qui nomme une annonce (`say(Announce.X, ...)`) donne les valeurs que son texte demande (les champs `{...}` de `Announce.fields`, et `line` quand la catégorie accepte « Lire la ligne »).
Les annonces dites par une variable y sont listées, avec le test de comportement qui les couvre ; les refus de commande sont vérifiés dans `tests/core/session/test_session_state.py` (leur texte n'a aucun champ).
`tests/test_specs.py` vérifie que les specs ne citent que des fichiers qui existent, et que les sections des specs citées dans le code existent.
`tests/core/config/test_settings.py` tient une table des réglages enregistrés (`CHANGED_VALUES`) : un champ ajouté à `Settings` doit y figurer.
Chaque champ de la table est écrit puis relu, donc un champ oublié dans `save` ou dans la lecture fait échouer un test.
`tests/core/session/test_session_state.py` vérifie que `LAUNCH_MODES` et `INTERPRETERS` (`core/config/settings.py`) sont les valeurs de `LaunchMode` et de `Interpreter`.
`settings.py` les écrit lui-même, parce que son sous-paquet précède `session/` et ne peut pas importer ces énumérations.

## Screen reader during the tests

Les tests `ui` ouvrent de vrais dialogues sur le bureau.
Avec NVDA allumé, la suite complète peut écrire « Windows fatal exception: code 0x8001010d » (`RPC_E_CANTCALLOUT_ININPUTSYNCCALL`) pendant `ShowModal`, par exemple dans `test_the_secret_is_given_back_when_ok_and_none_when_cancelled`.
Ce n'est pas un échec : le test passe, la suite passe, et COM gère l'exception lui-même ; `faulthandler` l'écrit parce qu'il voit toute exception système.
La cause est le lecteur d'écran, qui interroge la fenêtre par COM pendant que le dialogue traite un message synchrone ; avec le lecteur d'écran coupé, le message ne vient plus, ni en couple ni en suite complète.
Les autres tests qui font tourner une vraie boucle d'événements (`specs/manual-checks.md`) la produisaient aussi : plus aucune occurrence dans la suite complète sans NVDA.
Ce n'est donc ni un défaut de l'application, ni un état laissé par un test : ne pas chercher plus loin, et ne pas désactiver `faulthandler`, qui reste utile pour un vrai plantage.
Le message dépend du moment où NVDA est occupé, donc de l'ordre des tests.

## Coverage

Mesure du 2026-11-03, avant les derniers tests de la fenêtre : 90,1 % avec les branches, sur 112 fichiers de `src`, dont 60 couverts à 100 %.
La commande est `.venv\Scripts\python.exe -m pytest --cov=n5terminal --cov-branch --cov-report=term-missing:skip-covered` ; elle dure environ cinq minutes, contre une vingtaine de secondes pour la suite seule.
`core/` et `presenters/` sont solides (`session_presenter.py` : 98 %) ; les trous sont dans `ui/`, dans `__main__.py` et dans le code qui touche le système.
Les trous connus et laissés : `__main__.main` (38 %, du câblage qu'on ne teste qu'en lançant l'application), `catalogs_dialog.py` (15 %, outil du mode Develop), et les chemins d'échec de `process_tree.py`, `file_association.py` et des deux transports (75 à 83 %), qui demandent de simuler des erreurs de Windows.
Les commandes de la fenêtre se testent par `window.actions.run(...)` avec les dialogues remplacés par des réponses (`tests/ui/test_settings_actions.py`, `test_window_commands.py`).
Un pourcentage ne dit pas qu'une ligne est vérifiée, seulement qu'elle est exécutée : pour un comportement sensible, on casse le code un instant (mutation) et on regarde le test échouer.

## Fakes and simulators

1. **Faux transport** (`tests/fakes/fake_transport.py`) : implémente `Transport` dans le processus de test et joue n'importe quel scénario (états dont `authenticating`, données, sortie, échec).
   C'est la référence pour les présentateurs, et il tient lieu de SSH tant qu'il n'y en a pas un vrai.
   `tests/fakes/recording_listener.py` enregistre ce que rapporte un transport, depuis n'importe quel thread.
2. **Programmes simulés** (de vrais processus, lancés avec `sys.executable`, indépendants des programmes du système) : un script piloté par un scénario donné en argument.
   On teste le vrai transport, pas une imitation.
   - `program_cli.py` (CLI) : les deux flux avec un code de sortie, écho de stdin, flot de lignes, un caractère UTF-8 coupé entre deux écritures, un programme qui ne se termine jamais.
     À ajouter au besoin : barre de progression avec retours chariot, ligne très longue, un programme qui ne lit jamais stdin.
   - `program_tui_line.py` (mode 4) : refuse de s'exécuter sans terminal, couleurs, entrée dont le terminal fait l'écho, un mot de passe sans écho, la taille du terminal après un redimensionnement (le programme attend que la taille change, parce que ConPTY l'applique de façon asynchrone ; sans cette attente le test échouait environ une fois sur 80 sous charge), un code de sortie.
     `screen_text.py` transforme la sortie VT en lignes que montre un terminal (pyte).
   - Pas de simulateur plein écran : le mode 5 n'a plus de prise en charge propre (`specs/decisions.md`).
3. **Captures enregistrées** (`tests/data/captures/`, avec les étapes terminal) : les octets que ConPTY émet pour de vrais programmes (`vim`, `less`, un REPL), rejoués dans pyte.
   Rapides, déterministes, et faites de vraies séquences plutôt qu'imaginées.
4. **Tests de contrat du modèle d'écran** (`tests/fakes/screen_model_contract.py`) : une classe que toute implémentation sous-classe en donnant `make_model` (`tests/core/screen/test_pyte_screen_model.py` pour pyte, un module natif plus tard).
   Chaque capture est donnée entière et par morceaux de 1, 7 et 4096 octets et doit montrer les lignes de l'historique propre de pyte plus l'écran (`screen_text.py`, la référence quelle que soit l'implémentation) ; des cas synthétiques couvrent les mises à jour, les lignes fixes, les caractères et séquences coupés, et les lignes repliées.
   `ScreenMirror` applique les mises à jour comme le fera la zone de sortie.

Aucun test ne lit ni n'écrit le presse-papiers de l'ordinateur : `tests/fakes/fake_clipboard.py` (`FakeClipboard`) prend la place de `wx.TheClipboard` et garde chaque texte copié, dans l'ordre.
Avec `available=False` il joue un presse-papiers occupé par un autre programme (`Open` échoue) ; avec `accepts=False`, un presse-papiers qui refuse le texte.
Aucun test ne change le vrai premier plan : `tests/fakes/fake_foreground.py` (`FakeForeground`) prend la place de Windows pour le verrou et la garde (`tests/core/transport/test_foreground.py`).
Ce qui se passe avec une vraie fenêtre au premier plan ne se teste pas dans la suite : il déplacerait le focus de la personne qui travaille ; il se mesure à la main, avec un script jetable qui lit la fenêtre au premier plan (voir `specs/decisions.md`, 2026-11-03).
Les tests des dialogues de `Feedback` (`tests/ui/test_feedback_dialogs.py`) remplacent `ShowModal`, pour qu'aucun dialogue ne s'affiche, et `wx.Window.FindFocus`, pour la règle du retour du focus.
Le focus réel de Windows dépend de la fenêtre qui est devant pendant les tests : un test qui s'y fierait pourrait passer sans rien vérifier.

Un simulateur ne vérifie que nos propres hypothèses : les points « à vérifier par l'expérience » de `specs/open-questions.md` demandent de vrais programmes, et les captures les relient aux tests.

SSH : pas de simulateur de serveur, mais un **faux `ssh`** (`tests/fakes/program_ssh.py`, lancé avec `sys.executable`) qui joue les scénarios mesurés dans `specs/architecture/transport.md` (« What `ssh.exe` does (measured) ») et appelle le vrai programme de saisie comme le fait `ssh` (`specs/architecture/connection.md`, « Tests »).
Un vrai serveur ne sert qu'à la main : un `sshd` dans Debian sous WSL (`specs/manual-checks.md`, « SSH »).

Les tests du présentateur de session partagent `tests/fakes/session_support.py` (une session câblée avec la fausse vue, le faux lanceur et le faux transport, et de petits scénarios : lancer un programme, le terminer, démarrer un shell) et les fixtures `session` (pipes) et `terminal` de `tests/conftest.py`.
Ils sont répartis par sujet : la session elle-même, et l'environnement (dossier, interpréteur, taille).

`tests/presenters/test_session_with_real_programs.py` (`slow`) branche le vrai présentateur, le vrai lanceur et les vrais transports sur les programmes simulés ; seule la fenêtre est fausse.
Un assistant joue le thread de l'interface (`post` remplit une file, `tick` est appelé en boucle avec un délai).

La fenêtre est testée légèrement (`tests/ui`, marqueur `ui`) : noms accessibles, focus initial, ordre de Tab, items grisés, touches d'accès uniques par menu en anglais et en français, curseur de texte conservé à l'arrivée de la sortie, touches de titres, barre d'état ; avec des fausses implémentations (`pump` traite les événements en attente) et, dans `test_main_window_with_programs.py` (`slow`), avec le vrai lanceur et un vrai programme dans une vraie boucle d'événements (`tests/fakes/wx_loop.py`).
`test_translations.py` vérifie le catalogue français.

`tools/load_screen.py` est une mesure, pas un test (ses chiffres dépendent de la machine) : un flot de plusieurs mégaoctets à travers `ScreenPump`, avec un thread qui tient lieu d'interface.
Le côté test est dans `tests/core/screen/test_display_exchange.py` (fusion, limite, un flot donné pendant que l'interface prend : rien de perdu).

## Cases to cover

- Robustesse : sortie très rapide (pas de gel, rien de perdu), ligne très longue, limite de lignes, un programme qui ne lit pas stdin, un programme qui se termine pendant qu'on envoie de l'entrée, arrêt de tout l'arbre de processus.
- Sécurité : le texte tapé et les arguments n'apparaissent jamais dans le journal de diagnostic.

## Manual checks

NVDA à chaque étape : ce qui est lu quand la sortie arrive, lors d'un changement d'état, à la fin d'un programme ; focus jamais déplacé par la sortie ; tout atteignable au clavier.
La liste est dans `specs/manual-checks.md`.
