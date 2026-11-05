# Evaluation dataset

`evaluate.py` reads a CSV (copy `dataset.example.csv` to `dataset.csv`) with one row per photo:

| column | required | meaning |
|---|---|---|
| `image` | yes | path to the photo, relative to the CSV |
| `course` | yes | course code, e.g. `MTH111` |
| `quality` | no | your own label for how readable the handwriting is, e.g. `good` / `fair` / `poor` (used to group the results) |
| `topics` | no | the correct topic **keys** for this photo (the `key:` values in `courses/*.yaml`), separated by `;` |
| `transcript` | no | path to the typed correct text, defaults to the image name with `.txt` (`images/quad_01.jpg` -> `images/quad_01.txt`) |

## Typing the correct transcript

The score is the edit distance between your typed text and the model's, so type it the same way the model is told to write:

- Type **exactly what is written**, including your own mistakes. Do not fix or finish anything
- No bullet or list numbers (`1.`, `-`), they are not counted. Line breaks do not matter
- Write math as plain text: `x² - 5x + 6 = 0` or `x^2 - 5x + 6 = 0` both work. `sqrt` and `√` match, and so do `x^2`, `x²`, `x2`
- Leave out drawings and diagrams, only the written words and symbols count
- Type it **before** looking at the model's output, otherwise you will unconsciously copy its readings

## Running it

    python evaluate.py eval/dataset.csv

Raw results are saved in `eval_results/results.jsonl`, so a crash or Ctrl+C can be resumed by running the same command again.
`eval_results/summary.md` has the tables and `eval_results/per_image.csv` has one row per image and context level.

## Hypotheses 
H1 course context lowers CER relative to no context.   
H2: the benefit is larger for poor handwriting, where the image alone is more ambiguous.   
H3: full context is no worse than course context alone.   