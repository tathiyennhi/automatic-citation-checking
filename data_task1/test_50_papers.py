#!/usr/bin/env python3
"""
Test logic mới với 50-100 papers (parallel processing)
Output: data_outputs/task1a_test50/
"""
import os
import sys
import argparse
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
from citation_style_detector import detect_style
import APA_style_v2
import IEEE_style_v2

# ==========================================
# CONFIG
# ==========================================
OUTPUT_DIR = "../data_outputs/task1a_test50"
SENTENCES_PER_FILE = 5
GROBID_URL = "http://localhost:8070"
PAPERS_DIR = "../papers"
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

def process_batch_parallel(papers_dir, output_dir, sentences_per_file, grobid_url, num_papers, num_workers):
    """Process PDFs in parallel"""
    if not os.path.exists(papers_dir):
        print(f"❌ Directory '{papers_dir}' not found.")
        return

    pdf_files = sorted(Path(papers_dir).glob("*.pdf"))[:num_papers]

    if not pdf_files:
        print(f"❌ No PDF files found in '{papers_dir}'")
        return

    print(f"\n{'='*70}")
    print(f"🚀 TESTING NEW LOGIC WITH PARALLEL PROCESSING")
    print(f"{'='*70}")
    print(f"📁 Papers directory: {papers_dir}")
    print(f"📊 Papers to process: {len(pdf_files)}")
    print(f"👥 Parallel workers: {num_workers}")
    print(f"📂 Output: {output_dir}")
    print(f"{'='*70}\n")

    # Prepare arguments for each paper
    # Note: We need to distribute global_index properly for parallel processing
    # For simplicity, we'll reserve index ranges for each paper
    tasks = []
    index_step = 200  # Reserve 200 indices per paper (should be enough)
    for paper_idx, pdf_file in enumerate(pdf_files, start=1):
        starting_index = (paper_idx - 1) * index_step
        tasks.append((
            str(pdf_file),
            output_dir,
            sentences_per_file,
            grobid_url,
            starting_index,
            paper_idx
        ))

    # Process in parallel
    start_time = time.time()

    with Pool(processes=num_workers) as pool:
        results = pool.map(process_single_pdf, tasks)

    elapsed_time = time.time() - start_time

    # Collect results
    success_count = sum(1 for success, _, _ in results if success)
    failed_count = len(results) - success_count

    print(f"\n{'='*70}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*70}")
    print(f"⏱️  Time elapsed: {elapsed_time/60:.1f} minutes ({elapsed_time:.0f} seconds)")
    print(f"✅ Success: {success_count}/{len(pdf_files)}")
    print(f"❌ Failed: {failed_count}/{len(pdf_files)}")
    print(f"⚡ Speed: {elapsed_time/len(pdf_files):.1f} seconds/paper")
    print(f"📂 Output: {output_dir}")
    print(f"{'='*70}\n")

    # Show failed papers if any
    if failed_count > 0:
        print("\n⚠️  Failed papers:")
        for success, _, msg in results:
            if not success:
                print(f"  - {msg}")

    return success_count, failed_count, elapsed_time

def main():
    parser = argparse.ArgumentParser(description="Test new logic with 50-100 papers (parallel)")
    parser.add_argument("-n", "--num-papers", type=int, default=50,
                       help="Number of papers to test (default: 50)")
    parser.add_argument("-w", "--workers", type=int, default=min(4, cpu_count()),
                       help=f"Number of parallel workers (default: {min(4, cpu_count())})")
    args = parser.parse_args()

    if args.workers > cpu_count():
        print(f"⚠️  Warning: {args.workers} workers requested but only {cpu_count()} CPUs available")

    process_batch_parallel(
        PAPERS_DIR,
        OUTPUT_DIR,
        SENTENCES_PER_FILE,
        GROBID_URL,
        args.num_papers,
        args.workers
    )

if __name__ == "__main__":
    main()
