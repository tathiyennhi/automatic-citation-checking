import re
import pdfplumber
from docx import Document
import spacy

# Khởi tạo spaCy
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_path):
    """
    Trích xuất văn bản từ file PDF sử dụng pdfplumber.
    """
    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
    return all_text

def get_references_section(text):
    """
    Tìm và trích xuất phần 'References' từ văn bản.
    """
    match = re.search(r'\b[Rr]eferences\b[:\-—]?', text)
    if match:
        start = match.end()
        references_text = text[start:]
        return references_text.strip()
    else:
        return None

def fix_broken_urls(text):
    """
    Sửa các URL bị đứt đoạn trong văn bản.
    """
    # Pattern để nhận diện URL bị đứt đoạn
    url_patterns = [
        # DOI pattern
        (r'https?:\s*//\s*doi\s*\.\s*org\s*/\s*10\.\d{4,9}/[^\s]+(?:\s+[^\s]+)*', r'https://doi.org/'),
        # Regular URL pattern
        (r'https?://(?:[^\s]+(?:\s+[^\s]+)*)', r'https://'),
    ]
    
    fixed_text = text
    
    for pattern, prefix in url_patterns:
        # Tìm tất cả các URL khớp với pattern
        matches = re.finditer(pattern, fixed_text, re.IGNORECASE)
        for match in matches:
            url = match.group(0)
            # Loại bỏ khoảng trắng và ký tự đặc biệt trong URL
            cleaned_url = re.sub(r'\s+', '', url)
            cleaned_url = re.sub(r'[\(\)]', '', cleaned_url)
            # Thay thế URL gốc bằng URL đã được làm sạch
            fixed_text = fixed_text.replace(url, cleaned_url)
    
    return fixed_text

def reconstruct_references(text):
    """
    Tái cấu trúc các tham khảo và sửa URLs.
    """
    lines = text.split('\n')
    reconstructed = []
    current_ref = ""
    
    # Pattern để nhận diện bắt đầu tham khảo
    author_pattern = re.compile(r'^[A-Z][a-zA-Z\-\'\.]+\s*,\s*[A-Z]\.')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if author_pattern.match(line):
            if current_ref:
                # Sửa URLs trước khi thêm vào danh sách
                fixed_ref = fix_broken_urls(current_ref.strip())
                reconstructed.append(fixed_ref)
            current_ref = line
        else:
            current_ref += ' ' + line
    
    if current_ref:
        fixed_ref = fix_broken_urls(current_ref.strip())
        reconstructed.append(fixed_ref)
    
    return reconstructed

def clean_reference(reference):
    """
    Làm sạch tham khảo bằng cách loại bỏ các ký tự không mong muốn.
    """
    # Loại bỏ số trang ở cuối
    reference = re.sub(r'\s+\d+$', '', reference)
    
    # Loại bỏ dấu chấm thừa trong URL
    reference = re.sub(r'\.(?=\s|$)', '', reference)
    
    # Loại bỏ khoảng trắng thừa
    reference = re.sub(r'\s+', ' ', reference)
    
    return reference.strip()

def save_to_docx(references, docx_path):
    """
    Lưu danh sách tham khảo vào file DOCX.
    """
    doc = Document()
    for ref in references:
        doc.add_paragraph(ref)
    doc.save(docx_path)

def extract_references_from_pdf(pdf_path, docx_path):
    """
    Trích xuất các tham khảo từ file PDF và lưu vào file DOCX.
    """
    # Trích xuất văn bản từ PDF
    text = extract_text_from_pdf(pdf_path)
    
    # Tìm phần References
    references_section = get_references_section(text)
    if not references_section:
        print("Không tìm thấy phần 'References' trong tài liệu.")
        return
    
    # Tái cấu trúc và sửa URLs
    references = reconstruct_references(references_section)
    
    # Làm sạch từng tham khảo
    cleaned_references = [clean_reference(ref) for ref in references]
    
    # Lưu vào file DOCX
    save_to_docx(cleaned_references, docx_path)
    
    print(f"Nội dung 'References' đã được lưu vào {docx_path}")

if __name__ == "__main__":
    pdf_path = 'paper.pdf'
    docx_path = 'references.docx'
    extract_references_from_pdf(pdf_path, docx_path)
