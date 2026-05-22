# Task 2 — Co-citation Analysis Pipeline

## Folder structure

```
data_outputs/task2/
├── train/                  # 55,556 training files
├── val/                    # 3,000 validation files
├── test/                   # 3,000 test files
├── test_subset_250/        # 250 sampled test files với citation_analysis
└── cocitation_results/     # output của inference và analysis
    ├── predictions/
    │   ├── bm25/
    │   ├── bert_random/
    │   ├── bert_hard/
    │   ├── scibert_random/
    │   └── scibert_hard/
    ├── metrics_summary.csv
    ├── per_query_results.csv
    ├── metrics_report.txt
    └── error_analysis.csv
```

---

## Step 1: Inference (4 models)

Chạy từ project root:

```bash
source venv/bin/activate
python cocitation_inference.py
```

Thời gian ước tính: **~20-35 phút** (BM25 ~1 phút, mỗi neural model ~5-8 phút).

Output:
- `cocitation_results/predictions/[model]/` — ranked list per file
- `cocitation_results/metrics_summary.csv` — MRR, Hits@1/3/5 theo model và group
- `cocitation_results/per_query_results.csv` — kết quả từng query
- `cocitation_results/metrics_report.txt` — human-readable report

---

## Step 2: Error Analysis

```bash
# Tất cả models
python error_analysis.py

# Một model cụ thể
python error_analysis.py --model bm25
python error_analysis.py --model scibert_random
```

Output: `cocitation_results/error_analysis.csv`

Phân loại 3 loại lỗi trên **co-citation group**:
- `correct` — top-1 đúng
- `permutation_error` — top-1 sai nhưng nằm trong cùng co-citation group
- `true_error` — top-1 hoàn toàn sai

---

## Thêm model mới (LLM, v.v.)

1. Tạo folder `cocitation_results/predictions/[model_name]/`
2. Với mỗi file trong `test_subset_250/`, lưu predictions:
   - `{file_id}.json` — `{"[CITATION_1]": ["ref_002", "ref_001", ...], ...}`
   - `{file_id}.label` — `{"[CITATION_1]": "ref_001", ...}`
3. Chạy error analysis:
   ```bash
   python error_analysis.py --model [model_name]
   ```

---

## File format

**.in file** — input:
```json
{
  "text": "...",
  "citation_candidates": ["ref_001", "ref_002", ...],
  "bib_entries": {
    "ref_001": {"title": "...", "abstract": "..."},
    ...
  }
}
```

**.label file** — ground truth + annotation:
```json
{
  "correct_citation": {"[CITATION_1]": "ref_001"},
  "citation_analysis": {
    "[CITATION_1]": {
      "citation_type": "co-citation",
      "context_sentence": "...",
      "citation_group": ["[CITATION_1]", "[CITATION_2]"],
      "group_size": 2,
      "co_cited_with": ["[CITATION_2]"]
    }
  }
}
```
