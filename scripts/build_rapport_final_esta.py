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
ENCADRANT_P = "Dr YANOGO K Jean Hermann"
ENCADRANT_S = "Dr KYELEM"


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


def set_page_number_format(section, *, fmt: str, start: int | None = None):
    """
    Définit le format réel de pagination de la section (utilisé par le TOC).
    fmt: lowerRoman | decimal | none
    """
    sectPr = section._sectPr
    pg = sectPr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType")
        sectPr.append(pg)
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    else:
        if qn("w:start") in pg.attrib:
            del pg.attrib[qn("w:start")]


def _clear_paragraph(paragraph):
    for r in list(paragraph.runs):
        r._element.getparent().remove(r._element)


def _add_page_field(paragraph, placeholder: str = "1"):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _clear_paragraph(paragraph)
    run = paragraph.add_run()
    r = run._r
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    # Pas de \* ROMAN ici : le format vient de w:pgNumType (indispensable pour le TOC).
    it.text = "PAGE"
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = placeholder
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
    r.append(fc3)
    set_run_font(run, size=12)


def add_page_number(section, *, roman=False, start=1, hide_first_page=False):
    """
    Pagination de section. roman=True -> i, ii, iii (préliminaire).
    hide_first_page=True -> page de garde sans numéro (pied de première page vide).
    """
    set_page_number_format(
        section,
        fmt="lowerRoman" if roman else "decimal",
        start=start,
    )
    section.footer.is_linked_to_previous = False
    _add_page_field(
        section.footer.paragraphs[0],
        placeholder="i" if roman else "1",
    )
    if hide_first_page:
        section.different_first_page_header_footer = True
        fp = section.first_page_footer
        fp.is_linked_to_previous = False
        if not fp.paragraphs:
            fp.add_paragraph()
        _clear_paragraph(fp.paragraphs[0])
    else:
        section.different_first_page_header_footer = False


# Compteurs globaux pour numéros visibles (indépendants du cache SEQ Word)
_FIG_N = 0
_TAB_N = 0


def reset_caption_counters():
    global _FIG_N, _TAB_N
    _FIG_N = 0
    _TAB_N = 0


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


def add_toc_field(paragraph, instruction: str):
    """Insère un champ TOC Word ; à mettre à jour par clic droit dans Word."""
    run = paragraph.add_run()
    r = run._r
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instruction
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = " "
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
    r.append(fc3)
    set_run_font(run, size=12, italic=True)


def _next_caption_number(kind: str) -> int:
    global _FIG_N, _TAB_N
    if kind == "Figure":
        _FIG_N += 1
        return _FIG_N
    _TAB_N += 1
    return _TAB_N


def add_caption(doc, kind: str, title: str, *, align="center", bold=False):
    """
    Légende numérotée (Figure N / Tableau N) avec SEQ Word.
    Le numéro visible est posé explicitement pour éviter que tout reste à « 1 »
    avant / sans mise à jour des champs.
    """
    n = _next_caption_number(kind)
    para = doc.add_paragraph()
    if align == "center":
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.space_after = Pt(10)
    para.paragraph_format.line_spacing = 1.5
    # Style Caption aide le TOC \c "Figure" / \c "Tableau"
    try:
        para.style = doc.styles["Caption"]
    except KeyError:
        pass
    run1 = para.add_run(f"{kind} ")
    set_run_font(run1, size=11, bold=bold)
    run = para.add_run()
    r = run._r
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f"SEQ {kind} \\* ARABIC"
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = str(n)
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
    r.append(fc3)
    set_run_font(run, size=11, bold=bold)
    run2 = para.add_run(f" : {title}")
    set_run_font(run2, size=11, bold=bold)
    return para, n


