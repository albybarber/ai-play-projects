"""Score the classifier against hand-labelled comments.

    python eval/run_eval.py                    # runs the model on eval/labeled.jsonl
    python eval/run_eval.py --runs 3           # repeat to measure label stability

Prints per-field accuracy, a tone confusion matrix, and precision/recall for
the question that matters most: "is this comment mean or toxic?". Re-run it
after every prompt or model change and keep the change only if these improve.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentiment.classifier import Classifier  # noqa: E402
from sentiment.models import ClassificationInput  # noqa: E402

FIELDS = ["tone", "helpfulness", "conflict"]
TONES = ["kind", "neutral", "mean", "toxic"]
HARSH = {"mean", "toxic"}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def score(pairs: list[tuple[dict, dict | None]]) -> dict:
    """pairs are (expected, predicted) label dicts; predicted is None if the model declined."""
    n = len(pairs)
    acc = {f: sum(1 for e, p in pairs if p and p[f] == e[f]) / n for f in FIELDS} if n else {}
    confusion = Counter((e["tone"], p["tone"] if p else "declined") for e, p in pairs)
    tp = sum(1 for e, p in pairs if e["tone"] in HARSH and p and p["tone"] in HARSH)
    fp = sum(1 for e, p in pairs if e["tone"] not in HARSH and p and p["tone"] in HARSH)
    fn = sum(1 for e, p in pairs if e["tone"] in HARSH and not (p and p["tone"] in HARSH))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"n": n, "accuracy": acc, "confusion": confusion, "harsh_precision": precision, "harsh_recall": recall}


def print_report(s: dict, misses: list[str]) -> None:
    print(f"\n{s['n']} labelled examples")
    for f, a in s["accuracy"].items():
        print(f"  {f:<12} accuracy {a:.0%}")
    print(f"  mean|toxic   precision {s['harsh_precision']:.0%}  recall {s['harsh_recall']:.0%}")
    print("\nTone confusion (rows = expected, cols = predicted)")
    cols = TONES + ["declined"]
    print("            " + "".join(f"{c:>10}" for c in cols))
    for t in TONES:
        print(f"  {t:<10}" + "".join(f"{s['confusion'][(t, c)]:>10}" for c in cols))
    if misses:
        print("\nMisses")
        print("\n".join(misses))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(Path(__file__).parent / "labeled.jsonl"))
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--effort", default="medium")
    args = p.parse_args()

    rows = load(Path(args.data))
    clf = Classifier(effort=args.effort)
    pairs, misses = [], []
    for run in range(args.runs):
        results = clf.classify_all([ClassificationInput.model_validate(r["input"]) for r in rows])
        for row, res in zip(rows, results):
            pred = res.classification.model_dump() if res.classification else None
            pairs.append((row["expected"], pred))
            wrong = [f for f in FIELDS if not pred or pred[f] != row["expected"][f]]
            if wrong:
                got = {f: (pred[f] if pred else res.skipped_reason) for f in wrong}
                want = {f: row["expected"][f] for f in wrong}
                misses.append(f"  [run {run + 1}] {row.get('note', '')}: expected {want}, got {got}")
    print_report(score(pairs), misses)


if __name__ == "__main__":
    main()
