#!/usr/bin/env python3
"""
Rapport Cylentic — version finale pour dépôt / envoi au jury.
Forme inspirée du guide ESTA. Aucune consigne à l'auteur dans le texte.
Sommaire, listes et table des matières déjà rédigés (liens internes).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

OUT = Path("/workspace/docs/Rapport_Cylentic.docx")
ALSO = Path("/workspace/docs/Rapport_Cylentic_Carcasse_Chapitre3.docx")
EXTRACTED = Path("/workspace/scripts/_rapport_extracted.json")

# Infos de couverture (à ajuster seulement si l'équipe le souhaite)
ECOLE = "École Supérieure des Sciences et Technologies (ESST)"
FILIERE = "Génie Informatique"
ANNEE = "2025-2026"
AUTEURS = [
    "SAWADOGO Ibrahim",
    "OUÉDRAOGO Aïcha",
    "TANKOANO Martin",
]
ENCADRANT_P = "Dr. KABORÉ Jean-Baptiste, Enseignant-chercheur"
ENCADRANT_S = "M. ZONGO Paul, Ingénieur informatique"


def set_run_font(run, size=12, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def configure_styles(doc: Document):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(8)

    for i, size in [(1, 14), (2, 12), (3, 12)]:
        st = doc.styles[f"Heading {i}"]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        st.paragraph_format.space_before = Pt(12 if i == 1 else 8)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.5


def setup_margins(section):
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.5)  # 2.5 + reliure 1
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)


def add_page_number(section, roman=False):
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in list(p.runs):
        r._element.getparent().remove(r._element)

    run = p.add_run()
    r = run._r
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = r"PAGE \* ROMAN" if roman else "PAGE"
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = "i" if roman else "1"
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
    r.append(fc3)
    set_run_font(run, size=12)


def bookmark_heading(paragraph: Paragraph, name: str):
    """Add bookmark around heading paragraph text."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)[:40]
    tag = paragraph._p
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(abs(hash(name)) % 100000))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), start.get(qn("w:id")))
    tag.insert(0, start)
    tag.append(end)
    return name


def add_internal_link(paragraph: Paragraph, bookmark: str, text: str):
    bookmark = re.sub(r"[^A-Za-z0-9_]", "_", bookmark)[:40]
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), bookmark)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0000FF")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "24")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rPr.append(rFonts)
    rPr.append(sz)
    rPr.append(color)
    rPr.append(u)
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_external_hyperlink(paragraph: Paragraph, url: str, text: str):
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0000FF")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "24")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rPr.append(rFonts)
    rPr.append(sz)
    rPr.append(color)
    rPr.append(u)
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def p(
    doc,
    text="",
    *,
    size=12,
    bold=False,
    italic=False,
    align="justify",
    first_line=True,
    space_after=8,
):
    para = doc.add_paragraph()
    if align == "center":
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "left":
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    else:
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = para.paragraph_format
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.5
    if first_line and align == "justify" and text:
        pf.first_line_indent = Cm(0.75)
    if text:
        run = para.add_run(text)
        set_run_font(run, size=size, bold=bold, italic=italic)
    return para


def h(doc, text, level=1, bookmark=None):
    para = doc.add_heading(text, level=level)
    for run in para.runs:
        set_run_font(run, size=14 if level == 1 else 12, bold=True)
    para.paragraph_format.line_spacing = 1.5
    bm = bookmark or text
    bookmark_heading(para, bm)
    return para


def toc_line(doc, title: str, bookmark: str, indent=0):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.space_after = Pt(2)
    para.paragraph_format.line_spacing = 1.5
    para.paragraph_format.left_indent = Cm(0.75 * indent)
    add_internal_link(para, bookmark, title)
    return para


def figure_slot(doc, title: str):
    # Légende seule : l'image sera insérée juste au-dessus dans Word.
    p(doc, "", first_line=False, space_after=24)
    p(doc, f"Figure : {title}", size=11, align="center", first_line=False, space_after=10)


def add_table_with_title(doc, title: str, rows: list[list[str]], source: str):
    p(doc, f"Tableau : {title}", size=11, bold=True, align="left", first_line=False, space_after=4)
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = val
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, size=10, bold=(i == 0))
    p(doc, f"Source : {source}", size=10, italic=True, align="left", first_line=False, space_after=10)


