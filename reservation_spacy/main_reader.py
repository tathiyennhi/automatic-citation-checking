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
    # print(all_text)
    return all_text

# def get_references_section(text):
#     """
#     Tìm và trích xuất phần 'References' từ văn bản.
#     """
#     match = re.search(r'\b[Rr]eferences\b[:\-—]?', text)
#     if match:
#         start = match.end()
#         references_text = text[start:]
#         print(references_text.strip())
#         return references_text.strip()
#     else:
#         return None

def get_references_section(text):
    """
    Tìm và trích xuất phần 'References' từ văn bản và loại bỏ những dòng chỉ chứa từ không có ký tự đặc biệt.
    """
    match = re.search(r'\b[Rr]eferences\b[:\-—]?', text)
    if match:
        start = match.end()
        references_text = text[start:]
        
        # Tách văn bản thành các dòng
        lines = references_text.strip().split('\n')
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue  # Bỏ qua dòng trống
            # Kiểm tra xem dòng có chứa ký tự đặc biệt (không phải chữ, số, khoảng trắng) không
            if re.search(r'[^\w\s]', line):
                processed_lines.append(line)
        
        # Ghép lại các dòng đã xử lý
        processed_references_text = '\n'.join(processed_lines)
        # print(processed_references_text)
        return processed_references_text
    else:
        return None


# def fix_broken_urls(text):
#     """
#     Sửa các URL bị đứt đoạn trong văn bản.
#     """
#     url_patterns = [
#         # DOI pattern (improved to handle spaces)
#         (r'https?:\s*//\s*d\s*o\s*i\s*\.?\s*o?\s*r?\s*g?\s*/\s*1\s*0\s*\.\s*\d{4,9}\s*/\s*[^\s]+(?:\s+[^\s]+)*', r'https://doi.org/'),
#         # Regular URL pattern
#         (r'https?://(?:[^\s]+(?:\s+[^\s]+)*)', r'https://'),
#     ]

#     fixed_text = text
#     for pattern, prefix in url_patterns:
#         matches = re.finditer(pattern, fixed_text, re.IGNORECASE)
#         for match in matches:
#             url = match.group(0)
#             cleaned_url = re.sub(r'\s+', '', url)
#             cleaned_url = re.sub(r'[\(\)]', '', cleaned_url)
#             fixed_text = fixed_text.replace(url, cleaned_url)
    
#     return fixed_text
def fix_broken_urls(text):
    """
    Sửa các URL và DOI bị đứt đoạn trong văn bản.
    """
    # Pattern để tìm DOI có thể chứa khoảng trắng
    doi_pattern = re.compile(r'10\.\s*\d{4,9}\s*/\s*(?:[^\s]+(?:\s+[^\s]+)*)', re.IGNORECASE)
    # Pattern để tìm URL có thể chứa khoảng trắng
    url_pattern = re.compile(r'https?://(?:[^\s]+(?:\s+[^\s]+)*)', re.IGNORECASE)

    # Hàm thay thế DOI
    def replace_doi(match):
        doi = match.group(0)
        cleaned_doi = re.sub(r'\s+', '', doi)  # Loại bỏ khoảng trắng
        return 'https://doi.org/' + cleaned_doi

    # Hàm thay thế URL
    def replace_url(match):
        url = match.group(0)
        cleaned_url = re.sub(r'\s+', '', url)  # Loại bỏ khoảng trắng
        return cleaned_url

    # Sửa DOI trước
    text = doi_pattern.sub(replace_doi, text)
    # Sau đó sửa URL
    text = url_pattern.sub(replace_url, text)

    return text


def is_valid_reference_line(line):
    """
    Kiểm tra xem dòng có phải là tham khảo hợp lệ hay không.
    """
    # Bỏ qua dòng chỉ chứa số hoặc ký tự không phải là chữ cái
    if re.match(r'^\d+\s*$', line):
        return False
    return True

def reconstruct_references(text):
    """
    Tái cấu trúc các tham khảo và sửa URLs.
    """
    lines = text.split('\n')
    reconstructed = []
    current_ref = ""

    author_pattern = re.compile(r'^[A-Z][a-zA-Z\-\'\.]+\s*,\s*[A-Z]\.')

    for line in lines:
        line = line.strip()
        
        # Bỏ qua dòng không hợp lệ (chỉ chứa số)
        if not is_valid_reference_line(line):
            continue
        
        if author_pattern.match(line):
            if current_ref:
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
    reference = re.sub(r'\s+\d+$', '', reference)
    reference = re.sub(r'\.(?=\s|$)', '', reference)
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
    text = extract_text_from_pdf(pdf_path)
    
    references_section = get_references_section(text)
    if not references_section:
        print("Không tìm thấy phần 'References' trong tài liệu.")
        return
    
    references = reconstruct_references(references_section)
    
    cleaned_references = [clean_reference(ref) for ref in references]
    
    save_to_docx(cleaned_references, docx_path)
    
    print(f"Nội dung 'References' đã được lưu vào {docx_path}")

if __name__ == "__main__":
    pdf_path = 'paper.pdf'
    docx_path = 'references.docx'
    extract_references_from_pdf(pdf_path, docx_path)
