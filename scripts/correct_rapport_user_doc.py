#!/usr/bin/env python3
"""Applique les corrections encadrant sur le document utilisateur."""

from __future__ import annotations

import re
import shutil
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

SRC = Path("/home/ubuntu/.cursor/projects/workspace/uploads/Rapport_Cylentic__1__8fb9.docx")
OUT = Path("/workspace/docs/Rapport_Cylentic.docx")
BACKUP = Path("/workspace/docs/Rapport_Cylentic_avant_correction.docx")

FIGURE_COMMENTS = {
    "Architecture logique de Cylentic": "La figure {n} présente l'architecture logique de Cylentic : interface web, services métier, persistance des données et sandbox d'exécution du code.",
    "Déploiement de l'infrastructure": "La figure {n} illustre le déploiement physique de l'infrastructure : serveur applicatif, base MySQL, conteneurs Docker et postes clients en salle.",
    "Cas d'utilisation du Super Admin": "La figure {n} décrit les interactions du Super Admin avec la plateforme : gestion des établissements et pilotage global.",
    "Cas d'utilisation de l'administrateur (organisation)": "La figure {n} montre les cas d'utilisation de l'administrateur d'établissement pour la gestion de l'organisation scolaire.",
    "Cas d'utilisation de l'administrateur (comptes)": "La figure {n} présente la gestion des comptes professeurs et étudiants par l'administrateur d'établissement.",
    "Cas d'utilisation du professeur (examens)": "La figure {n} détaille les actions du professeur lors de la création, de la publication et de la configuration d'un examen.",
    "Cas d'utilisation du professeur (suivi)": "La figure {n} illustre le suivi en direct des participations et la consultation des résultats par le professeur.",
    "Cas d'utilisation de l'étudiant": "La figure {n} représente le parcours étudiant : connexion, salle d'attente, composition et soumission de l'examen.",
    "Classes organisation et comptes": "La figure {n} modélise les classes liées à l'organisation, aux établissements et aux comptes utilisateurs.",
    "Classes conception d'examen": "La figure {n} présente les classes intervenant dans la conception d'un examen et de ses exercices.",
    "Classes passation et correction": "La figure {n} décrit les classes de la passation d'examen, de la participation et de la correction automatique.",
    "Objets organisation": "La figure {n} montre un diagramme d'objets illustrant les relations entre établissement, classes et utilisateurs.",
    "Objets conception d'examen": "La figure {n} illustre un examen instancié avec ses exercices et tests unitaires associés.",
    "Objets passation": "La figure {n} présente une participation étudiante en cours avec copie, incidents et résultats.",
    "Composants vue d'ensemble": "La figure {n} donne une vue d'ensemble des composants logiciels de Cylentic et de leurs dépendances.",
    "Composants administration et authentification": "La figure {n} détaille les composants d'administration, d'authentification et de gestion des rôles.",
    "Composants examens et passation": "La figure {n} présente les composants chargés des examens, de la passation contrôlée et de l'exécution de code.",
    "États du cycle de vie d'un examen": "La figure {n} montre les états successifs d'un examen, du brouillon à la clôture des résultats.",
    "Séquence de connexion": "La figure {n} décrit la séquence d'authentification et d'attribution du rôle à la connexion.",
    "Séquence de publication d'un examen": "La figure {n} illustre la publication d'un examen et la génération du code d'accès.",
    "Séquence d'accès étudiant": "La figure {n} présente l'accès étudiant à l'examen via identifiant, mot de passe et code d'accès.",
    "Séquence d'exécution du code": "La figure {n} montre l'exécution du code Python dans la sandbox Docker isolée.",
    "Séquence de soumission et correction": "La figure {n} décrit la soumission de la copie et le déclenchement de la correction automatique.",
    "Séquence d'enregistrement d'un incident": "La figure {n} illustre l'enregistrement d'un incident de passation et son traitement.",
    "Activité accès et salle d'attente": "La figure {n} présente le flux d'activité depuis la connexion jusqu'à la salle d'attente.",
    "Activité composition et soumission": "La figure {n} décrit les activités de composition, d'exécution d'essai et de soumission finale.",
    "Page de connexion multi rôles": "La figure {n} montre l'interface de connexion permettant l'accès selon le rôle de l'utilisateur.",
    "Espace administrateur d'établissement": "La figure {n} présente l'espace de gestion réservé à l'administrateur d'établissement.",
    "Composition d'un examen côté professeur": "La figure {n} illustre l'interface de création et d'édition d'un examen par le professeur.",
    "Publication et code d'accès d'examen": "La figure {n} montre l'écran de publication d'un examen et l'affichage du code d'accès.",
    "Suivi live des participations": "La figure {n} présente le tableau de suivi en direct des étudiants pendant l'épreuve.",
    "Résultats et exports professeur": "La figure {n} illustre la consultation des résultats et les options d'export pour le professeur.",
    "Consignes et activation du plein écran": "La figure {n} montre les consignes de sécurité et l'activation du mode plein écran côté étudiant.",
    "Salle d'attente avant le démarrage de l'examen": "La figure {n} présente la salle d'attente affichée avant le démarrage officiel de l'épreuve.",
    "Environnement de composition pendant l'épreuve": "La figure {n} illustre l'éditeur de code et l'environnement de composition pendant l'examen.",
    "Page d'accueil Cylentic": "La figure {n} montre la page d'accueil publique de la plateforme Cylentic.",
}

