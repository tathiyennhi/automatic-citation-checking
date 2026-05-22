"""
Error Analysis — Co-citation Group
Reads predictions from disk, classifies errors per model.

Usage:
  python error_analysis.py                    # all models
  python error_analysis.py --model bm25       # single model
"""

import json, csv, argparse
from pathlib import Path

SUBSET_DIR  = Path("./data_outputs/task2/test_subset_250")
PRED_DIR    = Path("./data_outputs/task2/cocitation_results/predictions")
RESULTS_DIR = Path("./data_outputs/task2/cocitation_results")

MODEL_LABELS = {
    "bm25":           "BM25 (baseline)",
    "scibert_random": "SciBERT (random neg)",
    "scibert_hard":   "SciBERT (BM25 hard neg)",
    "bert_random":    "BERT (random neg)",
    "bert_hard":      "BERT (BM25 hard neg)",
}


def load_labeled_files():
    records = {}
    for lf in sorted(SUBSET_DIR.glob("*.label")):
        in_file = lf.with_suffix(".in")
        try:
            in_data    = json.loads(in_file.read_text())
            label_data = json.loads(lf.read_text())
        except Exception:
            continue
        records[lf.stem] = {
            "correct_map": label_data.get("correct_citation", {}),
            "analysis":    label_data.get("citation_analysis", {}),
        }
    print(f"✅ Loaded {len(records)} labeled files")
    return records


def load_predictions(model_name):
    model_dir = PRED_DIR / model_name
    if not model_dir.exists():
        print(f"⚠️  No predictions found for: {model_name}")
        return {}
    preds = {}
    for f in model_dir.glob("*.json"):
        try:
            preds[f.stem] = json.loads(f.read_text())
        except Exception:
            continue
    print(f"✅ Loaded predictions for {model_name} ({len(preds)} files)")
    return preds


def classify_error(top1, gold, group_markers, correct_map):
    if top1 == gold:
        return "correct"
    co_cited_refs = {correct_map[m] for m in group_markers if m in correct_map}
    if top1 in co_cited_refs:
        return "permutation_error"
    return "true_error"


def analyze_model(model_name, labeled_files, predictions):
    counts = {"correct": 0, "permutation_error": 0, "true_error": 0}
    total  = 0

    for fid, rec in labeled_files.items():
        file_preds = predictions.get(fid, {})
        for cid, gold in rec["correct_map"].items():
            analysis = rec["analysis"].get(cid, {})
            if analysis.get("citation_type") != "co-citation":
                continue

            ranked        = file_preds.get(cid, [])
            top1          = ranked[0] if ranked else ""
            group_markers = analysis.get("citation_group", [cid])
            error_type    = classify_error(top1, gold, group_markers, rec["correct_map"])

            counts[error_type] += 1
            total += 1

    return counts, total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None,
                        help="Model name to analyze (default: all available)")
    args = parser.parse_args()

    labeled_files = load_labeled_files()

    # Discover available models
    if args.model:
        models = [args.model]
    else:
        models = sorted([d.name for d in PRED_DIR.iterdir() if d.is_dir()])
        print(f"✅ Found models: {models}\n")

    rows = []
    print("=" * 55)
    print("=== Error Analysis on Co-citation Group ===")
    print("=" * 55)

    for mn in models:
        preds         = load_predictions(mn)
        counts, total = analyze_model(mn, labeled_files, preds)

        if total == 0:
            print(f"⚠️  No co-citation queries for {mn}")
            continue

        label = MODEL_LABELS.get(mn, mn)
        print(f"\n{label} — {total} queries:")
        print(f"  Correct           : {counts['correct']}  ({counts['correct']/total*100:.2f}%)")
        print(f"  Permutation error : {counts['permutation_error']}  ({counts['permutation_error']/total*100:.2f}%)")
        print(f"  True error        : {counts['true_error']}  ({counts['true_error']/total*100:.2f}%)")

        rows.append({
            "model":             mn,
            "group":             "co-citation",
            "total_queries":     total,
            "correct":           counts["correct"],
            "correct_pct":       round(counts["correct"] / total * 100, 2),
            "permutation_error": counts["permutation_error"],
            "permutation_pct":   round(counts["permutation_error"] / total * 100, 2),
            "true_error":        counts["true_error"],
            "true_error_pct":    round(counts["true_error"] / total * 100, 2),
        })

    # Save CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "error_analysis.csv"
    write_hdr = not out_path.exists()
    with open(out_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "model", "group", "total_queries",
            "correct", "correct_pct",
            "permutation_error", "permutation_pct",
            "true_error", "true_error_pct",
        ])
        if write_hdr:
            writer.writeheader()
        writer.writerows(rows)
    print(f"\n✅ Saved: {out_path}")


if __name__ == "__main__":
    main()
