import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# We are now doing courses with a yaml file instead
# just put in the same format as the template im gonna make
import yaml

# Courses is meant to be at the top level in a folder called courses but this can be changed with a env var
COURSES_DIR = Path(os.environ.get("EDUTRACKER_COURSES_DIR", Path(__file__).resolve().parent.parent / "courses"))

# dataclasses are like objects but less code
@dataclass
class Topic:
    key: str
    label: str
    description: str = ""
    # field(default_factory=list) is just sating create a fresh list for each instance
    visual_cues: list[str] = field(default_factory=list)

@dataclass
class Course:
    code: str # Like CSC311
    name: str # Like Comp Org and Arc
    topics: list[Topic]
    # Examples of subtopics to nudge the model, this is optional
    example_subtopics: list[str] = field(default_factory=list)
    topic_map: dict[str, Topic] = field(init=False)

    # Builds a dictonary from the topics list
    def __post_init__(self):
        self.topic_map = {t.key: t for t in self.topics}

    # Writes the full label of a class for UI purposes
    @property
    def label(self) -> str:
        return f"{self.code} - {self.name}"

def _load_course(path: Path) -> Course:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"{path.name}: inva;od  YAML ({e})") from e

    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected 'code', 'name', and 'topics' at the top level")
    for required in ("code", "name", "topics"):
        if not data.get(required):
            raise ValueError(f"{path.name}: missing '{required}'")

    topics, seen = [], set()
    for i, raw in enumerate(data["topics"], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{path.name}: topic #{i} should have key/label/etc, not a bare value")

        for required in ("key", "label"):
            if not raw.get(required):
                raise ValueError(f"{path.name}: topic #{i} is missing '{required}'")

        key = str(raw["key"])
        if key in seen:
            raise ValueError(f"{path.name}: duplicate topic key '{key}'")
        seen.add(key)
        topics.append(
            Topic(
                key=key,
                label=str(raw["label"]),
                description=str(raw.get("description") or "").strip(),
                visual_cues=[str(c) for c in raw.get("visual_cues") or []],
            )
        )

    return Course(
        code=str(data["code"]).strip(),
        name=str(data["name"]).strip(),
        topics=topics,
        example_subtopics=[str(s) for s in data.get("example_subtopics") or []],
    )

# This saves the courses in the cache so we arent constantly rereading the same files
# LRU is least recently used, youll learn about it in OS if you dont know
@lru_cache(maxsize=1)
def load_courses() -> dict[str, Course]:
    # loads all the yaml files, sorted because it makes the order alphabetical
    files = sorted([*COURSES_DIR.glob("*.yaml"), *COURSES_DIR.glob("*.yml")])
    courses: dict[str, Course] = {}
    for path in files:
        if path.name.startswith("_"):
            continue
        course = _load_course(path)
        code = course.code.upper()
        if code in courses:
            raise ValueError(f"{path.name}: Duplicate course '{code}'")

        courses[code] = course
    if not courses:
        raise ValueError(f"No course files found in {COURSES_DIR}")
    return dict(sorted(courses.items()))

def get_course(code: str | None = None) -> Course:
    courses = load_courses()
    if code is None:
        # If theres only one course then just use that
        if len(courses) == 1:
            # This is just how you grab one item from a dict without its key
            return next(iter(courses.values()))
        raise ValueError(f"No course selected. Available courses: {','.join(courses)}")

    try:
        return courses[code.strip().upper()]
    except KeyError:
        raise ValueError(f"Unknown course '{code}'. Available courses: {','.join(courses)}") from None