BIBLIO = [
    "[1] Object Management Group, OMG Unified Modeling Language (OMG UML), Version 2.5.1, 2017.",
    "[2] R. S. Pressman et B. R. Maxim, Software Engineering: A Practitioner's Approach, 9e éd., McGraw-Hill, 2019.",
    "[3] I. Sommerville, Software Engineering, 10e éd., Pearson, 2016.",
    "[4] G. Booch, J. Rumbaugh et I. Jacobson, The Unified Modeling Language User Guide, 2e éd., Addison-Wesley, 2005.",
    "[4] ESTA, Guide du stagiaire Master/Ingénieur, année académique 2024-2025.",  # retiré du livrable
    "[6] M. Fowler, Patterns of Enterprise Application Architecture, Addison-Wesley, 2002.",
]

WEBO = [
    "[1] Vercel, Next.js Documentation, https://nextjs.org/docs, consulté le 15/07/2026 à 09h20.",
    "[2] Prisma, Prisma Documentation, https://www.prisma.io/docs, consulté le 15/07/2026 à 09h45.",
    "[3] Oracle, MySQL 8 Documentation, https://dev.mysql.com/doc/, consulté le 15/07/2026 à 10h15.",
    "[4] Redis Ltd, Redis Documentation, https://redis.io/docs/, consulté le 15/07/2026 à 10h40.",
    "[5] Docker Inc., Docker Documentation, https://docs.docker.com/, consulté le 15/07/2026 à 11h25.",
    "[6] freeCodeCamp, https://www.freecodecamp.org/, consulté le 15/07/2026 à 14h10.",
    "[7] Moodle HQ, Moodle Documentation, https://docs.moodle.org/, consulté le 15/07/2026 à 15h05.",
    "[8] Judge0, Judge0 CE, https://judge0.com/, consulté le 15/07/2026 à 16h30.",
    "[9] Monaco Editor, https://microsoft.github.io/monaco-editor/, consulté le 15/07/2026 à 17h05.",
    "[10] PlantUML, https://plantuml.com/, consulté le 15/07/2026 à 17h40.",
]


