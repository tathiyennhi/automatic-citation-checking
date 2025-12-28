"""
Compare statistics between rule-based and manual-reviewed versions.

This script generates comparison reports for the thesis.
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics


def load_json(path: Path) -> dict:
    """Load JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_dataset(data_dir: Path) -> dict:
    """
    Analyze a dataset and return statistics.

    Returns:
    {
        "total_files": int,
        "total_citations": int,
        "avg_spans_per_file": float,
        "span_lengths": {
            "min": int,
            "max": int,
            "mean": float,
            "median": float,
            "std": float
        },
        "short_spans": {
            "count": int,
            "percentage": float,
            "examples": []
        },
        "empty_spans": {
            "count": int,
            "percentage": float
        },
        "length_distribution": {
            "0-15": int,
            "15-30": int,
            "30-50": int,
            "50-100": int,
            "100-200": int,
            "200-300": int,
            "300+": int
        }
    }
    """
    label_files = list(data_dir.glob("*.label"))

    total_files = len(label_files)
    total_citations = 0
    all_lengths = []
    short_spans = []
    empty_count = 0
    length_dist = defaultdict(int)

    print(f"Analyzing {total_files} files in {data_dir.name}...")

    for i, label_path in enumerate(label_files, 1):
        try:
            data = load_json(label_path)
            citation_spans = data.get("citation_spans", [])

            total_citations += len(citation_spans)

            for citation in citation_spans:
                span_text = citation.get("span_text", "").strip()
                span_len = len(span_text)

                if span_len == 0:
                    empty_count += 1
                else:
                    all_lengths.append(span_len)

                    if span_len < 15:
                        length_dist["0-15"] += 1
                        short_spans.append({
                            "doc_id": data.get("doc_id", label_path.stem),
                            "citation_id": citation.get("citation_id", ""),
                            "span_text": span_text,
                            "length": span_len
                        })
                    elif span_len < 30:
                        length_dist["15-30"] += 1
                        short_spans.append({
                            "doc_id": data.get("doc_id", label_path.stem),
                            "citation_id": citation.get("citation_id", ""),
                            "span_text": span_text,
                            "length": span_len
                        })
                    elif span_len < 50:
                        length_dist["30-50"] += 1
                    elif span_len < 100:
                        length_dist["50-100"] += 1
                    elif span_len < 200:
                        length_dist["100-200"] += 1
                    elif span_len < 300:
                        length_dist["200-300"] += 1
                    else:
                        length_dist["300+"] += 1

        except Exception as e:
            print(f"  Error processing {label_path}: {e}")

        if i % 10000 == 0:
            print(f"  [{i}/{total_files}] Processed...")

    # Calculate statistics
    stats = {
        "total_files": total_files,
        "total_citations": total_citations,
        "avg_spans_per_file": total_citations / total_files if total_files > 0 else 0,
        "span_lengths": {
            "min": min(all_lengths) if all_lengths else 0,
            "max": max(all_lengths) if all_lengths else 0,
            "mean": statistics.mean(all_lengths) if all_lengths else 0,
            "median": statistics.median(all_lengths) if all_lengths else 0,
            "std": statistics.stdev(all_lengths) if len(all_lengths) > 1 else 0
        },
        "short_spans": {
            "count": len(short_spans),
            "percentage": len(short_spans) * 100 / total_citations if total_citations > 0 else 0,
            "examples": short_spans[:10]  # First 10 examples
        },
        "empty_spans": {
            "count": empty_count,
            "percentage": empty_count * 100 / total_citations if total_citations > 0 else 0
        },
        "length_distribution": dict(length_dist)
    }

    return stats


