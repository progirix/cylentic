#!/usr/bin/env python3
"""
Génère le rapport Cylentic final, conforme au guide ESTA (forme),
avec TOC / listes de figures et tableaux cliquables (champs Word),
fond dédoublonné et aligné sur le dépôt anaxagore226/cylentic.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path("/workspace/docs/Rapport_Cylentic.docx")
EXTRACTED = Path("/workspace/scripts/_rapport_extracted.json")


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
    pf = normal.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(8)

    for i, size in [(1, 14), (2, 12), (3, 12)]:
        st = doc.styles[f"Heading {i}"]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        st.paragraph_format.space_before = Pt(14 if i == 1 else 10)
        st.paragraph_format.space_after = Pt(8)
        st.paragraph_format.line_spacing = 1.5

    # Caption style
    try:
        cap = doc.styles["Caption"]
    except KeyError:
        cap = doc.styles.add_style("Caption", 1)
    cap.font.name = "Times New Roman"
    cap.font.size = Pt(11)
    cap.font.italic = False
    cap.font.color.rgb = RGBColor(0, 0, 0)


def setup_margins(section, binding=True):
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.5 if binding else 2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)


def add_page_number(section, roman=False):
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    # clear
    for r in list(p.runs):
        r._element.getparent().remove(r._element)

    def add_field(instr: str):
        run = p.add_run()
        set_run_font(run, size=12)
        r = run._r
        fc1 = OxmlElement("w:fldChar")
        fc1.set(qn("w:fldCharType"), "begin")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = instr
        fc2 = OxmlElement("w:fldChar")
        fc2.set(qn("w:fldCharType"), "separate")
        ft = OxmlElement("w:t")
        ft.text = "1"
        fc3 = OxmlElement("w:fldChar")
        fc3.set(qn("w:fldCharType"), "end")
        r.append(fc1)
        r.append(it)
        r.append(fc2)
        r.append(ft)
        r.append(fc3)

    if roman:
        add_field(r"PAGE \* ROMAN")
    else:
        add_field("PAGE")


def add_toc_field(paragraph, instruction: str):
    """Insert a Word TOC field. Update via right-click in Word."""
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
    t.text = "(Cliquez droit > Mettre à jour les champs dans Word)"
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
    r.append(fc3)
    set_run_font(run, size=12, italic=True)


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
    space_before=0,
):
    para = doc.add_paragraph()
    if align == "center":
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "left":
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    else:
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = para.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = 1.5
    if first_line and align == "justify" and text:
        pf.first_line_indent = Cm(0.75)
    if text:
        run = para.add_run(text)
        set_run_font(run, size=size, bold=bold, italic=italic)
    return para


def h(doc, text, level=1):
    para = doc.add_heading(text, level=level)
    for run in para.runs:
        set_run_font(run, size=14 if level == 1 else 12, bold=True)
    para.paragraph_format.line_spacing = 1.5
    return para


def clean(text: str) -> str:
    text = text.replace("—", ",").replace("–", "-")
    text = re.sub(r"\(Texte à personnaliser.*?\)", "", text)
    text = re.sub(r"\(Compléter ou modifier.*?\)", "", text)
    text = text.replace("déjà développée dans ce document", "détaillée plus loin")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def page_break(doc):
    doc.add_page_break()


def add_caption(doc, kind: str, title: str):
    """Caption with SEQ field so Word can build Liste des figures/tableaux."""
    para = doc.add_paragraph()
    para.style = "Caption"
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(10)
    para.paragraph_format.line_spacing = 1.5

    run1 = para.add_run(f"{kind} ")
    set_run_font(run1, size=11)

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
    t.text = "1"
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
    r.append(fc3)
    set_run_font(run, size=11)

    run2 = para.add_run(f" : {title}")
    set_run_font(run2, size=11)
    return para


def figure_slot(doc, title: str, description: str):
    p(doc, "[Emplacement de figure]", italic=True, align="center", first_line=False, space_after=2)
    p(doc, description, italic=True, align="center", size=11, first_line=False, space_after=2)
    add_caption(doc, "Figure", title)


def add_table_with_title(doc, title: str, rows: list[list[str]]):
    tp = p(doc, "", align="left", first_line=False, space_after=4)
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
    t = OxmlElement("w:t")
    t.text = "1"
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r.append(fc1)
    r.append(it)
    r.append(fc2)
    r.append(t)
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
    p(doc, "Source : analyse comparative réalisée dans le cadre du projet.", size=10, italic=True, align="left", first_line=False, space_after=10)


def cover_page(doc):
    for _ in range(2):
        p(doc, "", first_line=False, space_after=0)
    p(doc, "BURKINA FASO", bold=True, align="center", first_line=False, space_after=2)
    p(doc, "La Patrie ou la Mort, nous Vaincrons", italic=True, align="center", first_line=False, space_after=10)
    p(
        doc,
        "Ministère de l'Enseignement Supérieur, de la Recherche et de l'Innovation",
        align="center",
        size=11,
        first_line=False,
        space_after=8,
    )
    p(doc, "[LOGO DE L'ÉTABLISSEMENT]", italic=True, align="center", first_line=False, space_after=6)
    p(doc, "Nom de l'établissement", bold=True, align="center", first_line=False, space_after=4)
    p(doc, "Filière / Option : Informatique", align="center", first_line=False, space_after=14)
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
    p(doc, "Nom et prénoms de l'étudiant 1", align="center", first_line=False, space_after=2)
    p(doc, "Nom et prénoms de l'étudiant 2", align="center", first_line=False, space_after=2)
    p(doc, "Nom et prénoms de l'étudiant 3", align="center", first_line=False, space_after=12)
    p(doc, "Encadrant principal : Nom, prénoms, grade et fonction", align="center", first_line=False, space_after=4)
    p(doc, "Encadrant : Nom, prénoms, grade et fonction", align="center", first_line=False, space_after=16)
    p(doc, "Année académique 20..-20..", align="center", first_line=False, space_after=4)


def replay_blocks(doc, blocks, *, skip_texts=None, figure_map=None):
    skip_texts = skip_texts or set()
    for item in blocks:
        t = clean(item["text"])
        if not t or t in skip_texts:
            continue
        typ = item["type"]
        if typ.startswith("h"):
            level = int(typ[1]) if typ[1:].isdigit() else 1
            # Normalize chapter 5 subheads that lacked numbering
            h(doc, t, level=level)
        else:
            # detect figure slots
            if t.startswith("[Emplacement de la figure") or t.startswith("[Emplacement de figure"):
                continue
            if t.startswith("Insérer ") or t.startswith("Schéma à insérer"):
                # Will be handled if previous was figure title via caption already in blocks as "Figure x :"
                continue
            if t.startswith("Figure ") and " : " in t:
                # Convert textual figure line into proper caption + slot
                title = t.split(" : ", 1)[1]
                # look ahead not available; use description generic
                desc = figure_map.get(title, "Insérer la figure correspondante (diagramme PlantUML ou capture).")
                figure_slot(doc, title, desc)
                continue
            if t.startswith("Tableau ") and " : " in t and len(t) < 120:
                # table titles in extracted text without actual table - skip, tables added manually in ch1/ch3
                continue
            p(doc, t)


def build():
    data = json.loads(EXTRACTED.read_text(encoding="utf-8"))
    tables = data["tables"]

    doc = Document()
    configure_styles(doc)
    setup_margins(doc.sections[0], binding=True)
    add_page_number(doc.sections[0], roman=True)
    # Different first page (cover without number display still counts in Word manually; we hide number on first)
    doc.sections[0].different_first_page_header_footer = True

    # ===== COVER =====
    cover_page(doc)

    # ===== TITLE PAGE =====
    page_break(doc)
    h(doc, "Page de titre", 1)
    p(
        doc,
        "Cette page reprend, en noir et blanc, les informations de la page de garde : "
        "établissement, filière, titre du projet, auteurs, encadrants et année académique.",
        italic=True,
        first_line=False,
    )

    # ===== DEDICACE =====
    page_break(doc)
    h(doc, "Dédicace", 1)
    p(
        doc,
        "À nos familles, pour leur soutien discret et constant. À nos enseignants, "
        "qui nous ont transmis les bases nécessaires pour mener un projet de bout en "
        "bout. À tous ceux qui ont accompagné Cylentic avant même que la première "
        "ligne de code n'existe.",
    )

    # ===== REMERCIEMENTS =====
    page_break(doc)
    h(doc, "Remerciements", 1)
    p(
        doc,
        "Nous remercions notre encadrant principal pour sa disponibilité, ses "
        "remarques précises et l'exigence qu'il a maintenue à chaque étape. Nous "
        "remercions également notre second encadrant pour ses conseils "
        "méthodologiques et techniques.",
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

    # ===== SOMMAIRE (grands titres seulement) =====
    page_break(doc)
    h(doc, "Sommaire", 1)
    p(
        doc,
        "Le sommaire ci-dessous reprend les grands titres. Mettez à jour le champ "
        "dans Word (clic droit > Mettre à jour les champs) pour afficher les numéros "
        "de pages et activer les liens.",
        italic=True,
        first_line=False,
        size=11,
    )
    toc_p = p(doc, "", first_line=False, align="left")
    add_toc_field(toc_p, r'TOC \o "1-1" \h \z \u')

    # ===== SIGLES =====
    page_break(doc)
    h(doc, "Liste des sigles et abréviations", 1)
    sigles = [
        ("API", "Application Programming Interface"),
        ("CSV", "Comma-Separated Values"),
        ("JWT", "JSON Web Token"),
        ("LMS", "Learning Management System"),
        ("MVP", "Minimum Viable Product"),
        ("QCM", "Questionnaire à choix multiples"),
        ("REST", "Representational State Transfer"),
        ("SGBD", "Système de gestion de bases de données"),
        ("UML", "Unified Modeling Language"),
    ]
    for s, dfn in sigles:
        p(doc, f"{s} : {dfn}", align="left", first_line=False, space_after=3)

    # ===== LISTE FIGURES / TABLEAUX (champs) =====
    page_break(doc)
    h(doc, "Liste des figures", 1)
    p(
        doc,
        "Liste générée automatiquement à partir des légendes. Dans Word : clic droit "
        "sur le champ > Mettre à jour les champs.",
        italic=True,
        first_line=False,
        size=11,
    )
    fp = p(doc, "", first_line=False, align="left")
    add_toc_field(fp, r'TOC \h \z \c "Figure"')

    page_break(doc)
    h(doc, "Liste des tableaux", 1)
    p(
        doc,
        "Liste générée automatiquement à partir des titres de tableaux. Dans Word : "
        "clic droit > Mettre à jour les champs.",
        italic=True,
        first_line=False,
        size=11,
    )
    tp = p(doc, "", first_line=False, align="left")
    add_toc_field(tp, r'TOC \h \z \c "Tableau"')

    # ===== RESUME =====
    page_break(doc)
    h(doc, "Résumé", 1)
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
        "présente l'analyse du besoin, la conception UML, la réalisation et les "
        "résultats de validation.",
    )
    p(
        doc,
        "Mots clés : examen de programmation, sécurité navigateur, sandbox, UML, Next.js, correction automatique.",
        first_line=False,
    )

    # ===== ABSTRACT =====
    page_break(doc)
    h(doc, "Abstract", 1)
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
        "presents the requirements analysis, UML design, implementation and "
        "validation results.",
    )
    p(
        doc,
        "Keywords: programming exam, browser security, sandbox, UML, Next.js, automated grading.",
        first_line=False,
    )

    # ===== SECTION BODY (arabic pages) =====
    new_sec = doc.add_section()
    setup_margins(new_sec, binding=True)
    add_page_number(new_sec, roman=False)
    # restart page numbering at 1
    sectPr = new_sec._sectPr
    pgNumType = OxmlElement("w:pgNumType")
    pgNumType.set(qn("w:start"), "1")
    sectPr.append(pgNumType)

    # ===== INTRODUCTION =====
    h(doc, "Introduction générale", 1)
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

    # ===== PROBLEMATIQUE (ESTA) =====
    h(doc, "Problématique", 1)
    p(
        doc,
        "Comment organiser un examen de programmation sur navigateur qui réduise "
        "fortement les possibilités de triche, conserve un rôle clair au surveillant "
        "humain, et restitue une correction lisible pour le professeur ?",
    )
    p(
        doc,
        "Objectif général : concevoir et réaliser une plateforme web multi "
        "établissement d'examens de programmation sécurisés, nommée Cylentic.",
    )
    p(doc, "Objectifs spécifiques :", first_line=False, space_after=4)
    for bullet in [
        "Structurer la gestion des établissements, des classes et des comptes selon des rôles distincts.",
        "Permettre au professeur de créer, publier et suivre un examen avec code d'accès.",
        "Contrôler la session de composition dans le navigateur et journaliser les incidents.",
        "Exécuter le code Python de façon isolée, puis corriger automatiquement par tests unitaires.",
        "Fournir au professeur des exports exploitables après l'épreuve.",
    ]:
        para = p(doc, f"• {bullet}", align="left", first_line=False, space_after=3)
    p(
        doc,
        "Méthodologie : étude de l'existant, spécification d'un MVP assumé, "
        "modélisation UML alignée sur le dépôt réel, implémentation avec Next.js, "
        "Prisma et MySQL, puis validation par parcours bout en bout et build de "
        "non régression.",
    )

    # ===== CHAPITRE 1 (dédoublonné) =====
    page_break(doc)
    h(doc, "Chapitre 1 : Contexte et étude de l'existant", 1)
    p(
        doc,
        "Ce chapitre ancre le projet dans son contexte pédagogique, détaille les "
        "sous problèmes techniques, compare les solutions existantes et positionne "
        "Cylentic. La formulation synthétique du problème et des objectifs figure "
        "dans la section Problématique ; elle n'est pas reprise ici en bloc.",
    )

    h(doc, "1.1 Contexte pédagogique et technologique", 2)
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
        "ni l'exécution réelle, ni le cycle d'essai correction propre à un "
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

    h(doc, "1.2 Sous-problèmes et contraintes locales", 2)
    p(
        doc,
        "Cinq sous problèmes structurent le besoin. Premier : contrôler "
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
        "donc rester simple à déployer le jour J, idéalement dans le navigateur, sans "
        "configuration lourde.",
    )
    p(
        doc,
        "Hypothèse de travail : si l'on verrouille suffisamment le navigateur et que "
        "l'on journalise les événements sensibles, on peut restaurer une crédibilité "
        "utile aux examens pratiques sur machine, sans revenir au papier, tout en "
        "conservant le jugement pédagogique du professeur.",
    )

    h(doc, "1.3 État de l'art et comparaison des solutions existantes", 2)
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
        "Les outils de proctoring répondent surtout à la surveillance d'examens "
        "généralistes. Leur licence est souvent élevée. Ils n'exécutent ni ne "
        "corrigent du code de programmation au sens attendu ici.",
    )
    p(
        doc,
        "Les sandboxes d'exécution, dont Judge0 est un exemple connu, isolent un "
        "programme et renvoient sa sortie. Ce sont des briques utiles, souvent auto "
        "hébergeables, mais pas une plateforme d'examen : pas de rôles scolaires, pas "
        "de passation contrôlée, pas de journal pédagogique.",
    )

    add_table_with_title(
        doc,
        "Comparaison des solutions existantes et de Cylentic",
        tables[0],
    )

    p(
        doc,
        "Aucune de ces solutions ne couvre à la fois composition sécurisée, exécution "
        "isolée, correction et traçabilité pour une école. C'est dans cet intervalle "
        "que se place Cylentic.",
    )

    h(doc, "1.4 Positionnement de Cylentic", 2)
    p(
        doc,
        "Cylentic n'est ni un clone d'une plateforme d'apprentissage ouverte, ni une "
        "simple variante de LMS. Il vise l'évaluation surveillée de la programmation.",
    )
    p(
        doc,
        "Sa singularité tient au couplage : éditeur dans le navigateur, sandbox Docker "
        "Python, contrôles de passation côté client, règles métier et timers côté "
        "serveur, journal d'incidents, exports professeur, et maintien du surveillant "
        "physique. S'y ajoute une gouvernance multi établissement, avec un Super Admin "
        "plateforme distinct de l'administrateur d'école.",
    )

    h(doc, "1.5 Conclusion partielle", 2)
    p(
        doc,
        "Le problème est réel, l'existant ne le résout que par fragments, et Cylentic "
        "occupe un espace utile. Le chapitre suivant fixe le cahier des charges du MVP.",
    )

    # ===== CHAPITRE 2 =====
    page_break(doc)
    figure_map = {}
    replay_blocks(
        doc,
        data["ch2"],
        skip_texts={
            "Ce chapitre délimite le MVP, identifie les acteurs, exprime les besoins fonctionnels et non fonctionnels, rappelle les règles métier structurantes et présente les scénarios d'usage prioritaires.",
        },
    )
    # Insert actors table after 2.2 if not already in stream - extracted ch2 has no tables.
    # Optionally insert after heading 2.2 content: find by re-adding table for actors at end of 2.2 section is hard.
    # Add actors & data tables at end of ch2 before conclusion? Better insert after 2.2 block manually in refined ch2.
    # For now add Tableau acteurs after section by scanning - simpler: append tables if titles exist later in ch3.

    # Add table acteurs after ch2.2 - we'll add after whole ch2 replay a second time? 
    # Inject: after playing ch2, we already finished. Insert actors table before 2.3 by rebuilding ch2 carefully.

    # ===== Rebuild ch2 more carefully =====
    # Actually we already wrote ch2. Let's continue and add missing comparison only was in ch1.
    # Actors table:
    # We can add after 2.2 by not using replay for ch2 and writing manually from extracted paras.

    # ===== CHAPITRE 3 =====
    page_break(doc)
    # Build figure descriptions map from extracted ch3 (pair Emplacement + Figure title)
    ch3 = data["ch3"]
    fig_desc = {}
    for i, item in enumerate(ch3):
        t = item["text"]
        if t.startswith("Figure ") and " : " in t:
            title = t.split(" : ", 1)[1]
            # previous non-empty descriptions
            desc = "Insérer le diagramme correspondant depuis docs/diagrammes/."
            for j in range(i - 1, max(-1, i - 4), -1):
                prev = ch3[j]["text"]
                if prev.startswith("Insérer") or prev.startswith("Schéma"):
                    desc = prev
                    break
            fig_desc[title] = desc

    # Skip overly long chapter intro fluff
    replay_blocks(
        doc,
        ch3,
        skip_texts={
            "Une fois les besoins posés, il reste à donner au système une forme stable, discutable devant un jury et transposable en code. Ce chapitre décrit la démarche de conception, l'architecture retenue, les vues UML produites à partir du fonctionnement réel de la plateforme, la structure des données, puis les choix liés à la sécurité de passation et à la correction automatique.",
        },
        figure_map=fig_desc,
    )

    # Insert class/data tables if not embedded - tables[1] actors was never inserted in ch2.
    # Insert actors table: add near end before ch3? Too late.
    # Insert data table again would duplicate - ch3 text mentions Tableau 3.2 - need to embed tables.

    # Re-insert Tableau acteurs and data by scanning written doc is complex.
    # Add them now with titles - if "Tableau 3.1" text was skipped, add physical tables at proper places via second pass.
    # Practical fix: append clear tables with SEQ after 3.3 and 3.7 headings by a second document walk - skip for time.
    # We'll add actors table into ch2 by regenerating ch2 properly below before ch3... 

    # Because ch2 already written, insert actors table now near ch2.2 by searching paragraphs.
    # Doc is sequential - can't insert midstream easily with high level API without XML.
    # Use insert after finding paragraph.

    from docx.text.paragraph import Paragraph as P

    def insert_after_heading(start_prefix, build_fn):
        target = None
        for para in doc.paragraphs:
            if para.style and para.style.name.startswith("Heading") and para.text.strip().startswith(start_prefix):
                target = para
        if not target:
            return
        # collect following paragraphs until next heading of same/higher? We append after next body blocks - complicated.
        # Simpler: call build_fn which adds at end - BAD.
        # Insert XML after the first body paragraph following heading.
        # Find the heading, then find last paragraph before next heading 2/1
        paras = list(doc.paragraphs)
        idx = None
        for i, para in enumerate(paras):
            if para._p is target._p:
                idx = i
                break
        if idx is None:
            return
        # find end of section content
        end = idx + 1
        while end < len(paras):
            st = paras[end].style.name if paras[end].style else ""
            tx = paras[end].text.strip()
            if st.startswith("Heading") and (st == "Heading 1" or st == "Heading 2"):
                break
            end += 1
        anchor = paras[end - 1] if end - 1 >= idx else target
        # temporarily set doc._body insertion by building table then moving - use build_fn(anchor)
        build_fn(anchor)

    def table_after(anchor, title, rows):
        # create elements after anchor by using a temporary approach:
        # add_table at end then move
        # Title paragraph
        new_p = OxmlElement("w:p")
        anchor._p.addnext(new_p)
        title_para = P(new_p, anchor._parent)
        run1 = title_para.add_run("Tableau ")
        set_run_font(run1, size=11, bold=True)
        run = title_para.add_run()
        r = run._r
        for el in [
            ("begin", None),
        ]:
            pass
        fc1 = OxmlElement("w:fldChar"); fc1.set(qn("w:fldCharType"), "begin")
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "SEQ Tableau \\* ARABIC"
        fc2 = OxmlElement("w:fldChar"); fc2.set(qn("w:fldCharType"), "separate")
        tt = OxmlElement("w:t"); tt.text = "1"
        fc3 = OxmlElement("w:fldChar"); fc3.set(qn("w:fldCharType"), "end")
        r.append(fc1); r.append(it); r.append(fc2); r.append(tt); r.append(fc3)
        set_run_font(run, size=11, bold=True)
        run2 = title_para.add_run(f" : {title}")
        set_run_font(run2, size=11, bold=True)
        title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT

        table = doc.add_table(rows=len(rows), cols=len(rows[0]))
        table.style = "Table Grid"
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = table.rows[i].cells[j]
                cell.text = val
                for paragraph in cell.paragraphs:
                    for rr in paragraph.runs:
                        set_run_font(rr, size=10, bold=(i == 0))
        tbl = table._tbl
        tbl.getparent().remove(tbl)
        title_para._p.addnext(tbl)
        src = OxmlElement("w:p")
        tbl.addnext(src)
        sp = P(src, anchor._parent)
        rr = sp.add_run("Source : spécification du projet Cylentic.")
        set_run_font(rr, size=10, italic=True)

    # Insert actors table after 2.2
    insert_after_heading("2.2 Identification des acteurs", lambda a: table_after(a, "Correspondance entre acteurs et responsabilités", tables[1]))
    # Insert data table after 3.7
    insert_after_heading("3.7 Conception des données", lambda a: table_after(a, "Principales tables persistantes et rôle", tables[2]))

    # ===== CHAPITRE 4 =====
    page_break(doc)
    fig4 = {
        "Salle d'attente avant le démarrage de l'examen": "Insérer la capture de la salle d'attente.",
        "Environnement de composition pendant l'épreuve": "Insérer la capture de la page de composition.",
    }
    replay_blocks(
        doc,
        data["ch4"],
        skip_texts={
            "Une fois le cadrage et la conception posés, la réalisation a pour objet de transformer le cahier des charges en un produit exécutable. L'équipe a cherché un dépôt unique, déployable localement, capable de faire vivre les rôles de la plateforme et surtout de faire passer un examen du début à la fin : création, publication, composition sous contraintes, correction, puis exports.",
        },
        figure_map=fig4,
    )

    # ===== CHAPITRE 5 =====
    page_break(doc)
    # Renumber awkward heading 3 without numbers
    ch5 = []
    for item in data["ch5"]:
        t = item["text"]
        if item["type"] == "h3" and not t[0].isdigit():
            mapping = {
                "Authentification et accès": "5.2.1 Authentification et accès",
                "Administration": "5.2.2 Administration",
                "Examens côté professeur": "5.2.3 Examens côté professeur",
                "Parcours étudiant et contrôles de passation": "5.2.4 Parcours étudiant et contrôles de passation",
            }
            t = mapping.get(t, t)
            ch5.append({"type": "h3", "text": t})
        else:
            ch5.append(item)
    replay_blocks(
        doc,
        ch5,
        skip_texts={
            "Ce chapitre présente la campagne de validation du MVP, les résultats observés, les anomalies corrigées en cours de route, les limites assumées et les perspectives de poursuite.",
        },
    )

    # ===== CONCLUSION =====
    page_break(doc)
    h(doc, "Conclusion générale", 1)
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
        "L'analyse a borné un MVP assumé. La conception UML a fixé rôles, données et "
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
        "objectifs du travail sont atteints pour le MVP ; les perspectives tracent "
        "une suite crédible sans promettre l'absolu.",
    )

    # ===== BIBLIO =====
    page_break(doc)
    h(doc, "Bibliographie et webographie", 1)
    refs = [
        "[1] Object Management Group, OMG Unified Modeling Language (OMG UML), documentation officielle.",
        "[2] Vercel, Next.js Documentation, https://nextjs.org/docs, consulté le 15/07/2026 à 12h.",
        "[3] Prisma, Prisma Documentation, https://www.prisma.io/docs, consulté le 15/07/2026 à 12h.",
        "[4] Oracle, MySQL 8 Documentation, https://dev.mysql.com/doc/, consulté le 15/07/2026 à 12h.",
        "[5] Redis Ltd, Redis Documentation, https://redis.io/docs/, consulté le 15/07/2026 à 12h.",
        "[6] Docker Inc., Docker Documentation, https://docs.docker.com/, consulté le 15/07/2026 à 12h.",
        "[7] ESTA, Guide du stagiaire Master/Ingénieur, année académique 2024-2025 (référence de mise en forme).",
        "[8] freeCodeCamp, plateforme d'apprentissage en ligne, https://www.freecodecamp.org/, consulté le 15/07/2026 à 12h.",
        "[9] Moodle HQ, Moodle Documentation, https://docs.moodle.org/, consulté le 15/07/2026 à 12h.",
        "[10] Judge0, Judge0 CE Documentation, https://judge0.com/, consulté le 15/07/2026 à 12h.",
    ]
    for r in refs:
        p(doc, r, align="left", first_line=False, space_after=6)

    # ===== ANNEXES =====
    page_break(doc)
    h(doc, "Annexes", 1)
    p(
        doc,
        "Les annexes regroupent des éléments utiles qui allègent le corps du rapport. "
        "Elles seront enrichies des diagrammes et captures en grand format lors de "
        "l'insertion manuelle des images.",
    )

    h(doc, "Annexe A : Inventaire des diagrammes UML", 2)
    p(
        doc,
        "Les fichiers sources PlantUML se trouvent dans le dépôt de rapport "
        "(docs/diagrammes/). Ils couvrent les cas d'utilisation, classes, objets, "
        "composants, déploiement, états, séquences et activités utilisés au chapitre 3.",
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
        "Espace réservé aux captures d'administration, de publication, de journal "
        "d'incidents et d'exports, au-delà des figures  déjà prévues dans le corps.",
        first_line=False,
    )

    h(doc, "Annexe D : Modèle CSV d'import des étudiants", 2)
    p(
        doc,
        "Colonnes attendues : nom, prénom, classe, matricule, email. Les lignes "
        "invalides sont rejetées avec un rapport d'erreurs exploitable.",
        first_line=False,
    )

    # ===== TABLE DES MATIERES (fin, ESTA) =====
    page_break(doc)
    h(doc, "Table des matières", 1)
    p(
        doc,
        "Table complète des titres et sous-titres. Dans Word : sélectionner le champ, "
        "clic droit, Mettre à jour les champs, choisir Mettre à jour toute la table. "
        "Les entrées deviennent cliquables.",
        italic=True,
        first_line=False,
        size=11,
    )
    tdm = p(doc, "", first_line=False, align="left")
    add_toc_field(tdm, r'TOC \o "1-3" \h \z \u')

    doc.save(OUT)
    # also replace carcasse name for clarity
    also = Path("/workspace/docs/Rapport_Cylentic_Carcasse_Chapitre3.docx")
    doc.save(also)
    print("Wrote", OUT)
    print("Also updated", also)


if __name__ == "__main__":
    build()
