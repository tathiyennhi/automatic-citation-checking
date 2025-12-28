#!/usr/bin/env python3
"""
Compare results between old logic and new logic
"""
import json
import glob
import os
from pathlib import Path
from collections import defaultdict

def analyze_directory(base_path):
    """Analyze all label files in a directory"""
    stats = {
        "total_papers": 0,
        "total_files": 0,
        "total_sentences": 0,
        "total_citations": 0,
        "files_with_citations": 0,
        "broken_et_al": 0,
        "papers_breakdown": {}
    }

    # Find all paper directories
    paper_dirs = sorted(glob.glob(f"{base_path}/*/"))
    stats["total_papers"] = len(paper_dirs)

    for paper_dir in paper_dirs:
        paper_name = Path(paper_dir).name
        paper_stats = {
            "files": 0,
            "sentences": 0,
            "citations": 0,
            "broken_et_al": 0
        }

        label_files = sorted(glob.glob(f"{paper_dir}/*.label"))

        for label_file in label_files:
            stats["total_files"] += 1
            paper_stats["files"] += 1

            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    texts = data.get("texts", [])
                    citations = data.get("correct_citations", [])

                    stats["total_sentences"] += len(texts)
                    paper_stats["sentences"] += len(texts)

                    if citations:
                        stats["files_with_citations"] += 1
                        stats["total_citations"] += len(citations)
                        paper_stats["citations"] += len(citations)

                    # Check for broken "et al." patterns
                    for text in texts:
                        if text.strip().endswith("et al."):
                            stats["broken_et_al"] += 1
                            paper_stats["broken_et_al"] += 1

            except Exception as e:
                print(f"Error reading {label_file}: {e}")

        stats["papers_breakdown"][paper_name] = paper_stats

    return stats

def print_comparison(old_stats, new_stats):
    """Print comparison table"""
    print("\n" + "="*80)
    print("📊 COMPARISON REPORT: Logic Cũ vs Logic Mới")
    print("="*80)

    print(f"\n{'Metric':<40} {'Logic Cũ':>15} {'Logic Mới':>15} {'Change':>10}")
    print("-"*80)

    # Papers
    print(f"{'Total Papers':<40} {old_stats['total_papers']:>15,} {new_stats['total_papers']:>15,} {''}")

    # Files
    old_files = old_stats['total_files']
    new_files = new_stats['total_files']
    diff_files = new_files - old_files
    pct_files = (diff_files / old_files * 100) if old_files > 0 else 0
    print(f"{'Total Files':<40} {old_files:>15,} {new_files:>15,} {diff_files:>9,} ({pct_files:+.1f}%)")

    # Sentences
    old_sents = old_stats['total_sentences']
    new_sents = new_stats['total_sentences']
    diff_sents = new_sents - old_sents
    pct_sents = (diff_sents / old_sents * 100) if old_sents > 0 else 0
    print(f"{'Total Sentences':<40} {old_sents:>15,} {new_sents:>15,} {diff_sents:>9,} ({pct_sents:+.1f}%)")

    # Citations
    old_cits = old_stats['total_citations']
    new_cits = new_stats['total_citations']
    diff_cits = new_cits - old_cits
    pct_cits = (diff_cits / old_cits * 100) if old_cits > 0 else 0
    print(f"{'Total Citations':<40} {old_cits:>15,} {new_cits:>15,} {diff_cits:>9,} ({pct_cits:+.1f}%)")

    # Files with citations
    old_fcits = old_stats['files_with_citations']
    new_fcits = new_stats['files_with_citations']
    diff_fcits = new_fcits - old_fcits
    print(f"{'Files with Citations':<40} {old_fcits:>15,} {new_fcits:>15,} {diff_fcits:>9,}")

    # Broken et al
    old_broken = old_stats['broken_et_al']
    new_broken = new_stats['broken_et_al']
    diff_broken = new_broken - old_broken
    pct_broken = ((old_broken - new_broken) / old_broken * 100) if old_broken > 0 else 0
    print(f"{'Broken \"et al.\" cases':<40} {old_broken:>15,} {new_broken:>15,} {diff_broken:>9,} ({-pct_broken:+.1f}% fixed)")

    print("-"*80)

    # Averages
    print(f"\n{'Average per Paper':<40} {'Logic Cũ':>15} {'Logic Mới':>15}")
    print("-"*80)

    if old_stats['total_papers'] > 0:
        print(f"{'Files/paper':<40} {old_files/old_stats['total_papers']:>15.1f} {new_files/new_stats['total_papers']:>15.1f}")
        print(f"{'Sentences/paper':<40} {old_sents/old_stats['total_papers']:>15.1f} {new_sents/new_stats['total_papers']:>15.1f}")
        print(f"{'Citations/paper':<40} {old_cits/old_stats['total_papers']:>15.1f} {new_cits/new_stats['total_papers']:>15.1f}")

        if old_broken > 0:
            print(f"{'Broken et al./paper':<40} {old_broken/old_stats['total_papers']:>15.2f} {new_broken/new_stats['total_papers']:>15.2f}")

    # Citation percentage
    print("\n" + "-"*80)
    old_cit_pct = (old_cits / old_sents * 100) if old_sents > 0 else 0
    new_cit_pct = (new_cits / new_sents * 100) if new_sents > 0 else 0
    print(f"{'Citation Percentage':<40} {old_cit_pct:>14.1f}% {new_cit_pct:>14.1f}%")

    # Broken percentage
    if old_sents > 0:
        old_broken_pct = (old_broken / old_sents * 100)
        new_broken_pct = (new_broken / new_sents * 100)
        print(f"{'Broken et al. / Total Sentences':<40} {old_broken_pct:>14.2f}% {new_broken_pct:>14.2f}%")

    print("="*80)

    # Summary
    print("\n📝 SUMMARY:")
    if new_broken < old_broken:
        improvement = (old_broken - new_broken) / old_broken * 100
        print(f"  ✅ Logic mới giảm {old_broken - new_broken} broken \"et al.\" cases ({improvement:.1f}% improvement)")

    if new_files < old_files:
        print(f"  ✅ Logic mới tạo ít files hơn {old_files - new_files} files (tổ chức tốt hơn)")

    if abs(new_cits - old_cits) < 5:
        print(f"  ✅ Citation detection ổn định (~{new_cits} citations)")
    else:
        print(f"  ⚠️  Citation detection có sự khác biệt: {diff_cits:+d} citations")

    print()

def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python compare_results.py <old_dir> <new_dir>")
        print("Example: python compare_results.py ../data_outputs/task1a ../data_outputs/task1a_test50")
        sys.exit(1)

    old_dir = sys.argv[1]
    new_dir = sys.argv[2]

    if not os.path.exists(old_dir):
        print(f"❌ Old directory not found: {old_dir}")
        sys.exit(1)

    if not os.path.exists(new_dir):
        print(f"❌ New directory not found: {new_dir}")
        sys.exit(1)

    print("🔍 Analyzing logic cũ...")
    old_stats = analyze_directory(old_dir)

    print("🔍 Analyzing logic mới...")
    new_stats = analyze_directory(new_dir)

    print_comparison(old_stats, new_stats)

if __name__ == "__main__":
    main()