def print_comparison(rule_based_stats: dict, manual_review_stats: dict):
    """Print side-by-side comparison"""
    print()
    print("=" * 100)
    print("DATASET COMPARISON: Rule-Based vs Manual-Review")
    print("=" * 100)
    print()

    # Basic stats
    print(f"{'Metric':<40} {'Rule-Based':>20} {'Manual-Review':>20} {'Δ':>15}")
    print("-" * 100)

    rb = rule_based_stats
    mr = manual_review_stats

    print(f"{'Total files':<40} {rb['total_files']:>20,} {mr['total_files']:>20,} {'-':>15}")
    print(f"{'Total citations':<40} {rb['total_citations']:>20,} {mr['total_citations']:>20,} {'-':>15}")
    print(f"{'Avg spans/file':<40} {rb['avg_spans_per_file']:>20.2f} {mr['avg_spans_per_file']:>20.2f} {'-':>15}")
    print()

    # Span lengths
    print(f"{'Mean span length (chars)':<40} {rb['span_lengths']['mean']:>20.1f} {mr['span_lengths']['mean']:>20.1f} {mr['span_lengths']['mean'] - rb['span_lengths']['mean']:>+15.1f}")
    print(f"{'Median span length (chars)':<40} {rb['span_lengths']['median']:>20.1f} {mr['span_lengths']['median']:>20.1f} {mr['span_lengths']['median'] - rb['span_lengths']['median']:>+15.1f}")
    print(f"{'Min span length (chars)':<40} {rb['span_lengths']['min']:>20} {mr['span_lengths']['min']:>20} {'-':>15}")
    print(f"{'Max span length (chars)':<40} {rb['span_lengths']['max']:>20} {mr['span_lengths']['max']:>20} {'-':>15}")
    print()

    # Quality metrics
    print(f"{'Short spans (<30 chars)':<40} {rb['short_spans']['count']:>20,} {mr['short_spans']['count']:>20,} {mr['short_spans']['count'] - rb['short_spans']['count']:>+15,}")
    print(f"{'Short spans %':<40} {rb['short_spans']['percentage']:>19.2f}% {mr['short_spans']['percentage']:>19.2f}% {mr['short_spans']['percentage'] - rb['short_spans']['percentage']:>+14.2f}%")
    print(f"{'Empty spans':<40} {rb['empty_spans']['count']:>20,} {mr['empty_spans']['count']:>20,} {mr['empty_spans']['count'] - rb['empty_spans']['count']:>+15,}")
    print(f"{'Empty spans %':<40} {rb['empty_spans']['percentage']:>19.2f}% {mr['empty_spans']['percentage']:>19.2f}% {mr['empty_spans']['percentage'] - rb['empty_spans']['percentage']:>+14.2f}%")
    print()

    # Length distribution
    print("SPAN LENGTH DISTRIBUTION")
    print("-" * 100)
    for bucket in ["0-15", "15-30", "30-50", "50-100", "100-200", "200-300", "300+"]:
        rb_count = rb['length_distribution'].get(bucket, 0)
        mr_count = mr['length_distribution'].get(bucket, 0)
        rb_pct = rb_count * 100 / rb['total_citations'] if rb['total_citations'] > 0 else 0
        mr_pct = mr_count * 100 / mr['total_citations'] if mr['total_citations'] > 0 else 0

        print(f"{bucket + ' chars':<40} {rb_count:>15,} ({rb_pct:>5.1f}%) {mr_count:>15,} ({mr_pct:>5.1f}%) {mr_count - rb_count:>+10,}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Compare rule-based vs manual-reviewed datasets")
    parser.add_argument(
        "--rule_based",
        type=str,
        default="/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3",
        help="Original rule-based dataset directory"
    )
    parser.add_argument(
        "--manual_review",
        type=str,
        default="/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3_manual_review",
        help="Manual-reviewed dataset directory"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/dataset_comparison.json",
        help="Output JSON file with statistics"
    )

    args = parser.parse_args()

    rule_based_dir = Path(args.rule_based)
    manual_review_dir = Path(args.manual_review)
    output_file = Path(args.output)

    print("=" * 100)
    print("DATASET VERSION COMPARISON")
    print("=" * 100)
    print(f"Rule-based: {rule_based_dir}")
    print(f"Manual-review: {manual_review_dir}")
    print()

    # Analyze both versions
    print("Analyzing rule-based version...")
    rule_based_stats = analyze_dataset(rule_based_dir)
    print("✅ Done\n")

    print("Analyzing manual-review version...")
    manual_review_stats = analyze_dataset(manual_review_dir)
    print("✅ Done\n")

    # Print comparison
    print_comparison(rule_based_stats, manual_review_stats)

    # Save to file
    comparison_data = {
        "rule_based": rule_based_stats,
        "manual_review": manual_review_stats,
        "metadata": {
            "rule_based_dir": str(rule_based_dir),
            "manual_review_dir": str(manual_review_dir),
            "generated_at": Path(__file__).name
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 100)
    print(f"✅ Comparison saved to: {output_file}")
    print("=" * 100)


if __name__ == "__main__":
    main()
