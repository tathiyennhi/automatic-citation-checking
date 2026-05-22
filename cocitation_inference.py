"""
Co-citation Inference & Analysis
Runs 4 models on 250-file subset, computes metrics by citation type.
"""

import json, re, csv, os
import numpy as np
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from rank_bm25 import BM25Okapi

# ── Config ───────────────────────────────────────────────────
SUBSET_DIR   = Path("./data_outputs/task2/test_subset_250")
RESULTS_DIR  = Path("./data_outputs/task2/cocitation_results")
BATCH_SIZE   = 32
DEVICE       = torch.device("mps" if torch.backends.mps.is_available() else
                            "cuda" if torch.cuda.is_available() else "cpu")

MODELS = {
    "scibert_random": "./outputs/models/task2-m4pro-scibert-lr3e5-bs32-ep3-window_1",
    "scibert_hard":   "./outputs/models/task2-m4pro-scibert-lr3e5-bs32-ep3-window_1-bm25hard",
    "bert_random":    "./outputs/models/task2-m4pro-bert-lr3e5-bs32-ep3-window_1",
    "bert_hard":      "./outputs/models/task2-m4pro-bert-lr3e5-bs32-ep3-window_1-bm25hard",
}
CONTEXT_MODE = "window_1"
MAX_LENGTH   = 512

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────
def get_context(text, citation_id, mode="window_1"):
    if mode == "full":
        return text
    window = int(mode.split("_")[1])
    sentences = re.split(r"(?<=[.!?])\s+", text)
    idx = next((i for i, s in enumerate(sentences) if citation_id in s), -1)
    if idx == -1:
        return text
    return " ".join(sentences[max(0, idx - window): idx + window + 1])


def load_subset():
    """Load all 250 files, return list of dicts."""
    label_files = sorted(SUBSET_DIR.glob("*.label"))
    records = []
    for lf in label_files:
        in_file = lf.with_suffix(".in")
        try:
            in_data    = json.loads(in_file.read_text())
            label_data = json.loads(lf.read_text())
        except Exception:
            continue
        records.append({
            "file_id":    lf.stem,
            "text":       in_data.get("text", ""),
            "candidates": in_data.get("citation_candidates", []),
            "bib_entries": in_data.get("bib_entries", {}),
            "correct_map": label_data.get("correct_citation", {}),
            "analysis":   label_data.get("citation_analysis", {}),
        })
    print(f"✅ Loaded {len(records)} files from subset")
    return records


def candidate_text(entry):
    return f"{entry.get('title', '')}. {entry.get('abstract', '')}"


# ── BM25 Inference ───────────────────────────────────────────
def tokenize_bm25(text):
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def infer_bm25(records):
    print("\n🔍 BM25 inference...")
    all_preds = {}

    for rec in records:
        fid     = rec["file_id"]
        bib     = rec["bib_entries"]
        cands   = [c for c in rec["candidates"] if c in bib]
        all_preds[fid] = {}

        corpus     = [tokenize_bm25(candidate_text(bib[c])) for c in cands]
        bm25_index = BM25Okapi(corpus)

        for cid in rec["correct_map"]:
            query  = tokenize_bm25(get_context(rec["text"], cid, CONTEXT_MODE))
            scores = bm25_index.get_scores(query)
            ranked = [cands[i] for i in np.argsort(scores)[::-1]]
            all_preds[fid][cid] = ranked

    print("  ✅ BM25 done")
    return all_preds


