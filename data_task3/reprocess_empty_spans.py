"""
Script to find and reprocess files with empty citation spans.

Usage:
  GEMINI_API_KEY=... python3 data_task3/reprocess_empty_spans.py [--auto-yes]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

def find_files_with_empty_spans(task3_dir: Path):
    """Find all .label files with empty span_text."""
    empty_files = []

    for label_file in sorted(task3_dir.glob("*.label"), key=lambda p: int(p.stem)):
        try:
            with open(label_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            citation_spans = data.get('citation_spans', [])
            empty_spans = [
                span for span in citation_spans
                if span.get('span_text', '').strip() == ''
            ]

            if empty_spans:
                empty_files.append({
                    'file': label_file.name,
                    'doc_id': label_file.stem,
                    'count': len(empty_spans),
                    'citations': [s.get('citation_id') for s in empty_spans]
                })
        except Exception as e:
            print(f"Error reading {label_file.name}: {e}", file=sys.stderr)

    return empty_files

def main():
    parser = argparse.ArgumentParser(description="Reprocess files with empty citation spans")
    parser.add_argument("--auto-yes", action="store_true", help="Automatically proceed without prompting")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    task3_dir = base / "data_outputs" / "task3"

    if not task3_dir.exists():
        print(f"Task3 directory not found: {task3_dir}")
        return

    print("Scanning for files with empty citation spans...")
    empty_files = find_files_with_empty_spans(task3_dir)

    if not empty_files:
        print("✓ No files with empty spans found!")
        return

    print(f"\nFound {len(empty_files)} files with empty spans:\n")
    for item in empty_files[:10]:
        print(f"  {item['file']}: {item['count']} empty - {item['citations']}")

    if len(empty_files) > 10:
        print(f"  ... and {len(empty_files) - 10} more files")

    print(f"\nTotal: {len(empty_files)} files need reprocessing")

    # Ask user if they want to reprocess
    if args.auto_yes:
        response = 'yes'
    else:
        response = input("\nDo you want to reprocess these files? (yes/no): ").strip().lower()

    if response in ('yes', 'y'):
        # Get doc_ids to process
        doc_ids = [item['doc_id'] for item in empty_files]

        # Create a temporary task2 subset
        task2_dir = base / "data_outputs" / "task2"
        temp_dir = base / "data_outputs" / "task2_subset_empty"
        temp_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nCopying {len(doc_ids)} files to temporary directory...")
        for doc_id in doc_ids:
            src = task2_dir / f"{doc_id}.label"
            dst = temp_dir / f"{doc_id}.label"
            if src.exists():
                with open(src, 'r') as f:
                    data = json.load(f)
                with open(dst, 'w') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

        # Run main.py with force reprocess
        print("\nReprocessing files with improved prompt...")
        cmd = [
            sys.executable,
            str(base / "data_task3" / "main.py"),
            "--task2-dir", str(temp_dir),
            "--output-dir", str(task3_dir),
            "--force-reprocess"
        ]

        subprocess.run(cmd)

        print("\n✓ Reprocessing complete! Check the output above for any remaining warnings.")
    else:
        print("Skipped reprocessing.")

if __name__ == "__main__":
    main()
