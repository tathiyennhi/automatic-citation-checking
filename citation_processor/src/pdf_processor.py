import pdfplumber
from typing import Dict

class PDFProcessor:
    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def process_pdf(self, pdf_path: str) -> Dict:
        text = self.extract_text_from_pdf(pdf_path)
        return {"raw_text": text}
