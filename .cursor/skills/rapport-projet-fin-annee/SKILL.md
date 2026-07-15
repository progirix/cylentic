---
name: rapport-projet-fin-annee
description: >
  Rédige et humanise le rapport FINAL de projet de fin d'année Cylentic
  (école d'ingénieurs, Burkina Faso) pour un jury. À utiliser dès qu'on
  rédige, réécrit, humanise ou titre une partie du rapport. Ne pas traiter
  comme un rapport de stage ni comme un PFE. Produit du texte de rapport
  prêt à loler, jamais des consignes destinées à l'étudiant.
---

# Skill : Rapport de projet de fin d'année (Cylentic)

## Contexte à mémoriser (non négociable)

- Document produit : **rapport de projet de fin d'année**.
- Ce n'est **pas** un rapport de stage.
- Ce n'est **pas** un rapport de fin d'études / PFE.
- Dans l'école de l'auteur, un projet est mené **chaque année** avec un rapport ;
  c'est le « petit frère » du PFE, au niveau prépa puis année de cycle ingénieur informatique.
- L'école **n'a pas fourni** de trame officielle.
- La **mise en forme** s'inspire du guide ESTA (Burkina Faso) fourni par l'utilisateur :
  Times New Roman, corps 12, titres 14, légendes 11, interligne 1,5, texte justifié,
  marges 2,5 cm (reliure 1 cm), figures numérotées avec légende en bas,
  tableaux avec titre en haut, numérotation arabe des chapitres,
  pages de tête en romain, corps à partir de l'introduction générale.
- Groupe de **trois** auteurs, **un encadrant principal** et **un second encadrant**.
- Interdiction stricte : tirets longs (—) au milieu des phrases, emojis,
  et tournures caractéristiques des textes générés mécaniquement.
- Les **volumes / plafonds de pages** restent ceux du plan validé
  (`docs/Plan_Rapport_Cylentic.docx`). Ne pas exploser les plafonds.
- Les **titres** des parties/chapitres/sections ne sont pas figés : le skill doit
  **proposer et appliquer** des intitulés clairs, académiques et adaptés au contenu
  réel, tout en respectant la structure et les volumes prévus.
- Lecteur cible : **un jury**. Le texte est le **rapport final**, pas un aide-mémoire,
  pas un plan commenté, pas des instructions du type « tu dois », « dans cette
  section tu expliques », « mets un tableau ici ».

## Nature du texte à produire

Écrire **à la première personne plurielle ou singulière académique** selon
l'usage local du rapport (préférer « nous » de modestie académique si plusieurs
auteurs ; « je » seulement si le règlement / le PDF modèle l'impose).  
Décrire ce qui a été fait dans le projet Cylentic, au passé ou au présent de
présentation scientifique selon la section.

Interdit dans le corps du rapport :
- tutoyer le lecteur ;
- parler comme un coach (« n'oublie pas », « pense à », « évite de ») ;
- meta-commentaires (« dans ce chapitre nous allons voir que… » répété mécaniquement ;
  une courte phrase d'annonce de plan est acceptable une fois en introduction
  de chapitre ou de section majeure) ;
- anglais inutile, emojis, tirets longs décoratifs en milieu de phrase ;
- formules creuses « IA » (voir liste ci-dessous).

Autorisé et attendu :
- démonstration structurée, vocabulaire technique juste ;
- justification des choix ;
- honnêteté sur le périmètre MVP ;
- renvois aux figures UML déjà produites dans `docs/diagrammes/` ;
- ancrage burkinabè factuel (salles info, connexion, surveillance humaine) sans folklore.

Produit Cylentic (source de vérité) : dépôt et comportement réel de la plateforme
(multi-établissement, rôles dont super-admin, examens code/QCM, sandbox Python,
sécurité navigateur, incidents, correction). Ne jamais inventer une fonctionnalité
absente ; si une transition est prévue mais partielle, la présenter comme conception
visée, sans dramatiser.

## volumes à respecter (rappel)

Hors pages de tête : viser **45 à 65 pages** (intro générale → conclusion générale).

| Bloc | Plafond indicatif |
|------|-------------------|
| Pages de tête (garde, dédicace, remerciements, sommaire, sigles, figures, résumé, abstract) | 6 à 8 pages |
| Introduction générale | 2 à 3 pages |
| Chapitre 1 (contexte, problématique, existant) | 10 à 12 pages |
| Chapitre 2 (besoins / spécification) | 8 à 10 pages |
| Chapitre 3 (conception UML) | selon plan déjà défini autour des diagrammes validés |
| Chapitres suivants (réalisation, tests, etc.) | selon `docs/Plan_Rapport_Cylentic.docx` |
| Conclusion générale | selon plan |

En cas de doute sur un plafond, **relire le plan** avant d'allonger.

## Titres

Lors de la rédaction ou de la révision d'une partie :
1. Lire le contenu réel et les diagrammes associés.
2. Proposer un titre de chapitre / section **spécifique**, académique, en français.
3. Éviter les titres génériques vides (« Généralités », « Présentation », « Basé sur le code réel »).
4. Numéroter comme dans un mémoire (1, 1.1, 1.1.1…) sauf si le PDF modèle impose un autre système.
5. Une fois un titre choisi et validé dans le document livré, l'utiliser partout
   (sommaire, renvois, légendes si besoin).

## Humanisation (français académique)

Appliquer ces passes **après** chaque draft :

### Passe 1 — Enlever la voix chatbot
Remplacer ou supprimer :
- « Il est important de noter que », « Il convient de souligner », « Dans le monde d'aujourd'hui »,
  « À l'ère du numérique », « révolutionner », « solution innovante de bout en bout »,
  « robuste et scalable » sans explication, « paradigm », anglicismes inutiles,
  listes à puces décoratives là où un paragraphe structuré suffit,
  triples adjectifs empilés, transitions artificielles (« Par ailleurs », « En outre »,
  « De plus » à chaque phrase).

### Passe 2 — Rythme et précision
- Alterner phrases courtes et moyennes.
- Une idée forte par paragraphe.
- Nommer les acteurs, composants et règles métier concrets (code d'accès, salle d'attente,
  plein écran, sandbox Docker, Redis, MySQL, etc.) quand c'est pertinent.
- Couper les répétitions.

### Passe 3 — Contrôle jury
Se demander : « Un enseignant burkinabè lit ceci sans moi à côté : comprend-il le problème,
ce que nous avons conçu, et ce que le MVP fait vraiment ? »  
Si non, clarifier. Si oui mais le ton donne encore des ordres à l'étudiant, réécrire.

## Mise en forme (en attendant / avec le PDF modèle)

Toujours :
- français correct ;
- titres hiérarchisés ;
- figures et tableaux numérotés avec légendes explicites ;
- citations / références si état de l'art ;
- cohérence typographique (guillemets français « », espaces insécables usuelles devant ; ? ! :).

Dès que le PDF modèle est fourni :
- extraire et appliquer la logique de page de garde, marges, en-têtes/pieds,
  style de sommaire, présentation des figures ;
- ne pas contredire les volumes du plan Cylentic.

## Déclencheurs

Utiliser ce skill dès que l'utilisateur demande de :
- rédiger / réécrire une partie du rapport ;
- humaniser un texte du rapport ;
- trouver / corriger des titres ;
- produire le document Word final d'un chapitre ;
- aligner le style sur le PDF modèle burkinabè.

## Sortie attendue

- Texte **prêt à intégrer** dans le rapport (paragraphes de soutenance), **pas** une fiche méthode.
- Si plusieurs titres sont possibles, en choisir **un** cohérent et l'utiliser dans le livrable ;
  n'énumérer des alternatives que si l'utilisateur le demande explicitement.
- Continuer à s'appuyer sur le code / dépôt GitHub et sur `docs/diagrammes/` pour le fond.
- Réponses de chat en français ; le corps du rapport aussi.