def set_font(run, *, bold=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(12)
    run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def set_para_text(para: Paragraph, text: str, *, align=None, bold=False, first_line=True):
    para.clear()
    run = para.add_run(text)
    set_font(run, bold=bold)
    if align == "center":
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "left":
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    else:
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = para.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(8)
    if first_line and para.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY:
        pf.first_line_indent = Cm(0.75)
    else:
        pf.first_line_indent = Cm(0)


def insert_after(anchor: Paragraph, text: str, *, style=None, align=None, bold=False, first_line=True) -> Paragraph:
    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    para = Paragraph(new_p, anchor._parent)
    if style:
        try:
            para.style = style
        except KeyError:
            pass
    set_para_text(para, text, align=align, bold=bold, first_line=first_line)
    return para


def delete_paragraph(para: Paragraph):
    p = para._element
    p.getparent().remove(p)


def find_para(doc: Document, text: str, *, start=0, exact=False):
    for i, p in enumerate(doc.paragraphs):
        if i < start:
            continue
        t = p.text.strip()
        if exact and t == text:
            return p, i
        if not exact and t == text:
            return p, i
    return None, -1


def find_heading(doc: Document, text: str, start=0):
    for i, p in enumerate(doc.paragraphs):
        if i < start:
            continue
        if p.text.strip() == text and (p.style and "Heading" in p.style.name):
            return p, i
    return None, -1


def figure_title(caption: str) -> str | None:
    m = re.match(r"Figure\s+\d+\s*:\s*(.+)", caption.strip())
    return m.group(1).strip() if m else None


def sort_sigles(doc: Document):
    h, idx = find_heading(doc, "Liste des sigles et abréviations")
    if not h:
        return
    entries = []
    paras = doc.paragraphs
    i = idx + 1
    while i < len(paras):
        p = paras[i]
        if p.style and p.style.name.startswith("Heading"):
            break
        t = p.text.strip()
        if t and " : " in t:
            abbr, _, rest = t.partition(" : ")
            entries.append((abbr.strip().upper(), abbr.strip(), rest.strip()))
            delete_paragraph(p)
            paras = doc.paragraphs
            continue
        i += 1
    entries.sort(key=lambda x: x[0])
    anchor = h
    for _, abbr, rest in entries:
        anchor = insert_after(anchor, f"{abbr} : {rest}", align="left", first_line=False)


def add_figure_comments(doc: Document):
    in_body = False
    i = 0
    while i < len(doc.paragraphs):
        p = doc.paragraphs[i]
        t = p.text.strip()
        if t == "Introduction générale" and p.style and "Heading" in p.style.name:
            in_body = True
        if not in_body or not t.startswith("Figure ") or "\t" in t:
            i += 1
            continue
        title = figure_title(t)
        if not title:
            i += 1
            continue
        n = re.search(r"Figure\s+(\d+)", t)
        num = int(n.group(1)) if n else 0
        nxt = doc.paragraphs[i + 1].text.strip() if i + 1 < len(doc.paragraphs) else ""
        if nxt.startswith("La figure "):
            i += 1
            continue
        tpl = FIGURE_COMMENTS.get(title)
        if tpl:
            insert_after(p, tpl.format(n=num))
            i += 2
            continue
        i += 1


def move_comparison_to_ch2(doc: Document):
    """Déplace tableau comparatif et positionnement du ch.1 vers le ch.2."""
    pos_h, _ = find_heading(doc, "1.4 Positionnement de Cylentic")
    if not pos_h:
        pos_h, _ = find_heading(doc, "1.4 Synthèse des lacunes du domaine")
    concl_h, _ = find_heading(doc, "1.5 Conclusion partielle")
    if not concl_h:
        concl_h, _ = find_heading(doc, "1.5 Conclusion")

    pos_texts = []
    if pos_h and concl_h:
        cur = pos_h._p.getnext()
        end = concl_h._p
        while cur is not None and cur is not end:
            nxt = cur.getnext()
            if cur.tag.endswith("}p"):
                para = Paragraph(cur, pos_h._parent)
                txt = para.text.strip()
                if txt:
                    pos_texts.append(txt)
            cur = nxt

    cmp_table = doc.tables[0]._tbl
    cmp_table.getparent().remove(cmp_table)

    for p in list(doc.paragraphs):
        tx = p.text.strip()
        if tx.startswith("Tableau 1 : Comparaison"):
            delete_paragraph(p)
        if tx.startswith("Au total, aucune de ces solutions"):
            delete_paragraph(p)
        if pos_h and p._p is pos_h._p:
            delete_paragraph(p)
    for txt in pos_texts:
        for p in list(doc.paragraphs):
            if p.text.strip() == txt and p.style and "Heading" not in p.style.name:
                delete_paragraph(p)
                break

    # Renommer d'abord les sections existantes du ch.2
    renumber_ch2_headings(doc)

    target, _ = find_heading(doc, "2.3 Périmètre du projet et du MVP")
    if not target:
        return

  # insérer 2.1 / 2.2 juste avant 2.3
    h21 = OxmlElement("w:p")
    target._p.addprevious(h21)
    h21_para = Paragraph(h21, target._parent)
    try:
        h21_para.style = "Heading 2"
    except KeyError:
        pass
    set_para_text(h21_para, "2.1 Comparaison des solutions existantes", bold=True, first_line=False)

    p21 = insert_after(h21_para, "Pour objectiver l'analyse de l'état de l'art, le tableau ci-dessous compare les principales familles de solutions aux exigences d'un examen de programmation surveillé en salle.")
    p21._p.addnext(deepcopy(cmp_table))
    cap = insert_after(p21, "Tableau 1 : Comparaison des solutions existantes et de Cylentic", bold=True, align="left", first_line=False)

    h22 = insert_after(cap, "2.2 Positionnement de Cylentic", style="Heading 2")
    anchor = h22
    for txt in pos_texts:
        anchor = insert_after(anchor, txt)


def renumber_ch2_headings(doc: Document):
    mapping = {
        "2.1 Périmètre du projet et du MVP": "2.3 Périmètre du projet et du MVP",
        "2.2 Identification des acteurs": "2.4 Identification des acteurs",
        "2.3 Besoins fonctionnels": "2.5 Besoins fonctionnels",
        "2.4 Besoins non fonctionnels": "2.6 Besoins non fonctionnels",
        "2.5 Règles métier structurantes": "2.7 Règles métier structurantes",
        "2.6 Scénarios d'usage prioritaires": "2.8 Scénarios d'usage prioritaires",
        "2.7 Conclusion partielle": "2.9 Conclusion",
        "2.7 Conclusion": "2.9 Conclusion",
    }
    for p in doc.paragraphs:
        t = p.text.strip()
        if t in mapping and p.style and "Heading" in p.style.name:
            set_para_text(p, mapping[t], bold=True, first_line=False)


def add_cost_section(doc: Document):
    h, _ = find_heading(doc, "5.6 Conclusion partielle")
    if not h:
        h, _ = find_heading(doc, "5.6 Conclusion")
    if not h:
        return
    old_concl_text = ""
    nxt = h._p.getnext()
    if nxt is not None and nxt.tag.endswith("}p"):
        old_concl_text = Paragraph(nxt, h._parent).text.strip()
        delete_paragraph(Paragraph(nxt, h._parent))

    set_para_text(h, "5.6 Coût estimatif du projet", bold=True, first_line=False)
    intro = insert_after(
        h,
        "Le tableau ci-dessous estime le coût du projet pour un déploiement pilote "
        "sur douze mois, dimensionné pour environ 200 étudiants simultanés. "
        "Le développement est valorisé au forfait pour l'équipe de trois personnes. "
        "L'hébergement correspond à une configuration serveur capable d'absorber "
        "un pic de composition en salle.",
    )
    # table after intro
    rows = [
        ["Poste", "Détail", "Coût estimé (FCFA)"],
        ["Développement", "3 développeurs × 4 mois × 200 000 FCFA/mois", "2 400 000"],
        [
            "Hébergement VPS",
            "Serveur 8 vCPU, 16 Go RAM, 12 mois à 30 000 FCFA/mois, "
            "capacité d'environ 200 étudiants simultanés",
            "360 000",
        ],
        ["Nom de domaine", "Enregistrement annuel", "15 000"],
        ["Certificat SSL", "Let's Encrypt (gratuit)", "0"],
        ["Outils", "IDE, Git, Docker (open source)", "0"],
        ["Total", "Déploiement pilote sur 12 mois", "2 775 000"],
    ]
    table = doc.add_table(rows=len(rows), cols=3)
    table.style = "Table Grid"
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            table.rows[ri].cells[ci].text = val
    tbl = table._tbl
    tbl.getparent().remove(tbl)
    intro._p.addnext(tbl)
    cap = insert_after(Paragraph(tbl, intro._parent), "Tableau 4 : Coût estimatif du projet Cylentic", bold=True, align="left", first_line=False)
    src = insert_after(cap, "Source : estimation réalisée par l'équipe projet, juillet 2026.", align="left", first_line=False)
    h57 = insert_after(src, "5.7 Conclusion", style="Heading 2")
    final = (
        old_concl_text
        if old_concl_text
        else "Les tests confirment la faisabilité du MVP dans son périmètre. Les limites "
        "identifiées ouvrent des perspectives d'évolution sans remettre en cause la "
        "pertinence de la solution pour un usage pilote en salle informatique."
    )
    insert_after(h57, final)


def split_bibliography(doc: Document):
    h, idx = find_heading(doc, "Bibliographie et webographie")
    if not h:
        h, idx = find_heading(doc, "Bibliographie")
    if not h:
        return

    annex_h, _ = find_heading(doc, "Annexes")
    # supprimer tout le contenu entre bibliographie et annexes
    to_delete = []
    capture = False
    for p in doc.paragraphs:
        if p._p is h._p:
            capture = True
            continue
        if annex_h and p._p is annex_h._p:
            break
        if capture:
            to_delete.append(p)
    for p in to_delete:
        delete_paragraph(p)

    set_para_text(h, "Bibliographie", bold=True, first_line=False)
    anchor = h
    for ref in BIBLIO:
        anchor = insert_after(anchor, ref, align="left", first_line=False)

    pb = insert_after(anchor, "")
    br_run = pb.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    br_run._r.append(br)

    wh = insert_after(pb, "Webographie", style="Heading 1")
    wanchor = wh
    for ref in WEBO:
        wanchor = insert_after(wanchor, ref, align="left", first_line=False)


def apply_corrections():
    shutil.copy2(SRC, BACKUP)
    doc = Document(str(SRC))
    print("[1/6] Dédicace, sigles, mots-clés…")

    # 1 Dédicace
    for p in doc.paragraphs:
        if p.text.strip().startswith("À nos familles"):
            set_para_text(p, "À ma famille.", align="center", first_line=False)
            break

    sort_sigles(doc)

    # 3 Mots-clés
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip() == "Abstract" and p.style and "Heading" in p.style.name:
            # resume keywords before abstract
            prev = doc.paragraphs[i - 1]
            if "Mots-clés" not in prev.text:
                insert_after(
                    prev,
                    "Mots-clés : examen de programmation, plateforme web, intégrité académique, "
                    "sandbox, correction automatique, école d'ingénieurs.",
                    bold=True,
                    first_line=False,
                )
            break
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip() == "Introduction générale" and p.style and "Heading" in p.style.name:
            prev = doc.paragraphs[i - 1]
            if "Keywords" not in prev.text:
                insert_after(
                    prev,
                    "Keywords: programming exam, web platform, academic integrity, sandbox, "
                    "automatic grading, engineering school.",
                    bold=True,
                    first_line=False,
                )
            break

    print("[2/6] Introduction, problématique, objectifs…")

    # 6 Intro enrichie — avant Problématique
    probl_h, _ = find_heading(doc, "Problématique")
    if probl_h:
        prev = probl_h
        for ptxt in doc.paragraphs:
            if ptxt._p is probl_h._p.getprevious():
                prev = ptxt
                break
        # update last intro paragraph about chapters
        for p in doc.paragraphs:
            if p.text.strip().startswith("Cinq chapitres suivent"):
                set_para_text(
                    p,
                    "Le rapport s'organise en cinq chapitres. Le premier présente l'état de "
                    "l'art. Le deuxième formalise les besoins et compare les solutions "
                    "existantes. Le troisième présente la conception. Le quatrième décrit la "
                    "réalisation. Le cinquième discute les tests, les limites et les perspectives.",
                )
        anchor = prev
        blocks = [
            (
                "Au terme de ce travail, plusieurs résultats sont attendus : une analyse "
                "structurée des limites des outils existants pour l'évaluation de la "
                "programmation en salle ; une conception documentée de Cylentic (UML, "
                "architecture, données) ; un prototype fonctionnel couvrant les parcours "
                "critiques du MVP ; une validation par tests des scénarios d'examen surveillé."
            ),
            "L'atteinte de ces objectifs repose sur les hypothèses de recherche suivantes :",
            "• un verrouillage suffisant du navigateur, couplé à la journalisation des incidents, permet de restaurer la crédibilité des épreuves pratiques sur machine ;",
            "• l'exécution isolée du code dans une sandbox et la correction automatique par tests unitaires offrent une évaluation fiable et reproductible ;",
            "• une architecture web multi établissement, déployable sans installation lourde côté étudiant, répond aux contraintes des salles informatiques partagées.",
            (
                "Pour répondre à la problématique, nous avons adopté une démarche "
                "méthodologique structurée en cinq étapes : revue de l'état de l'art et "
                "analyse comparative des solutions existantes ; spécification des besoins et "
                "définition du périmètre du MVP ; conception UML et modélisation de "
                "l'architecture ; réalisation itérative avec Next.js, Prisma et MySQL ; "
                "validation par tests de parcours complets et contrôle de non régression."
            ),
        ]
        for b in blocks:
            anchor = insert_after(anchor, b, first_line=b.startswith("Au") or b.startswith("Pour") or b.startswith("L'"))

    # 4-5 Problématique et objectif
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("Comment organiser un examen"):
            set_para_text(
                p,
                "Face à la montée des assistants de génération de code, comment garantir "
                "l'intégrité et la crédibilité de l'évaluation de la programmation sur "
                "machine en salle informatique, tout en permettant l'exécution réelle du code "
                "et une correction fiable pour le professeur ?",
            )
        if t.startswith("L'objectif général consiste"):
            set_para_text(
                p,
                "L'objectif général consiste à concevoir une plateforme web d'examens de "
                "programmation sécurisés, nommée Cylentic.",
            )
        if t.startswith("Le travail a suivi un enchaînement"):
            delete_paragraph(p)

    print("[3/6] Chapitre 1 → état de l'art, déplacement comparaison…")

    # 7 Chapitre 1
    for p in doc.paragraphs:
        t = p.text.strip()
        if t == "Chapitre 1 : Contexte et étude de l'existant":
            set_para_text(p, "Chapitre 1 : État de l'art", bold=True, first_line=False)
        if t.startswith("Ce chapitre replace le projet"):
            set_para_text(
                p,
                "Ce chapitre présente l'état de l'art du domaine : contexte pédagogique, "
                "contraintes locales et panorama des solutions existantes. La comparaison "
                "détaillée et le positionnement de Cylentic sont traités au chapitre 2.",
            )
        if t == "1.3 Examen des solutions existantes":
            set_para_text(p, "1.3 Panorama des solutions existantes", bold=True, first_line=False)
        if t.startswith("Nous partons de l'hypothèse suivante"):
            delete_paragraph(p)

    # synthèse ch1 avant conclusion (seulement si 1.4 positionnement encore présent)
    pos14, _ = find_heading(doc, "1.4 Positionnement de Cylentic")
    concl15, _ = find_heading(doc, "1.5 Conclusion partielle")
    if not concl15:
        concl15, _ = find_heading(doc, "1.5 Conclusion")
    if pos14 and concl15:
        h14 = insert_after(pos14, "1.4 Synthèse des lacunes du domaine", style="Heading 2")
        set_para_text(pos14, "1.4 Synthèse des lacunes du domaine", bold=True, first_line=False)
        insert_after(
            h14,
            "L'état de l'art montre que les outils disponibles couvrent chacun une facette "
            "du problème : apprentissage ouvert, gestion de cours, surveillance généraliste "
            "ou exécution isolée. Aucun ne réunit composition sécurisée, exécution réelle, "
            "correction automatique et traçabilité pédagogique dans un cadre adapté aux "
            "salles informatiques d'une école d'ingénieurs. Cette lacune justifie l'étude "
            "d'une solution dédiée.",
        )
    elif concl15:
        prev_idx = [i for i, x in enumerate(doc.paragraphs) if x._p is concl15._p][0] - 1
        prev = doc.paragraphs[prev_idx]
        if prev.text.strip() and "Heading" not in (prev.style.name if prev.style else ""):
            h14 = insert_after(prev, "1.4 Synthèse des lacunes du domaine", style="Heading 2")
            insert_after(
                h14,
                "L'état de l'art montre que les outils disponibles couvrent chacun une facette "
                "du problème : apprentissage ouvert, gestion de cours, surveillance généraliste "
                "ou exécution isolée. Aucun ne réunit composition sécurisée, exécution réelle, "
                "correction automatique et traçabilité pédagogique dans un cadre adapté aux "
                "salles informatiques d'une école d'ingénieurs. Cette lacune justifie l'étude "
                "d'une solution dédiée.",
            )

    move_comparison_to_ch2(doc)

    print("[4/6] Conclusions de chapitres, coût estimatif…")

    for p in doc.paragraphs:
        if "Conclusion partielle" in p.text and p.style and "Heading" in p.style.name:
            set_para_text(p, p.text.replace("Conclusion partielle", "Conclusion"), bold=True, first_line=False)

    add_cost_section(doc)

    print("[5/6] Commentaires des figures, bibliographie…")

    add_figure_comments(doc)
    split_bibliography(doc)

    print("[6/6] Sauvegarde…")
    for p in doc.paragraphs:
        if p.style and p.style.name.startswith("toc") and "Conclusion partielle" in p.text:
            for r in p.runs:
                r.text = r.text.replace("Conclusion partielle", "Conclusion")
    doc.save(OUT)
    print("OK ->", OUT)


if __name__ == "__main__":
    apply_corrections()