def clean(text: str) -> str:
    text = text.replace("—", ",").replace("–", "-")
    text = re.sub(r"\(Texte à personnaliser.*?\)", "", text)
    text = re.sub(r"\(Compléter ou modifier.*?\)", "", text)
    text = re.sub(r"Dans Word.*", "", text)
    text = re.sub(r"Cliquez droit.*", "", text)
    text = re.sub(r"Mettre à jour les champs.*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def page_break(doc):
    doc.add_page_break()


def cover_block(doc):
    for _ in range(1):
        p(doc, "", first_line=False, space_after=6)
    p(doc, "BURKINA FASO", bold=True, align="center", first_line=False, space_after=2)
    p(doc, "La Patrie ou la Mort, nous Vaincrons", italic=True, align="center", first_line=False, space_after=10)
    p(
        doc,
        "Ministère de l'Enseignement Supérieur, de la Recherche et de l'Innovation",
        align="center",
        size=11,
        first_line=False,
        space_after=10,
    )
    p(doc, ECOLE, bold=True, align="center", first_line=False, space_after=4)
    p(doc, f"Filière / Option : {FILIERE}", align="center", first_line=False, space_after=14)
    p(doc, "RAPPORT DE PROJET DE FIN D'ANNÉE", bold=True, size=14, align="center", first_line=False, space_after=10)
    p(
        doc,
        "Cylentic : plateforme web sécurisée d'examens de programmation",
        bold=True,
        size=14,
        align="center",
        first_line=False,
        space_after=16,
    )
    p(doc, "Présenté par :", align="center", first_line=False, space_after=4)
    for a in AUTEURS:
        p(doc, a, align="center", first_line=False, space_after=2)
    p(doc, "", first_line=False, space_after=8)
    p(doc, f"Encadrant principal : {ENCADRANT_P}", align="center", first_line=False, space_after=4)
    p(doc, f"Encadrant : {ENCADRANT_S}", align="center", first_line=False, space_after=14)
    p(doc, f"Année académique {ANNEE}", align="center", first_line=False, space_after=4)


FIGURES = [
    ("Architecture logique de Cylentic", "bm_fig_arch"),
    ("Déploiement de l'infrastructure", "bm_fig_deploy"),
    ("Cas d'utilisation du Super Admin", "bm_fig_uc_sa"),
    ("Cas d'utilisation de l'administrateur (organisation)", "bm_fig_uc_ao"),
    ("Cas d'utilisation de l'administrateur (comptes)", "bm_fig_uc_ac"),
    ("Cas d'utilisation du professeur (examens)", "bm_fig_uc_pe"),
    ("Cas d'utilisation du professeur (suivi)", "bm_fig_uc_ps"),
    ("Cas d'utilisation de l'étudiant", "bm_fig_uc_et"),
    ("Classes organisation et comptes", "bm_fig_cl_org"),
    ("Classes conception d'examen", "bm_fig_cl_ex"),
    ("Classes passation et correction", "bm_fig_cl_pass"),
    ("Objets organisation", "bm_fig_ob_org"),
    ("Objets conception d'examen", "bm_fig_ob_ex"),
    ("Objets passation", "bm_fig_ob_pass"),
    ("Composants vue d'ensemble", "bm_fig_cp_all"),
    ("Composants administration et authentification", "bm_fig_cp_auth"),
    ("Composants examens et passation", "bm_fig_cp_ex"),
    ("États du cycle de vie d'un examen", "bm_fig_etat"),
    ("Séquence de connexion", "bm_fig_seq_login"),
    ("Séquence de publication d'un examen", "bm_fig_seq_pub"),
    ("Séquence d'accès étudiant", "bm_fig_seq_acc"),
    ("Séquence d'exécution du code", "bm_fig_seq_run"),
    ("Séquence de soumission et correction", "bm_fig_seq_sub"),
    ("Séquence d'enregistrement d'un incident", "bm_fig_seq_inc"),
    ("Activité accès et salle d'attente", "bm_fig_act_a"),
    ("Activité composition et soumission", "bm_fig_act_b"),
    ("Salle d'attente avant le démarrage de l'examen", "bm_fig_wait"),
    ("Environnement de composition pendant l'épreuve", "bm_fig_compose"),
]

TABLES = [
    "Comparaison des solutions existantes et de Cylentic",
    "Correspondance entre acteurs et responsabilités",
    "Principales tables persistantes et rôle",
]

SOMMAIRE = [
    ("Dédicace", "bm_dedicace"),
    ("Remerciements", "bm_remerciements"),
    ("Liste des sigles et abréviations", "bm_sigles"),
    ("Liste des figures", "bm_liste_figures"),
    ("Liste des tableaux", "bm_liste_tableaux"),
    ("Résumé", "bm_resume"),
    ("Abstract", "bm_abstract"),
    ("Introduction générale", "bm_intro"),
    ("Problématique", "bm_probl"),
    ("Chapitre 1 : Contexte et étude de l'existant", "bm_ch1"),
    ("Chapitre 2 : Analyse des besoins et spécification du système", "bm_ch2"),
    ("Chapitre 3 : Conception du système Cylentic", "bm_ch3"),
    ("Chapitre 4 : Réalisation et mise en œuvre", "bm_ch4"),
    ("Chapitre 5 : Tests, résultats, limites et perspectives", "bm_ch5"),
    ("Conclusion générale", "bm_concl"),
    ("Bibliographie et webographie", "bm_biblio"),
    ("Annexes", "bm_annexes"),
]

TDM = [
    ("Introduction générale", "bm_intro", 0),
    ("Problématique", "bm_probl", 0),
    ("Chapitre 1 : Contexte et étude de l'existant", "bm_ch1", 0),
    ("1.1 Contexte pédagogique et technologique", "bm_ch1_1", 1),
    ("1.2 Sous-problèmes et contraintes locales", "bm_ch1_2", 1),
    ("1.3 Examen des solutions existantes", "bm_ch1_3", 1),
    ("1.4 Positionnement de Cylentic", "bm_ch1_4", 1),
    ("1.5 Conclusion partielle", "bm_ch1_5", 1),
    ("Chapitre 2 : Analyse des besoins et spécification du système", "bm_ch2", 0),
    ("2.1 Périmètre du projet et du MVP", "bm_ch2_1", 1),
    ("2.2 Identification des acteurs", "bm_ch2_2", 1),
    ("2.3 Besoins fonctionnels", "bm_ch2_3", 1),
    ("2.4 Besoins non fonctionnels", "bm_ch2_4", 1),
    ("2.5 Règles métier structurantes", "bm_ch2_5", 1),
    ("2.6 Scénarios d'usage prioritaires", "bm_ch2_6", 1),
    ("2.7 Conclusion partielle", "bm_ch2_7", 1),
    ("Chapitre 3 : Conception du système Cylentic", "bm_ch3", 0),
    ("3.1 Démarche de conception", "bm_ch3_1", 1),
    ("3.2 Architecture générale et déploiement", "bm_ch3_2", 1),
    ("3.3 Vue des cas d'utilisation", "bm_ch3_3", 1),
    ("3.4 Structure statique : classes et objets", "bm_ch3_4", 1),
    ("3.5 Organisation en composants", "bm_ch3_5", 1),
    ("3.6 Dynamique du système", "bm_ch3_6", 1),
    ("3.7 Conception des données", "bm_ch3_7", 1),
    ("3.8 Conception de la sécurité de passation", "bm_ch3_8", 1),
    ("3.9 Conception de la correction automatique", "bm_ch3_9", 1),
    ("3.10 Conclusion partielle", "bm_ch3_10", 1),
    ("Chapitre 4 : Réalisation et mise en œuvre", "bm_ch4", 0),
    ("4.1 Environnement de travail", "bm_ch4_1", 1),
    ("4.2 Choix technologiques", "bm_ch4_2", 1),
    ("4.3 Organisation du code et architecture applicative", "bm_ch4_3", 1),
    ("4.4 Réalisation des modules principaux", "bm_ch4_4", 1),
    ("4.5 Points techniques difficiles", "bm_ch4_5", 1),
    ("4.6 Déploiement", "bm_ch4_6", 1),
    ("4.7 Conclusion partielle", "bm_ch4_7", 1),
    ("Chapitre 5 : Tests, résultats, limites et perspectives", "bm_ch5", 0),
    ("5.1 Stratégie de tests", "bm_ch5_1", 1),
    ("5.2 Jeux de tests et résultats", "bm_ch5_2", 1),
    ("5.3 Discussion des résultats", "bm_ch5_3", 1),
    ("5.4 Limites et risques résiduels", "bm_ch5_4", 1),
    ("5.5 Perspectives", "bm_ch5_5", 1),
    ("5.6 Conclusion partielle", "bm_ch5_6", 1),
    ("Conclusion générale", "bm_concl", 0),
    ("Bibliographie et webographie", "bm_biblio", 0),
    ("Annexes", "bm_annexes", 0),
]


def replay_chapter(doc, blocks, *, chapter_bookmark_map=None, skip_prefixes=None):
    skip_prefixes = skip_prefixes or []
    chapter_bookmark_map = chapter_bookmark_map or {}
    for item in blocks:
        t = clean(item["text"])
        if not t:
            continue
        if any(t.startswith(sp) for sp in skip_prefixes):
            continue
        typ = item["type"]
        if typ.startswith("h"):
            level = int(typ[1]) if typ[1:].isdigit() else 1
            # rename état de l'art if present
            t = t.replace(
                "1.3 État de l'art et comparaison des solutions existantes",
                "1.3 Examen des solutions existantes",
            )
            # number ch5 subs if needed
            mapping = {
                "Authentification et accès": "5.2.1 Authentification et accès",
                "Administration": "5.2.2 Administration",
                "Examens côté professeur": "5.2.3 Examens côté professeur",
                "Parcours étudiant et contrôles de passation": "5.2.4 Parcours étudiant et contrôles de passation",
            }
            t = mapping.get(t, t)
            bm = chapter_bookmark_map.get(t)
            if not bm:
                # try by startswith key
                for k, v in chapter_bookmark_map.items():
                    if t.startswith(k) or k.startswith(t[:20]):
                        bm = v
                        break
            h(doc, t, level=level, bookmark=bm or t)
        else:
            if t.startswith("[Emplacement") or t.startswith("Insérer ") or t.startswith("Schéma à"):
                continue
            if t.startswith("Figure ") and " : " in t:
                title = t.split(" : ", 1)[1]
                figure_slot(doc, title)
                continue
            if t.startswith("Tableau ") and " : " in t and len(t) < 140:
                continue
            # drop meta phrases
            if "Mettre à jour" in t or "Cliquez" in t or "clic droit" in t.lower():
                continue
            p(doc, t)


def build():
    data = json.loads(EXTRACTED.read_text(encoding="utf-8"))
    tables = data["tables"]

    doc = Document()
    configure_styles(doc)
    setup_margins(doc.sections[0])
    add_page_number(doc.sections[0], roman=True)
    doc.sections[0].different_first_page_header_footer = True

    # ===== GARDE =====
    cover_block(doc)

    # ===== PAGE DE TITRE (copie sobre) =====
    page_break(doc)
    cover_block(doc)

    # ===== DEDICACE =====
    page_break(doc)
    h(doc, "Dédicace", 1, "bm_dedicace")
    p(
        doc,
        "À nos familles, pour leur soutien discret et constant. À nos enseignants, "
        "qui nous ont transmis les bases nécessaires pour mener un projet de bout en "
        "bout. À tous ceux qui ont accompagné Cylentic avant même que la première "
        "ligne de code n'existe.",
    )

    # ===== REMERCIEMENTS =====
    page_break(doc)
    h(doc, "Remerciements", 1, "bm_remerciements")
    p(
        doc,
        "Nous remercions notre encadrant principal pour sa disponibilité, ses "
        "remarques précises et l'exigence maintenue à chaque étape. Nous remercions "
        "également notre second encadrant pour ses conseils méthodologiques et "
        "techniques.",
    )
    p(
        doc,
        "Nos remerciements vont à l'administration et au corps enseignant de notre "
        "établissement, ainsi qu'aux camarades qui ont testé les premiers parcours "
        "de passation et signalé les points durs de l'interface.",
    )
    p(
        doc,
        "Enfin, nous remercions nos familles pour le soutien quotidien sans lequel "
        "ce travail n'aurait pas abouti dans les délais impartis.",
    )

    # ===== SOMMAIRE =====
    page_break(doc)
    h(doc, "Sommaire", 1, "bm_sommaire")
    for title, bm in SOMMAIRE:
        toc_line(doc, title, bm, indent=0)

    # ===== SIGLES =====
    page_break(doc)
    h(doc, "Liste des sigles et abréviations", 1, "bm_sigles")
    sigles = [
        ("ADM", "Préfixe d'identifiant administrateur d'établissement"),
        ("API", "Application Programming Interface"),
        ("CSV", "Comma-Separated Values"),
        ("ETU", "Préfixe d'identifiant étudiant"),
        ("HTTP", "HyperText Transfer Protocol"),
        ("HTTPS", "HyperText Transfer Protocol Secure"),
        ("IDE", "Integrated Development Environment"),
        ("IP", "Internet Protocol"),
        ("JSON", "JavaScript Object Notation"),
        ("JWT", "JSON Web Token"),
        ("LMS", "Learning Management System"),
        ("MVP", "Minimum Viable Product"),
        ("PDF", "Portable Document Format"),
        ("PROF", "Préfixe d'identifiant professeur"),
        ("QCM", "Questionnaire à choix multiples"),
        ("REST", "Representational State Transfer"),
        ("SADM", "Préfixe d'identifiant Super Admin"),
        ("SGBD", "Système de gestion de bases de données"),
        ("UML", "Unified Modeling Language"),
    ]
    for s, dfn in sigles:
        p(doc, f"{s} : {dfn}", align="left", first_line=False, space_after=3)

    # ===== LISTE FIGURES =====
    page_break(doc)
    h(doc, "Liste des figures", 1, "bm_liste_figures")
    for i, (title, _) in enumerate(FIGURES, 1):
        p(doc, f"Figure {i} : {title}", align="left", first_line=False, space_after=2)

    # ===== LISTE TABLEAUX =====
    page_break(doc)
    h(doc, "Liste des tableaux", 1, "bm_liste_tableaux")
    for i, title in enumerate(TABLES, 1):
        p(doc, f"Tableau {i} : {title}", align="left", first_line=False, space_after=2)

    # ===== RESUME =====
    page_break(doc)
    h(doc, "Résumé", 1, "bm_resume")
    p(
        doc,
        "Évaluer la programmation sur machine est devenu ambigu : un étudiant peut "
        "obtenir rapidement une solution plausible grâce à un assistant de génération "
        "de code, sans que le professeur dispose d'une preuve claire. Revenir au "
        "papier protège une partie de l'intégrité, mais élude l'exécution réelle. "
        "Dans le contexte d'une école d'ingénieurs au Burkina Faso, où les épreuves "
        "se déroulent souvent en salle informatique, nous proposons Cylentic, une "
        "plateforme web multi établissement d'examens sécurisés.",
    )
    p(
        doc,
        "Le MVP couvre la gestion des établissements et des comptes, la création et "
        "la publication d'examens, la passation contrôlée dans le navigateur, "
        "l'exécution isolée de code Python, la journalisation des incidents, la "
        "correction automatique et les exports destinés au professeur. Ce rapport "
        "présente l'analyse du besoin, la conception, la réalisation et les résultats "
        "de validation de la plateforme.",
    )

    # ===== ABSTRACT =====
    page_break(doc)
    h(doc, "Abstract", 1, "bm_abstract")
    p(
        doc,
        "Assessing programming skills on a lab computer has become ambiguous: a "
        "student can obtain a plausible solution quickly with a code generation "
        "assistant, while the instructor lacks clear evidence. Paper exams protect "
        "integrity only partially and sidestep real execution. In a Burkina Faso "
        "engineering school setting, where exams often take place in shared computer "
        "rooms, we propose Cylentic, a multi tenant web platform for secured "
        "programming exams.",
    )
    p(
        doc,
        "The MVP covers establishment and account management, exam authoring and "
        "publication, browser controlled exam sessions, isolated Python execution, "
        "incident logging, automatic grading and teacher facing exports. This report "
        "presents the requirements analysis, design, implementation and validation "
        "results of the platform.",
    )

    # ===== BODY SECTION (arabic) =====
    new_sec = doc.add_section()
    setup_margins(new_sec)
    add_page_number(new_sec, roman=False)
    sectPr = new_sec._sectPr
    pgNumType = OxmlElement("w:pgNumType")
    pgNumType.set(qn("w:start"), "1")
    sectPr.append(pgNumType)

    h(doc, "Introduction générale", 1, "bm_intro")
    p(
        doc,
        "Former un informaticien, c'est aussi vérifier qu'il sait résoudre un problème "
        "sur machine. Or la nature des rendus a changé. Les assistants de génération "
        "de code produisent rapidement des réponses plausibles. Un devoir réalisé hors "
        "salle devient alors difficile à interpréter : le professeur voit un résultat, "
        "rarement le chemin qui y a mené.",
    )
    p(
        doc,
        "Dans nos écoles, l'épreuve pratique a généralement lieu en salle informatique. "
        "Les postes sont partagés, le réseau est parfois instable, et le surveillant "
        "reste présent. Ce cadre impose une solution légère côté étudiant, sans "
        "installation lourde, tout en donnant au professeur des éléments exploitables "
        "après l'épreuve : copie, journal d'incidents, scores issus des tests.",
    )
    p(
        doc,
        "Cylentic est notre réponse à ce besoin. Le présent rapport décrit pourquoi le "
        "problème se pose, comment la plateforme a été spécifiée et conçue, ce qui a "
        "été réellement livré, puis ce que la validation a confirmé ou laissé ouvert.",
    )
    p(
        doc,
        "Le rapport s'organise en cinq chapitres. Le premier situe le contexte et "
        "l'existant. Le deuxième formalise les besoins. Le troisième présente la "
        "conception. Le quatrième décrit la réalisation. Le cinquième discute les "
        "tests, les limites et les perspectives.",
    )

    # Problématique ESTA — sans étiquette scolaire « Méthodologie »
    h(doc, "Problématique", 1, "bm_probl")
    p(
        doc,
        "Comment organiser un examen de programmation sur navigateur qui réduise "
        "fortement les possibilités de triche, conserve un rôle clair au surveillant "
        "humain, et restitue une correction lisible pour le professeur ?",
    )
    p(
        doc,
        "L'objectif général consiste à concevoir et réaliser une plateforme web multi "
        "établissement d'examens de programmation sécurisés, nommée Cylentic.",
    )
    p(doc, "Pour atteindre cet objectif, nous nous sommes fixé les objectifs spécifiques suivants :", first_line=False, space_after=4)
    for bullet in [
        "structurer la gestion des établissements, des classes et des comptes selon des rôles distincts ;",
        "permettre au professeur de créer, publier et suivre un examen avec code d'accès ;",
        "contrôler la session de composition dans le navigateur et journaliser les incidents ;",
        "exécuter le code Python de façon isolée, puis corriger automatiquement par tests unitaires ;",
        "fournir au professeur des exports exploitables après l'épreuve.",
    ]:
        p(doc, f"• {bullet}", align="left", first_line=False, space_after=3)
    p(
        doc,
        "Nous avons procédé par étapes : étude des outils déjà disponibles, "
        "spécification d'un MVP borné, modélisation UML calquée sur le fonctionnement "
        "réel de la plateforme, développement avec Next.js, Prisma et MySQL, puis "
        "validation par parcours complets et contrôle de non régression à chaque "
        "correctif majeur.",
    )

    # CH1
    page_break(doc)
    h(doc, "Chapitre 1 : Contexte et étude de l'existant", 1, "bm_ch1")
    p(
        doc,
        "Ce chapitre ancre le projet dans son contexte pédagogique, précise les "
        "sous-problèmes techniques, examine les solutions déjà disponibles et "
        "positionne Cylentic. La formulation synthétique du problème et des objectifs "
        "a été posée dans la section Problématique ; elle n'est pas reprise ici en bloc.",
    )

    h(doc, "1.1 Contexte pédagogique et technologique", 2, "bm_ch1_1")
    p(
        doc,
        "Dans une formation en informatique, les exercices de programmation mesurent "
        "surtout une compétence pratique : analyser un problème, écrire une solution, "
        "exécuter, lire une erreur, corriger. Cette compétence ne se laisse pas "
        "réduire à la récitation d'une syntaxe sur feuille.",
    )
    p(
        doc,
        "L'examen papier évalue une capacité voisine, mais différente. Il ne montre "
        "ni l'exécution réelle, ni le cycle d'essai et de correction propre à un "
        "environnement de développement. Or c'est précisément ce cycle que le métier "
        "demande.",
    )
    p(
        doc,
        "La démocratisation des assistants de génération de code a transformé les "
        "devoirs hors salle. Un rendu individuel de qualité ne garantit plus que "
        "l'étudiant maîtrise la compétence évaluée. Le numérique ne remplace pas pour "
        "autant la surveillance humaine : un surveillant en salle reste utile face à "
        "un téléphone ou à une communication directe entre étudiants.",
    )

    h(doc, "1.2 Sous-problèmes et contraintes locales", 2, "bm_ch1_2")
    p(
        doc,
        "Cinq sous-problèmes structurent le besoin. Premier : contrôler "
        "l'environnement de composition (plein écran, onglets, collage). Deuxième : "
        "détecter et journaliser les comportements suspects. Troisième : corriger de "
        "façon fiable lors d'un pic de soumissions. Quatrième : produire des preuves "
        "lisibles pour le professeur. Cinquième : tolérer des coupures réseau "
        "ponctuelles sans effacer le travail déjà sauvegardé.",
    )
    p(
        doc,
        "Dans le contexte burkinabè visé, les examens se déroulent souvent sur des "
        "postes partagés, avec une qualité de connexion variable. La solution doit "
        "donc rester simple à déployer le jour de l'épreuve, idéalement dans le "
        "navigateur, sans configuration lourde.",
    )
    p(
        doc,
        "Nous partons de l'hypothèse suivante : si l'on verrouille suffisamment le "
        "navigateur et que l'on journalise les événements sensibles, on peut "
        "restaurer une crédibilité utile aux examens pratiques sur machine, sans "
        "revenir au papier, tout en conservant le jugement pédagogique du professeur.",
    )

    h(doc, "1.3 Examen des solutions existantes", 2, "bm_ch1_3")
    p(
        doc,
        "Plusieurs familles d'outils couvrent chacune une partie du problème, jamais "
        "l'ensemble dans une forme adaptée à une épreuve de code en salle.",
    )
    p(
        doc,
        "Les plateformes d'apprentissage comme freeCodeCamp offrent un éditeur et une "
        "exécution immédiate, mais dans un cadre ouvert, sans verrouillage digne d'une "
        "épreuve ni journal d'incidents orienté professeur.",
    )
    p(
        doc,
        "Les LMS comme Moodle gèrent cours, comptes, créneaux et QCM. Ils restent "
        "généralistes : l'éditeur de code avec exécution isolée n'est pas natif, et la "
        "surveillance poussée passe souvent par des extensions coûteuses.",
    )
    p(
        doc,
        "Les outils de surveillance d'examen à distance répondent surtout à des "
        "épreuves généralistes. Leur licence est souvent élevée. Ils n'exécutent ni "
        "ne corrigent du code de programmation au sens attendu ici.",
    )
    p(
        doc,
        "Les environnements d'exécution isolée, dont Judge0 est un exemple connu, "
        "isolent un programme et renvoient sa sortie. Ce sont des briques utiles, "
        "souvent auto hébergeables, mais pas une plateforme d'examen : pas de rôles "
        "scolaires, pas de passation contrôlée, pas de journal pédagogique.",
    )
    add_table_with_title(
        doc,
        "Comparaison des solutions existantes et de Cylentic",
        tables[0],
        "analyse comparative réalisée dans le cadre du projet",
    )
    p(
        doc,
        "Aucune de ces solutions ne couvre à la fois composition sécurisée, exécution "
        "isolée, correction et traçabilité pour une école. C'est dans cet intervalle "
        "que se place Cylentic.",
    )

    h(doc, "1.4 Positionnement de Cylentic", 2, "bm_ch1_4")
    p(
        doc,
        "Cylentic n'est ni une plateforme d'apprentissage ouverte, ni une simple "
        "variante de LMS. Il vise l'évaluation surveillée de la programmation.",
    )
    p(
        doc,
        "Sa singularité tient au couplage : éditeur dans le navigateur, sandbox Docker "
        "Python, contrôles de passation côté client, règles métier et timers côté "
        "serveur, journal d'incidents, exports professeur, et maintien du surveillant "
        "physique. S'y ajoute une gouvernance multi établissement, avec un Super Admin "
        "plateforme distinct de l'administrateur d'école.",
    )

    h(doc, "1.5 Conclusion partielle", 2, "bm_ch1_5")
    p(
        doc,
        "Le problème est réel, les outils disponibles ne le résolvent que par "
        "fragments, et Cylentic occupe un espace utile. Le chapitre suivant fixe le "
        "cahier des charges du MVP.",
    )

    # CH2
    page_break(doc)
    bm2 = {
        "Chapitre 2 : Analyse des besoins et spécification du système": "bm_ch2",
        "2.1 Périmètre du projet et du MVP": "bm_ch2_1",
        "2.2 Identification des acteurs": "bm_ch2_2",
        "2.3 Besoins fonctionnels": "bm_ch2_3",
        "2.4 Besoins non fonctionnels": "bm_ch2_4",
        "2.5 Règles métier structurantes": "bm_ch2_5",
        "2.6 Scénarios d'usage prioritaires": "bm_ch2_6",
        "2.7 Conclusion partielle": "bm_ch2_7",
    }
    replay_chapter(
        doc,
        data["ch2"],
        chapter_bookmark_map=bm2,
        skip_prefixes=[
            "Ce chapitre délimite",
        ],
    )
    # actors table after 2.2
    # find last para and insert? Add now at end of 2.2 content - simpler append after replay then move is hard.
    # Insert by scanning
    from docx.text.paragraph import Paragraph as P

    def insert_table_after_heading(prefix, title, rows, source):
        target = None
        for para in doc.paragraphs:
            if para.style and str(para.style.name).startswith("Heading") and para.text.strip().startswith(prefix):
                target = para
        if not target:
            return
        paras = list(doc.paragraphs)
        idx = next(i for i, x in enumerate(paras) if x._p is target._p)
        end = idx + 1
        while end < len(paras):
            st = paras[end].style.name if paras[end].style else ""
            if st.startswith("Heading") and st in ("Heading 1", "Heading 2"):
                break
            end += 1
        anchor = paras[end - 1]

        title_p = OxmlElement("w:p")
        anchor._p.addnext(title_p)
        tp = P(title_p, anchor._parent)
        rr = tp.add_run(f"Tableau : {title}")
        set_run_font(rr, size=11, bold=True)

        table = doc.add_table(rows=len(rows), cols=len(rows[0]))
        table.style = "Table Grid"
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = table.rows[i].cells[j]
                cell.text = val
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        set_run_font(run, size=10, bold=(i == 0))
        tbl = table._tbl
        tbl.getparent().remove(tbl)
        title_p.addnext(tbl)

        src_p = OxmlElement("w:p")
        tbl.addnext(src_p)
        sp = P(src_p, anchor._parent)
        sr = sp.add_run(f"Source : {source}")
        set_run_font(sr, size=10, italic=True)

    insert_table_after_heading(
        "2.2 Identification des acteurs",
        "Correspondance entre acteurs et responsabilités",
        tables[1],
        "spécification du projet Cylentic",
    )

    # CH3
    page_break(doc)
    bm3 = {
        "Chapitre 3 : Conception du système Cylentic": "bm_ch3",
        "3.1 Démarche de conception": "bm_ch3_1",
        "3.2 Architecture générale et déploiement": "bm_ch3_2",
        "3.3 Vue des cas d'utilisation": "bm_ch3_3",
        "3.4 Structure statique : classes et objets": "bm_ch3_4",
        "3.5 Organisation en composants": "bm_ch3_5",
        "3.6 Dynamique du système": "bm_ch3_6",
        "3.7 Conception des données": "bm_ch3_7",
        "3.8 Conception de la sécurité de passation": "bm_ch3_8",
        "3.9 Conception de la correction automatique": "bm_ch3_9",
        "3.10 Conclusion partielle": "bm_ch3_10",
    }
    replay_chapter(
        doc,
        data["ch3"],
        chapter_bookmark_map=bm3,
        skip_prefixes=["Une fois les besoins posés"],
    )
    insert_table_after_heading(
        "3.7 Conception des données",
        "Principales tables persistantes et rôle",
        tables[2],
        "schéma de persistance du projet Cylentic",
    )

    # CH4
    page_break(doc)
    bm4 = {
        "Chapitre 4 : Réalisation et mise en œuvre": "bm_ch4",
        "4.1 Environnement de travail": "bm_ch4_1",
        "4.2 Choix technologiques": "bm_ch4_2",
        "4.3 Organisation du code et architecture applicative": "bm_ch4_3",
        "4.4 Réalisation des modules principaux": "bm_ch4_4",
        "4.5 Points techniques difficiles": "bm_ch4_5",
        "4.6 Déploiement": "bm_ch4_6",
        "4.7 Conclusion partielle": "bm_ch4_7",
    }
    replay_chapter(
        doc,
        data["ch4"],
        chapter_bookmark_map=bm4,
        skip_prefixes=["Une fois le cadrage et la conception"],
    )

    # CH5
    page_break(doc)
    bm5 = {
        "Chapitre 5 : Tests, résultats, limites et perspectives": "bm_ch5",
        "5.1 Stratégie de tests": "bm_ch5_1",
        "5.2 Jeux de tests et résultats": "bm_ch5_2",
        "5.3 Discussion des résultats": "bm_ch5_3",
        "5.4 Limites et risques résiduels": "bm_ch5_4",
        "5.5 Perspectives": "bm_ch5_5",
        "5.6 Conclusion partielle": "bm_ch5_6",
    }
    replay_chapter(
        doc,
        data["ch5"],
        chapter_bookmark_map=bm5,
        skip_prefixes=["Ce chapitre présente la campagne"],
    )

    # CONCLUSION
    page_break(doc)
    h(doc, "Conclusion générale", 1, "bm_concl")
    p(
        doc,
        "Ce projet partait d'un écart concret : besoin d'évaluer la programmation sur "
        "machine, difficulté à garantir l'intégrité des rendus lorsque la génération "
        "de code devient banale. Cylentic propose une réponse pragmatique pour une "
        "salle d'examen : plateforme web multi établissement, parcours étudiant "
        "contrôlé, exécution isolée et journal d'incidents lisible.",
    )
    p(
        doc,
        "L'analyse a borné un MVP assumé. La conception a fixé rôles, données et "
        "flux. La réalisation a livré une chaîne complète, de l'onboarding "
        "administrateur à la soumission étudiant, avec publication, contrôles de "
        "passation, correction automatique et exports. La validation a confirmé les "
        "parcours critiques après correction des anomalies de cookie Secure, de "
        "sérialisation Decimal et de synchronisation du timer.",
    )
    p(
        doc,
        "Des limites demeurent : second appareil hors contrôle, Python seul pour "
        "l'instant, Redis et workers non industrialisés, temps réel par polling. "
        "Elles n'effacent pas le résultat principal : un système utilisable dans son "
        "périmètre, justifié dans ses choix, prêt pour des usages pilotes. Les "
        "objectifs fixés pour le MVP sont atteints ; la suite pourra élargir les "
        "langages et renforcer l'infrastructure de charge.",
    )

    # BIBLIO with clickable links
    page_break(doc)
    h(doc, "Bibliographie et webographie", 1, "bm_biblio")
    refs = [
        ("[1] Object Management Group, OMG Unified Modeling Language (OMG UML), documentation officielle. ", None),
        ("[2] Vercel, Next.js Documentation, ", "https://nextjs.org/docs"),
        ("[3] Prisma, Prisma Documentation, ", "https://www.prisma.io/docs"),
        ("[4] Oracle, MySQL 8 Documentation, ", "https://dev.mysql.com/doc/"),
        ("[5] Redis Ltd, Redis Documentation, ", "https://redis.io/docs/"),
        ("[6] Docker Inc., Docker Documentation, ", "https://docs.docker.com/"),
        ("[7] ESTA, Guide du stagiaire Master/Ingénieur, année académique 2024-2025.", None),
        ("[8] freeCodeCamp, ", "https://www.freecodecamp.org/"),
        ("[9] Moodle HQ, Moodle Documentation, ", "https://docs.moodle.org/"),
        ("[10] Judge0, Judge0 CE, ", "https://judge0.com/"),
    ]
    for prefix, url in refs:
        para = p(doc, "", align="left", first_line=False, space_after=6)
        run = para.add_run(prefix)
        set_run_font(run, size=12)
        if url:
            add_external_hyperlink(para, url, url)
            run2 = para.add_run(", consulté le 15/07/2026 à 12h.")
            set_run_font(run2, size=12)

    # ANNEXES
    page_break(doc)
    h(doc, "Annexes", 1, "bm_annexes")
    h(doc, "Annexe A : Inventaire des diagrammes UML", 2)
    p(
        doc,
        "Les diagrammes PlantUML du projet couvrent les cas d'utilisation, classes, "
        "objets, composants, déploiement, états, séquences et activités présentés au "
        "chapitre 3. Ils sont fournis avec le dossier technique du projet.",
        first_line=False,
    )
    h(doc, "Annexe B : Préfixes d'identifiants", 2)
    p(
        doc,
        "SADM- : Super Admin ; ADM- : administrateur d'établissement ; PROF- : "
        "professeur ; ETU- : étudiant. Le rôle est déduit du préfixe à la connexion.",
        first_line=False,
    )
    h(doc, "Annexe C : Captures d'écran complémentaires", 2)
    p(
        doc,
        "Cette annexe regroupe les captures d'administration, de publication, de "
        "journal d'incidents et d'exports au-delà des figures placées dans le corps "
        "du rapport.",
        first_line=False,
    )
    h(doc, "Annexe D : Modèle CSV d'import des étudiants", 2)
    p(
        doc,
        "Colonnes attendues : nom, prénom, classe, matricule, email. Les lignes "
        "invalides sont rejetées avec un rapport d'erreurs exploitable.",
        first_line=False,
    )

    # TABLE DES MATIERES (fin)
    page_break(doc)
    h(doc, "Table des matières", 1, "bm_tdm")
    for title, bm, indent in TDM:
        toc_line(doc, title, bm, indent=indent)

    # Final hygiene pass: remove residual instruction sentences
    forbidden = [
        "Mettre à jour les champs",
        "Cliquez droit",
        "clic droit",
        "Dans Word",
        "[LOGO",
        "Nom de l'établissement",
        "à coller",
        "Texte à personnaliser",
    ]
    for para in doc.paragraphs:
        t = para.text
        if any(f in t for f in forbidden):
            # clear paragraph content if instructional
            if any(f in t for f in ["Mettre à jour", "Cliquez", "clic droit", "Dans Word", "à coller", "personnaliser"]):
                for r in list(para.runs):
                    r.text = ""

    doc.save(OUT)
    doc.save(ALSO)
    print("Wrote", OUT)

    # verify
    d2 = Document(str(OUT))
    full = "\n".join(p.text for p in d2.paragraphs)
    assert "Cliquez droit" not in full
    assert "Mettre à jour les champs" not in full
    assert "Mots clés" not in full
    assert "Méthodologie" not in full
    assert "État de l'art" not in full
    assert "Problématique" in full
    assert ECOLE in full
    print("intro headings", sum(1 for para in d2.paragraphs if para.style and para.style.name=="Heading 1" and para.text.strip()=="Introduction générale"))
    print("checks OK, size", OUT.stat().st_size)


if __name__ == "__main__":
    build()
