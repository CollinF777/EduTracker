import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .courses import Course
from .transcription import Transcription

# Splits texts so unsure bits ([[guess]] and [illegible]) end up in their own pieces
_SPLIT = re.compile(r"(\[\[.+?\]\]|\[illegible\])")

# Add texts to a paragraph, will highlight anything the model isnt sure about
def _add_text(paragraph, text: str, *, bold=False, italic=False, font=None, size=None):
    for piece in _SPLIT.split(text):
        if not piece:
            continue
        unsure = bool(_SPLIT.fullmatch(piece))
        if piece.startswith("[["):
            # Show the guess without the brackets
            piece = piece[2:-2]

        # A run is a section of text within a paragraph
        run = paragraph.add_run(piece)
        run.bold = bold
        run.italic = italic
        if font:
            run.font.name = font
        if size:
            run.font.size = Pt(size)
        if unsure:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW

# used to shade table
def _shade(cell, fill: str):
    # The w means its an XML attribute used by Word
    shd = OxmlElement("w:shd")
    # We use clear as solid would render it black
    # qn just means qualified name aka it just translates the word shorthand name to the full name so we can modify the formatting
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    # Adds the shade to each table cell prop (thats what tcPr means)
    cell._tc.get_or_add_tcPr().append(shd)

# used to make tables
def _add_table(doc, rows: list[list[str]], header: bool):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            para = cell.paragraphs[0]
            _add_text(para, val, bold=(header and r == 0))
            if header and r == 0:
                _shade(cell, "D9D9D9")
    # Marks the row as a header so screen readers can announce the column names
    if header:
        trPr = table.rows[0]._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:tblHeader"))
    # Breathing room so whatever is after the table isnt hugging it
    doc.add_paragraph()

# Saves the docx, recognitionresult is optional, if its there its just used for info under the title
def save_docx(transcription: Transcription, path: str | Path, *, course: Course | None = None, result = None, plain: bool = False) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    doc.core_properties.title = transcription.title or "Transcribed notes"
    doc.core_properties.language = "en-US"

    # Default settings
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    if not plain:
        # Level 0 means its a title style
        doc.add_heading(transcription.title or "Transcribed notes", level=0)

        # Small info line including course, detected topics, where a pic came from
        info = []
        if course:
            info.append(course.label)
        if result is not None and result.topics:
            info.append("Topics: " + ", ".join(t.label for t in result.topics))
        if result is not None and not str(result.image_path).startswith("<"):
            info.append("Source: " + Path(result.image_path).name)
        if info:
            p = doc.add_paragraph()
            _add_text(p, " | ".join(info), italic=True, size=10)
            for run in p.runs:
                run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    if transcription.uncertain_count and not plain:
        p = doc.add_paragraph()
        _add_text(p, "Highlighted text was hard to read. Please check it against the original.", italic=True, size=10)

    if transcription.error:
        p = doc.add_paragraph()
        _add_text(p, f"Note: {transcription.error}. The raw response is shown below", italic=True, size=10)

    number = 0
    for b in transcription.blocks:
        number = number + 1 if b.type == "numbered" else 0

        if b.type == "heading":
            _add_text(doc.add_heading("", level=2), b.text)
        elif b.type == "bullet":
            _add_text(doc.add_paragraph(style="List Bullet"), b.text)
        # Numbers are written in by hand because Word keeps counting across separate lists
        elif b.type == "numbered":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            _add_text(p, f"{number}. {b.text}")
        elif b.type == "equation":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_text(p, b.text, font="Cambria Math", size=13)
        elif b.type == "figure":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            _add_text(p, "Figure: ", bold=True, italic=True)
            _add_text(p, b.text, italic=True)
        elif b.type == "table":
            _add_table(doc, b.rows, b.header)
        else:
            _add_text(doc.add_paragraph(), b.text)

    doc.save(path)
    return path

# Pick a file name that doesnt overwrite anything. Live caputres and uploads have labels like <camera> which gets replaced with a timestamp
def docx_path_for(label: str, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    # Live camera or upload
    if label.startswith("<"):
        stem = f"notes_{datetime.now():%Y%m%d_%H%M%S}"
    else:
        # .stem is because it needs a .docx extension and not the image extension
        stem = Path(label).stem
    # Not division, this joins out_dir and {stem}.docx
    candidate = out_dir / f"{stem}.docx"
    n = 2
    # prevent overwriting an existing file
    while candidate.exists():
        candidate = out_dir / f"{stem}_{n}.docx"
        n+= 1
    return candidate