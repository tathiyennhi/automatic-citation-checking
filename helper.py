import logging
from pdf2docx import Converter
import os
import re
import requests
from scholarly import scholarly  # Thư viện để tìm kiếm bài báo
from docx import Document
import json


def convert_pdf_to_docx(pdf_file, docx_file):
    """
    Chuyển đổi tệp PDF thành DOCX và trả về đường dẫn đến tệp DOCX.

    Args:
        pdf_file (str): Đường dẫn đến tệp PDF nguồn.
        docx_file (str): Đường dẫn đến tệp DOCX đích.

    Returns:
        str: Đường dẫn đến tệp DOCX đã được tạo.
    """
    logging.info(f"Bắt đầu chuyển đổi {pdf_file} thành {docx_file}")
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        logging.info(f"Đã chuyển đổi {pdf_file} thành {docx_file}.")
        # Kiểm tra xem tệp DOCX đã được tạo thành công hay chưa
        if os.path.exists(docx_file):
            return docx_file
        else:
            logging.error(f"Tệp DOCX {docx_file} không được tạo ra.")
            raise FileNotFoundError(f"Tệp DOCX {docx_file} không được tạo ra.")
    except Exception as e:
        logging.error(f"Lỗi trong quá trình chuyển đổi PDF sang DOCX: {e}")
        raise

def clean_text(text):
    """
    Loại bỏ ký tự xuống dòng, tab, carriage return, dấu gạch ngang ở cuối dòng
    và thay thế bằng dấu cách. Đồng thời loại bỏ các dấu gạch ngang không hợp lệ.
    """
    # Bước 1: Loại bỏ dấu gạch ngang từ ngắt dòng trước khi thay thế các ký tự đặc biệt
    text = remove_hyphenation(text)
    
    # Bước 2: Thay thế \n, \r, \t bằng dấu cách
    text = re.sub(r'[\n\r\t]+', ' ', text)
    
    # Bước 3: Thay thế các khoảng trắng liên tiếp bằng một dấu cách duy nhất
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def remove_hyphenation(text):
    """
    Loại bỏ các dấu gạch ngang được sử dụng để ngắt dòng mà không làm mất dấu gạch ngang hợp lệ trong từ.
    """
    # Loại bỏ dấu gạch ngang ở cuối dòng (hyphenation)
    # Giả sử dấu gạch ngang này luôn theo sau bởi xuống dòng hoặc khoảng trắng
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # Loại bỏ dấu gạch ngang giữa các chữ cái nếu chúng được ngắt dòng
    # Ví dụ: "co-\noperation" thành "cooperation"
    text = re.sub(r'(\w+)-\s*(\w+)', r'\1\2', text)
    
    return text

def detect_citation_format(text):
    """Hàm phát hiện định dạng trích dẫn."""
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

# Các hàm mới thêm vào để crawl dữ liệu

def search_paper(reference):
    """
    Tìm kiếm bài báo dựa trên reference sử dụng Semantic Scholar API.

    Args:
        reference (str): Chuỗi tham chiếu.

    Returns:
        dict: Thông tin bài báo tìm được hoặc None nếu không tìm thấy.
    """
    try:
        search_query = scholarly.search_pubs(reference)
        
        paper = next(search_query, None)
        if paper:
            logging.info(f"Tìm thấy bài báo: {paper.get('bib', {}).get('title', 'No Title')}")
            return paper
        else:
            logging.warning(f"Không tìm thấy bài báo cho reference: {reference}")
            return None
    except Exception as e:
        logging.error(f"Lỗi khi tìm kiếm bài báo cho reference '{reference}': {e}")
        return None


def download_paper_pdf(paper, download_dir="downloaded_papers"):
    """
    Tải xuống file PDF của bài báo nếu có sẵn.

    Args:
        paper (dict): Thông tin bài báo.
        download_dir (str): Thư mục lưu trữ file PDF.

    Returns:
        str: Đường dẫn đến file PDF đã tải xuống, hoặc None nếu không tải được.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    pdf_url = paper.get('bib', {}).get('url', None)
    title = paper.get('bib', {}).get('title', 'unknown_title').replace('/', '_').replace('\\', '_')
    pdf_path = os.path.join(download_dir, f"{title}.pdf")

    if pdf_url and pdf_url.endswith('.pdf'):
        try:
            response = requests.get(pdf_url, timeout=10)
            if response.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                logging.info(f"Tải xuống PDF: {pdf_path}")
                return pdf_path
            else:
                logging.warning(f"Không thể tải xuống PDF từ {pdf_url} (Status Code: {response.status_code})")
                return None
        except Exception as e:
            logging.error(f"Lỗi khi tải xuống PDF từ {pdf_url}: {e}")
            return None
    else:
        logging.warning(f"Không có URL PDF hợp lệ cho bài báo: {title}")
        return None


def extract_text_from_docx(docx_path):
    """
    Trích xuất văn bản từ file DOCX sử dụng python-docx.

    Args:
        docx_path (str): Đường dẫn đến file DOCX.

    Returns:
        str: Văn bản trích xuất được từ DOCX.
    """
    try:
        doc = Document(docx_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        logging.info(f"Trích xuất văn bản từ DOCX: {docx_path}")
        return full_text
    except Exception as e:
        logging.error(f"Lỗi khi trích xuất văn bản từ DOCX '{docx_path}': {e}")
        return ""

def generate_json_output(citation_entries, output_file):
    """
    Tạo file JSON từ các trích dẫn.

    Args:
        citation_entries (list): Danh sách các trích dẫn.
        output_file (str): Đường dẫn tới file JSON xuất ra.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(citation_entries, f, ensure_ascii=False, indent=4)
    logging.info(f"Đã tạo file JSON tại: {output_file}")


def crawl_references(citation_entries, download_dir="downloaded_papers"):
    """
    Crawl các bài báo dựa trên references.

    Args:
        citation_entries (list): Danh sách các trích dẫn.
        download_dir (str): Thư mục để lưu trữ các file PDF đã tải xuống.

    Returns:
        list: Cập nhật danh sách các trích dẫn với đường dẫn PDF nếu tải thành công.
    """
    updated_citations = []

    for entry in citation_entries:
        reference = entry['reference']
        if reference == "Reference not found.":
            entry['pdf_path'] = None
            updated_citations.append(entry)
            continue

        # Tìm kiếm và tải xuống bài báo
        paper = search_paper(reference)
        if not paper:
            entry['pdf_path'] = None
            updated_citations.append(entry)
            continue

        pdf_path = download_paper_pdf(paper, download_dir)
        if not pdf_path:
            entry['pdf_path'] = None
            updated_citations.append(entry)
            continue

        # Trích xuất văn bản từ DOCX đã chuyển đổi
        docx_path = pdf_path.replace('.pdf', '.docx')
        try:
            convert_pdf_to_docx(pdf_path, docx_path)
            paper_text = extract_text_from_docx(docx_path)
        except Exception as e:
            logging.error(f"Lỗi khi chuyển đổi và trích xuất văn bản từ DOCX '{docx_path}': {e}")
            paper_text = ""

        # Kiểm tra xem citation_content có nằm trong paper_text không
        citation_content = entry['citation_content']
        if citation_content:
            if citation_content in paper_text:
                entry['verification'] = "Trích dẫn chính xác."
            else:
                entry['verification'] = "Trích dẫn không khớp với nội dung bài báo."
        else:
            entry['verification'] = "Không có nội dung trích dẫn để kiểm tra."

        # Lưu đường dẫn PDF vào entry
        entry['pdf_path'] = pdf_path
        updated_citations.append(entry)

    return updated_citations
