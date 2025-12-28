"""
Manual Annotation Tool for Citation Span Review

Interactive CLI tool to review and correct short citation spans.
Changes are saved to task3_manual_review and logged automatically.
"""

import json
from pathlib import Path
from datetime import datetime
import re
from typing import List, Dict, Optional


def load_json(path: Path) -> dict:
    """Load JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path):
    """Save JSON file"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_change(change: dict, log_file: Path):
    """Append change to log file"""
    # Load existing log
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            log_data = json.load(f)
    else:
        log_data = {"changes": [], "statistics": {}}

    # Add new change
    log_data["changes"].append(change)

    # Update statistics
    stats = log_data["statistics"]
    stats["total_changes"] = len(log_data["changes"])
    stats["last_updated"] = datetime.now().isoformat()

    # Save log
    save_json(log_data, log_file)


def find_short_spans(data_dir: Path, max_length: int = 30) -> List[Dict]:
    """
    Find all citation spans shorter than max_length.

    Returns: [
        {
            "file_path": Path,
            "doc_id": "123",
            "citation_index": 0,
            "citation_id": "[CITATION_1]",
            "span_text": "short span",
            "span_length": 10
        },
        ...
    ]
    """
    short_spans = []

    label_files = sorted(data_dir.glob("*.label"))
    print(f"Scanning {len(label_files)} files for short spans (<{max_length} chars)...")

    for i, label_path in enumerate(label_files, 1):
        data = load_json(label_path)
        doc_id = data.get("doc_id", label_path.stem)
        citation_spans = data.get("citation_spans", [])

        for idx, citation in enumerate(citation_spans):
            span_text = citation.get("span_text", "").strip()
            citation_id = citation.get("citation_id", "")

            if 0 < len(span_text) < max_length:
                short_spans.append({
                    "file_path": label_path,
                    "doc_id": doc_id,
                    "citation_index": idx,
                    "citation_id": citation_id,
                    "span_text": span_text,
                    "span_length": len(span_text)
                })

        if i % 10000 == 0:
            print(f"  [{i}/{len(label_files)}] Found {len(short_spans)} short spans so far...")

    print(f"✅ Found {len(short_spans)} short spans")
    return short_spans


def highlight_citation_in_text(text: str, citation_marker: str) -> str:
    """Add visual markers around citation for better visibility"""
    return text.replace(citation_marker, f">>>{citation_marker}<<<")


def show_citation_context(
    file_path: Path,
    doc_id: str,
    citation_index: int,
    citation_id: str,
    current_span: str
) -> Optional[str]:
    """
    Display citation context and prompt for new span.

    Returns: New span text or None if keeping original
    """
    # Load data
    data = load_json(file_path)
    text = data.get("text", "")
    citation_spans = data.get("citation_spans", [])

    if citation_index >= len(citation_spans):
        print("❌ Error: Citation index out of range")
        return None

    citation = citation_spans[citation_index]

    # Find citation marker in text
    marker_pos = text.find(citation_id)
    if marker_pos == -1:
        print(f"⚠️  Warning: Citation marker not found in text")
        context_window = 300
        context_start = max(0, marker_pos - context_window)
        context_end = min(len(text), marker_pos + len(citation_id) + context_window)
    else:
        # Show context window around citation
        context_window = 300
        context_start = max(0, marker_pos - context_window)
        context_end = min(len(text), marker_pos + len(citation_id) + context_window)

    context = text[context_start:context_end]
    context_highlighted = highlight_citation_in_text(context, citation_id)

    # Display
    print()
    print("=" * 80)
    print(f"📄 Doc ID: {doc_id}")
    print(f"🔖 Citation: {citation_id}")
    print(f"📏 Current span length: {len(current_span)} chars")
    print()
    print("📝 CURRENT SPAN:")
    print(f'   "{current_span}"')
    print()
    print("📖 CONTEXT (citation marked with >>>...<<<):")
    print("-" * 80)
    print(context_highlighted)
    print("-" * 80)
    print()

    # Find sentence containing citation
    # Simple sentence detection
    sentences = re.split(r'[.!?]\s+(?=[A-Z•])', text)
    citation_sentence = None
    for sent in sentences:
        if citation_id in sent:
            citation_sentence = sent
            break

    if citation_sentence:
        # Remove citation markers for cleaner view
        clean_sentence = re.sub(r'\[CITATION_\d+\]', '', citation_sentence).strip()
        print("💡 FULL SENTENCE (citations removed):")
        print(f'   "{clean_sentence}"')
        print()

    # Options
    print("OPTIONS:")
    print("  1. Enter new span text (copy-paste recommended)")
    print("  2. Type 'full' to use full sentence")
    print("  3. Press Enter to keep current span")
    print("  4. Type 'skip' to skip this file")
    print("  5. Type 'quit' to save and exit")
    print()

    choice = input("Your choice: ").strip()

    if choice.lower() == 'quit':
        return 'QUIT'
    elif choice.lower() == 'skip':
        return None
    elif choice.lower() == 'full' and citation_sentence:
        # Use full sentence without citations
        return clean_sentence
    elif choice == '':
        return None
    else:
        # User entered custom span
        return choice


