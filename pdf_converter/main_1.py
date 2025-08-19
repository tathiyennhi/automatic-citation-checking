import fitz  # PyMuPDF
import re

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Trích xuất toàn bộ văn bản từ tệp PDF.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text

def detect_reference_heading(text: str) -> int:
    """
    Tìm chỉ số dòng bắt đầu phần Tài liệu tham khảo (References).
    Hợp lệ nếu dòng có độ dài ngắn, in hoa, chứa 'REFERENCES', 'BIBLIOGRAPHY', 'LITERATURE'.
    """
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if (
            len(line_clean) <= 30
            and line_clean.isupper()
            and re.search(r'\b(REFERENCES|BIBLIOGRAPHY|LITERATURE)\b', line_clean)
        ):
            return idx
    return -1

def extract_text_before_references(text: str) -> str:
    """
    Lấy phần văn bản trước mục References nếu tìm thấy.
    """
    lines = text.splitlines()
    ref_idx = detect_reference_heading(text)
    if ref_idx != -1:
        return "\n".join(lines[:ref_idx])
    return text

def fix_hyphen_linebreaks(text: str) -> str:
    """
    Gộp các từ bị chia tách bằng dấu '-' và xuống dòng (ví dụ: compre-\nhensive → comprehensive).
    """
    return re.sub(r'-\s*\n\s*', '', text)

def clean_pdf_text(pdf_path: str) -> str:
    """
    Pipeline xử lý văn bản PDF:
    - Trích xuất nội dung
    - Cắt bỏ phần References
    - Gộp các từ bị ngắt dòng do '-'
    """
    raw_text = extract_text_from_pdf(pdf_path)
    before_ref = extract_text_before_references(raw_text)
    cleaned = fix_hyphen_linebreaks(before_ref)
    return cleaned

def main():
    # Chỉnh đường dẫn ở đây nếu muốn test
    pdf_path = "paper.pdf"
    cleaned_text = clean_pdf_text(pdf_path)

    # Lưu ra file nếu cần
    with open("output_cleaned.txt", "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    print("✅ Done. Cleaned text saved to output_cleaned.txt")

if __name__ == "__main__":
    main()