FIGURE_IMAGE_FILES = {
    "Architecture logique de Cylentic": "00_architecture_logique.png",
    "Déploiement de l'infrastructure": "08_deploiement.png",
    "Cas d'utilisation du Super Admin": "01_usecase_super_admin.png",
    "Cas d'utilisation de l'administrateur (organisation)": "02a_usecase_admin_organisation.png",
    "Cas d'utilisation de l'administrateur (comptes)": "02b_usecase_admin_comptes.png",
    "Cas d'utilisation du professeur (examens)": "03a_usecase_professeur_examens.png",
    "Cas d'utilisation du professeur (suivi)": "03b_usecase_professeur_suivi.png",
    "Cas d'utilisation de l'étudiant": "04_usecase_etudiant.png",
    "Classes organisation et comptes": "05a_classes_organisation.png",
    "Classes conception d'examen": "05b1_classes_conception_examen.png",
    "Classes passation et correction": "05b2_classes_passation.png",
    "Objets organisation": "06a_objets_organisation.png",
    "Objets conception d'examen": "06b_objets_conception_examen.png",
    "Objets passation": "06c_objets_passation.png",
    "Composants vue d'ensemble": "07a_composants_vue_ensemble.png",
    "Composants administration et authentification": "07b_composants_admin_auth.png",
    "Composants examens et passation": "07c_composants_examens.png",
    "États du cycle de vie d'un examen": "09_etats_examen.png",
    "Séquence de connexion": "10_sequence_connexion.png",
    "Séquence de publication d'un examen": "11_sequence_publication.png",
    "Séquence d'accès étudiant": "12_sequence_acces_etudiant.png",
    "Séquence d'exécution du code": "13_sequence_execution.png",
    "Séquence de soumission et correction": "14_sequence_soumission_correction.png",
    "Séquence d'enregistrement d'un incident": "15_sequence_incidents.png",
    "Activité accès et salle d'attente": "16a_activite_acces_attente.png",
    "Activité composition et soumission": "16b_activite_composition_soumission.png",
}

DIAGRAMMES_DIR = Path("/workspace/docs/diagrammes")

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


def figure_slot(doc, title: str):
    """Insère l'image UML si disponible, sinon un emplacement pour capture d'écran."""
    img_name = FIGURE_IMAGE_FILES.get(title)
    img_path = DIAGRAMMES_DIR / img_name if img_name else None
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(4)
    para.paragraph_format.line_spacing = 1.0
    if img_path and img_path.is_file():
        run = para.add_run()
        run.add_picture(str(img_path), width=Cm(14.0))
    else:
        para.paragraph_format.space_before = Pt(12)
        para.paragraph_format.space_after = Pt(28)
    _, n = add_caption(doc, "Figure", title, align="center")
    comment_tpl = FIGURE_COMMENTS.get(title)
    if comment_tpl:
        p(doc, comment_tpl.format(n=n), first_line=True, space_after=8)


def add_table_with_title(doc, title: str, rows: list[list[str]], source: str):
    add_caption(doc, "Tableau", title, align="left", bold=True)
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
    ("Page de connexion multi rôles", "bm_fig_login"),
    ("Espace administrateur d'établissement", "bm_fig_admin"),
    ("Composition d'un examen côté professeur", "bm_fig_teach_edit"),
    ("Publication et code d'accès d'examen", "bm_fig_teach_pub"),
    ("Suivi live des participations", "bm_fig_teach_live"),
    ("Résultats et exports professeur", "bm_fig_teach_res"),
    ("Consignes et activation du plein écran", "bm_fig_stu_sec"),
    ("Salle d'attente avant le démarrage de l'examen", "bm_fig_wait"),
    ("Environnement de composition pendant l'épreuve", "bm_fig_compose"),
    ("Page d'accueil Cylentic", "bm_fig_landing"),
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
    ("Chapitre 1 : État de l'art", "bm_ch1"),
    ("Chapitre 2 : Analyse des besoins et spécification du système", "bm_ch2"),
    ("Chapitre 3 : Conception du système Cylentic", "bm_ch3"),
    ("Chapitre 4 : Réalisation et mise en œuvre", "bm_ch4"),
    ("Chapitre 5 : Tests, résultats, limites et perspectives", "bm_ch5"),
    ("Conclusion générale", "bm_concl"),
    ("Bibliographie", "bm_bibliographie"),
    ("Webographie", "bm_webographie"),
    ("Annexes", "bm_annexes"),
]

