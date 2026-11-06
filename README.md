# MiTerm-N5

Une application de terminal pour Windows faite pour être utilisée avec un lecteur d'écran (NVDA, JAWS).
Elle lance des programmes en ligne de commande, un shell (Cmd, PowerShell) ou une connexion SSH, et montre leur sortie dans des contrôles natifs que le lecteur d'écran lit comme n'importe quel texte.

A terminal application for Windows made for screen reader users (NVDA, JAWS).

## Utilisation

Télécharger le zip de la dernière version dans les « Releases », le décompresser et lancer `MiTerm-N5.exe`.
Aucune installation, et Python n'est pas nécessaire.
L'application n'est pas signée : Windows (SmartScreen) peut afficher un avertissement au premier lancement.

L'aide est dans l'application (Aide > Ouvrir l'aide, F1) et dans le dossier `Help`.

## Depuis les sources

Python 3.14 et wxPython 4.3 sont nécessaires.

```
python -m venv .venv --system-site-packages
.venv\Scripts\python.exe -m pip install -e .[dev]
Start.bat
```

La documentation du projet est dans `specs/` (en français) ; commencer par `specs/roadmap.md`.

## Contributions

Ce projet n'accepte ni contributions, ni demandes de fusion, ni messages.

## Licence

GNU General Public License v3.0, voir `LICENSE`.
Les composants tiers sont listés dans `THIRD-PARTY-NOTICES.md`.
