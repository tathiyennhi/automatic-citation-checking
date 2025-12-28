"""
Check V4 quality metrics across all processed files

Usage:
  python3 data_task3/check_v4_quality.py
"""

import json
from pathlib import Path
from typing import Dict, List


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


def check_empty_spans(spans: List[Dict]) -> int:
    """Count empty or whitespace-only spans"""
    return sum(1 for s in spans if not s.get("span_text", "").strip())


def main():
    v4_dir = Path("data_outputs/task3_v4")

    label_files = sorted(
        v4_dir.glob("*.label"),
        key=lambda p: (int(p.stem) if p.stem.isdigit() else float('inf'), p.stem)
    )

    if not label_files:
        print("No V4 files found!")
        return

    print("=" * 80)
    print(f"V4 QUALITY CHECK - {len(label_files)} files")
    print("=" * 80)
    print()

    # Aggregate metrics
    total_spans = 0
    total_duplicates = 0
    total_very_short = 0
    total_incomplete = 0
    total_empty = 0

    files_with_issues = []

    for path in label_files:
        data = load_json(path)
        spans = data.get("citation_spans", [])

        if not spans:
            continue

        total_spans += len(spans)

        duplicates = check_duplicate_spans(spans)
        very_short = check_very_short_spans(spans)
        incomplete = check_incomplete_endings(spans)
        empty = check_empty_spans(spans)

        total_duplicates += duplicates
        total_very_short += very_short
        total_incomplete += incomplete
        total_empty += empty

        # Track files with issues
        if duplicates > 0 or very_short > 0 or incomplete > 0 or empty > 0:
            files_with_issues.append({
                "doc_id": path.stem,
                "total": len(spans),
                "duplicates": duplicates,
                "very_short": very_short,
                "incomplete": incomplete,
                "empty": empty,
                "generator": data.get("generator", "unknown")
            })

    # Calculate rates
    if total_spans > 0:
        dup_rate = (total_duplicates / total_spans) * 100
        short_rate = (total_very_short / total_spans) * 100
        incomplete_rate = (total_incomplete / total_spans) * 100
        empty_rate = (total_empty / total_spans) * 100

        # Quality score = 100% - all error rates
        quality_score = 100 - dup_rate - short_rate - incomplete_rate - empty_rate
    else:
        dup_rate = short_rate = incomplete_rate = empty_rate = quality_score = 0

    print(f"{'Metric':<30} {'Count':<15} {'Rate (%)':<15}")
    print("-" * 60)
    print(f"{'Total Spans':<30} {total_spans:<15} {'-':<15}")
    print(f"{'Empty Spans':<30} {total_empty:<15} {empty_rate:<15.2f}")
    print(f"{'Duplicate Spans':<30} {total_duplicates:<15} {dup_rate:<15.2f}")
    print(f"{'Very Short (<15 chars)':<30} {total_very_short:<15} {short_rate:<15.2f}")
    print(f"{'Incomplete Endings':<30} {total_incomplete:<15} {incomplete_rate:<15.2f}")
    print("-" * 60)
    print(f"{'✅ QUALITY SCORE':<30} {'-':<15} {quality_score:<15.2f}")
    print()

    # Interpretation
    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)

    if quality_score >= 95:
        print("🏆 EXCELLENT: V4 quality is outstanding (≥95%)")
    elif quality_score >= 90:
        print("✅ VERY GOOD: V4 quality is very good (90-95%)")
    elif quality_score >= 85:
        print("✓ GOOD: V4 quality is acceptable (85-90%)")
    elif quality_score >= 80:
        print("⚠️  FAIR: V4 quality needs improvement (80-85%)")
    else:
        print("❌ POOR: V4 quality is below acceptable (<80%)")

    print()
    print(f"Files with issues: {len(files_with_issues)}/{len(label_files)} ({len(files_with_issues)/len(label_files)*100:.1f}%)")
    print(f"Clean files: {len(label_files) - len(files_with_issues)}/{len(label_files)} ({(len(label_files) - len(files_with_issues))/len(label_files)*100:.1f}%)")
    print()

    # Show files with issues
    if files_with_issues:
        print("=" * 80)
        print("FILES WITH ISSUES (Top 10)")
        print("=" * 80)
        print()

        # Sort by total issues
        files_with_issues.sort(
            key=lambda x: x["duplicates"] + x["very_short"] + x["incomplete"] + x["empty"],
            reverse=True
        )

        for f in files_with_issues[:10]:
            issues = []
            if f["empty"] > 0:
                issues.append(f"{f['empty']} empty")
            if f["duplicates"] > 0:
                issues.append(f"{f['duplicates']} dup")
            if f["very_short"] > 0:
                issues.append(f"{f['very_short']} short")
            if f["incomplete"] > 0:
                issues.append(f"{f['incomplete']} incomplete")

            issue_str = ", ".join(issues)
            print(f"Doc {f['doc_id']:<5} ({f['generator']:<15}): {issue_str} | {f['total']} total spans")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
