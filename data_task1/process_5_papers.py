#!/usr/bin/env python3
"""
Process first 5 papers from manifest for task 1a
"""
import json
import os
import sys
import re
from pathlib import Path

# Import processing functions
from citation_style_detector import detect_style
import APA_style
import IEEE_style

# ==========================================
# CONFIG
# ==========================================
OUTPUT_DIR = "../data_outputs/task1a"
SENTENCES_PER_FILE = 5
GROBID_URL = "http://localhost:8070"
MANIFEST_PATH = "../papers/manifest.jsonl"
PAPERS_DIR = "../papers"
NUM_PAPERS = 5
# ==========================================


def sanitize_filename(title: str) -> str:
    """Create filename from title"""
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", title)[:120]
    return name


def find_pdf_file(papers_dir: Path, title: str, hash_value: str) -> Path:
    """Find PDF file based on title or hash"""
    # Try sanitized title
    sanitized = sanitize_filename(title)
    pdf_path = papers_dir / f"{sanitized}.pdf"
    if pdf_path.exists():
        return pdf_path

    # Try hash-based name
    hash_path = papers_dir / f"{hash_value[:16]}.pdf"
    if hash_path.exists():
        return hash_path

    # Search for partial match
    for pdf_file in papers_dir.glob("*.pdf"):
        if sanitized[:50] in pdf_file.stem or title[:30].lower() in pdf_file.stem.lower():
            return pdf_file

    return None


def rename_files_with_global_index(pdf_output_dir, global_index):
    """Rename data_000.in/label -> data_XXX.in/label with global index"""
    files = sorted(Path(pdf_output_dir).glob("data_*.in"))

    new_index = global_index
    for file in files:
        # Rename .in file
        new_name = f"data_{new_index:03d}.in"
        new_path = file.parent / new_name
        file.rename(new_path)

        # Rename corresponding .label file
        old_label = file.with_suffix(".label")
        if old_label.exists():
            new_label = file.parent / f"data_{new_index:03d}.label"
            old_label.rename(new_label)

        new_index += 1

    return new_index


def process_single_pdf(pdf_path, output_dir, sentences_per_file, grobid_url, starting_index, paper_index):
    """Process a single PDF file"""
    if not os.path.exists(pdf_path):
        print(f"❌ PDF '{pdf_path}' not found.")
        return False, starting_index

    # Create subfolder for this PDF
    pdf_name = Path(pdf_path).stem
    folder_name = f"{paper_index:03d}_{pdf_name}"
    pdf_output_dir = os.path.join(output_dir, folder_name)
    os.makedirs(pdf_output_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"📄 Processing: {pdf_path}")
    print(f"📁 Output: {pdf_output_dir}")
    print(f"{'='*70}")

    try:
        # Detect style
        style, cleaned_text, sentences = detect_style(pdf_path)
        print(f"✅ Citation Style: {style}")
        print(f"📝 Found {len(sentences)} sentences")

        # Route to appropriate pipeline
        if style == "IEEE/Numeric":
            IEEE_style.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)
        else:
            APA_style.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)

        # Rename files with global index
        next_index = rename_files_with_global_index(pdf_output_dir, starting_index)

        print(f"✅ Complete: {pdf_path}")
        print(f"📊 Generated files: data_{starting_index:03d} to data_{next_index-1:03d}")
        return True, next_index

    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {e}")
        import traceback
        traceback.print_exc()
        return False, starting_index


def main():
    print("=" * 70)
    print("PROCESSING FIRST 5 PAPERS FROM MANIFEST - TASK 1A")
    print("=" * 70)

    # Read first 5 papers from manifest
    manifest_path = Path(MANIFEST_PATH)
    papers_dir = Path(PAPERS_DIR)
    output_dir = OUTPUT_DIR

    if not manifest_path.exists():
        print(f"❌ Manifest not found: {manifest_path}")
        return

    print(f"\n📖 Reading manifest: {manifest_path}")
    papers = []
    with open(manifest_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= NUM_PAPERS:
                break
            papers.append(json.loads(line))

    print(f"✅ Loaded {len(papers)} papers from manifest")
    print(f"📁 Papers directory: {papers_dir}")
    print(f"📂 Output directory: {output_dir}")
    print(f"🔧 GROBID URL: {GROBID_URL}")

    # Process each paper
    success_count = 0
    failed_count = 0
    not_found_count = 0
    global_index = 0

    for idx, paper in enumerate(papers, start=1):
        print(f"\n{'='*70}")
        print(f"Paper {idx}/{len(papers)}")
        print(f"Title: {paper['title'][:60]}...")
        print(f"DOI: {paper.get('doi', 'N/A')}")
        print(f"{'='*70}")

        # Find PDF file
        pdf_path = find_pdf_file(papers_dir, paper['title'], paper['hash'])

        if not pdf_path:
            print(f"⚠️  PDF not found for: {paper['title']}")
            not_found_count += 1
            continue

        print(f"✓ Found PDF: {pdf_path.name}")

        # Process PDF
        try:
            success, global_index = process_single_pdf(
                str(pdf_path),
                output_dir,
                SENTENCES_PER_FILE,
                GROBID_URL,
                global_index,
                paper_index=idx
            )
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ Error processing paper {idx}: {e}")
            failed_count += 1

    # Print summary
    print(f"\n{'='*70}")
    print("PROCESSING SUMMARY")
    print(f"{'='*70}")
    print(f"Total papers: {len(papers)}")
    print(f"✅ Successfully processed: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️  PDF not found: {not_found_count}")
    print(f"📄 Total data files generated: {global_index}")
    print(f"📂 Output location: {output_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
