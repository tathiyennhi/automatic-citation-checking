import logging
from pdf2docx import Converter
import os
import re

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