#!/usr/bin/env python3
"""
Test new sentence splitting logic with first 20 papers
Output to: data_outputs/task1a_new_logic
"""
import os
import argparse
from pathlib import Path
from citation_style_detector import detect_style
import APA_style_v2
import IEEE_style_v2

# ==========================================
# CONFIG
# ==========================================
OUTPUT_DIR = "../data_outputs/task1a_new_logic"
SENTENCES_PER_FILE = 5
GROBID_URL = "http://localhost:8070"
PAPERS_DIR = "../papers"
NUM_TEST_PAPERS = 20  # Test first 20 papers
# ==========================================

def rename_files_with_global_index(pdf_output_dir, global_index):
    """Rename 000.in/label -> XXX.in/label with global index"""
    files = sorted(Path(pdf_output_dir).glob("*.in"))

    new_index = global_index
    for file in files:
        # Skip non-numeric files
        if not file.stem.isdigit():
            continue

        # Rename .in file
        new_name = f"{new_index:03d}.in"
        new_path = file.parent / new_name
        file.rename(new_path)

        # Rename corresponding .label file
        old_label = file.with_suffix(".label")
        if old_label.exists():
            new_label = file.parent / f"{new_index:03d}.label"
            old_label.rename(new_label)

        new_index += 1

    return new_index

def process_single_pdf(pdf_path, output_dir, sentences_per_file, grobid_url, starting_index=0, paper_index=None):
    """Process a single PDF file with NEW logic"""
    if not os.path.exists(pdf_path):
        print(f"❌ PDF '{pdf_path}' not found.")
        return False, starting_index

    # Create subfolder for this PDF
    pdf_name = Path(pdf_path).stem
    if paper_index is not None:
        folder_name = f"{paper_index:03d}_{pdf_name}"
    else:
        folder_name = pdf_name
    pdf_output_dir = os.path.join(output_dir, folder_name)
    os.makedirs(pdf_output_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"📄 Processing: {pdf_path}")
    print(f"📁 Output: {pdf_output_dir}")
    print(f"{'='*70}")

    # Detect style
    style, cleaned_text, sentences = detect_style(pdf_path)
    print(f"✅ Citation Style: {style}")

    # Route to NEW v2 pipelines
    if style == "IEEE/Numeric":
        IEEE_style_v2.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)
    else:
        APA_style_v2.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)

    # Rename files with global index
    next_index = rename_files_with_global_index(pdf_output_dir, starting_index)

    print(f"✅ Complete: {pdf_path} (files {starting_index:03d}-{next_index-1:03d})\n")
    return True, next_index

def process_batch(papers_dir, output_dir, sentences_per_file, grobid_url, num_papers):
    """Process first N PDF files in a directory"""
    if not os.path.exists(papers_dir):
        print(f"❌ Directory '{papers_dir}' not found.")
        return

    pdf_files = sorted(Path(papers_dir).glob("*.pdf"))[:num_papers]

    if not pdf_files:
        print(f"❌ No PDF files found in '{papers_dir}'")
        return

    print(f"\n{'='*70}")
    print(f"🚀 TESTING NEW SENTENCE SPLITTING LOGIC")
    print(f"{'='*70}")
    print(f"📁 Directory: {papers_dir}")
    print(f"📊 Testing first {num_papers} papers (found {len(pdf_files)})")
    print(f"📂 Output: {output_dir}")
    print(f"{'='*70}")

    success_count = 0
    failed_count = 0
    global_index = 0

    for paper_idx, pdf_file in enumerate(pdf_files, start=1):
        try:
            success, global_index = process_single_pdf(
                str(pdf_file), output_dir, sentences_per_file, grobid_url, global_index, paper_index=paper_idx
            )
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ Error processing {pdf_file}: {e}\n")
            import traceback
            traceback.print_exc()
            failed_count += 1

    print(f"\n{'='*70}")
    print(f"📊 TEST SUMMARY (NEW LOGIC)")
    print(f"{'='*70}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📄 Total files generated: {global_index}")
    print(f"📂 Output: {output_dir}")
    print(f"{'='*70}")
    print(f"\nNext: Compare with old logic in data_outputs/task1a/")

def main():
    parser = argparse.ArgumentParser(description="Test new sentence splitting logic")
    parser.add_argument("-n", "--num-papers", type=int, default=NUM_TEST_PAPERS,
                       help="Number of papers to test")
    args = parser.parse_args()

    output_dir = OUTPUT_DIR
    sentences_per_file = SENTENCES_PER_FILE
    grobid_url = GROBID_URL

    process_batch(PAPERS_DIR, output_dir, sentences_per_file, grobid_url, args.num_papers)

if __name__ == "__main__":
    main()
