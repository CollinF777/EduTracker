import random
import re
import unicodedata

# Different ways of typing the same math symbol should not count as transcription errors
_CHAR_MAP = str.maketrans({
    "−": "-", "–": "-", "—": "-", "‐": "-", "‑": "-", # All the dashes and minus signs
    "⁄": "/",
    "’": "'", "‘": "'", "“": '"', "”": '"',
})

'''
lowercase. NFKC (x² -> x2), unify dashes/quotes, 
drop ^ * x · (x^2, x² and x2 all match), sqrt -> √
also collapse all whitespace/line breaks to single spaces
'''
def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().translate(_CHAR_MAP)
    text = text.replace("sqrt", "√")
    text = re.sub(r"[\^*x·]", "", text)
    return " ".join(text.split())

'''
Levenshtein distance between two sequences
Scary word but it just means how many changes it would
take to change one word to another
'''
def edit_distance(a, b) -> int:
    # We want to edit the shortest one to use less memory
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        cur = [i]
        for j, y in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]

# Calculates the character error rate between ref and hyp text
def char_edits(reference: str, hypothesis: str) -> tuple[int, int]:
    ref, hyp = normalize_text(reference), normalize_text(hypothesis)
    return edit_distance(ref, hyp), len(ref)

# Calculates the word error rate between ref and hyp text
def word_edits(reference: str, hypothesis: str) -> tuple[int, int]:
    ref, hyp = normalize_text(reference).split(), normalize_text(hypothesis).split()
    return edit_distance(ref, hyp), len(ref)

# Prevent division by zero errors
def safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0

# This calculates the difference between two error rates anda  95% bootstrap confidence interval, bootstrap is used to estimate how reliable a result is
def bootstrap_diff_ci(pairs: list[tuple[int, int, int]], n_boot: int = 5000, seed: int = 0):
    # Calculates the difference in between Model A and Model B's error rate
    def diff(sample):
        length = sum(p[2] for p in sample)
        return safe_div(sum(p[0] for p in sample), length) - safe_div(sum(p[1] for p in sample), length)

    rng = random.Random(seed)
    boots = sorted(diff([rng.choice(pairs) for _ in pairs]) for _ in range(n_boot))
    return diff(pairs), boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) -1]