# ── Neural Inference ─────────────────────────────────────────
def infer_neural(records, model_name, model_dir):
    print(f"\n🔍 {model_name} inference from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model     = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.to(DEVICE)
    model.eval()

    all_preds = {}

    for i, rec in enumerate(records):
        if (i + 1) % 50 == 0:
            print(f"  ⏳ {i+1}/{len(records)}")

        fid   = rec["file_id"]
        bib   = rec["bib_entries"]
        cands = [c for c in rec["candidates"] if c in bib]
        all_preds[fid] = {}

        if not cands:
            continue

        cand_texts = [candidate_text(bib[c]) for c in cands]

        for cid in rec["correct_map"]:
            context = get_context(rec["text"], cid, CONTEXT_MODE)
            queries = [context] * len(cands)
            scores  = []

            with torch.no_grad():
                for start in range(0, len(cands), BATCH_SIZE):
                    end = min(start + BATCH_SIZE, len(cands))
                    enc = tokenizer(
                        queries[start:end], cand_texts[start:end],
                        max_length=MAX_LENGTH, truncation=True,
                        padding="max_length", return_tensors="pt"
                    ).to(DEVICE)
                    logits = model(**enc).logits
                    s = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
                    scores.extend(s.tolist())

            ranked = [cands[i] for i in np.argsort(scores)[::-1]]
            all_preds[fid][cid] = ranked

    del model
    print(f"  ✅ {model_name} done")
    return all_preds


# ── Metrics ──────────────────────────────────────────────────
def compute_metrics(queries):
    """queries: list of (gold, ranked_list)"""
    if not queries:
        return {"num_queries": 0, "mrr": 0, "hits@1": 0, "hits@3": 0, "hits@5": 0}

    rr, h1, h3, h5 = [], 0, 0, 0
    for gold, ranked in queries:
        try:
            rank = ranked.index(gold) + 1
        except ValueError:
            rr.append(0.0)
            continue
        rr.append(1.0 / rank)
        if rank <= 1: h1 += 1
        if rank <= 3: h3 += 1
        if rank <= 5: h5 += 1

    n = len(queries)
    return {
        "num_queries": n,
        "mrr":    round(float(np.mean(rr)), 4),
        "hits@1": round(h1 / n, 4),
        "hits@3": round(h3 / n, 4),
        "hits@5": round(h5 / n, 4),
    }


def evaluate(records, predictions, model_name):
    """Returns metrics_rows (for CSV) and per_query_rows."""
    overall, co_cite, non_co = [], [], []
    per_query_rows = []

    for rec in records:
        fid   = rec["file_id"]
        preds = predictions.get(fid, {})

        for cid, gold in rec["correct_map"].items():
            ranked   = preds.get(cid, [])
            analysis = rec["analysis"].get(cid, {})
            ctype    = analysis.get("citation_type", "unknown")
            gsize    = analysis.get("group_size", 1)

            try:
                rank = ranked.index(gold) + 1
            except ValueError:
                rank = 0

            top1       = ranked[0] if ranked else ""
            is_correct = int(top1 == gold)

            per_query_rows.append({
                "file_id":          fid,
                "citation_marker":  cid,
                "citation_type":    ctype,
                "group_size":       gsize,
                "gold_ref_id":      gold,
                "predicted_ref_id": top1,
                "rank":             rank,
                "model":            model_name,
                "is_correct":       is_correct,
            })

            entry = (gold, ranked)
            overall.append(entry)
            if ctype == "co-citation":
                co_cite.append(entry)
            else:
                non_co.append(entry)

    metrics_rows = []
    for group_name, queries in [("overall", overall),
                                 ("co-citation", co_cite),
                                 ("non-co-citation", non_co)]:
        m = compute_metrics(queries)
        metrics_rows.append({"model": model_name, "group": group_name, **m})

    return metrics_rows, per_query_rows


# ── Main ─────────────────────────────────────────────────────
def main():
    records = load_subset()

    all_metrics    = []
    all_per_query  = []
    all_predictions = {}   # model_name → predictions dict
    model_order    = ["bm25"] + list(MODELS.keys())
    model_labels   = {
        "bm25":           "BM25 (baseline)",
        "scibert_random": "SciBERT (random neg)",
        "scibert_hard":   "SciBERT (BM25 hard neg)",
        "bert_random":    "BERT (random neg)",
        "bert_hard":      "BERT (BM25 hard neg)",
    }

    # BM25
    preds = infer_bm25(records)
    all_predictions["bm25"] = preds
    m_rows, pq_rows = evaluate(records, preds, "bm25")
    all_metrics   += m_rows
    all_per_query += pq_rows

    # Neural models
    for model_name, model_dir in MODELS.items():
        preds = infer_neural(records, model_name, model_dir)
        all_predictions[model_name] = preds
        m_rows, pq_rows = evaluate(records, preds, model_name)
        all_metrics   += m_rows
        all_per_query += pq_rows

    # ── Save predictions to disk ─────────────────────────────
    PRED_DIR = RESULTS_DIR / "predictions"
    for mn, preds in all_predictions.items():
        model_pred_dir = PRED_DIR / mn
        model_pred_dir.mkdir(parents=True, exist_ok=True)
        for rec in records:
            fid = rec["file_id"]
            # ranked list per citation
            (model_pred_dir / f"{fid}.json").write_text(
                json.dumps(preds.get(fid, {}), indent=2)
            )
            # gold labels
            (model_pred_dir / f"{fid}.label").write_text(
                json.dumps(rec["correct_map"], indent=2)
            )
    print(f"\n✅ Predictions saved to {PRED_DIR}")

    # ── Write metrics_summary.csv ────────────────────────────
    csv_path = RESULTS_DIR / "metrics_summary.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model","group","num_queries","mrr","hits@1","hits@3","hits@5"])
        writer.writeheader()
        writer.writerows(all_metrics)
    print(f"\n✅ {csv_path}")

    # ── Write per_query_results.csv ──────────────────────────
    pq_path = RESULTS_DIR / "per_query_results.csv"
    with open(pq_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file_id","citation_marker","citation_type","group_size",
            "gold_ref_id","predicted_ref_id","rank","model","is_correct"
        ])
        writer.writeheader()
        writer.writerows(all_per_query)
    print(f"✅ {pq_path}")

    # ── Write metrics_report.txt ─────────────────────────────
    group_order = ["overall", "co-citation", "non-co-citation"]
    metrics_index = {(r["model"], r["group"]): r for r in all_metrics}

    report_path = RESULTS_DIR / "metrics_report.txt"
    with open(report_path, "w") as f:
        for mn in model_order:
            label = model_labels.get(mn, mn)
            f.write(f"=== {label} ===\n")
            for g in group_order:
                m = metrics_index.get((mn, g), {})
                n = m.get("num_queries", 0)
                f.write(f"{g.capitalize()} ({n} queries):\n")
                f.write(f"  MRR: {m.get('mrr',0):.4f}  "
                        f"Hits@1: {m.get('hits@1',0):.4f}  "
                        f"Hits@3: {m.get('hits@3',0):.4f}  "
                        f"Hits@5: {m.get('hits@5',0):.4f}\n")
            f.write("\n")
    print(f"✅ {report_path}")

    # ── Print summary ────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"{'Model':<24} {'Group':<18} {'MRR':>6} {'H@1':>6} {'H@3':>6} {'H@5':>6}")
    print("-" * 65)
    for mn in model_order:
        for g in group_order:
            m = metrics_index.get((mn, g), {})
            print(f"{mn:<24} {g:<18} "
                  f"{m.get('mrr',0):>6.4f} "
                  f"{m.get('hits@1',0):>6.4f} "
                  f"{m.get('hits@3',0):>6.4f} "
                  f"{m.get('hits@5',0):>6.4f}")
    print("=" * 65)


if __name__ == "__main__":
    main()
