# -*- coding: utf-8 -*-
"""Rendu PDF du manuel d'étude PEB à partir de fichiers .md au balisage léger."""
import os, re, glob, sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                               Table, TableStyle, PageBreak, KeepTogether, HRFlowable,
                               NextPageTemplate, Flowable, ListFlowable, ListItem)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas as canvaslib

ROOT = "/home/user/scaling-guacamole"
SRC = os.path.join(ROOT, "work/book")
OUT = os.path.join(ROOT, "Manuel_PEB_Bruxelles_Etude_Intensive.pdf")

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DJ", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJ-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJ-M", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("DJ-I", F + "DejaVuSerif.ttf"))
pdfmetrics.registerFont(TTFont("DJ-BI", F + "DejaVuSerif-Bold.ttf"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B", italic="DJ-I", boldItalic="DJ-BI")

NAVY = colors.HexColor("#12304A")
BLUE = colors.HexColor("#1B5E8C")
TEAL = colors.HexColor("#0E6E6E")
ORANGE = colors.HexColor("#B85C00")
RED = colors.HexColor("#A32828")
LIGHT = colors.HexColor("#EEF4F8")
LIGHT2 = colors.HexColor("#F5F8E9")
LIGHT3 = colors.HexColor("#FDF0EC")
GREY = colors.HexColor("#5A6672")
GOLD = colors.HexColor("#F2C14E")

PW, PH = A4
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 17*mm, 15*mm, 19*mm, 17*mm
FRAME_W = PW - MARGIN_L - MARGIN_R

styles = {}
def S(name, **kw):
    base = dict(fontName="DJ", fontSize=9.1, leading=12.7, textColor=colors.HexColor("#1E2830"),
                alignment=TA_JUSTIFY, spaceAfter=3.5)
    base.update(kw)
    styles[name] = ParagraphStyle(name, **base)
    return styles[name]

S("body")
S("small", fontSize=7.7, leading=10.2, alignment=TA_LEFT, spaceAfter=2)
S("tiny", fontSize=6.9, leading=8.9, alignment=TA_LEFT, spaceAfter=1)
S("bullet", fontSize=8.9, leading=12.0, alignment=TA_LEFT, spaceAfter=1.8, leftIndent=9, bulletIndent=1)
S("bullet2", fontSize=8.6, leading=11.5, alignment=TA_LEFT, spaceAfter=1.2, leftIndent=18, bulletIndent=10)
S("h1", fontName="DJ-B", fontSize=21, leading=25, textColor=NAVY, alignment=TA_LEFT, spaceBefore=6, spaceAfter=9)
S("h2", fontName="DJ-B", fontSize=14.2, leading=17.5, textColor=BLUE, alignment=TA_LEFT,
  spaceBefore=11, spaceAfter=6)
S("h3", fontName="DJ-B", fontSize=10.7, leading=13.6, textColor=TEAL, alignment=TA_LEFT,
  spaceBefore=8, spaceAfter=4)
S("h4", fontName="DJ-B", fontSize=9.4, leading=12, textColor=NAVY, alignment=TA_LEFT,
  spaceBefore=5, spaceAfter=3)
S("box", fontSize=8.6, leading=11.8, alignment=TA_LEFT, spaceAfter=0)
S("boxb", fontName="DJ-B", fontSize=8.6, leading=11.8, alignment=TA_LEFT, spaceAfter=0)
S("table", fontSize=7.5, leading=9.6, alignment=TA_LEFT, spaceAfter=0)
S("tableb", fontName="DJ-B", fontSize=7.5, leading=9.6, alignment=TA_LEFT,
  textColor=colors.white, spaceAfter=0)
S("q", fontSize=8.7, leading=11.7, alignment=TA_LEFT, spaceAfter=2, leftIndent=0)
S("caption", fontName="DJ-B", fontSize=8, leading=10.5, textColor=GREY, alignment=TA_LEFT,
  spaceBefore=3, spaceAfter=5)
S("cover_t", fontName="DJ-B", fontSize=27, leading=32, textColor=NAVY, alignment=TA_LEFT, spaceAfter=10)
S("cover_s", fontName="DJ", fontSize=13.5, leading=18, textColor=BLUE, alignment=TA_LEFT, spaceAfter=8)
S("cover_x", fontSize=9.5, leading=14, textColor=GREY, alignment=TA_LEFT, spaceAfter=4)
S("toc1", fontName="DJ-B", fontSize=9.7, leading=14.5, textColor=NAVY,
  alignment=TA_LEFT, spaceBefore=5, spaceAfter=0)
S("toc2", fontSize=8.2, leading=11.3, textColor=colors.HexColor("#22303C"),
  alignment=TA_LEFT, leftIndent=12, spaceBefore=0, spaceAfter=0)
S("answer", fontSize=8.2, leading=11, alignment=TA_LEFT, spaceAfter=2)

INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
INLINE_ITALIC = re.compile(r"\*([^*]+?)\*")

def esc(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = INLINE_BOLD.sub(lambda m: "<b>%s</b>" % m.group(1), t)
    t = INLINE_ITALIC.sub(lambda m: "<i>%s</i>" % m.group(1), t)
    return t

def P(text, style="body"):
    return Paragraph(esc(text), styles[style])

class Rule(Flowable):
    def __init__(self, color=BLUE, thickness=0.9, width=None):
        Flowable.__init__(self); self.color=color; self.th=thickness
        self.width = width or FRAME_W
        self.height = thickness + 3
    def wrap(self, aw, ah):
        return (min(self.width, aw), self.height)
    def draw(self):
        self.canv.setStrokeColor(self.color); self.canv.setLineWidth(self.th)
        self.canv.line(0, 2, min(self.width, FRAME_W), 2)

def box(lines, bg=LIGHT, bar=BLUE, style="box", pad=6):
    # une ligne = une ligne du tableau : permet la coupure entre pages
    data = []
    for ln in lines:
        if ln.startswith("!!"):
            data.append([Paragraph(esc(ln[2:].strip()), styles["boxb"])])
        else:
            data.append([Paragraph(esc(ln), styles[style])])
    t = Table(data, colWidths=[FRAME_W], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("LINEBEFORE", (0,0), (0,-1), 3, bar),
        ("BOX", (0,0), (-1,-1), 0.4, colors.HexColor("#D5DEE5")),
        ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (0,0), 6), ("BOTTOMPADDING", (0,-1), (-1,-1), 6),
        ("TOPPADDING", (0,1), (-1,-1), 1.2), ("BOTTOMPADDING", (0,0), (-1,-2), 1.2),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return t

def make_table(rows, caption=None, widths=None):
    if not rows: return Spacer(1,1)
    ncol = max(len(r) for r in rows)
    rows = [r + [""]*(ncol-len(r)) for r in rows]
    data = []
    for i, r in enumerate(rows):
        st = "tableb" if i == 0 else "table"
        data.append([Paragraph(esc(str(c)), styles[st]) for c in r])
    if widths:
        cw = [FRAME_W*w for w in widths]
    else:
        # répartition : première colonne plus étroite si beaucoup de colonnes
        if ncol == 2: cw = [FRAME_W*0.34, FRAME_W*0.66]
        elif ncol == 3: cw = [FRAME_W*0.27, FRAME_W*0.40, FRAME_W*0.33]
        elif ncol == 4: cw = [FRAME_W*0.24, FRAME_W*0.26, FRAME_W*0.26, FRAME_W*0.24]
        else: cw = [FRAME_W/ncol]*ncol
    t = Table(data, colWidths=cw, repeatRows=1, hAlign="LEFT")
    ts = [("BACKGROUND", (0,0), (-1,0), NAVY),
          ("VALIGN", (0,0), (-1,-1), "TOP"),
          ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#C8D3DC")),
          ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F4F8FB")]),
          ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
          ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]
    t.setStyle(TableStyle(ts))
    out = []
    if caption: out.append(P("TABLEAU · " + caption, "caption"))
    out.append(t); out.append(Spacer(1, 6))
    return out

class BookDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        frame = Frame(MARGIN_L, MARGIN_B, FRAME_W, PH-MARGIN_T-MARGIN_B, id="main",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        cover = Frame(MARGIN_L, MARGIN_B, FRAME_W, PH-MARGIN_T-MARGIN_B, id="cover",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[cover], onPage=self.cover_page),
            # décor en fin de page : le libellé de partie reflète le contenu de la page elle-même
            PageTemplate(id="Main", frames=[frame], onPageEnd=self.normal_page),
        ])
        self.part_name = ""
        self.chap_name = ""
    def cover_page(self, canv, doc):
        canv.saveState()
        canv.setFillColor(NAVY); canv.rect(0, PH-13*mm, PW, 13*mm, stroke=0, fill=1)
        canv.setFillColor(GOLD); canv.rect(0, 0, PW, 8*mm, stroke=0, fill=1)
        canv.restoreState()
    def normal_page(self, canv, doc):
        canv.saveState()
        canv.setFillColor(NAVY); canv.rect(0, PH-11*mm, PW, 11*mm, stroke=0, fill=1)
        canv.setFont("DJ-B", 7.4); canv.setFillColor(colors.white)
        canv.drawString(MARGIN_L, PH-7.6*mm, "MANUEL D'ÉTUDE INTENSIF  ·  CERTIFICATEUR PEB RÉSIDENTIEL  ·  BRUXELLES")
        canv.setFont("DJ", 7.4)
        canv.drawRightString(PW-MARGIN_R, PH-7.6*mm, CURRENT_PART["short"])
        canv.setStrokeColor(colors.HexColor("#C8D3DC")); canv.setLineWidth(0.5)
        canv.line(MARGIN_L, 12*mm, PW-MARGIN_R, 12*mm)
        canv.setFont("DJ", 7.3); canv.setFillColor(GREY)
        canv.drawString(MARGIN_L, 8*mm, "Protocole v2.7 – nov. 2024  ·  Livres I, II, III  ·  références de page entre ( )")
        canv.drawRightString(PW-MARGIN_R, 8*mm, "Page %d" % doc.page)
        canv.setFillColor(GOLD); canv.rect(0, 0, PW, 2.2*mm, stroke=0, fill=1)
        canv.restoreState()
    def beforeDocument(self):
        # multiBuild rejoue plusieurs passes : repartir d'un état propre à chaque fois
        CURRENT_PART["name"] = ""
        CURRENT_PART["short"] = ""
        OUTLINE.clear()
    def afterFlowable(self, flowable):
        if hasattr(flowable, "_toc_level"):
            lvl = flowable._toc_level; txt = flowable._toc_text
            self.notify("TOCEntry", (lvl, txt, self.page))
            OUTLINE.append((lvl, txt, self.page))

def heading(text, level):
    st = {0:"h1", 1:"h2", 2:"h3", 3:"h4"}[level]
    p = Paragraph(esc(text), styles[st])
    plain = INLINE_BOLD.sub(lambda m: m.group(1), text)
    plain = INLINE_ITALIC.sub(lambda m: m.group(1), plain)
    p._toc_level = level; p._toc_text = plain
    return p

CURRENT_PART = {"name": "", "short": ""}
OUTLINE = []

SHORT_PARTS = {
    "PARTIE 0": "PARTIE 0 · MÉTHODE",
    "PARTIE I": "LIVRE I · GÉNÉRALITÉS",
    "PARTIE II": "LIVRE II · ENVELOPPE",
    "PARTIE III": "LIVRE III · INSTALLATIONS",
    "PARTIE IV": "PARTIE IV · ANTI-OUBLI",
    "PARTIE V": "PARTIE V · EXAMENS BLANCS",
    "PARTIE VI": "PARTIE VI · CORRIGÉS",
    "PARTIE VII": "PARTIE VII · ANNEXES",
}

def short_part(name):
    if name == "Table des matières": return "TABLE DES MATIÈRES"
    key = name.split(" — ")[0].strip()
    return SHORT_PARTS.get(key, name[:28])

class SetPart(Flowable):
    def __init__(self, name): Flowable.__init__(self); self.name=name; self.width=0; self.height=0
    def draw(self):
        CURRENT_PART["name"] = self.name
        CURRENT_PART["short"] = short_part(self.name)
    def wrap(self, aw, ah): return (0,0)

def parse_files():
    files = sorted(glob.glob(os.path.join(SRC, "*.md")))
    # ordre explicite
    order = ["00","01a","01b","01c","01d","02a","02b","02c","03a","03b","03c","03d",
             "04","05","06","07"]
    def key(p):
        b = os.path.basename(p)[:-3]
        for i,o in enumerate(order):
            if b.endswith(o) or b.split("_")[0]==o: return i
        return 99
    files.sort(key=lambda p: (key(p), p))
    print("Fichiers sources:", [os.path.basename(f) for f in files])
    return files

def build():
    story = []
    questions = {}   # id -> (chapter, text)
    answers = {}     # id -> text
    # ---------- couverture ----------
    story += [Spacer(1, 24*mm)]
    story += [P("PRÉPARATION À L'EXAMEN", "cover_s")]
    story += [Paragraph("Manuel d'étude intensif", styles["cover_t"])]
    story += [Paragraph("Certificateur PEB<br/>« Habitation individuelle »", styles["cover_t"])]
    story += [Spacer(1, 6*mm), Rule(GOLD, 2.2), Spacer(1, 7*mm)]
    story += [P("Synthèse exhaustive des trois livres du Protocole de certification PEB résidentiel "
                "(Bruxelles Environnement, version 2.7 – novembre 2024), conçue selon les résultats "
                "de la recherche en psychologie de l'apprentissage.", "cover_x")]
    story += [Spacer(1, 4*mm)]
    story += [P("LIVRE I – Généralités  ·  LIVRE II – Enveloppe  ·  LIVRE III – Installations techniques", "cover_x")]
    story += [Spacer(1, 10*mm)]
    cover_box = box([
        "!!MODE D'EMPLOI EN UNE PHRASE",
        "Lisez une fiche, FERMEZ le livre, répondez aux questions de rappel, puis seulement ensuite "
        "vérifiez dans les corrigés ; recommencez selon le planning espacé de la Partie 0.",
        "Ce document n'est pas une lecture : c'est un programme d'entraînement. Les protocoles officiels "
        "restent la référence juridique ; les numéros de page entre parenthèses renvoient aux PDF sources."
    ], bg=LIGHT2, bar=TEAL, style="box")
    story += [cover_box]
    story += [Spacer(1, 8*mm)]
    story += [P("Document d'étude privé — français — généré le 4 novembre 2026. Aucune valeur du protocole "
                "officiel n'a été modifiée : les chiffres, seuils et règles sont ceux de la version 2.7 (novembre 2024).", "small")]
    story += [NextPageTemplate("Main"), PageBreak()]

    # ---------- table des matières ----------
    story += [SetPart("Table des matières")]
    story += [heading("Table des matières", 0)]
    toc = TableOfContents()
    toc.levelStyles = [styles["toc1"], styles["toc2"], styles["toc2"], styles["toc2"]]
    story += [toc, PageBreak()]

    files = parse_files()
    for f in files:
        lines = open(f, encoding="utf-8").read().split("\n")
        i = 0
        pending_table = []
        table_caption = None
        table_widths = None
        def flush_table():
            nonlocal pending_table, table_caption, table_widths
            if pending_table:
                story.extend(make_table(pending_table, table_caption, table_widths))
                pending_table = []; table_caption = None; table_widths = None
        while i < len(lines):
            ln = lines[i].rstrip()
            s = ln.strip()
            if s.startswith("|"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                # la légende et les largeurs peuvent être attachées à n'importe quelle cellule
                keep = []
                for c in cells:
                    if c.startswith("~~"):
                        table_caption = c[2:].strip()
                    elif c.startswith("w:"):
                        try: table_widths = [float(x) for x in c[2:].split(",")]
                        except: pass
                    else:
                        keep.append(c)
                while keep and keep[-1] == "":
                    keep.pop()
                if keep and not all(re.fullmatch(r"[-: ]*", c) for c in keep):
                    pending_table.append(keep)
                i += 1; continue
            flush_table()
            if not s:
                i += 1; continue
            if s.startswith("#### "): story.append(heading(s[5:], 3)); i+=1; continue
            if s.startswith("### "):  story.append(heading(s[4:], 2)); i+=1; continue
            if s.startswith("## "):   story.append(heading(s[3:], 1)); i+=1; continue
            if s.startswith("# "):
                name = s[2:]
                story.append(PageBreak())
                story.append(SetPart(name))
                story.append(heading(name, 0))
                story.append(Rule(GOLD, 1.6))
                story.append(Spacer(1, 5))
                i+=1; continue
            if s == "---":
                story.append(Spacer(1, 3)); story.append(Rule(colors.HexColor("#D5DEE5"), 0.6)); story.append(Spacer(1, 4))
                i+=1; continue
            if s == "***": story.append(PageBreak()); i+=1; continue
            if s.startswith("@PART|"):
                story.append(SetPart(s.split("|",1)[1])); i+=1; continue
            if s.startswith("@Q|"):
                parts = s.split("|", 2)
                qid, qtext = parts[1], parts[2]
                questions[qid] = qtext
                story.append(Spacer(1, 3))
                story.append(Paragraph("<b>Q %s</b> — %s" % (esc(qid), esc(qtext)), styles["q"]))
                story.append(Paragraph("<font color='#9AA7B1'>Réponse (sans regarder) : "
                                       ".......................................................................................................................</font>", styles["tiny"]))
                i+=1; continue
            if s.startswith("@A|"):
                parts = s.split("|", 2); answers[parts[1]] = parts[2]
                i+=1; continue
            if s.startswith("@ANSWERS"):
                # titre + corrigés générés automatiquement
                story.append(heading("Corrigés des questions de rappel", 1))
                story.append(P("Les corrigés sont volontairement regroupés ici, loin des questions : la "
                               "recherche montre que l'effort de récupération, et non la relecture de la réponse, "
                               "crée l'apprentissage (Roediger & Karpicke, 2006). Notez votre confiance (1–3) "
                               "avant de corriger : les erreurs très confiantes sont les plus instructives "
                               "(Butterfield & Metcalfe, 2001).", "box"))
                story.append(Spacer(1,4))
                for qid in sorted(questions, key=lambda x: (x.split(".")[0], x)):
                    ans = answers.get(qid, "— corrigé à compléter —")
                    t = Table([[Paragraph("<b>%s</b>  %s" % (esc(qid), esc(ans)), styles["answer"])]],
                              colWidths=[FRAME_W])
                    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#F7F9FB")),
                                           ("LINEBEFORE",(0,0),(0,-1),2,TEAL),
                                           ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),5),
                                           ("TOPPADDING",(0,0),(-1,-1),2.5),("BOTTOMPADDING",(0,0),(-1,-1),2.5)]))
                    story.append(t); story.append(Spacer(1,1.5))
                i+=1; continue
            if s.startswith("> "):
                # encadré : rassembler les lignes consécutives
                buf=[]
                while i < len(lines) and lines[i].strip().startswith("> "):
                    buf.append(lines[i].strip()[2:]); i+=1
                story.append(box(buf, LIGHT, BLUE)); story.append(Spacer(1,5)); continue
            if s.startswith("! "):
                buf=[]
                while i < len(lines) and lines[i].strip().startswith("! "):
                    buf.append(lines[i].strip()[2:]); i+=1
                story.append(box(buf, LIGHT3, RED)); story.append(Spacer(1,5)); continue
            if s.startswith("+ "):
                buf=[]
                while i < len(lines) and lines[i].strip().startswith("+ "):
                    buf.append(lines[i].strip()[2:]); i+=1
                story.append(box(buf, LIGHT2, TEAL)); story.append(Spacer(1,5)); continue
            if s.startswith("~ "):
                story.append(P(s[2:], "caption")); i+=1; continue
            if s.startswith("- "):
                story.append(Paragraph(esc(s[2:]), styles["bullet"], bulletText="•")); i+=1; continue
            if s.startswith("-- "):
                story.append(Paragraph(esc(s[3:]), styles["bullet2"], bulletText="–")); i+=1; continue
            if re.match(r"^\d+\) ", s):
                story.append(Paragraph(esc(s), styles["bullet"])); i+=1; continue
            story.append(P(s, "body")); i+=1
        flush_table()

    doc = BookDoc(OUT, pagesize=A4, leftMargin=MARGIN_L, rightMargin=MARGIN_R,
                  topMargin=MARGIN_T, bottomMargin=MARGIN_B,
                  title="Manuel d'étude intensif — Certificateur PEB résidentiel (Bruxelles)",
                  author="Manuel de préparation – Protocole PEB v2.7", subject="PEB Bruxelles")
    doc.multiBuild(story)
    # signets de navigation (plan du PDF), issus de la dernière passe de mise en page
    try:
        import pymupdf
        pdoc = pymupdf.open(OUT)
        pdoc.set_toc([[lvl+1, txt, max(1, pg)] for lvl, txt, pg in OUTLINE])
        tmp = OUT + ".tmp"
        pdoc.save(tmp, garbage=3, deflate=True)
        pdoc.close()
        os.replace(tmp, OUT)
        print("Signets PDF :", len(OUTLINE))
    except Exception as e:
        print("Signets non ajoutés :", e)
    print("PDF écrit :", OUT, os.path.getsize(OUT), "octets")
    print("Questions:", len(questions), "Corrigés:", len(answers))
    missing = set(questions)-set(answers)
    print("Corrigés manquants:", sorted(missing)[:30], "total", len(missing))

if __name__ == "__main__":
    build()