def main():
    """Main annotation workflow"""
    import argparse

    parser = argparse.ArgumentParser(description="Manual annotation tool for citation spans")
    parser.add_argument(
        "--data_dir",
        type=str,
        default="/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3_manual_review",
        help="Directory containing .label files to review"
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=30,
        help="Maximum span length to consider as 'short' (default: 30)"
    )
    parser.add_argument(
        "--log_file",
        type=str,
        default="/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/manual_review_log.json",
        help="Log file for tracking changes"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last saved position"
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    log_file = Path(args.log_file)

    print("=" * 80)
    print("MANUAL ANNOTATION TOOL - Citation Span Review")
    print("=" * 80)
    print(f"Data directory: {data_dir}")
    print(f"Max span length: {args.max_length} chars")
    print(f"Log file: {log_file}")
    print()

    # Find short spans
    short_spans = find_short_spans(data_dir, args.max_length)

    if not short_spans:
        print("✅ No short spans found! All spans are adequate.")
        return

    print()
    print(f"Found {len(short_spans)} short spans to review")
    print()

    # Check if resuming
    start_index = 0
    if args.resume and log_file.exists():
        log_data = load_json(log_file)
        completed_keys = set()
        for change in log_data.get("changes", []):
            key = f"{change['doc_id']}_{change['citation_id']}"
            completed_keys.add(key)

        # Filter out already completed
        short_spans = [
            s for s in short_spans
            if f"{s['doc_id']}_{s['citation_id']}" not in completed_keys
        ]
        print(f"📌 Resuming: {len(short_spans)} spans remaining")
        print()

    if not short_spans:
        print("✅ All short spans already reviewed!")
        return

    # Start annotation
    total = len(short_spans)
    changes_made = 0

    for i, span_info in enumerate(short_spans, 1):
        print(f"\n{'='*80}")
        print(f"Progress: {i}/{total} ({i*100//total}%)")
        print(f"Changes made so far: {changes_made}")
        print(f"{'='*80}")

        new_span = show_citation_context(
            file_path=span_info["file_path"],
            doc_id=span_info["doc_id"],
            citation_index=span_info["citation_index"],
            citation_id=span_info["citation_id"],
            current_span=span_info["span_text"]
        )

        if new_span == 'QUIT':
            print("\n✅ Saving and exiting...")
            break

        if new_span and new_span != span_info["span_text"]:
            # Update the file
            data = load_json(span_info["file_path"])
            old_span = data["citation_spans"][span_info["citation_index"]]["span_text"]
            data["citation_spans"][span_info["citation_index"]]["span_text"] = new_span

            # Save updated file
            save_json(data, span_info["file_path"])

            # Log change
            change_record = {
                "doc_id": span_info["doc_id"],
                "citation_id": span_info["citation_id"],
                "citation_index": span_info["citation_index"],
                "old_span": old_span,
                "new_span": new_span,
                "old_length": len(old_span),
                "new_length": len(new_span),
                "timestamp": datetime.now().isoformat(),
                "file_path": str(span_info["file_path"])
            }
            log_change(change_record, log_file)

            changes_made += 1
            print(f"✅ Updated and logged!")

    # Final summary
    print()
    print("=" * 80)
    print("ANNOTATION SESSION COMPLETE")
    print("=" * 80)
    print(f"Reviewed: {i}/{total} spans")
    print(f"Changes made: {changes_made}")
    print(f"Log file: {log_file}")
    print()
    print("Next steps:")
    print("1. Continue reviewing: python manual_annotation_tool.py --resume")
    print("2. View statistics: python compare_versions.py")


if __name__ == "__main__":
    main()
