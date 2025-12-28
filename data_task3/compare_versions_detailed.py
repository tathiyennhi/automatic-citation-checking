"""
Compare Task3 V1 (old logic) vs V2 (new logic)

Metrics:
- Duplicate rate
- Incomplete rate (ends with by/in/etc)
- Length distribution
- Exact match rate between V1 and V2
- Per-file comparison

Usage:
  python3 compare_versions_detailed.py --v1-dir data_outputs/task3_manual_review --v2-dir data_outputs/task3_v2
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict, Counter
import re


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_quality(spans: list) -> dict:
    """Analyze quality metrics for a list of spans"""
    metrics = {
        'total_spans': len(spans),
        'empty_count': 0,
        'very_short_count': 0,  # < 15
        'short_count': 0,  # 15-30
        'normal_count': 0,  # 30+
        'duplicate_count': 0,
        'incomplete_end_count': 0,
        'incomplete_start_count': 0,
        'lengths': [],
        'span_texts': []
    }

    span_text_counts = Counter()

    for span in spans:
        span_text = span.get('span_text', '').strip()
        span_len = len(span_text)

        metrics['lengths'].append(span_len)
        metrics['span_texts'].append(span_text)
        span_text_counts[span_text] += 1

        # Length categories
        if span_len == 0:
            metrics['empty_count'] += 1
        elif span_len < 15:
            metrics['very_short_count'] += 1
        elif span_len < 30:
            metrics['short_count'] += 1
        else:
            metrics['normal_count'] += 1

        # Incomplete ending
        if re.search(r'(,| by| in| to| and| or| the| of| for| with| as)$', span_text):
            metrics['incomplete_end_count'] += 1

        # Incomplete start
        if span_text.startswith(',') or span_text.startswith('and ') or span_text.startswith('or '):
            metrics['incomplete_start_count'] += 1

    # Count duplicates
    for span_text, count in span_text_counts.items():
        if count > 1 and span_text:  # Don't count empty strings
            metrics['duplicate_count'] += count - 1  # Count extra occurrences

    # Calculate rates
    if metrics['total_spans'] > 0:
        metrics['empty_rate'] = metrics['empty_count'] / metrics['total_spans'] * 100
        metrics['very_short_rate'] = metrics['very_short_count'] / metrics['total_spans'] * 100
        metrics['short_rate'] = metrics['short_count'] / metrics['total_spans'] * 100
        metrics['duplicate_rate'] = metrics['duplicate_count'] / metrics['total_spans'] * 100
        metrics['incomplete_end_rate'] = metrics['incomplete_end_count'] / metrics['total_spans'] * 100
        metrics['incomplete_start_rate'] = metrics['incomplete_start_count'] / metrics['total_spans'] * 100

        # Overall quality score (higher is better)
        issue_count = (metrics['empty_count'] + metrics['very_short_count'] +
                      metrics['duplicate_count'] + metrics['incomplete_end_count'] +
                      metrics['incomplete_start_count'])
        metrics['quality_score'] = (1 - issue_count / metrics['total_spans']) * 100

    # Length stats
    if metrics['lengths']:
        metrics['avg_length'] = sum(metrics['lengths']) / len(metrics['lengths'])
        metrics['min_length'] = min(metrics['lengths'])
        metrics['max_length'] = max(metrics['lengths'])

    return metrics


def compare_files(v1_file: Path, v2_file: Path) -> dict:
    """Compare a single file between V1 and V2"""
    v1_data = load_json(v1_file)
    v2_data = load_json(v2_file)

    v1_spans = v1_data.get('citation_spans', [])
    v2_spans = v2_data.get('citation_spans', [])

    # Create mapping by citation_id
    v1_map = {s['citation_id']: s['span_text'] for s in v1_spans}
    v2_map = {s['citation_id']: s['span_text'] for s in v2_spans}

    comparison = {
        'doc_id': v1_data.get('doc_id', v1_file.stem),
        'v1_quality': analyze_quality(v1_spans),
        'v2_quality': analyze_quality(v2_spans),
        'exact_match': 0,
        'different': 0,
        'v1_only': 0,
        'v2_only': 0,
        'changes': []
    }

    all_citation_ids = set(v1_map.keys()) | set(v2_map.keys())

    for cid in all_citation_ids:
        v1_text = v1_map.get(cid, '')
        v2_text = v2_map.get(cid, '')

        if cid not in v1_map:
            comparison['v2_only'] += 1
        elif cid not in v2_map:
            comparison['v1_only'] += 1
        elif v1_text == v2_text:
            comparison['exact_match'] += 1
        else:
            comparison['different'] += 1
            comparison['changes'].append({
                'citation_id': cid,
                'v1_text': v1_text,
                'v1_len': len(v1_text),
                'v2_text': v2_text,
                'v2_len': len(v2_text)
            })

    return comparison


def main():
    parser = argparse.ArgumentParser(description='Compare Task3 V1 vs V2')
    parser.add_argument('--v1-dir', type=str, default='data_outputs/task3_manual_review',
                       help='V1 directory (old logic)')
    parser.add_argument('--v2-dir', type=str, default='data_outputs/task3_v2',
                       help='V2 directory (new logic)')
    parser.add_argument('--report-file', type=str, default='data_task3/COMPARISON_REPORT.txt',
                       help='Output report file')
    args = parser.parse_args()

    base = Path('/Users/tathiyennhi/Documents/automatic-citation-checking')
    v1_dir = base / args.v1_dir
    v2_dir = base / args.v2_dir

    if not v1_dir.exists():
        print(f"❌ V1 directory not found: {v1_dir}")
        return

    if not v2_dir.exists():
        print(f"❌ V2 directory not found: {v2_dir}")
        return

    # Get common files
    v1_files = set(f.stem for f in v1_dir.glob('*.label'))
    v2_files = set(f.stem for f in v2_dir.glob('*.label'))
    common_files = v1_files & v2_files

    print(f"V1 files: {len(v1_files)}")
    print(f"V2 files: {len(v2_files)}")
    print(f"Common files: {len(common_files)}")
    print()

    if not common_files:
        print("❌ No common files to compare!")
        return

    # Aggregate metrics
    v1_total_metrics = defaultdict(int)
    v2_total_metrics = defaultdict(int)
    file_comparisons = []

    print("Comparing files...")
    for i, doc_id in enumerate(sorted(common_files), 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(common_files)}")

        v1_file = v1_dir / f"{doc_id}.label"
        v2_file = v2_dir / f"{doc_id}.label"

        try:
            comp = compare_files(v1_file, v2_file)
            file_comparisons.append(comp)

            # Aggregate
            for key in ['total_spans', 'empty_count', 'very_short_count', 'short_count',
                       'duplicate_count', 'incomplete_end_count', 'incomplete_start_count']:
                v1_total_metrics[key] += comp['v1_quality'].get(key, 0)
                v2_total_metrics[key] += comp['v2_quality'].get(key, 0)

        except Exception as e:
            print(f"  Error comparing {doc_id}: {e}")

    # Calculate aggregate rates
    if v1_total_metrics['total_spans'] > 0:
        v1_total_metrics['duplicate_rate'] = (v1_total_metrics['duplicate_count'] /
                                              v1_total_metrics['total_spans'] * 100)
        v1_total_metrics['incomplete_rate'] = (v1_total_metrics['incomplete_end_count'] /
                                               v1_total_metrics['total_spans'] * 100)
        v1_total_metrics['very_short_rate'] = (v1_total_metrics['very_short_count'] /
                                               v1_total_metrics['total_spans'] * 100)

        issue_count = (v1_total_metrics['empty_count'] + v1_total_metrics['very_short_count'] +
                      v1_total_metrics['duplicate_count'] + v1_total_metrics['incomplete_end_count'])
        v1_total_metrics['quality_score'] = (1 - issue_count / v1_total_metrics['total_spans']) * 100

    if v2_total_metrics['total_spans'] > 0:
        v2_total_metrics['duplicate_rate'] = (v2_total_metrics['duplicate_count'] /
                                              v2_total_metrics['total_spans'] * 100)
        v2_total_metrics['incomplete_rate'] = (v2_total_metrics['incomplete_end_count'] /
                                               v2_total_metrics['total_spans'] * 100)
        v2_total_metrics['very_short_rate'] = (v2_total_metrics['very_short_count'] /
                                               v2_total_metrics['total_spans'] * 100)

        issue_count = (v2_total_metrics['empty_count'] + v2_total_metrics['very_short_count'] +
                      v2_total_metrics['duplicate_count'] + v2_total_metrics['incomplete_end_count'])
        v2_total_metrics['quality_score'] = (1 - issue_count / v2_total_metrics['total_spans']) * 100

    # Generate report
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("TASK3 VERSION COMPARISON REPORT")
    report_lines.append("="*80)
    report_lines.append(f"Files compared: {len(common_files)}")
    report_lines.append("")

    report_lines.append("="*80)
    report_lines.append("AGGREGATE METRICS")
    report_lines.append("="*80)
    report_lines.append("")

    report_lines.append(f"{'Metric':<30} {'V1 (Old)':<20} {'V2 (New)':<20} {'Δ Change':<15}")
    report_lines.append("-"*80)

    metrics_to_show = [
        ('total_spans', 'Total Spans'),
        ('duplicate_count', 'Duplicate Spans'),
        ('duplicate_rate', 'Duplicate Rate (%)'),
        ('very_short_count', 'Very Short (<15)'),
        ('very_short_rate', 'Very Short Rate (%)'),
        ('incomplete_end_count', 'Incomplete Ending'),
        ('incomplete_rate', 'Incomplete Rate (%)'),
        ('quality_score', '✅ QUALITY SCORE (%)')
    ]

    for key, label in metrics_to_show:
        v1_val = v1_total_metrics.get(key, 0)
        v2_val = v2_total_metrics.get(key, 0)

        if 'rate' in key or 'score' in key:
            delta = v2_val - v1_val
            delta_str = f"{delta:+.2f}%"
            v1_str = f"{v1_val:.2f}%"
            v2_str = f"{v2_val:.2f}%"
        else:
            delta = int(v2_val - v1_val)
            delta_str = f"{delta:+d}"
            v1_str = f"{int(v1_val):,}"
            v2_str = f"{int(v2_val):,}"

        report_lines.append(f"{label:<30} {v1_str:<20} {v2_str:<20} {delta_str:<15}")

    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("INTERPRETATION")
    report_lines.append("="*80)

    quality_delta = v2_total_metrics['quality_score'] - v1_total_metrics['quality_score']
    duplicate_delta = v2_total_metrics['duplicate_rate'] - v1_total_metrics['duplicate_rate']

    if quality_delta > 5:
        report_lines.append(f"✅ V2 is SIGNIFICANTLY BETTER (+{quality_delta:.1f}% quality)")
        report_lines.append("   Recommendation: USE V2 for full dataset")
    elif quality_delta > 0:
        report_lines.append(f"✅ V2 is BETTER (+{quality_delta:.1f}% quality)")
        report_lines.append("   Recommendation: USE V2")
    elif quality_delta > -5:
        report_lines.append(f"⚠️  V2 is SIMILAR ({quality_delta:+.1f}% quality)")
        report_lines.append("   Recommendation: Either version OK, prefer V2 for new logic")
    else:
        report_lines.append(f"❌ V2 is WORSE ({quality_delta:.1f}% quality)")
        report_lines.append("   Recommendation: KEEP V1, debug V2 logic")

    report_lines.append("")
    if duplicate_delta < -5:
        report_lines.append(f"✅ V2 fixes duplicate issue: {duplicate_delta:.1f}% reduction")

    # Show example improvements
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("EXAMPLE CHANGES (First 10 files with differences)")
    report_lines.append("="*80)
    report_lines.append("")

    files_with_changes = [fc for fc in file_comparisons if fc['different'] > 0][:10]

    for fc in files_with_changes:
        report_lines.append(f"Doc {fc['doc_id']}:")
        report_lines.append(f"  V1 quality: {fc['v1_quality']['quality_score']:.1f}%")
        report_lines.append(f"  V2 quality: {fc['v2_quality']['quality_score']:.1f}%")

        if fc['changes']:
            report_lines.append(f"  Changes: {len(fc['changes'])} spans modified")
            for change in fc['changes'][:2]:  # Show first 2
                report_lines.append(f"    {change['citation_id']}:")
                report_lines.append(f"      V1 ({change['v1_len']} chars): \"{change['v1_text'][:60]}...\"")
                report_lines.append(f"      V2 ({change['v2_len']} chars): \"{change['v2_text'][:60]}...\"")
        report_lines.append("")

    # Print and save
    report_text = "\n".join(report_lines)
    print()
    print(report_text)

    # Save report
    report_file = base / args.report_file
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print()
    print(f"📄 Report saved to: {report_file}")

    # Save detailed JSON
    json_file = report_file.with_suffix('.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'v1_metrics': dict(v1_total_metrics),
            'v2_metrics': dict(v2_total_metrics),
            'file_comparisons': file_comparisons[:100]  # First 100 files
        }, f, indent=2, ensure_ascii=False)

    print(f"📄 Detailed JSON saved to: {json_file}")


if __name__ == '__main__':
    main()
