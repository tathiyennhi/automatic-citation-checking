import re
import os
from pdf2docx import Converter
from docx import Document

# Hàm để phát hiện định dạng trích dẫn
def detect_citation_format(text):
    # APA format: Author, A. A. (Year)
    apa_pattern = re.compile(r'\b[A-Z][a-z]+, [A-Z]\. [A-Z]\. \(\d{4}\)')

    # IEEE format: [1], [2], etc.
    ieee_pattern = re.compile(r'\[\d+\]')

    # Chicago format: Author, Full Name. Year. Title of the Book.
    chicago_pattern = re.compile(r'\b[A-Z][a-z]+, [A-Z][a-z]+\. \d{4}\. [A-Za-z\s]+\.')

    # Kiểm tra APA format
    if apa_pattern.search(text):
        return "APA"
    # Kiểm tra IEEE format
    elif ieee_pattern.search(text):
        return "IEEE"
    # Kiểm tra Chicago format
    elif chicago_pattern.search(text):
        return "Chicago"
    else:
        return "Unknown format"

# Hàm đọc nội dung từ file DOCX
def read_docx_file(file_path):
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"Không thể đọc file DOCX: {e}")
        return None

# Hàm chuyển file PDF sang DOCX
def convert_pdf_to_docx(pdf_path, docx_path):
    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        print(f"Đã chuyển đổi thành công từ PDF sang DOCX: {docx_path}")
    except Exception as e:
        print(f"Lỗi khi chuyển đổi PDF sang DOCX: {e}")

# Hàm chính để kiểm tra và phát hiện trích dẫn
def main():
    file_path = input("Nhập đường dẫn file PDF: ")
    
    if file_path.endswith('.pdf'):
        # Lấy tên file không có đuôi .pdf và thêm đuôi .docx
        docx_path = file_path.replace('.pdf', '.docx')
        
        # Kiểm tra xem file DOCX có tồn tại không
        if not os.path.exists(docx_path):
            print("File DOCX chưa tồn tại, bắt đầu chuyển đổi...")
            convert_pdf_to_docx(file_path, docx_path)
        else:
            print(f"File DOCX đã tồn tại: {docx_path}")

        # Đọc file DOCX và phát hiện trích dẫn
        text = read_docx_file(docx_path)
        if text:
            citation_format = detect_citation_format(text)
            print(f"Định dạng trích dẫn phát hiện: {citation_format}")
    else:
        print("Chỉ hỗ trợ file PDF.")

if __name__ == "__main__":
    main()
