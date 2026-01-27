#!/usr/bin/env python3
"""
Add s_span and e_span to Task 3 label files.

Strategy: Use span_text as anchor to find exact position in original text.
"""
import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple


def add_positions_to_label(label_path: Path, dry_run: bool = False) -> Dict[str, int]:
    """Add s_span and e_span to one label file."""

    try:
        with open(label_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ERROR reading {label_path.name}: {e}")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    text = data.get('text', '')
    citation_spans = data.get('citation_spans', [])

    stats = {'success': 0, 'failed': 0, 'skipped': 0}
    modified = False

    for span_info in citation_spans:
        # Skip if already has positions
        if 's_span' in span_info and 'e_span' in span_info:
            stats['skipped'] += 1
            continue

        citation_id = span_info['citation_id']
        span_text = span_info['span_text']

        # Find position using citation as context
        try:
            result = find_span_position(text, span_text, citation_id)
        except Exception as e:
            print(f"❌ {label_path.name} - {citation_id}: Exception in find_span_position: {e}")
            result = None

        if result is None:
            print(f"❌ {label_path.name} - {citation_id}: Cannot find span")
            print(f"   Span (first 80 chars): {span_text[:80]}...")
            stats['failed'] += 1
            span_info['s_span'] = -1
            span_info['e_span'] = -1
            modified = True
            continue

        s_span, e_span = result

        # Verify
        extracted = text[s_span:e_span]
        # Remove citation markers from extracted text for comparison
        extracted_clean = re.sub(r'\[CITATION_\d+\]', '', extracted).strip()
        span_clean = span_text.strip()

        # Normalize whitespace for comparison
        extracted_norm = re.sub(r'\s+', ' ', extracted_clean)
        span_norm = re.sub(r'\s+', ' ', span_clean)

        if extracted_norm == span_norm:
            span_info['s_span'] = s_span
            span_info['e_span'] = e_span
            stats['success'] += 1
            modified = True
        else:
            print(f"⚠️  {label_path.name} - {citation_id}: Mismatch")
            print(f"   Expected: {span_clean[:80]}...")
            print(f"   Got:      {extracted_clean[:80]}...")
            stats['failed'] += 1
            span_info['s_span'] = -1
            span_info['e_span'] = -1
            modified = True

    # Save ONLY if modified and not dry_run
    if modified and not dry_run:
        try:
            with open(label_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ ERROR saving {label_path.name}: {e}")

    return stats


def find_span_position(text: str, span_text: str, citation_id: str) -> Optional[Tuple[int, int]]:
    """
    Find position of span_text in original text.

    SIMPLE STRATEGY:
    - span_text is the CLEANED version (no [CITATION_X])
    - Use citation position to find sentence boundaries
    - Return boundaries from original text
    """

    # Find citation position
    citation_idx = text.find(citation_id)
    if citation_idx == -1:
        print(f"    Cannot find {citation_id} in text")
        return None

    # Import sentence boundary finder from main_v4.py
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    try:
        from data_task3.main_v4 import find_sentence_boundaries_v4
        start, end = find_sentence_boundaries_v4(text, citation_idx)
        return (start, end)
    except Exception as e:
        print(f"    Error using v4 logic: {e}")
        # Fallback: simple sentence detection
        return fallback_sentence_detection(text, citation_idx)


def fallback_sentence_detection(text: str, citation_idx: int) -> Tuple[int, int]:
    """
    Simple fallback to detect sentence boundaries.
    """
    # Find start: look backwards for sentence boundary
    start = 0
    for i in range(citation_idx - 1, -1, -1):
        if text[i] in '.!?' and (i == 0 or text[i+1].isspace()):
            start = i + 1
            while start < len(text) and text[start].isspace():
                start += 1
            break

    # Find end: look forwards for sentence boundary
    end = len(text)
    for i in range(citation_idx, len(text)):
        if text[i] in '.!?':
            end = i + 1
            break

    return (start, end)


def process_directory(data_dir: Path, dry_run: bool = False, limit: int = -1):
    """Process all .label files in directory."""

    label_files = sorted(data_dir.glob('*.label'))

    if limit > 0:
        label_files = label_files[:limit]

    print(f"\n📂 Processing {len(label_files)} files in {data_dir.name}/")
    print("=" * 60)

    total_stats = {'success': 0, 'failed': 0, 'skipped': 0, 'files': 0}

    for i, label_path in enumerate(label_files, 1):
        stats = add_positions_to_label(label_path, dry_run=dry_run)

        for key in stats:
            total_stats[key] += stats[key]
        total_stats['files'] += 1

        if i % 500 == 0:
            print(f"  [{i}/{len(label_files)}] {total_stats}")

    print(f"\n✅ Results for {data_dir.name}/:")
    print(f"   Files: {total_stats['files']}")
    print(f"   Success: {total_stats['success']}")
    print(f"   Skipped: {total_stats['skipped']}")
    print(f"   Failed: {total_stats['failed']}")

    if total_stats['failed'] > 0:
        total = total_stats['success'] + total_stats['failed']
        fail_rate = (total_stats['failed'] * 100 / total) if total > 0 else 0
        print(f"   Failure rate: {fail_rate:.2f}%")

    return total_stats


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Add s_span and e_span to Task 3 labels')
    parser.add_argument('--task3-dir', type=Path,
                       default=Path('/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3'),
                       help='Task3 root directory')
    parser.add_argument('--dry-run', action='store_true', help='Test without saving')
    parser.add_argument('--limit', type=int, default=-1, help='Limit files per directory')
    parser.add_argument('--subdirs', nargs='+',
                       default=['train', 'val', 'test_gold_500'],
                       help='Subdirectories to process')

    args = parser.parse_args()

    if not args.task3_dir.exists():
        print(f"❌ Directory not found: {args.task3_dir}")
        exit(1)

    print("=" * 60)
    print("🚀 ADDING SPAN POSITIONS TO TASK 3 DATA")
    print("=" * 60)
    print(f"Root: {args.task3_dir}")
    print(f"Subdirs: {args.subdirs}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    grand_total = {'success': 0, 'failed': 0, 'skipped': 0, 'files': 0}

    for subdir_name in args.subdirs:
        subdir = args.task3_dir / subdir_name
        if not subdir.exists():
            print(f"⚠️  Skipping {subdir_name}/ (not found)")
            continue

        stats = process_directory(subdir, dry_run=args.dry_run, limit=args.limit)

        for key in stats:
            grand_total[key] += stats[key]

    print("\n" + "=" * 60)
    print("🎉 GRAND TOTAL:")
    print("=" * 60)
    print(f"Files: {grand_total['files']}")
    print(f"✅ Success: {grand_total['success']}")
    print(f"⏭️  Skipped: {grand_total['skipped']}")
    print(f"❌ Failed: {grand_total['failed']}")

    if grand_total['failed'] > 0:
        total = grand_total['success'] + grand_total['failed']
        fail_rate = (grand_total['failed'] * 100 / total) if total > 0 else 0
        print(f"\n⚠️  Overall failure rate: {fail_rate:.2f}%")
    else:
        print("\n✨ Perfect! All spans mapped successfully!")
