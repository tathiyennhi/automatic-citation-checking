"""
Auto-fix short spans with AI-assisted expansion
Logs all changes for thesis documentation
"""

import json
from pathlib import Path
from datetime import datetime
import re

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def find_sentence_containing_citation(text, citation_marker):
    """
    Find the full sentence containing the citation marker.
    Uses same logic as position-based strategy.
    """
    idx = text.find(citation_marker)
    if idx == -1:
        return None, None, None

    # Find sentence boundaries
    before_text = text[:idx]
    after_text = text[idx + len(citation_marker):]

    # Find sentence start
    start = 0
    matches = list(re.finditer(r"[.!?]\s+(?=[A-Z•])", before_text))
    if matches:
        start = matches[-1].end()

    # Find sentence end
    end = len(text)
    match = re.search(r"[.!?]", after_text)
    if match:
        end = idx + len(citation_marker) + match.end()

    return start, end, text[start:end]

def expand_short_span(text, citation_marker, current_span, span_length):
    """
    Expand short span to full sentence using smart heuristics.

    Returns: (new_span, method_used)
    """
    # Strategy 1: Get full sentence
    start, end, full_sentence = find_sentence_containing_citation(text, citation_marker)

    if not full_sentence:
        return current_span, "no_change_no_sentence"

    # Remove citation markers from sentence
    clean_sentence = re.sub(r"\[CITATION_\d+\]", "", full_sentence).strip()

    # Clean up spacing
    clean_sentence = re.sub(r"\s+", " ", clean_sentence)
    clean_sentence = re.sub(r"\s+([.,!?;:])", r"\1", clean_sentence)

    # Strategy 2: If very short (<15), always use full sentence
    if span_length < 15:
        return clean_sentence, "full_sentence_very_short"

    # Strategy 3: If short (15-30), check if current span is fragment
    # If it's a fragment (starts with comma, lowercase, etc.), use full sentence
    if current_span and len(current_span) > 0:
        first_char = current_span[0]
        if first_char in [',', ';', ':', '-', 'and', 'or', 'but'] or first_char.islower():
            return clean_sentence, "full_sentence_fragment"

    # Strategy 4: If current span seems incomplete (no verb/subject), use full
    if len(current_span.split()) < 4:  # Less than 4 words usually incomplete
        return clean_sentence, "full_sentence_too_short"

    # Default: use full sentence
    return clean_sentence, "full_sentence_default"

def auto_fix_file(label_file, body_dir, output_dir, log):
    """
    Fix short spans in one file.
    Returns: number of spans fixed
    """
    try:
        data = load_json(label_file)
        doc_id = data.get("doc_id", label_file.stem)
        citation_spans = data.get("citation_spans", [])

        # Load body text
        body_file = body_dir / f"{doc_id}.body"
        if not body_file.exists():
            log.append({
                "doc_id": doc_id,
                "status": "error",
                "reason": "body_file_not_found",
                "file": str(label_file)
            })
            return 0

        body_data = load_json(body_file)
        text = body_data.get("text", "")

        if not text:
            log.append({
                "doc_id": doc_id,
                "status": "error",
                "reason": "empty_body_text",
                "file": str(label_file)
            })
            return 0

        # Check and fix each span
        fixes_made = 0
        for i, span in enumerate(citation_spans):
            span_text = span.get("span_text", "").strip()
            citation_id = span.get("citation_id", "")
            span_len = len(span_text)

            # Only fix if span is short (<30 chars)
            if 0 < span_len < 30:
                new_span, method = expand_short_span(text, citation_id, span_text, span_len)

                # Update span
                old_span = span_text
                citation_spans[i]["span_text"] = new_span
                fixes_made += 1

                # Log the change
                log.append({
                    "doc_id": doc_id,
                    "citation_id": citation_id,
                    "citation_index": i,
                    "old_span": old_span,
                    "new_span": new_span,
                    "old_length": len(old_span),
                    "new_length": len(new_span),
                    "method": method,
                    "timestamp": datetime.now().isoformat(),
                    "file": str(label_file)
                })

        # Save updated file if any fixes were made
        if fixes_made > 0:
            # Update data
            data["citation_spans"] = citation_spans

            # Save to output directory
            output_file = output_dir / label_file.name
            save_json(data, output_file)

        return fixes_made

    except Exception as e:
        log.append({
            "doc_id": label_file.stem,
            "status": "error",
            "reason": str(e),
            "file": str(label_file)
        })
        return 0

def main():
    print("="*80)
    print("AUTO-FIX SHORT SPANS WITH AI-ASSISTED EXPANSION")
    print("="*80)
    print()

    # Paths
    task3_dir = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3")
    task3_manual_dir = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3_manual_review")
    body_dir = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task1_body")

    # Load quality report to get list of files with issues
    report_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_task3/data_quality_report.json")

    if not report_file.exists():
        print("❌ Error: data_quality_report.json not found!")
        print("   Run check_data_quality.py first")
        return

    with open(report_file, 'r') as f:
        report = json.load(f)

    # Collect all files that need fixing
    files_to_fix = set()

    for issue in report['issues']['very_short_spans']:
        files_to_fix.add(issue['file'])

    for issue in report['issues']['short_spans']:
        files_to_fix.add(issue['file'])

    print(f"Files to fix: {len(files_to_fix)}")
    print(f"Body directory: {body_dir}")
    print(f"Output directory: {task3_manual_dir}")
    print()

    # Confirm
    response = input("Start auto-fix? This will modify files in task3_manual_review. (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        return

    print()
    print("Processing...")
    print()

    # Process files
    log = []
    total_fixes = 0

    for i, file_path in enumerate(sorted(files_to_fix), 1):
        label_file = Path(file_path)

        fixes = auto_fix_file(label_file, body_dir, task3_manual_dir, log)
        total_fixes += fixes

        if (i % 100 == 0) or (i == len(files_to_fix)):
            print(f"[{i}/{len(files_to_fix)}] Fixed {total_fixes} spans so far...")

    print()
    print("="*80)
    print("AUTO-FIX COMPLETE")
    print("="*80)
    print(f"Files processed: {len(files_to_fix)}")
    print(f"Total spans fixed: {total_fixes}")
    print()

    # Save detailed log
    log_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/auto_fix_log.json")

    log_data = {
        "summary": {
            "files_processed": len(files_to_fix),
            "total_fixes": total_fixes,
            "timestamp": datetime.now().isoformat(),
            "method": "AI-assisted expansion (heuristic)",
            "output_directory": str(task3_manual_dir)
        },
        "changes": log
    }

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"Detailed log saved to: {log_file}")
    print()

    # Show statistics by method
    from collections import Counter
    methods = Counter([change.get('method', 'unknown') for change in log if 'method' in change])

    print("FIXES BY METHOD:")
    print("-"*80)
    for method, count in methods.most_common():
        print(f"  {method}: {count}")
    print()

    # Show examples
    print("EXAMPLE FIXES:")
    print("-"*80)
    for change in log[:5]:
        if 'old_span' in change:
            print(f"Doc {change['doc_id']} | {change['citation_id']}")
            print(f"  OLD ({change['old_length']} chars): \"{change['old_span']}\"")
            print(f"  NEW ({change['new_length']} chars): \"{change['new_span']}\"")
            print(f"  Method: {change['method']}")
            print()

    print("✅ All changes logged and saved!")
    print(f"   Modified files in: {task3_manual_dir}")
    print(f"   Change log: {log_file}")

if __name__ == "__main__":
    main()
