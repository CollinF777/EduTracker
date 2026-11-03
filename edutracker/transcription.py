import json
import re
from dataclasses import dataclass, field

from .courses import Course, Topic

# This is specifying what the model can return, anything else must be a paragraph
BLOCK_TYPES = {"heading", "paragraph", "bullet", "numbered", "equation", "figure", "table"}

# This is how the model is going to mark stuff, if you dont know regex ill explain below
'''
You open with r so that python treats it as a raw string so \ is interpreted literally and not as a string escape
Okay now for the actual regex. So note that theres a | in the middle, this is an or so the regex looks for either pattern

The first part: \[\[.+?\]\]
This is matching text surrounded by double square brackets like this [[missing word]]
The \[\[ the backslashes escape the square brackets so it means literally [[ at the start of the pattern
Inside is .+? which can be broken down for each character
. matches almost any character except newline by default 
+ means theres is one or more characters so we cant have [[]]
? makes the match non greedy aka it matches as little as possible while still satisfying the pattern so [[a]] is good
Lastly \]\] is just matching literal ]] so the pattern ends with ]]

The second part: \[illegible\]
This one is a lot more simple, by this is just saying [illegible] is okay
if we did [illegible] instead of \[illegible\] then it would just match the characters instead of the word
'''
UNCERTAIN_PATTERN = re.compile(r"\[\[.+?\]\]|\[illegible\]")

@dataclass
class Block:
    type: str # One of the above block types
    text: str = "" # Used by everything but tables
    rows: list[list[str]] = field(default_factory=list) # Used for tables
    header: bool = False # only used by tables True if the first row is a header row

@dataclass
class Transcription:
    title: str # Short title, its fine if its empty
    blocks: list[Block]
    raw_response: str = "" # Full model response for debugging purposes
    error: str = "" # Filled in if response cant be parsed

    # How many spots the model flagged as unsure, helps tell the user how much they should double check
    @property
    def uncertain_count(self) -> int:
        total = 0
        for b in self.blocks:
            cells = [b.text] + [c for row in b.rows for c in row]
            total += sum(len(UNCERTAIN_PATTERN.findall(c)) for c in cells)
        return total

    def to_text(self) -> str:
        # Plain text version for terminal
        lines = [self.title, ""] if self.title else []
        n = 0
        for b in self.blocks:
            n = n + 1 if b.type == "numbered" else 0
            if b.type == "bullet":
                lines.append(f"- {b.text}")
            elif b.type == "numbered":
                lines.append(f"{n}. {b.text}")
            elif b.type == "heading":
                lines.append(f"\n{b.text}")
            elif b.type == "figure":
                lines.append(f"[Figure: {b.text}]")
            elif b.type == "table":
                lines.extend(" | ".join(row) for row in b.rows)
            else:
                lines.append(b.text)
        return "\n".join(lines).strip()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "blocks": [
                {"type": b.type, "text": b.text, "rows": b.rows, "header": b.header} for b in self.blocks],
            "uncertain_count": self.uncertain_count,
            "error": self.error,
        }

'''
How much course info the prompt gets, this is mostly useful to see how much the context is helping
none = no idea what the notes are about
course = course name and its topic list
full = course + the topics/subtopics the recognition step found (the normal setting)
'''
CONTEXT_LEVELS = ("none", "course", "full")

# We give the model the course and detected topics as well the vocab for the course to give it more context
def build_transcription_prompt(course: Course, topics: list[Topic], subtopics: list[str], context: str = "full") -> str:
    if context not in CONTEXT_LEVELS:
        raise ValueError(f"Context must be one of {CONTEXT_LEVELS}, got '{context}'")
    if topics:
        detected = "The recognition step found these topics in the image: " + ", ".join(t.label for t in topics) + "."
    else:
        detected = f"No {course.code} topic was detected, so the image may be unrelated to the course. Transcribe it anyways to be safe."
    if subtopics:
        detected += " Specific concepts spotted: " + ", ".join(subtopics) + "."

    vocab = "; ".join(t.label for t in course.topics)
    if course.example_subtopics:
        vocab += ". Example terms: " + ", ".join(course.example_subtopics)

    lines = ["You are transcribing a photo of handwritten notes or a whiteboard into clean, accessible digital text"]
    if context != "none":
        student = f"The student is taking {course.code} ({course.name})."
        if context == "full":
            student += f" {detected}"
        lines.append(student)
        lines.append(f"Course vocabulary, use it ONLY to pick between plausible readings of unclear handwriting: {vocab}")
    header = "\n    ".join(lines)

    return f"""{header}
    
    === RULES ===
    - Transcribe what is written. Do not add content, solve problems, finish unfinished work, or correct the writers mistakes (including math mistakes)
    - Read top to bottom, left to right. If there are columns, finish one before starting the next
    - If you are unsure of a word or symbol, give your best guess wrapped in double square brackets like [[guess]]
    - If something is completely unreadable write [illegible]
    - Write math as plain Unicode text a screen reader can handle. NOT LaTeX: x² − 5x + 6 = 0, √(x + 1), ≤, π, ½ use parentheses so fractions are unambiguous e.g. (x + 1)/(x - 2)
    - Keep the structure: headings, bullet lists, numbered lists, and tables (truth tables, K-maps, trace tables, etc)
    - Diagrams, graphs, circuits and drawings become a "figure" block: one or two sentences describing the drawing plus any labels written on it, like alt text for someone who cant see it
    
    === OUTPUT FORMAT ===
    Respond ONLY with one valid JSON object, no prose and no markdown fences:
    {{
        "title": "short title taken from the notes, or empty string if there isnt one",
        "blocks": [
            {{"type": "heading", "text", "..."}},
            {{"type": "paragraph", "text", "..."}},
            {{"type": "bullet", "text", "..."}},
            {{"type": "numbered", "text", "text without the number, numbering is added automatically"}},
            {{"type": "equation", "text", "..."}},
            {{"type", "figure", "text": "description of the drawing and its labels"}},
            {{"type", "table", "header": true, "rows": [["col1", "col2"], ["a", "b:]]}}
        ]
    }}
    "type" must be one of: heading, paragraph, bullet, numbered, equation, figure, table
    "header" is true only when the first table row is a row of column names
    """

# Same fence stripping idea s the recognizer, just in case the model adds fences anyways
def _extract_json(raw: str) -> str:
    text = raw.strip()
    if "```" in text:
        for part in text.split("```"):
            stripped = part.strip().removeprefix("json").strip()
            if stripped.startswith("{"):
                return stripped
    return text

def parse_transcription(raw: str) -> Transcription:
    try:
        data = json.loads(_extract_json(raw))
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
    except (json.JSONDecodeError, ValueError) as e:
        # Dont lose the entire response
        return Transcription(
            title="",
            blocks=[Block("paragraph", raw.strip())] if raw.strip() else [],
            raw_response=raw,
            error=f"Model returned unparsable response ({e})",
        )

    blocks: list[Block] = []
    for item in data.get("blocks") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", "paragraph")).lower()
        if kind not in BLOCK_TYPES:
            kind = "paragraph"

        if kind == "table":
            rows = [[str(c) for c in row] for row in item.get("rows") or [] if isinstance(row, list)]

            if not rows:
                continue

            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows] # every row needs the same number of cells
            blocks.append(Block("table", rows=rows, header=bool(item.get("header"))))

        else:
            text = str(item.get("text") or "").strip()
            if text:
                blocks.append(Block(kind, text=text))
    return Transcription(
        title=str(data.get("title") or "").strip(),
        blocks=blocks,
        raw_response=raw,
    )
