"""
Compare V1 (old), V2 (improved), and V3 (sentence-level) outputs

Usage:
  python3 data_task3/compare_3_versions.py
"""

import json
from pathlib import Path
from typing import Dict, List

# Directories
V1_DIR = Path("data_outputs/task3")
V2_DIR = Path("data_outputs/task3_v2_test")
V3_DIR = Path("data_outputs/task3_v3")
OUTPUT_FILE = Path("data_task3/COMPARE_V1_V2_V3.txt")


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def check_duplicate_spans(spans: List[Dict]) -> int:
    """Count duplicate span_text occurrences"""
    span_texts = [s.get("span_text", "") for s in spans]
    unique = set(span_texts)
    return len(span_texts) - len(unique)


def check_very_short_spans(spans: List[Dict], threshold: int = 15) -> int:
    """Count spans with length < threshold"""
    return sum(1 for s in spans if len(s.get("span_text", "")) < threshold)


def check_incomplete_endings(spans: List[Dict]) -> int:
    """Count spans ending with conjunctions/prepositions"""
    incomplete_words = ["and", "or", "but", "with", "in", "of", "to", "for", "on", "at", "by"]
    count = 0
    for s in spans:
        text = s.get("span_text", "").strip()
        if text:
            last_word = text.split()[-1].lower().rstrip(".,!?;:")
            if last_word in incomplete_words:
                count += 1
    return count


def calculate_quality_score(spans: List[Dict]) -> float:
    """
    Quality score (0-100%):
    - No duplicates
    - No very short spans
    - No incomplete endings
    """
    if not spans:
        return 0.0

    total = len(spans)
    duplicates = check_duplicate_spans(spans)
    very_short = check_very_short_spans(spans)
    incomplete = check_incomplete_endings(spans)

    issues = duplicates + very_short + incomplete
    clean = max(0, total - issues)

    return (clean / total) * 100


def compare_file(doc_id: str) -> Dict:
    """Compare a single file across V1, V2, V3"""
    v1_path = V1_DIR / f"{doc_id}.label"
    v2_path = V2_DIR / f"{doc_id}.label"
    v3_path = V3_DIR / f"{doc_id}.label"

    if not v1_path.exists() or not v2_path.exists() or not v3_path.exists():
        return None

    v1_data = load_json(v1_path)
    v2_data = load_json(v2_path)
    v3_data = load_json(v3_path)

    v1_spans = v1_data.get("citation_spans", [])
    v2_spans = v2_data.get("citation_spans", [])
    v3_spans = v3_data.get("citation_spans", [])

    # Metrics for each version
    v1_metrics = {
        "total": len(v1_spans),
        "duplicates": check_duplicate_spans(v1_spans),
        "very_short": check_very_short_spans(v1_spans),
        "incomplete": check_incomplete_endings(v1_spans),
        "quality": calculate_quality_score(v1_spans),
    }

    v2_metrics = {
        "total": len(v2_spans),
        "duplicates": check_duplicate_spans(v2_spans),
        "very_short": check_very_short_spans(v2_spans),
        "incomplete": check_incomplete_endings(v2_spans),
        "quality": calculate_quality_score(v2_spans),
    }

    v3_metrics = {
        "total": len(v3_spans),
        "duplicates": check_duplicate_spans(v3_spans),
        "very_short": check_very_short_spans(v3_spans),
        "incomplete": check_incomplete_endings(v3_spans),
        "quality": calculate_quality_score(v3_spans),
    }

    # Check for differences
    changes = []
    for i, (v1_s, v2_s, v3_s) in enumerate(zip(v1_spans, v2_spans, v3_spans)):
        cid = v1_s.get("citation_id", f"[CITATION_{i+1}]")
        v1_text = v1_s.get("span_text", "")
        v2_text = v2_s.get("span_text", "")
        v3_text = v3_s.get("span_text", "")

        if v1_text != v2_text or v2_text != v3_text or v1_text != v3_text:
            changes.append({
                "citation_id": cid,
                "v1": v1_text,
                "v2": v2_text,
                "v3": v3_text,
            })

    return {
        "doc_id": doc_id,
        "v1": v1_metrics,
        "v2": v2_metrics,
        "v3": v3_metrics,
        "changes": changes,
    }


