import json
import re
import random
import shutil
from pathlib import Path

SEED       = 42
N_SAMPLE   = 250
TEST_DIR   = Path("./data_outputs/task2/test")
OUTPUT_DIR = Path("./test_subset_250")

random.seed(SEED)

# ── Pattern co-citation: 2+ [CITATION_X] liên tiếp ──────────
CO_CITE_PATTERN = re.compile(
    r'\[CITATION_\d+\](?:\s*[,;\-]?\s*\[CITATION_\d+\])+'
)

def find_sentence(text, citation_id):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for s in sentences:
        if citation_id in s:
            return s.strip()
    return ""

def analyze_citations(text, correct_map):
    # Tìm tất cả co-citation clusters trong text
    clusters = CO_CITE_PATTERN.findall(text)
    co_cited_ids = set()
    cluster_map  = {}  # citation_id → list các citation cùng cluster

    for cluster in clusters:
        members = re.findall(r'\[CITATION_\d+\]', cluster)
        for m in members:
            co_cited_ids.add(m)
            cluster_map[m] = [x for x in members if x != m]

    analysis = {}
    for cid in correct_map:
        context_sentence = find_sentence(text, cid)
        if cid in co_cited_ids:
            co_cited_with  = cluster_map.get(cid, [])
            analysis[cid] = {
                "citation_type":    "co-citation",
                "context_sentence": context_sentence,
                "co_citation_count": len(co_cited_with),
                "co_cited_with":    co_cited_with,
            }
        else:
            analysis[cid] = {
                "citation_type":    "non-co-citation",
                "context_sentence": context_sentence,
                "co_citation_count": 0,
                "co_cited_with":    [],
            }
    return analysis


# ── Sample 250 files ─────────────────────────────────────────
label_files = sorted(TEST_DIR.glob("*.label"))
sampled     = random.sample(label_files, N_SAMPLE)

OUTPUT_DIR.mkdir(exist_ok=True)

stats = {"co_citation": 0, "non_co_citation": 0, "total_queries": 0}

for lf in sampled:
    in_file = lf.with_suffix(".in")
    try:
        in_data    = json.loads(in_file.read_text())
        label_data = json.loads(lf.read_text())
    except Exception as e:
        print(f"⚠️ Skip {lf.name}: {e}")
        continue

    text        = in_data.get("text", "")
    correct_map = label_data.get("correct_citation", {})

    analysis = analyze_citations(text, correct_map)

    # Ghi vào label file mới
    label_data["citation_analysis"] = analysis
    out_label = OUTPUT_DIR / lf.name
    out_in    = OUTPUT_DIR / in_file.name

    out_label.write_text(json.dumps(label_data, indent=2, ensure_ascii=False))
    shutil.copy(in_file, out_in)

    for cid, info in analysis.items():
        stats["total_queries"] += 1
        if info["citation_type"] == "co-citation":
            stats["co_citation"] += 1
        else:
            stats["non_co_citation"] += 1

print(f"✅ Sampled  : {N_SAMPLE} files → {OUTPUT_DIR}/")
print(f"   Queries  : {stats['total_queries']}")
print(f"   Co-cite  : {stats['co_citation']}  ({stats['co_citation']/stats['total_queries']*100:.1f}%)")
print(f"   Non-cite : {stats['non_co_citation']}  ({stats['non_co_citation']/stats['total_queries']*100:.1f}%)")
