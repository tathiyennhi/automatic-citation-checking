"""
Generate clear list of files that need fixing for manual review
"""

import json
from pathlib import Path
from collections import defaultdict

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # Load quality report
    report_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_task3/data_quality_report.json")
    report = load_json(report_file)

    # Organize by file
    files_info = defaultdict(lambda: {"very_short": [], "short": []})

    # Process very short spans
    for issue in report['issues']['very_short_spans']:
        doc_id = issue['doc_id']
        files_info[doc_id]["very_short"].append({
            "citation_id": issue['citation_id'],
            "span_text": issue['span_text'],
            "length": issue['length']
        })

    # Process short spans
    for issue in report['issues']['short_spans']:
        doc_id = issue['doc_id']
        files_info[doc_id]["short"].append({
            "citation_id": issue['citation_id'],
            "span_text": issue['span_text'],
            "length": issue['length']
        })

    # Create comprehensive list
    print("="*80)
    print("FILES NEEDING MANUAL REVIEW - DETAILED LIST")
    print("="*80)
    print(f"Total files: {len(files_info)}")
    print(f"Total issues: {report['summary']['total_need_review']}")
    print()

    # Sort by doc_id
    sorted_files = sorted(files_info.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0])

    output_lines = []
    output_lines.append("="*80)
    output_lines.append("FILES TO FIX - COMPLETE LIST")
    output_lines.append("="*80)
    output_lines.append(f"Total: {len(files_info)} files with {report['summary']['total_need_review']} short spans")
    output_lines.append("")

    for doc_id, info in sorted_files:
        very_short = info["very_short"]
        short = info["short"]
        total = len(very_short) + len(short)

        output_lines.append(f"Doc ID: {doc_id} ({total} spans)")
        output_lines.append(f"  File: task3/{doc_id}.label")
        output_lines.append(f"  Text source: task2/{doc_id}.in")
        output_lines.append("")

        if very_short:
            output_lines.append(f"  Very Short (<15 chars): {len(very_short)}")
            for span in very_short:
                output_lines.append(f"    - {span['citation_id']}: \"{span['span_text']}\" ({span['length']} chars)")
            output_lines.append("")

        if short:
            output_lines.append(f"  Short (15-30 chars): {len(short)}")
            for span in short:
                output_lines.append(f"    - {span['citation_id']}: \"{span['span_text']}\" ({span['length']} chars)")
            output_lines.append("")

        output_lines.append("-"*80)
        output_lines.append("")

    # Save to file
    output_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_task3/FILES_TO_FIX.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))

    print(f"✅ Detailed list saved to: {output_file}")
    print()

    # Also create simple CSV for easier parsing
    csv_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_task3/FILES_TO_FIX.csv")
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("doc_id,citation_id,span_text,length,category,task3_file,task2_file\n")
        for doc_id, info in sorted_files:
            for span in info["very_short"]:
                f.write(f"{doc_id},{span['citation_id']},\"{span['span_text']}\",{span['length']},very_short,task3/{doc_id}.label,task2/{doc_id}.in\n")
            for span in info["short"]:
                f.write(f"{doc_id},{span['citation_id']},\"{span['span_text']}\",{span['length']},short,task3/{doc_id}.label,task2/{doc_id}.in\n")

    print(f"✅ CSV saved to: {csv_file}")
    print()

    # Print summary by category
    print("SUMMARY BY CATEGORY:")
    print("-"*80)
    total_very_short = sum(len(info["very_short"]) for info in files_info.values())
    total_short = sum(len(info["short"]) for info in files_info.values())
    print(f"Very short (<15 chars):  {total_very_short:,} spans in {sum(1 for info in files_info.values() if info['very_short'])} files")
    print(f"Short (15-30 chars):     {total_short:,} spans in {sum(1 for info in files_info.values() if info['short'])} files")
    print(f"Total:                   {total_very_short + total_short:,} spans in {len(files_info)} files")
    print()

    # Print first 10 files as preview
    print("PREVIEW - First 10 files:")
    print("-"*80)
    for doc_id, info in sorted_files[:10]:
        very_short = info["very_short"]
        short = info["short"]
        total = len(very_short) + len(short)
        print(f"{doc_id}: {total} spans ({len(very_short)} very short, {len(short)} short)")
        for span in (very_short + short)[:3]:  # Show first 3 spans
            print(f"  {span['citation_id']}: \"{span['span_text']}\" ({span['length']} chars)")
        if len(very_short) + len(short) > 3:
            print(f"  ... and {len(very_short) + len(short) - 3} more")
        print()

if __name__ == "__main__":
    main()
