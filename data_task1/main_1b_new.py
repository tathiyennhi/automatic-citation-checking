# main_1b.py
# Router for Task 1b: PDF -> TEI -> (APA|IEEE) -> citation_XXX.in/.label
# Prioritize automatic detection if citation_style_detector.detect_style module is available
# Can force style via --style {APA, IEEE}

import os
import argparse
from pathlib import Path

# optional detect
def try_detect_style(pdf_path: str) -> str:
    try:
        from citation_style_detector import detect_style
        style, cleaned_text, sentences = detect_style(pdf_path)
        # normalize
        if isinstance(style, str) and style.lower().startswith("ieee"):
            return "IEEE"
        return "APA"
    except Exception:
        return "APA"

def process_single_pdf(pdf_path: str, output_dir: str, grobid_url: str, style: str):
    if not os.path.exists(pdf_path):
        print(f"❌ PDF '{pdf_path}' not found.")
        return False

    pdf_name = Path(pdf_path).stem
    pdf_output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(pdf_output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"📄 Processing: {pdf_path}")
    print(f"📁 Output: {pdf_output_dir}")
    print(f"🔎 Style: {style}")
    print(f"{'='*60}")

    if style.upper() == "IEEE":
        import IEEE_style_1b as runner
    else:
        import APA_style_1b as runner

    runner.run(pdf_path, pdf_output_dir, grobid_url)
    print(f"✅ Complete: {pdf_path}\n")
    return True

def process_batch(papers_dir: str, output_dir: str, grobid_url: str, style_arg: str):
    if not os.path.exists(papers_dir):
        print(f"❌ Directory '{papers_dir}' not found.")
        return
    pdf_files = sorted(Path(papers_dir).glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in '{papers_dir}'")
        return

    print(f"\n{'='*60}")
    print(f"🚀 BATCH 1b")
    print(f"📁 Directory: {papers_dir}")
    print(f"📊 Found {len(pdf_files)} PDF(s)")
    print(f"{'='*60}")

    success = 0
    failed = 0
    for pdf_file in pdf_files:
        style = style_arg.upper() if style_arg else try_detect_style(str(pdf_file))
        ok = process_single_pdf(str(pdf_file), output_dir, grobid_url, style)
        success += int(ok)
        failed += int(not ok)

    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"✅ Success: {success}")
    print(f"❌ Failed: {failed}")
    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description="Task 1b generator (TEI-first)")
    parser.add_argument("--single", type=str, help="Process a single PDF file")
    parser.add_argument("--papers_dir", type=str, default="papers", help="Directory of PDFs for batch")
    parser.add_argument("--out", type=str, default="task1b_output", help="Output root directory")
    parser.add_argument("--grobid", type=str, default="http://localhost:8070", help="GROBID endpoint")
    parser.add_argument("--style", type=str, choices=["APA","IEEE"], help="Force style (override detection)")
    args = parser.parse_args()

    output_dir = args.out
    grobid_url = args.grobid

    if args.single:
        style = args.style.upper() if args.style else try_detect_style(args.single)
        process_single_pdf(args.single, output_dir, grobid_url, style)
    else:
        process_batch(args.papers_dir, output_dir, grobid_url, args.style)

if __name__ == "__main__":
    main()