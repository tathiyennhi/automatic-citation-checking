# main.py
import os
import argparse
from pathlib import Path
from citation_style_detector import detect_style
import APA_style
import IEEE_style

# ==========================================
# CONFIG
# ==========================================
OUTPUT_DIR = "output"
SENTENCES_PER_FILE = 5
GROBID_URL = "http://localhost:8070"
PAPERS_DIR = "papers"
# ==========================================

def rename_files_with_global_index(pdf_output_dir, global_index):
    """Rename data_000.in/label -> data_XXX.in/label with global index"""
    files = sorted(Path(pdf_output_dir).glob("data_*.in"))
    
    new_index = global_index
    for file in files:
        old_base = file.stem  # data_000
        
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

def process_single_pdf(pdf_path, output_dir, sentences_per_file, grobid_url, starting_index=0):
    """Process a single PDF file"""
    if not os.path.exists(pdf_path):
        print(f"❌ PDF '{pdf_path}' not found.")
        return False, starting_index

    # Create subfolder for this PDF
    pdf_name = Path(pdf_path).stem
    pdf_output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(pdf_output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"📄 Processing: {pdf_path}")
    print(f"📁 Output: {pdf_output_dir}")
    print(f"{'='*60}")

    # Detect style
    style, cleaned_text, sentences = detect_style(pdf_path)
    print(f"✅ Style: {style}")

    # Route to appropriate pipeline
    if style == "IEEE/Numeric":
        IEEE_style.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)
    else:
        APA_style.run(pdf_path, pdf_output_dir, sentences_per_file, grobid_url)
    
    # Rename files with global index
    next_index = rename_files_with_global_index(pdf_output_dir, starting_index)
    
    print(f"✅ Complete: {pdf_path} (files {starting_index:03d}-{next_index-1:03d})\n")
    return True, next_index

def process_batch(papers_dir, output_dir, sentences_per_file, grobid_url):
    """Process all PDF files in a directory"""
    if not os.path.exists(papers_dir):
        print(f"❌ Directory '{papers_dir}' not found.")
        return

    pdf_files = sorted(Path(papers_dir).glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in '{papers_dir}'")
        return

    print(f"\n{'='*60}")
    print(f"🚀 BATCH PROCESSING MODE")
    print(f"{'='*60}")
    print(f"📁 Directory: {papers_dir}")
    print(f"📊 Found {len(pdf_files)} PDF file(s)")
    print(f"{'='*60}")

    success_count = 0
    failed_count = 0
    global_index = 0

    for pdf_file in pdf_files:
        try:
            success, global_index = process_single_pdf(
                str(pdf_file), output_dir, sentences_per_file, grobid_url, global_index
            )
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ Error processing {pdf_file}: {e}\n")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"📊 BATCH SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📄 Total files generated: {global_index}")
    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description="Citation Style Detection & Processing")
    parser.add_argument("-s", "--single", type=str, help="Process a single PDF file")
    args = parser.parse_args()

    output_dir = OUTPUT_DIR
    sentences_per_file = SENTENCES_PER_FILE
    grobid_url = GROBID_URL

    if args.single:
        process_single_pdf(args.single, output_dir, sentences_per_file, grobid_url)
    else:
        process_batch(PAPERS_DIR, output_dir, sentences_per_file, grobid_url)

if __name__ == "__main__":
    main()