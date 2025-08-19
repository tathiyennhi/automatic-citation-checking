"""
PDF Extractor - Lấy từ Abstract đến hết (bao gồm References)
"""

import pdf2image
import pytesseract
import re

def extract_full_pdf(pdf_path, output_path=None):
    """
    Trích xuất từ Abstract/Introduction đến hết document
    """
    print(f"Processing {pdf_path}...")
    
    # Convert PDF to images
    images = pdf2image.convert_from_path(pdf_path, dpi=300)
    
    # Extract text from all pages
    full_text = ""
    for i, image in enumerate(images):
        print(f"Page {i+1}/{len(images)}")
        text = pytesseract.image_to_string(image, lang='eng')
        full_text += text + "\n\n"
    
    # Find where main content starts (Abstract/Introduction)
    start_patterns = [
        r'\bABSTRACT\b',
        r'\bAbstract\b', 
        r'\bINTRODUCTION\b',
        r'\bIntroduction\b',
        r'^1\.\s*Introduction',
    ]
    
    start_pos = 0
    for pattern in start_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
        if match:
            start_pos = match.start()
            print(f"✅ Found start point: '{match.group()}' at position {start_pos}")
            break
    
    if start_pos == 0:
        print("⚠️ No Abstract/Introduction found, taking from beginning")
    
    # Take from start point to END (including all References)
    extracted = full_text[start_pos:]
    
    # Clean text
    extracted = re.sub(r'\n\s*\n\s*\n', '\n\n', extracted)
    extracted = re.sub(r' +', ' ', extracted)
    extracted = extracted.strip()
    
    # Save to file
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(extracted)
        print(f"✅ Saved to {output_path}")
    
    print(f"📏 Extracted {len(extracted):,} characters")
    
    # Check if References section exists
    if re.search(r'References?|Bibliography', extracted, re.IGNORECASE):
        print("✅ References section included")
    else:
        print("⚠️ No References section found")
    
    return extracted

if __name__ == "__main__":
    # Extract everything from Abstract to end
    text = extract_full_pdf("paper.pdf", "full_output.txt")
    
    print("\nPreview of last 500 characters:")
    print("-" * 60)
    print(text[-500:])