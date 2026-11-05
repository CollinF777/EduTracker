import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from edutracker.courses import get_course
from eval.metrics import bootstrap_diff_ci, char_edits, safe_div, word_edits
from edutracker.recognizer import Recognizer
from edutracker.transcription import CONTEXT_LEVELS

def load_dataset(csv_path: Path) -> list[dict]:
    base = csv_path.parent
    rows = []
    # we put utf-8-sig so csvs saved from Excel works
    with open(csv_path, newline='', encoding="utf-8-sig") as f:
        # Line 1 is the header so we start at 2
        for line_no, raw in enumerate(csv.DictReader(f), start=2):
            where = f"{csv_path.name} line {line_no}"
            for col in ("image", "course"):
                if not (raw.get(col) or "").strip():
                    raise ValueError(f"{where}: missing '{col}'")

            name = raw["image"].strip()
            image = base / name
            if not image.exists():
                raise ValueError(f"{where}: image '{image}' does not exist")
            ref_path = base / (raw.get("transcript") or "").strip() if (raw.get("transcript") or "").strip() else image.with_suffix(".txt")
            if not ref_path.exists():
                raise ValueError(f"{where}: transcript '{ref_path}' does not exist")
            reference = ref_path.read_text(encoding="utf-8").strip()
            if not reference:
                raise ValueError(f"{where}: transcript '{ref_path}' is empty")

            try:
                course = get_course(raw["course"])
            except ValueError as e:
                raise ValueError(f"{where}: {e}") from None
            topics = [t.strip() for t in (raw.get("topics") or "").split(";") if t.strip()]
            for t in topics:
                if t not in course.topic_map:
                    raise ValueError(f"{where}: topic '{t}' is not a topic key in {course.code}")

            rows.append({
                "name": name,
                "image": str(image),
                "course": course.code,
                "quality": (raw.get("quality") or "unlabeled").strip().lower(),
                "topics": topics,
                "reference": reference
            })

    if not rows:
        raise ValueError(f"{csv_path.name} has no rows")
    return rows

# Saved results (one json line per API result)
def load_store(path: Path) -> dict:
    store = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                # Makes a JSON-formatted string a python object
                rec = json.loads(line)
                # Stores the record in store using a tuple (imgName, stage, context) as the key
                store[(rec["image"], rec["stage"], rec.get("context", ""))] = rec
    return store

# Saves a record into a JSONL file
def save_record(path: Path, store: dict, rec: dict) -> None:
    store[(rec["image"], rec["stage"], rec.get("context", ""))] = rec
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Run the api pipeline
def run_api(rows, store, results_path, args) -> None:
    recognizers: dict[str, Recognizer] = {}
    for i, row in enumerate(rows, start=1):
        print(f"[{i}/{len(rows)}] {row['name']}", file=sys.stderr)
        if row["course"] not in recognizers:
            recognizers[row["course"]] = Recognizer(
                course=row["course"], model=args.model, preprocess=not args.no_preprocess
            )
        rec = recognizers[row["course"]]
        course = rec.course

        # Recognition needed for topic scores and for "full" context
        key = (row["name"], "recognition", "")
        if args.force or key not in store:
            try:
                t0 = time.perf_counter()
                result = rec.recognize(row["image"])
                save_record(results_path, store, {
                    "image": row["name"], "stage": "recognition", "model": args.model,
                    "topics": [t.key for t in result.topics],
                    "subtopics": result.subtopics,
                    "seconds": round(time.perf_counter() - t0, 2),
                })
            except Exception as e:
                print(f"  recognition failed: {e}", file=sys.stderr)
        saved = store.get(key)
        topics = [course.topic_map[k] for k in (saved["topics"] if saved else []) if k in course.topic_map]
        subtopics = saved["subtopics"] if saved else []

        # One transcription per context level
        for ctx in args.contexts:
            key = (row["name"], "transcription", ctx)
            if not args.force and key in store:
                continue
            # Full needs the recognition result, so we cant do anything without it
            if ctx == "full" and not saved:
                continue
            try:
                t0 = time.perf_counter()
                tr = rec.transcribe_image(row["image"], topics, subtopics, context=ctx)
                save_record(results_path, store, {
                    "image": row["name"], "stage": "transcription", "context": ctx, "model": args.model,
                    "text": tr.plain_text(), "uncertain": tr.uncertain_count, "parse_error": tr.error,
                    "seconds": round(time.perf_counter() - t0, 2),
                })
            except Exception as e:
                print(f"  transcription ({ctx}) failed: {e}", file=sys.stderr)

# Scoring
def score(rows, store, contexts):
    topic_items, trans_items = [], []
    for r in rows:
        rec = store.get((r["name"], "recognition", ""))
        if rec:
            pred, gold = set(rec["topics"]), set(r["topics"])
            topic_items.append({"row": r, "tp": len(pred & gold), "fp": len(pred - gold), "fn": len(gold - pred), "exact": pred == gold})
        for ctx in contexts:
            t = store.get((r["name"], "transcription", ctx))
            if t:
                ce, cl = char_edits(r["reference"], t["text"])
                we, wl, = word_edits(r["reference"], t["text"])
                trans_items.append({"row": r, "context": ctx, "ce": ce, "cl": cl, "we": we, "wl": wl, "uncertain" : t["uncertain"], "seconds": t["seconds"]})
    return topic_items, trans_items

def md_table(headers, body):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in line) + " |" for line in body]
    return "\n".join(out)

