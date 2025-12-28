"""
Check data quality in task3 outputs - find files that need manual review
"""

import json
from pathlib import Path
from collections import defaultdict

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_quality(task3_dir):
    """Check all .label files for quality issues"""

    task3_path = Path(task3_dir)
    label_files = list(task3_path.glob("*.label"))

    print(f"Checking {len(label_files)} files...")
    print("=" * 80)

    issues = {
        "empty_spans": [],
        "very_short_spans": [],  # < 15 chars
        "short_spans": [],  # 15-30 chars
        "malformed": [],
        "no_citations": []
    }

    stats = {
        "total_files": 0,
        "total_spans": 0,
        "span_lengths": []
    }

    for i, label_file in enumerate(label_files, 1):
        if i % 5000 == 0:
            print(f"Progress: {i}/{len(label_files)}...")

        try:
            data = load_json(label_file)
            doc_id = data.get("doc_id", label_file.stem)
            citation_spans = data.get("citation_spans", [])

            stats["total_files"] += 1
            stats["total_spans"] += len(citation_spans)

            if not citation_spans:
                issues["no_citations"].append(doc_id)
                continue

            for span in citation_spans:
                span_text = span.get("span_text", "").strip()
                citation_id = span.get("citation_id", "")
                span_len = len(span_text)

                stats["span_lengths"].append(span_len)

                if span_len == 0:
                    issues["empty_spans"].append({
                        "doc_id": doc_id,
                        "citation_id": citation_id,
                        "file": str(label_file)
                    })
                elif span_len < 15:
                    issues["very_short_spans"].append({
                        "doc_id": doc_id,
                        "citation_id": citation_id,
                        "span_text": span_text,
                        "length": span_len,
                        "file": str(label_file)
                    })
                elif span_len < 30:
                    issues["short_spans"].append({
                        "doc_id": doc_id,
                        "citation_id": citation_id,
                        "span_text": span_text,
                        "length": span_len,
                        "file": str(label_file)
                    })

        except Exception as e:
            issues["malformed"].append({
                "file": str(label_file),
                "error": str(e)
            })

    # Print summary
    print()
    print("=" * 80)
    print("QUALITY CHECK SUMMARY")
    print("=" * 80)
    print(f"Total files: {stats['total_files']:,}")
    print(f"Total spans: {stats['total_spans']:,}")
    print(f"Avg spans/file: {stats['total_spans']/stats['total_files']:.2f}")
    print()

    print("ISSUES FOUND:")
    print("-" * 80)
    print(f"Empty spans (0 chars):       {len(issues['empty_spans']):,}")
    print(f"Very short spans (<15 chars): {len(issues['very_short_spans']):,}")
    print(f"Short spans (15-30 chars):    {len(issues['short_spans']):,}")
    print(f"Files with no citations:      {len(issues['no_citations']):,}")
    print(f"Malformed files:              {len(issues['malformed']):,}")
    print()

    # Total needing review
    total_need_review = len(issues['empty_spans']) + len(issues['very_short_spans']) + len(issues['short_spans'])
    print(f"TOTAL SPANS NEEDING REVIEW: {total_need_review:,}")
    print(f"Percentage: {total_need_review * 100 / stats['total_spans']:.2f}%")
    print()

    # Show examples
    if issues['very_short_spans']:
        print("=" * 80)
        print("EXAMPLES - VERY SHORT SPANS (< 15 chars)")
        print("=" * 80)
        for issue in issues['very_short_spans'][:10]:
            print(f"Doc {issue['doc_id']} | {issue['citation_id']} | Length: {issue['length']}")
            print(f"  Text: \"{issue['span_text']}\"")
            print()

    if issues['short_spans']:
        print("=" * 80)
        print("EXAMPLES - SHORT SPANS (15-30 chars)")
        print("=" * 80)
        for issue in issues['short_spans'][:10]:
            print(f"Doc {issue['doc_id']} | {issue['citation_id']} | Length: {issue['length']}")
            print(f"  Text: \"{issue['span_text']}\"")
            print()

    # Save detailed report
    report_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_task3/data_quality_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "statistics": stats,
            "issues": {
                "empty_spans": issues['empty_spans'],
                "very_short_spans": issues['very_short_spans'],  # Save ALL
                "short_spans": issues['short_spans'],  # Save ALL
                "no_citations": issues['no_citations'],
                "malformed": issues['malformed']
            },
            "summary": {
                "total_files": stats['total_files'],
                "total_spans": stats['total_spans'],
                "empty_count": len(issues['empty_spans']),
                "very_short_count": len(issues['very_short_spans']),
                "short_count": len(issues['short_spans']),
                "total_need_review": total_need_review,
                "percentage_need_review": total_need_review * 100 / stats['total_spans']
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"Detailed report saved to: {report_file}")

    return issues, stats

if __name__ == "__main__":
    task3_dir = "/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3"
    issues, stats = check_quality(task3_dir)
