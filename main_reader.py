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
    # Tìm vị trí bắt đầu của 'References'
    match = re.search(r'\b[Rr]eferences\b[:\-—]?', text)
    if match:
        start = match.end()
        references_text = text[start:]
        return references_text.strip()
    else:
        return None

def reconstruct_references(text):
    """
    Tái cấu trúc các tham khảo bằng cách kết hợp các dòng bị chia cắt thành một dòng duy nhất.
    """
    lines = text.split('\n')
    reconstructed = []
    current_ref = ""

    # Định nghĩa mẫu để nhận diện bắt đầu tham khảo (Tên tác giả)
    author_pattern = re.compile(r'^[A-Z][a-zA-Z\-\'\.]+\s*,\s*[A-Z]\.')

    for line in lines:
        line = line.strip()
        if not line:
            continue  # Bỏ qua các dòng trống
        if author_pattern.match(line):
            if current_ref:
                reconstructed.append(current_ref.strip())
            current_ref = line
        else:
            current_ref += ' ' + line
    if current_ref:
        reconstructed.append(current_ref.strip())
    return reconstructed

def fix_urls(reference):
    """
    Sửa các URL trong một tham khảo bằng cách loại bỏ dấu cách bên trong URL.
    """
    # Sửa DOI URLs
    # doi_pattern = re.compile(r'https?:\s*//\s*doi\s*\.\s*org\s*/\s*10\.\d{4,9}/\S+', re.IGNORECASE)
    # reference = doi_pattern.sub(lambda x: ''.join(x.group(0).split()), reference)
    
    # Sửa các URL thông thường (không phải DOI)
    # url_pattern = re.compile(r'https?://(?!doi\.org)\S+', re.IGNORECASE)
    # reference = url_pattern.sub(lambda x: ''.join(x.group(0).split()), reference)
    
    return reference

def remove_trailing_numbers(references):
    """
    Loại bỏ các số trang dư thừa như '13' ở cuối tham khảo.
    """
    cleaned_references = []
    trailing_number_pattern = re.compile(r'\s+\d+$')

    for ref in references:
        ref = trailing_number_pattern.sub('', ref)
        cleaned_references.append(ref)
    return cleaned_references

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
    # Bước 1: Trích xuất văn bản từ PDF
    text = extract_text_from_pdf(pdf_path)
    
    # Bước 2: Tìm phần 'References'
    references_section = get_references_section(text)
    
    if not references_section:
        print("Không tìm thấy phần 'References' trong tài liệu.")
        return
    
    # Bước 3: Tái cấu trúc các tham khảo
    references = reconstruct_references(references_section)
    
    # Bước 4: Sửa các URL trong từng tham khảo
    references = [fix_urls(ref) for ref in references]
    
    # Bước 5: Loại bỏ các số trang dư thừa
    references = remove_trailing_numbers(references)
    
    # Bước 6: Lọc các tham khảo chỉ lấy từ tên tác giả đầu tiên đến hết URL
    # Giả định rằng URL là phần cuối của tham khảo
    filtered_references = []
    url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
    
    for ref in references:
        match = re.search(url_pattern, ref)
        if match:
            # Lấy phần từ đầu đến cuối URL
            filtered_ref = ref[:match.end()]
            filtered_references.append(filtered_ref)
        else:
            # Nếu không tìm thấy URL, giữ nguyên tham khảo
            filtered_references.append(ref)
    
    # Bước 7: Lưu vào file DOCX
    save_to_docx(filtered_references, docx_path)
    
    print(f"Nội dung 'References' đã được lưu vào {docx_path}")

if __name__ == "__main__":
    pdf_path = 'paper.pdf'      # Thay bằng đường dẫn file PDF của bạn
    docx_path = 'references.docx'
    
    extract_references_from_pdf(pdf_path, docx_path)
