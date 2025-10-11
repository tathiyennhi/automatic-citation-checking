# main.py
import os
from citation_style_detector import detect_style
import APA_style
import IEEE_style

# ==========================================
# CONFIG
# ==========================================
PDF_PATH = "967.pdf"
OUTPUT_DIR = "output"
SENTENCES_PER_FILE = 5
GROBID_URL = "http://localhost:8070"
# ==========================================

def main():
    pdf_path = PDF_PATH
    output_dir = OUTPUT_DIR
    sentences_per_file = SENTENCES_PER_FILE
    grobid_url = GROBID_URL

    if not os.path.exists(pdf_path):
        print(f"❌ PDF '{pdf_path}' not found.")
        print("Please make sure the PDF file exists in the current directory.")
        return

    print("="*60)
    print("🚀 CITATION STYLE DETECTION & PROCESSING")
    print("="*60)
    print(f"📄 PDF: {pdf_path}")
    print(f"📁 Output: {output_dir}")
    print(f"📊 Sentences per file: {sentences_per_file}")
    print(f"🌐 Grobid URL: {grobid_url}")
    print("="*60)

    # 1) Detect style once
    print("\n[Step 1] Detecting citation style...")
    style, cleaned_text, sentences = detect_style(pdf_path)
    print(f"✅ Dominant style detected: {style}")

    # 2) Route to the appropriate pipeline
    print(f"\n[Step 2] Processing with {style} pipeline...\n")
    
    if style == "IEEE/Numeric":
        IEEE_style.run(pdf_path, output_dir, sentences_per_file, grobid_url)
    else:
        # Default to APA (works for APA and Unknown/Mixed)
        APA_style.run(pdf_path, output_dir, sentences_per_file, grobid_url)
    
    print("\n" + "="*60)
    print("✅ PROCESSING COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    main()