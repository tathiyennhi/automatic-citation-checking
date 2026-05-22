"""
Evaluate all models on 250-file subset.
Computes F1, Hits@1/3/5 and MRR by group (overall, co-citation, non-co-citation).

Usage:
  python evaluate_all.py
"""

import json
from pathlib import Path
import numpy as np

SUBSET_DIR = Path("./data_outputs/task2/test_subset_250")
PRED_DIR   = Path("./data_outputs/task2/cocitation_results/predictions")

MODELS = [
    "bm25",
    "bert_random",
    "bert_hard",
    "scibert_random",
    "scibert_hard",
    "gemma_4_e4b",
    "llama3_1_8b",
]


def load_labels():
    labeled = {}
    for lf in sorted(SUBSET_DIR.glob("*.label")):
        d = json.loads(lf.read_text())
        labeled[lf.stem] = {
            "correct_map": d.get("correct_citation", {}),
            "analysis":    d.get("citation_analysis", {}),
        }
    print(f"Loaded {len(labeled)} labeled files\n")
    return labeled


def evaluate(model_name, labeled):
    pred_dir = PRED_DIR / model_name
    if not pred_dir.exists():
        return None

    preds = {}
    for f in pred_dir.glob("*.json"):
        preds[f.stem] = json.loads(f.read_text())

    groups = [
        ("overall",         lambda c: True),
        ("co-citation",     lambda c: c.get("citation_type") == "co-citation"),
        ("non-co-citation", lambda c: c.get("citation_type") != "co-citation"),
    ]

    rows = []
    for group_name, filter_fn in groups:
        rr = []
        h1 = h3 = h5 = 0
        tp = fp = fn = 0
        relaxed_correct = 0
        n = 0

        for fid, rec in labeled.items():
            fp_preds = preds.get(fid, {})
            for cid, gold in rec["correct_map"].items():
                analysis = rec["analysis"].get(cid, {})
                if not filter_fn(analysis):
                    continue
                ranked = fp_preds.get(cid, [])
                top1   = ranked[0] if ranked else ""
                try:    rank = ranked.index(gold) + 1
                except: rank = 0

                rr.append(1 / rank if rank else 0)
                if rank == 1: h1 += 1
                if rank and rank <= 3: h3 += 1
                if rank and rank <= 5: h5 += 1

                if top1 == gold:
                    tp += 1
                else:
                    fp += 1
                    fn += 1

                # Relaxed: correct if top1 is any paper in co-citation group
                if group_name == "co-citation":
                    group_markers  = analysis.get("citation_group", [cid])
                    co_cited_refs  = {rec["correct_map"][m] for m in group_markers if m in rec["correct_map"]}
                    if top1 in co_cited_refs:
                        relaxed_correct += 1

                n += 1

        if n == 0:
            continue

        f1 = tp / n  # == Hits@1 since single gold per query
        relaxed_f1 = relaxed_correct / n if group_name == "co-citation" else None

        rows.append((group_name, n, f1, relaxed_f1, h1/n, h3/n, h5/n, float(np.mean(rr))))
    return rows


def main():
    labeled = load_labels()

    header = "{:<22} {:<18} {:>5} {:>7} {:>10} {:>7} {:>7} {:>7} {:>7}".format(
        "Model", "Group", "N", "F1", "F1-relaxed", "Hits@1", "Hits@3", "Hits@5", "MRR"
    )
    print(header)
    print("-" * 90)

    all_rows = []
    for mn in MODELS:
        rows = evaluate(mn, labeled)
        if rows is None:
            print(f"{mn:<22} — no predictions found")
            continue
        for group_name, n, f1, relaxed_f1, h1, h3, h5, mrr in rows:
            relaxed_str = f"{relaxed_f1:.4f}" if relaxed_f1 is not None else "    —   "
            print("{:<22} {:<18} {:>5} {:>7.4f} {:>10} {:>7.4f} {:>7.4f} {:>7.4f} {:>7.4f}".format(
                mn, group_name, n, f1, relaxed_str, h1, h3, h5, mrr
            ))
            all_rows.append({
                "model": mn, "group": group_name, "n": n,
                "f1": round(f1, 4),
                "f1_relaxed": round(relaxed_f1, 4) if relaxed_f1 is not None else "",
                "hits@1": round(h1, 4), "hits@3": round(h3, 4),
                "hits@5": round(h5, 4), "mrr": round(mrr, 4),
            })
        print()

    # Save CSV
    import csv
    out_path = Path("./data_outputs/task2/cocitation_results/evaluation_results.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model","group","n","f1","f1_relaxed","hits@1","hits@3","hits@5","mrr"])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