TDM = [
    ("Introduction générale", "bm_intro", 0),
    ("Problématique", "bm_probl", 0),
    ("Chapitre 1 : État de l'art", "bm_ch1", 0),
    ("1.1 Contexte pédagogique et technologique", "bm_ch1_1", 1),
    ("1.2 Sous-problèmes et contraintes locales", "bm_ch1_2", 1),
    ("1.3 Panorama des solutions existantes", "bm_ch1_3", 1),
    ("1.4 Synthèse des lacunes du domaine", "bm_ch1_4", 1),
    ("1.5 Conclusion", "bm_ch1_5", 1),
    ("Chapitre 2 : Analyse des besoins et spécification du système", "bm_ch2", 0),
    ("2.1 Comparaison des solutions existantes", "bm_ch2_1", 1),
    ("2.2 Positionnement de Cylentic", "bm_ch2_2", 1),
    ("2.3 Périmètre du projet et du MVP", "bm_ch2_3", 1),
    ("2.4 Identification des acteurs", "bm_ch2_4", 1),
    ("2.5 Besoins fonctionnels", "bm_ch2_5", 1),
    ("2.6 Besoins non fonctionnels", "bm_ch2_6", 1),
    ("2.7 Règles métier structurantes", "bm_ch2_7", 1),
    ("2.8 Scénarios d'usage prioritaires", "bm_ch2_8", 1),
    ("2.9 Conclusion", "bm_ch2_9", 1),
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
    ("3.10 Conclusion", "bm_ch3_10", 1),
    ("Chapitre 4 : Réalisation et mise en œuvre", "bm_ch4", 0),
    ("4.1 Environnement de travail", "bm_ch4_1", 1),
    ("4.2 Choix technologiques", "bm_ch4_2", 1),
    ("4.3 Organisation du code et architecture applicative", "bm_ch4_3", 1),
    ("4.4 Réalisation des modules principaux", "bm_ch4_4", 1),
    ("4.5 Points techniques difficiles", "bm_ch4_5", 1),
    ("4.6 Déploiement", "bm_ch4_6", 1),
    ("4.7 Conclusion", "bm_ch4_7", 1),
    ("Chapitre 5 : Tests, résultats, limites et perspectives", "bm_ch5", 0),
    ("5.1 Stratégie de tests", "bm_ch5_1", 1),
    ("5.2 Jeux de tests et résultats", "bm_ch5_2", 1),
    ("5.3 Discussion des résultats", "bm_ch5_3", 1),
    ("5.4 Limites et risques résiduels", "bm_ch5_4", 1),
    ("5.5 Perspectives", "bm_ch5_5", 1),
    ("5.6 Coût estimatif du projet", "bm_ch5_6", 1),
    ("5.7 Conclusion", "bm_ch5_7", 1),
    ("Conclusion générale", "bm_concl", 0),
    ("Bibliographie", "bm_bibliographie", 0),
    ("Webographie", "bm_webographie", 0),
    ("Annexes", "bm_annexes", 0),
]


CH2_HEADING_REMAP = {
    "2.1 Périmètre du projet et du MVP": "2.3 Périmètre du projet et du MVP",
    "2.2 Identification des acteurs": "2.4 Identification des acteurs",
    "2.3 Besoins fonctionnels": "2.5 Besoins fonctionnels",
    "2.4 Besoins non fonctionnels": "2.6 Besoins non fonctionnels",
    "2.5 Règles métier structurantes": "2.7 Règles métier structurantes",
    "2.6 Scénarios d'usage prioritaires": "2.8 Scénarios d'usage prioritaires",
    "2.7 Conclusion partielle": "2.9 Conclusion",
    "2.7 Conclusion": "2.9 Conclusion",
}


