#!/usr/bin/env python3
"""
Run full 2000 papers with NEW LOGIC (sentence_utils.py with 5 patterns)
Output: ../data_outputs/task1a_v2_full/
"""
import os
import sys
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
from citation_style_detector import detect_style
import APA_style_v2
import IEEE_style_v2

# ==========================================
# CONFIG
# ==========================================
OUTPUT_DIR = "../data_outputs/task1a_v2_full"
SENTENCES_PER_FILE = 5
GROBID_URL = "http://localhost:8070"
PAPERS_DIR = "../papers"
NUM_WORKERS = 4  # Parallel workers
# ==========================================

def rename_files_with_global_index(pdf_output_dir, global_index):
    """Rename 000.in/label -> XXX.in/label with global index"""
    files = sorted(Path(pdf_output_dir).glob("*.in"))

    new_index = global_index
    for file in files:
        if not file.stem.isdigit():
            continue

        new_name = f"{new_index:03d}.in"
        new_path = file.parent / new_name
        file.rename(new_path)

        old_label = file.with_suffix(".label")
        if old_label.exists():
            new_label = file.parent / f"{new_index:03d}.label"
            old_label.rename(new_label)

        new_index += 1

    return new_index

def process_single_pdf(args):
    """Process a single PDF file - worker function for parallel processing"""
    pdf_path, output_dir, sentences_per_file, grobid_url, starting_index, paper_index = args

    try:
        if not os.path.exists(pdf_path):
            return False, starting_index, f"PDF not found: {pdf_path}"

        # Create subfolder for this PDF
        pdf_name = Path(pdf_path).stem
        folder_name = f"{paper_index:03d}_{pdf_name}"
        pdf_output_dir = os.path.join(output_dir, folder_name)
        os.makedirs(pdf_output_dir, exist_ok=True)

        print(f"[{paper_index:03d}] Processing: {pdf_name}")

        # Detect style
        style, cleaned_text, sentences = detect_style(pdf_path)

        # Route to v2 pipelines
        if style == "IEEE/Numeric":
            IEEE_style_v2.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)
        else:
            APA_style_v2.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)

        # Rename files with global index
        next_index = rename_files_with_global_index(pdf_output_dir, starting_index)

        return True, next_index, f"Success: {pdf_name}"

    except Exception as e:
        return False, starting_index, f"Error: {pdf_path} - {str(e)}"

def main():
    if not os.path.exists(PAPERS_DIR):
        print(f"❌ Directory '{PAPERS_DIR}' not found.")
        return

    pdf_files = sorted(Path(PAPERS_DIR).glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in '{PAPERS_DIR}'")
        return

    print(f"\n{'='*80}")
    print(f"🚀 RUNNING FULL 2000 PAPERS WITH NEW LOGIC (sentence_utils.py)")
    print(f"{'='*80}")
    print(f"📁 Papers directory: {PAPERS_DIR}")
    print(f"📊 Papers to process: {len(pdf_files)}")
    print(f"👥 Parallel workers: {NUM_WORKERS}")
    print(f"📂 Output: {OUTPUT_DIR}")
    print(f"🔧 Logic: APA_style_v2.py + IEEE_style_v2.py + sentence_utils.py (5 patterns)")
    print(f"{'='*80}\n")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Prepare arguments for each paper
    tasks = []
    index_step = 200  # Reserve 200 indices per paper
    for paper_idx, pdf_file in enumerate(pdf_files, start=1):
        starting_index = (paper_idx - 1) * index_step
        tasks.append((
            str(pdf_file),
            OUTPUT_DIR,
            SENTENCES_PER_FILE,
            GROBID_URL,
            starting_index,
            paper_idx
        ))

    # Process in parallel
    start_time = time.time()

    with Pool(processes=NUM_WORKERS) as pool:
        results = pool.map(process_single_pdf, tasks)

    elapsed_time = time.time() - start_time

    # Collect results
    success_count = sum(1 for success, _, _ in results if success)
    failed_count = len(results) - success_count

    print(f"\n{'='*80}")
    print(f"📊 FINAL SUMMARY - FULL 2000 PAPERS")
    print(f"{'='*80}")
    print(f"⏱️  Total time: {elapsed_time/3600:.1f} hours ({elapsed_time/60:.0f} minutes)")
    print(f"✅ Success: {success_count}/{len(pdf_files)}")
    print(f"❌ Failed: {failed_count}/{len(pdf_files)}")
    print(f"⚡ Speed: {elapsed_time/len(pdf_files):.1f} seconds/paper")
    print(f"📂 Output: {OUTPUT_DIR}")
    print(f"{'='*80}\n")

    # Show failed papers if any
    if failed_count > 0:
        print("\n⚠️  Failed papers:")
        for success, _, msg in results:
            if not success:
                print(f"  - {msg}")

    # Next steps
    print("\n📝 NEXT STEPS:")
    print(f"  1. Compare results: python3 compare_results.py ../data_outputs/task1a {OUTPUT_DIR}")
    print(f"  2. If OK, delete old: rm -rf ../data_outputs/task1a")
    print(f"  3. Rename: mv {OUTPUT_DIR} ../data_outputs/task1a")
    print()

    return success_count, failed_count, elapsed_time

if __name__ == "__main__":
    main()