def topic_line(items):
    tp, fp, fn = (sum(i[k] for i in items) for k in ("tp", "fp", "fn"))
    p, r = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
    f1 = safe_div(2 * p * r, p + r)
    return [len(items), f"{p:.1%}", f"{r:.1%}", f"{f1:.1%}", f"{safe_div(sum(i['exact'] for i in items), len(items)):.1%}"]

def trans_line(items):
    return [
        len({i["row"]["name"] for i in items}),
        f"{safe_div(sum(i['ce'] for i in items), sum(i['cl'] for i in items)):.1%}",
        f"{safe_div(sum(i['we'] for i in items), sum(i['wl'] for i in items)):.1%}",
        f"{sum(i['uncertain'] for i in items) / len(items):.1f}",
    ]

def summarize(rows, store, contexts, n_boot) -> str:
    topic_items, trans_items = score(rows, store, contexts)
    out = [f"# EduTracker evaluation ({len(rows)} images)\n"]
    models = sorted({r["model"] for r in store.values()})
    out.append(f"Model(s): {'. '.join(models) or 'unknown'}. Error rates are pooled (total edits / total reference length).\n")

    if topic_items:
        out.append(f"## Topic recognition\n")
        t_head = ["Group", "n", "Precision", "Recall", "F1", "Exact set match"]
        body = [["All"] + topic_line(topic_items)]
        for field in ("quality", "course"):
            groups = defaultdict(list)
            for i in topic_items:
                groups[i["row"][field]].append(i)
            body += [[f"{field}: {k}"] + topic_line(v) for k, v in sorted(groups.items())]
        out.append(md_table(t_head, body) + "\n")

    if trans_items:
        out.append("## Transcription by context level\n")
        head = ["Group", "Context", "n", "CER", "WER", "Flags/img"]
        body = []
        for ctx in contexts:
            items = [i for i in trans_items if i["context"] == ctx]
            if items:
                body.append(["All", ctx] + trans_line(items))
        for field in ("quality", "course"):
            for k in sorted({i["row"][field] for i in trans_items}):
                for ctx in contexts:
                    items = [i for i in trans_items if i["context"] == ctx and i["row"][field] == k]
                    if items:
                        body.append([f"{field}: {k}", ctx] + trans_line(items))
        out.append(md_table(head, body) + "\n")


        # Paired comparison against "none", only images that have both results
        if "none" in contexts:
            out.append("## Does context help? (CER difference vs. no context, negative = better)\n")
            by = {(i["row"]["name"], i["context"]): i for i in trans_items}
            body = []
            for ctx in contexts:
                if ctx == "none":
                    continue
                pairs = [(by[(n, ctx)]["ce"], by[(n, "none")]["ce"], by[(n, ctx)]["cl"]) for n in {i["row"]["name"] for i in trans_items} if (n, ctx) in by and (n, "none") in by]
                if len(pairs) < 5:
                    body.append([ctx, len(pairs), "too few images for an interval", ""])
                    continue
                d, lo, hi = bootstrap_diff_ci(pairs, n_boot)
                body.append([ctx, len(pairs), f"{d * 100:+.2f} pp", f"[{lo * 100:+.2f}, {hi * 100:+.2f}] pp"])
            out.append(md_table(["Context", "n paired", "CER difference", "95% bootstrap CI"], body) + "\n")
    missing = len(rows) * (1 + len(contexts)) - len(topic_items) - len(trans_items)
    if missing:
        out.append(f"_{missing} result(s) missing (failed calls or not run yet), rerun to fill them in._\n")
    return "\n".join(out)

def write_per_image(path: Path, rows, store, contexts) -> None:
    topic_items, trans_items = score(rows, store, contexts)
    tmap = {i["row"]["name"]: i for i in topic_items}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["image", "course", "quality", "context", "char_edits", "ref_chars", "word_edits", "ref_words", "flags", "seconds", "topic_exact"])
        for i in trans_items:
            r = i["row"]
            w.writerow([r["name"], r["course"], r["quality"], i["context"], i["ce"], i["cl"], i["we"], i["wl"], i["uncertain"], i["seconds"], tmap[r["name"]]["exact"] if r["name"] in tmap else ""])

def main():
    parser = argparse.ArgumentParser(description="Evaluate topic recognition and transcription on your own photos.")
    parser.add_argument("dataset", help="CSV file, see eval/README.md")
    parser.add_argument("--results", default="eval_results/results.jsonl", help="Where raw results are saved")
    parser.add_argument("--contexts", nargs="+", choices=CONTEXT_LEVELS, default=list(CONTEXT_LEVELS))
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--no-preprocess", action="store_true")
    parser.add_argument("--score-only", action="store_true", help="Skip API calls, score what is already saved")
    parser.add_argument("--force", action="store_true", help="Redo API calls even if a result is saved")
    parser.add_argument("--bootstrap", type=int, default=5000, help="Resamples for confidence interval")
    args = parser.parse_args()

    try:
        rows = load_dataset(Path(args.dataset))
    except ValueError as e:
        sys.exit(f"Dataset error: {e}")

    results_path = Path(args.results)
    if args.force and not args.score_only and results_path.exists():
        # Start clean so old and new results dont mix
        results_path.unlink()
    store = load_store(results_path)

    if not args.score_only:
        run_api(rows, store, results_path, args)

    summary = summarize(rows, store, args.contexts, args.bootstrap)
    print(summary)
    (results_path.parent / "summary.md").write_text(summary, encoding="utf-8")
    write_per_image(results_path.parent / "per_image.csv", rows, store, args.contexts)

if __name__ == "__main__":
    main()