def replay_chapter(doc, blocks, *, chapter_bookmark_map=None, skip_prefixes=None, heading_remap=None):
    skip_prefixes = skip_prefixes or []
    chapter_bookmark_map = chapter_bookmark_map or {}
    heading_remap = heading_remap or {}
    for item in blocks:
        t = clean(item["text"])
        if not t:
            continue
        if any(t.startswith(sp) for sp in skip_prefixes):
            continue
        if t in skip_prefixes:
            continue
        typ = item["type"]
        if typ.startswith("h"):
            level = int(typ[1]) if typ[1:].isdigit() else 1
            t = t.replace("Conclusion partielle", "Conclusion")
            t = heading_remap.get(t, t)
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
    reset_caption_counters()

    doc = Document()
    configure_styles(doc)

    # ===== Section 0 : pages de garde (sans numéro) =====
    setup_margins(doc.sections[0])
    set_page_number_format(doc.sections[0], fmt="lowerRoman", start=1)
    doc.sections[0].different_first_page_header_footer = False
    doc.sections[0].footer.is_linked_to_previous = False
    _clear_paragraph(doc.sections[0].footer.paragraphs[0])

    # ===== GARDE =====
    cover_block(doc)

    # ===== PAGE DE TITRE (copie sobre) =====
    page_break(doc)
    cover_block(doc)

    # ===== Section 1 : préliminaire (romains i, ii, iii…) =====
    front = doc.add_section()
    setup_margins(front)
    add_page_number(front, roman=True, start=1, hide_first_page=False)

    # ===== DEDICACE =====
    h(doc, "Dédicace", 1, "bm_dedicace")
    p(doc, "À ma famille.", align="center", first_line=False, space_after=8)

    # ===== REMERCIEMENTS =====
    page_break(doc)
    h(doc, "Remerciements", 1, "bm_remerciements")
    p(
        doc,
        "Nous tenons à exprimer notre profonde gratitude à toutes les personnes et "
        "institutions qui ont contribué, de près ou de loin, à la réalisation de "
        "notre projet de fin d'année.",
    )
    p(
        doc,
        "Nous adressons tout d'abord nos sincères remerciements à Dieu Tout-Puissant "
        "pour la santé, la force et la persévérance qu'Il nous a accordées tout au "
        "long de notre parcours académique.",
    )
    p(
        doc,
        f"{ENCADRANT_P}, notre encadrant principal, dont les conseils avisés, la "
        "disponibilité, la rigueur scientifique et les orientations ont été "
        "déterminants dans la conduite de ce projet.",
    )
    p(
        doc,
        f"{ENCADRANT_S}, notre encadrant, pour ses conseils méthodologiques et "
        "techniques, ainsi que pour son accompagnement tout au long de ce travail.",
    )
    p(
        doc,
        "L'ensemble du corps professoral et administratif de l'Institut du Génie "
        "Informatique pour la qualité de la formation reçue et pour l'encadrement "
        "académique dont nous avons bénéficié.",
    )
    p(
        doc,
        "Notre gratitude à nos collègues, amis et camarades de promotion pour leurs "
        "encouragements, leurs conseils et les échanges constructifs, notamment ceux "
        "qui ont testé les premiers parcours d'examen et signalé les points durs de "
        "l'interface.",
    )
    p(
        doc,
        "Notre famille, pour son soutien moral, sa compréhension et sa confiance "
        "tout au long de nos études.",
    )
    p(
        doc,
        "Nos sincères remerciements à toutes les personnes qui, d'une manière ou "
        "d'une autre, ont contribué à la réalisation de ce rapport et à la réussite "
        "de notre formation.",
    )

    # ===== SOMMAIRE (grands titres seulement) =====
    page_break(doc)
    h(doc, "Sommaire", 1, "bm_sommaire")
    toc_p = p(doc, "", first_line=False, align="left")
    add_toc_field(toc_p, r'TOC \o "1-1" \h \z \u')

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

    # ===== LISTE FIGURES / TABLEAUX (champs Word) =====
    page_break(doc)
    h(doc, "Liste des figures", 1, "bm_liste_figures")
    fp = p(doc, "", first_line=False, align="left")
    add_toc_field(fp, r'TOC \h \z \c "Figure"')

    page_break(doc)
    h(doc, "Liste des tableaux", 1, "bm_liste_tableaux")
    tp = p(doc, "", first_line=False, align="left")
    add_toc_field(tp, r'TOC \h \z \c "Tableau"')

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
    p(
        doc,
        "Mots-clés : examen de programmation, plateforme web, intégrité académique, "
        "sandbox, correction automatique, école d'ingénieurs.",
        bold=True,
        first_line=False,
        space_after=8,
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
    p(
        doc,
        "Keywords: programming exam, web platform, academic integrity, sandbox, "
        "automatic grading, engineering school.",
        bold=True,
        first_line=False,
        space_after=8,
    )

    # ===== BODY SECTION (arabe 1, 2, 3…) =====
    new_sec = doc.add_section()
    setup_margins(new_sec)
    add_page_number(new_sec, roman=False, start=1, hide_first_page=False)

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
        "Le rapport s'organise en cinq chapitres. Le premier présente l'état de "
        "l'art. Le deuxième formalise les besoins et compare les solutions existantes. "
        "Le troisième présente la conception. Le quatrième décrit la réalisation. "
        "Le cinquième discute les tests, les limites et les perspectives.",
    )
    p(
        doc,
        "Au terme de ce travail, plusieurs résultats sont attendus : une analyse "
        "structurée des limites des outils existants pour l'évaluation de la "
        "programmation en salle ; une conception documentée de Cylentic (UML, "
        "architecture, données) ; un prototype fonctionnel couvrant les parcours "
        "critiques du MVP ; une validation par tests des scénarios d'examen surveillé.",
    )
    p(
        doc,
        "L'atteinte de ces objectifs repose sur les hypothèses de recherche suivantes :",
        first_line=False,
        space_after=4,
    )
    for hyp in [
        "un verrouillage suffisant du navigateur, couplé à la journalisation des incidents, permet de restaurer la crédibilité des épreuves pratiques sur machine ;",
        "l'exécution isolée du code dans une sandbox et la correction automatique par tests unitaires offrent une évaluation fiable et reproductible ;",
        "une architecture web multi établissement, déployable sans installation lourde côté étudiant, répond aux contraintes des salles informatiques partagées.",
    ]:
        p(doc, f"• {hyp}", align="left", first_line=False, space_after=3)
    p(
        doc,
        "Pour répondre à la problématique, nous avons adopté une démarche "
        "méthodologique structurée en cinq étapes : revue de l'état de l'art et "
        "analyse comparative des solutions existantes ; spécification des besoins et "
        "définition du périmètre du MVP ; conception UML et modélisation de "
        "l'architecture ; réalisation itérative avec Next.js, Prisma et MySQL ; "
        "validation par tests de parcours complets et contrôle de non régression.",
    )

    h(doc, "Problématique", 1, "bm_probl")
    p(
        doc,
        "Face à la montée des assistants de génération de code, comment garantir "
        "l'intégrité et la crédibilité de l'évaluation de la programmation sur "
        "machine en salle informatique, tout en permettant l'exécution réelle du code "
        "et une correction fiable pour le professeur ?",
    )
    p(
        doc,
        "L'objectif général consiste à concevoir une plateforme web multi "
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

    # CH1 — État de l'art
    page_break(doc)
    h(doc, "Chapitre 1 : État de l'art", 1, "bm_ch1")
    p(
        doc,
        "Ce chapitre présente l'état de l'art du domaine : contexte pédagogique, "
        "contraintes locales et panorama des solutions existantes. La comparaison "
        "détaillée et le positionnement de Cylentic sont traités au chapitre 2.",
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
    h(doc, "1.3 Panorama des solutions existantes", 2, "bm_ch1_3")
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

    h(doc, "1.4 Synthèse des lacunes du domaine", 2, "bm_ch1_4")
    p(
        doc,
        "L'état de l'art montre que les outils disponibles couvrent chacun une facette "
        "du problème : apprentissage ouvert, gestion de cours, surveillance généraliste "
        "ou exécution isolée. Aucun ne réunit composition sécurisée, exécution réelle, "
        "correction automatique et traçabilité pédagogique dans un cadre adapté aux "
        "salles informatiques d'une école d'ingénieurs.",
    )
    p(
        doc,
        "Cette lacune justifie l'étude d'une solution dédiée. Le chapitre suivant "
        "compare formellement les approches existantes et précise le positionnement de "
        "Cylentic avant de fixer le cahier des charges.",
    )

    h(doc, "1.5 Conclusion", 2, "bm_ch1_5")
    p(
        doc,
        "Le contexte pédagogique, les contraintes locales et le panorama des solutions "
        "établissent un état de l'art clair : le besoin d'évaluer la programmation sur "
        "machine avec intégrité reste mal couvert par l'existant. Le chapitre 2 en "
        "déduit la spécification et la comparaison structurée.",
    )

    # CH2
    page_break(doc)
    h(doc, "Chapitre 2 : Analyse des besoins et spécification du système", 1, "bm_ch2")
    p(
        doc,
        "Ce chapitre compare les solutions existantes, positionne Cylentic, puis "
        "délimite le MVP, identifie les acteurs et formalise les besoins fonctionnels "
        "et non fonctionnels du système.",
    )
    h(doc, "2.1 Comparaison des solutions existantes", 2, "bm_ch2_1")
    p(
        doc,
        "Pour objectiver l'analyse de l'état de l'art, le tableau ci-dessous compare "
        "les principales familles de solutions aux exigences d'un examen de "
        "programmation surveillé en salle.",
    )
    add_table_with_title(
        doc,
        "Comparaison des solutions existantes et de Cylentic",
        tables[0],
        "analyse comparative réalisée dans le cadre du projet",
    )
    h(doc, "2.2 Positionnement de Cylentic", 2, "bm_ch2_2")
    p(
        doc,
        "Cylentic n'est ni une plateforme d'apprentissage ouverte, ni une simple "
        "variante de LMS. Elle vise l'évaluation surveillée de la programmation.",
    )
    p(
        doc,
        "Sa singularité tient au couplage : éditeur dans le navigateur, sandbox Docker "
        "Python, contrôles de passation côté client, règles métier et timers côté "
        "serveur, journal d'incidents, exports professeur, et maintien du surveillant "
        "physique. S'y ajoute une gouvernance multi établissement, avec un Super Admin "
        "plateforme distinct de l'administrateur d'école.",
    )
    bm2 = {
        "2.3 Périmètre du projet et du MVP": "bm_ch2_3",
        "2.4 Identification des acteurs": "bm_ch2_4",
        "2.5 Besoins fonctionnels": "bm_ch2_5",
        "2.6 Besoins non fonctionnels": "bm_ch2_6",
        "2.7 Règles métier structurantes": "bm_ch2_7",
        "2.8 Scénarios d'usage prioritaires": "bm_ch2_8",
        "2.9 Conclusion": "bm_ch2_9",
    }
    replay_chapter(
        doc,
        data["ch2"],
        chapter_bookmark_map=bm2,
        skip_prefixes=[
            "Ce chapitre délimite",
            "Chapitre 2 : Analyse des besoins et spécification du système",
        ],
        heading_remap=CH2_HEADING_REMAP,
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
        n = _next_caption_number("Tableau")
        try:
            tp.style = doc.styles["Caption"]
        except KeyError:
            pass
        run1 = tp.add_run("Tableau ")
        set_run_font(run1, size=11, bold=True)
        run = tp.add_run()
        r = run._r
        fc1 = OxmlElement("w:fldChar")
        fc1.set(qn("w:fldCharType"), "begin")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = "SEQ Tableau \\* ARABIC"
        fc2 = OxmlElement("w:fldChar")
        fc2.set(qn("w:fldCharType"), "separate")
        tnode = OxmlElement("w:t")
        tnode.text = str(n)
        fc3 = OxmlElement("w:fldChar")
        fc3.set(qn("w:fldCharType"), "end")
        r.append(fc1)
        r.append(it)
        r.append(fc2)
        r.append(tnode)
        r.append(fc3)
        set_run_font(run, size=11, bold=True)
        run2 = tp.add_run(f" : {title}")
        set_run_font(run2, size=11, bold=True)

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
        "2.4 Identification des acteurs",
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
        "3.10 Conclusion": "bm_ch3_10",
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
        "4.7 Conclusion": "bm_ch4_7",
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
    }
    replay_chapter(
        doc,
        data["ch5"],
        chapter_bookmark_map=bm5,
        skip_prefixes=[
            "Ce chapitre présente la campagne",
            "5.6 Conclusion partielle",
            "5.6 Conclusion",
        ],
    )
    h(doc, "5.6 Coût estimatif du projet", 2, "bm_ch5_6")
    p(
        doc,
        "Le tableau ci-dessous estime le coût du projet pour un déploiement pilote "
        "sur douze mois. Les postes de développement sont intégrés au cadre académique "
        "du projet de fin d'année.",
    )
    add_table_with_title(
        doc,
        "Coût estimatif du projet Cylentic",
        [
            ["Poste", "Détail", "Coût estimé (FCFA)"],
            ["Développement", "Équipe de 3 étudiants, cadre académique", "0"],
            ["Hébergement VPS", "Serveur 4 vCPU, 8 Go RAM, 12 mois", "180 000"],
            ["Nom de domaine", "Enregistrement annuel", "15 000"],
            ["Outils", "IDE, Git, Docker (open source)", "0"],
            ["Total", "Déploiement pilote sur 12 mois", "195 000"],
        ],
        "estimation réalisée par l'équipe projet, juillet 2026",
    )
    h(doc, "5.7 Conclusion", 2, "bm_ch5_7")
    p(
        doc,
        "Les tests confirment la faisabilité du MVP dans son périmètre. Les limites "
        "identifiées ouvrent des perspectives d'évolution sans remettre en cause la "
        "pertinence de la solution pour un usage pilote en salle informatique.",
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

    # BIBLIOGRAPHIE
    page_break(doc)
    h(doc, "Bibliographie", 1, "bm_bibliographie")
    biblio_refs = [
        "[1] Object Management Group, OMG Unified Modeling Language (OMG UML), Version 2.5.1, 2017.",
        "[2] R. S. Pressman et B. R. Maxim, Software Engineering: A Practitioner's Approach, 9e éd., McGraw-Hill, 2019.",
        "[3] I. Sommerville, Software Engineering, 10e éd., Pearson, 2016.",
        "[4] G. Booch, J. Rumbaugh et I. Jacobson, The Unified Modeling Language User Guide, 2e éd., Addison-Wesley, 2005.",
        "[5] ESTA, Guide du stagiaire Master/Ingénieur, année académique 2024-2025.",
        "[6] M. Fowler, Patterns of Enterprise Application Architecture, Addison-Wesley, 2002.",
    ]
    for ref in biblio_refs:
        p(doc, ref, align="left", first_line=False, space_after=6)

    # WEBOGRAPHIE
    page_break(doc)
    h(doc, "Webographie", 1, "bm_webographie")
    web_refs = [
        ("[1] Vercel, Next.js Documentation, ", "https://nextjs.org/docs", "09h20"),
        ("[2] Prisma, Prisma Documentation, ", "https://www.prisma.io/docs", "09h45"),
        ("[3] Oracle, MySQL 8 Documentation, ", "https://dev.mysql.com/doc/", "10h15"),
        ("[4] Redis Ltd, Redis Documentation, ", "https://redis.io/docs/", "10h40"),
        ("[5] Docker Inc., Docker Documentation, ", "https://docs.docker.com/", "11h25"),
        ("[6] freeCodeCamp, ", "https://www.freecodecamp.org/", "14h10"),
        ("[7] Moodle HQ, Moodle Documentation, ", "https://docs.moodle.org/", "15h05"),
        ("[8] Judge0, Judge0 CE, ", "https://judge0.com/", "16h30"),
        ("[9] Monaco Editor, ", "https://microsoft.github.io/monaco-editor/", "17h05"),
        ("[10] PlantUML, ", "https://plantuml.com/", "17h40"),
    ]
    for prefix, url, heure in web_refs:
        para = p(doc, "", align="left", first_line=False, space_after=6)
        run = para.add_run(prefix)
        set_run_font(run, size=12)
        add_external_hyperlink(para, url, url)
        run2 = para.add_run(f", consulté le 15/07/2026 à {heure}.")
        set_run_font(run2, size=12)

    # ANNEXES
    page_break(doc)
    h(doc, "Annexes", 1, "bm_annexes")
    h(doc, "Annexe A : Préfixes d'identifiants", 2)
    p(
        doc,
        "SADM- : Super Admin ; ADM- : administrateur d'établissement ; PROF- : "
        "professeur ; ETU- : étudiant. Le rôle est déduit du préfixe à la connexion.",
        first_line=False,
    )
    h(doc, "Annexe B : Modèle CSV d'import des étudiants", 2)
    p(
        doc,
        "Colonnes attendues : nom, prénom, classe, matricule, email. Les lignes "
        "invalides sont rejetées avec un rapport d'erreurs exploitable.",
        first_line=False,
    )

    # TABLE DES MATIERES (fin, ESTA)
    page_break(doc)
    h(doc, "Table des matières", 1, "bm_tdm")
    tdm = p(doc, "", first_line=False, align="left")
    add_toc_field(tdm, r'TOC \o "1-3" \h \z \u')

    # Hygiene : retirer seulement les placeholders de couverture / texte à coller
    forbidden_clear = ["[LOGO", "à coller", "Texte à personnaliser", "Nom de l'établissement"]
    for para in doc.paragraphs:
        t = para.text
        if any(f in t for f in forbidden_clear):
            for r in list(para.runs):
                r.text = ""

    doc.save(OUT)
    doc.save(ALSO)
    print("Wrote", OUT)

    # verify
    d2 = Document(str(OUT))
    full = "\n".join(p.text for p in d2.paragraphs)
    assert "Mettre à jour les champs" not in full
    assert "Mots-clés" in full
    assert "Keywords:" in full
    assert "État de l'art" in full
    assert "Coût estimatif" in full
    assert "Bibliographie" in full
    assert "Webographie" in full
    assert "conclusion partielle" not in full.lower()
    assert "À ma famille" in full
    # Figures and tables numbered consecutively
    figs = [p.text for p in d2.paragraphs if p.text.strip().startswith("Figure ")]
    tabs = [p.text for p in d2.paragraphs if p.text.strip().startswith("Tableau ")]
    assert figs and all(f"Figure {i} :" in figs[i - 1] for i in range(1, len(figs) + 1)), figs[:5]
    assert len(tabs) >= 4
    assert any("Tableau 1 :" in t for t in tabs)
    assert any("Tableau 2 :" in t for t in tabs)
    assert any("Tableau 3 :" in t for t in tabs)
    # Page format on sections
    from docx.oxml.ns import qn as _qn
    assert len(d2.sections) >= 3
    fmts = []
    for s in d2.sections:
        pg = s._sectPr.find(_qn("w:pgNumType"))
        fmts.append(None if pg is None else pg.get(_qn("w:fmt")))
    assert "lowerRoman" in fmts
    assert "decimal" in fmts
    assert "Mots clés" not in full
    assert "Problématique" in full
    assert ECOLE in full
    print("figures", len(figs), "first/last", figs[0][:60], "|", figs[-1][:60])
    print("tableaux", tabs)
    print("page fmts", fmts)
    print("intro headings", sum(1 for para in d2.paragraphs if para.style and para.style.name=="Heading 1" and para.text.strip()=="Introduction générale"))
    print("checks OK, size", OUT.stat().st_size)


if __name__ == "__main__":
    build()
