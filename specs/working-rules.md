# Working rules

Règles générales pour écrire et organiser le code, à copier telles quelles dans un autre projet.
Rien ici n'est propre à une application : ce qui appartient à un projet (modules, exemples, décisions) est dans ses propres documents, et les limites chiffrées vérifiées par les outils (taille d'une fonction, nombre d'arguments, complexité) vivent dans la configuration de ces outils, pas ici.

## Structure and size

- Une responsabilité par fichier.
  Si son but ne peut pas se dire en une phrase sans « et », il en fait trop.
  Découper par raison de changer, pas par taille : ce qui change ensemble reste ensemble.
- Un fichier source dépasse rarement 400 lignes et jamais 600.
  Quand un fichier s'en approche, le découper avant d'y ajouter.
  Une classe dépasse rarement 300 lignes.
- Une nouvelle fonction a son propre module.
  Un gros fichier, comme une fenêtre principale, ne reçoit que le câblage.
- Ne pas découper trop fin : dix fichiers de quarante lignes qui s'appellent coûtent plus à lire qu'un seul.
  Ne pas découper par genre technique (un fichier de « constantes », un fichier d'« utilitaires ») : découper par sujet.
  Un nom qui dit ce que contient le fichier est le signe d'un bon découpage.
- Couches : la couche d'interface utilisateur ne fait que la mise en page et le câblage.
  Toute logique qui peut se tester sans fenêtre va dans la couche logique, qui n'importe jamais la couche d'interface.
  Pas de dépendances circulaires : elles vont dans un seul sens.
- Les threads de travail ne touchent jamais l'interface ; ils remettent leurs résultats au thread de l'interface.
- L'état partagé est explicite : les composants reçoivent un objet de contexte ou des rappels, ils ne vont pas chercher dans les attributs les uns des autres.

## When a tool says the code is too big or too complex

Un outil détecte le problème, pas la cause.
Décider dans cet ordre :

1. **La fonction fait-elle deux choses ?** Alors la découper en fonctions nommées.
   C'est la cause la plus fréquente, et elle règle d'un coup trop d'arguments, de branches et d'instructions.
2. **Les valeurs voyagent-elles ensemble ?** Si plusieurs fonctions reçoivent les mêmes valeurs, les grouper dans un petit objet typé (une dataclass) qui a un sens propre.
   Réutiliser un objet qui existe déjà.
3. **Est-ce une longue chaîne de conditions ?** La remplacer par une table ou extraire des conditions nommées.
4. **Est-ce seulement de la description** (libellés et noms d'un dialogue) ?
   La grouper dans un objet de description ou, pour la couche d'interface seulement, relever la limite dans la configuration de l'outil.

Ne jamais contourner une alerte par un dictionnaire non typé ou des `**kwargs`.
Ne jamais en faire taire une sans une phrase qui dit pourquoi, et le dire à l'utilisateur quand c'est fait.

## At each milestone

- Avant de proposer un commit, vérifier la taille des fichiers touchés et découper ceux qui dépassent la limite.
- Pendant le travail, lancer les tests qui concernent le changement ; lancer la suite complète et les vérifications (lint, format, types) une seule fois, juste avant de proposer le commit.

## Tests

- Un fichier de test par module.
  Un test qui demande une vraie fenêtre pour vérifier de la logique montre que la logique est au mauvais endroit.
- Les tests ne lisent jamais la vraie configuration de l'utilisateur : elle est redirigée vers un dossier temporaire.
  Une fausse implémentation remplace chaque programme externe, quel que soit le coût de son exécution.
- Un test manuel avec le vrai programme externe utilise son modèle et ses réglages les moins chers.
- Ne pas deviner un protocole ou un format de sortie : regarder une vraie exécution, et écrire ce qui a été vérifié dans la documentation de ce programme.

## Reading and context

- Lire un gros fichier par plages plutôt qu'en entier.
  Chaque appel renvoie tout le contexte, donc ce qui est lu tôt est payé de nouveau à chaque étape.
- Garder court le fichier toujours chargé : la règle en une ou deux lignes, les raisons et les exemples dans un document lu à la demande.

## Files and data

- Un fichier de l'application est écrit dans un fichier temporaire du même dossier, puis déplacé sur l'ancien : un plantage ne laisse jamais un fichier à moitié écrit.
- La dernière version valide est gardée comme sauvegarde.
  Un fichier illisible est mis de côté, pas écrasé, pour que rien ne soit perdu.
  À la lecture, un fichier abîmé donne sa sauvegarde, sinon les valeurs par défaut, et l'utilisateur en est informé par un dialogue, pas par un plantage.
- Un fichier qui appartient à un autre programme (ses réglages, par exemple) est lu avec soin : s'il n'est pas valide il n'est jamais écrasé, et les autres clés d'un fichier valide sont conservées à l'écriture.
- Une seule instance de l'application écrit les fichiers d'un utilisateur.

## Texts and languages

- Chaque texte visible passe par la fonction de traduction ; pas de concaténation de textes, un texte avec des champs nommés à la place.
  Le catalogue est recompilé après chaque modification.
- Les touches d'accès sont uniques dans un dialogue, dans chaque langue.

## Accessible interfaces

- Tout est utilisable au clavier seul.
  Chaque contrôle a un nom accessible et chaque dialogue un focus initial défini.
- Une étiquette est créée juste avant son contrôle, pour que les lecteurs d'écran les associent.
- Aucun changement de focus inattendu.
  Où vont le focus et le curseur de texte dans chaque cas est écrit, et chaque nouvelle fonction suit une règle ou ajoute son cas.
- Contrôles natifs d'abord.
  Un champ en lecture seule est un champ de texte multiligne, que la touche Tab atteint.
- Aucune information donnée par la couleur seule.
- Ce qui ne peut pas être utilisé est grisé, ni masqué ni silencieux.
- Une information affichée dans une liste va dans le texte de chaque ligne, séparée par des virgules, en omettant ce qui n'a pas de valeur ; rien ne dépend de colonnes.
- Ce que dit l'application (un résultat, un changement d'état) passe par un seul centre d'annonces, utilisant ce que la plateforme offre aux technologies d'assistance, pas l'API d'un seul éditeur.
- L'accessibilité est vérifiée à la main avec les lecteurs d'écran à chaque étape.
