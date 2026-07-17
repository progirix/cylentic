# Références de style — rapport de projet de fin d'année Cylentic

## Identité du document
- Type : rapport de **projet de fin d'année** (projet annuel d'école d'ingénieurs).
- Pas un rapport de stage.
- Pas un PFE / mémoire de fin d'études (niveau voisin, amplitude plus restreinte).
- Cadre : Burkina Faso, filière informatique.
- Lecteur : jury.
- Produit : Cylentic (examens de programmation sécurisés en navigateur).

## Ce que le texte doit être
Texte final de rapport. Description, analyse, conception, réalisation.
Jamais une to-do list pour l'étudiant auteur.

## Formules à éviter (marqueurs IA / oral de coach)
- « Il est important de noter que »
- « Dans le monde d'aujourd'hui » / « À l'ère du numérique »
- « solution innovante » sans contenu
- « robuste, sécurisé et scalable » empilé sans critère
- « nous allons voir » répété mécaniquement
- « n'oublie pas », « tu dois », « pense à »
- titres du type « basé sur le code réel »

## Terminologie produit utile
Super Admin, Admin établissement, Professeur, Étudiant, surveillant physique (sans compte),
code d'accès, salle d'attente, composition, Monaco, sandbox Python / Docker,
incidents (plein écran, onglet, presse-papiers…), correction automatique, MySQL, Redis, Next.js.

## Volumes
Suivre `docs/Plan_Rapport_Cylentic.docx`. Global corps : ~45–65 pages.

## Diagrammes
Source : `docs/diagrammes/*.puml` (architecture logique `00_` → cas d'utilisation → activité 16a/16b).
Exporter en PNG (`plantuml -tpng`) ; le script `build_rapport_final_esta.py` les insère dans le Word.
