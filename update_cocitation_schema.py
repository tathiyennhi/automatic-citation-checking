import json
import re
from pathlib import Path

SUBSET_DIR = Path("./data_outputs/task2/test_subset_250")

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
    clusters = CO_CITE_PATTERN.findall(text)
    cluster_map = {}
    for cluster in clusters:
        members = re.findall(r'\[CITATION_\d+\]', cluster)
        for m in members:
            cluster_map[m] = members

    analysis = {}
    for cid in correct_map:
        context_sentence = find_sentence(text, cid)
        if cid in cluster_map:
            group         = cluster_map[cid]
            co_cited_with = [x for x in group if x != cid]
            analysis[cid] = {
                "citation_type":    "co-citation",
                "context_sentence": context_sentence,
                "citation_group":   group,
                "group_size":       len(group),
                "co_cited_with":    co_cited_with,
            }
        else:
            analysis[cid] = {
                "citation_type":    "non-co-citation",
                "context_sentence": context_sentence,
                "citation_group":   [cid],
                "group_size":       1,
                "co_cited_with":    [],
            }
    return analysis


label_files = sorted(SUBSET_DIR.glob("*.label"))
stats = {"co_citation": 0, "non_co_citation": 0, "total_queries": 0}

for lf in label_files:
    in_file = lf.with_suffix(".in")
    try:
        in_data    = json.loads(in_file.read_text())
        label_data = json.loads(lf.read_text())
    except Exception as e:
        print(f"⚠️ Skip {lf.name}: {e}")
        continue

    text        = in_data.get("text", "")
    correct_map = label_data.get("correct_citation", {})

    label_data["citation_analysis"] = analyze_citations(text, correct_map)
    lf.write_text(json.dumps(label_data, indent=2, ensure_ascii=False))

    for cid, info in label_data["citation_analysis"].items():
        stats["total_queries"] += 1
        if info["citation_type"] == "co-citation":
            stats["co_citation"] += 1
        else:
            stats["non_co_citation"] += 1

print(f"✅ Updated {len(label_files)} files in {SUBSET_DIR}")
print(f"   Queries  : {stats['total_queries']}")
print(f"   Co-cite  : {stats['co_citation']}  ({stats['co_citation']/stats['total_queries']*100:.1f}%)")
print(f"   Non-cite : {stats['non_co_citation']}  ({stats['non_co_citation']/stats['total_queries']*100:.1f}%)")