def main():
    # Find common files
    v1_files = {f.stem for f in V1_DIR.glob("*.label")}
    v2_files = {f.stem for f in V2_DIR.glob("*.label")}
    v3_files = {f.stem for f in V3_DIR.glob("*.label")}

    common_files = v1_files & v2_files & v3_files

    # Sort numerically
    common_files = sorted(common_files, key=lambda x: (int(x) if x.isdigit() else float('inf'), x))

    print(f"Comparing {len(common_files)} files across V1, V2, V3...")

    results = []
    for doc_id in common_files:
        result = compare_file(doc_id)
        if result:
            results.append(result)

    # Aggregate metrics
    agg = {
        "v1": {"total": 0, "duplicates": 0, "very_short": 0, "incomplete": 0},
        "v2": {"total": 0, "duplicates": 0, "very_short": 0, "incomplete": 0},
        "v3": {"total": 0, "duplicates": 0, "very_short": 0, "incomplete": 0},
    }

    for r in results:
        for version in ["v1", "v2", "v3"]:
            agg[version]["total"] += r[version]["total"]
            agg[version]["duplicates"] += r[version]["duplicates"]
            agg[version]["very_short"] += r[version]["very_short"]
            agg[version]["incomplete"] += r[version]["incomplete"]

    # Calculate rates
    for version in ["v1", "v2", "v3"]:
        total = agg[version]["total"]
        if total > 0:
            agg[version]["dup_rate"] = (agg[version]["duplicates"] / total) * 100
            agg[version]["short_rate"] = (agg[version]["very_short"] / total) * 100
            agg[version]["incomplete_rate"] = (agg[version]["incomplete"] / total) * 100
            agg[version]["quality"] = 100 - agg[version]["dup_rate"] - agg[version]["short_rate"] - agg[version]["incomplete_rate"]
        else:
            agg[version]["dup_rate"] = 0
            agg[version]["short_rate"] = 0
            agg[version]["incomplete_rate"] = 0
            agg[version]["quality"] = 0

    # Generate report
    lines = []
    lines.append("=" * 80)
    lines.append("TASK3 VERSION COMPARISON: V1 vs V2 vs V3")
    lines.append("=" * 80)
    lines.append(f"Files compared: {len(results)}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("AGGREGATE METRICS")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'Metric':<30} {'V1 (Old)':<20} {'V2 (Improved)':<20} {'V3 (Sentence-level)':<20}")
    lines.append("-" * 90)
    lines.append(f"{'Total Spans':<30} {agg['v1']['total']:<20} {agg['v2']['total']:<20} {agg['v3']['total']:<20}")
    lines.append(f"{'Duplicate Spans':<30} {agg['v1']['duplicates']:<20} {agg['v2']['duplicates']:<20} {agg['v3']['duplicates']:<20}")
    lines.append(f"{'Duplicate Rate (%)':<30} {agg['v1']['dup_rate']:<20.2f} {agg['v2']['dup_rate']:<20.2f} {agg['v3']['dup_rate']:<20.2f}")
    lines.append(f"{'Very Short (<15)':<30} {agg['v1']['very_short']:<20} {agg['v2']['very_short']:<20} {agg['v3']['very_short']:<20}")
    lines.append(f"{'Very Short Rate (%)':<30} {agg['v1']['short_rate']:<20.2f} {agg['v2']['short_rate']:<20.2f} {agg['v3']['short_rate']:<20.2f}")
    lines.append(f"{'Incomplete Ending':<30} {agg['v1']['incomplete']:<20} {agg['v2']['incomplete']:<20} {agg['v3']['incomplete']:<20}")
    lines.append(f"{'Incomplete Rate (%)':<30} {agg['v1']['incomplete_rate']:<20.2f} {agg['v2']['incomplete_rate']:<20.2f} {agg['v3']['incomplete_rate']:<20.2f}")
    lines.append(f"{'✅ QUALITY SCORE (%)':<30} {agg['v1']['quality']:<20.2f} {agg['v2']['quality']:<20.2f} {agg['v3']['quality']:<20.2f}")
    lines.append("")

    # Interpretation
    lines.append("=" * 80)
    lines.append("INTERPRETATION")
    lines.append("=" * 80)

    best_quality = max(agg['v1']['quality'], agg['v2']['quality'], agg['v3']['quality'])
    best_version = None
    if agg['v3']['quality'] == best_quality:
        best_version = "V3"
    elif agg['v2']['quality'] == best_quality:
        best_version = "V2"
    else:
        best_version = "V1"

    v3_improvement_v1 = agg['v3']['quality'] - agg['v1']['quality']
    v3_improvement_v2 = agg['v3']['quality'] - agg['v2']['quality']

    lines.append(f"🏆 BEST VERSION: {best_version} (quality: {best_quality:.2f}%)")
    lines.append("")
    lines.append(f"V3 vs V1: {v3_improvement_v1:+.2f}% quality")
    lines.append(f"V3 vs V2: {v3_improvement_v2:+.2f}% quality")
    lines.append("")

    # Key changes
    v3_v2_dup_change = agg['v3']['dup_rate'] - agg['v2']['dup_rate']
    v3_v2_short_change = agg['v3']['short_rate'] - agg['v2']['short_rate']

    if abs(v3_v2_dup_change) > 1:
        if v3_v2_dup_change < 0:
            lines.append(f"✅ V3 reduces duplicates: {v3_v2_dup_change:.1f}% vs V2")
        else:
            lines.append(f"⚠️  V3 increases duplicates: {v3_v2_dup_change:+.1f}% vs V2")

    if abs(v3_v2_short_change) > 1:
        if v3_v2_short_change < 0:
            lines.append(f"✅ V3 reduces very short spans: {v3_v2_short_change:.1f}% vs V2")
        else:
            lines.append(f"⚠️  V3 increases very short spans: {v3_v2_short_change:+.1f}% vs V2")

    lines.append("")

    # Example changes
    lines.append("=" * 80)
    lines.append("EXAMPLE CHANGES (First 5 files with differences)")
    lines.append("=" * 80)
    lines.append("")

    count = 0
    for r in results:
        if r["changes"] and count < 5:
            count += 1
            lines.append(f"Doc {r['doc_id']}:")
            lines.append(f"  V1 quality: {r['v1']['quality']:.1f}%")
            lines.append(f"  V2 quality: {r['v2']['quality']:.1f}%")
            lines.append(f"  V3 quality: {r['v3']['quality']:.1f}%")
            lines.append(f"  Changes: {len(r['changes'])} spans modified")

            for change in r['changes'][:3]:  # Show first 3 changes
                cid = change['citation_id']
                v1_preview = change['v1'][:60] + "..." if len(change['v1']) > 60 else change['v1']
                v2_preview = change['v2'][:60] + "..." if len(change['v2']) > 60 else change['v2']
                v3_preview = change['v3'][:60] + "..." if len(change['v3']) > 60 else change['v3']

                lines.append(f"    {cid}:")
                lines.append(f'      V1 ({len(change["v1"])} chars): "{v1_preview}"')
                lines.append(f'      V2 ({len(change["v2"])} chars): "{v2_preview}"')
                lines.append(f'      V3 ({len(change["v3"])} chars): "{v3_preview}"')
            lines.append("")

    # Write report
    report = "\n".join(lines)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n✅ Report saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
