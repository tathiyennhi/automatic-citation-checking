import fitz  # PyMuPDF
import re
import spacy

# Load spaCy's English model
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_path):
    # Mở file PDF
    doc = fitz.open(pdf_path)
    full_text = ""
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        full_text += page.get_text()

    # Xử lý các ký tự không đúng định dạng như \xa0 (khoảng trắng không đúng)
    full_text = full_text.replace('\xa0', ' ')
    
    return full_text

def extract_citations(text):
    # Các biểu thức chính quy để tìm các trích dẫn APA mở rộng
    patterns = [
        r'\(\w+(?:\s(?:and|&) \w+)*,\s\d{4}\)',  # (Tác giả và Tác giả, Năm)
        r'\w+\sand\s\w+\s\(\d{4}\)',  # Tác giả1 and Tác giả2 (Năm)
        r'\(\w+ et al.,\s\d{4}\)',  # (Tác giả et al., Năm)
        r'\(\w+\s\[\w+\],\s\d{4}\)',  # (Tổ chức [Viết tắt], Năm)
        r'\(\w+\s\[\w+\]\)',  # (Viết tắt, Năm)
        r'\(\w+,\s\d{4};\s\w+,\s\d{4};\s\w+,\s\d{4}\)',  # (Tác giả1, Năm; Tác giả2, Năm; Tác giả3, Năm)
        r'\w+\s\(\d{4}\)',  # Tác giả (Năm)
        r'\w+\s&\s\w+\s\(\d{4}\)',  # Tác giả1 & Tác giả2 (Năm)
        r'\w+\set\sal.\s\(\d{4}\)',  # Tác giả et al. (Năm)
        r'\w+\s\(\w+,\s\d{4}\)',  # Tổ chức (Viết tắt, Năm)
        r'\w+\s\(\d{4}\)',  # Tổ chức (Năm)
    ]
    
    citations = []
    for pattern in patterns:
        citations.extend(re.findall(pattern, text))
    
    # Loại bỏ trích dẫn trùng lặp
    citations = list(set(citations))
    
    return citations


def extract_cited_sentences(text):
    doc = nlp(text)
    
    cited_sentences = []
    for sentence in doc.sents:
        sentence_text = sentence.text
        citations = extract_citations(sentence_text)
        if citations:
            cited_sentences.append(f"Nội dung: {sentence_text.strip()}")
            cited_sentences.append(f"Trích dẫn: {citations}")
    
    return cited_sentences

def main():
    pdf_path = "paper.pdf"  # Thay thế bằng đường dẫn tới file PDF của bạn

    text = extract_text_from_pdf(pdf_path)
    
    cited_sentences = extract_cited_sentences(text)
    
    for sentence in cited_sentences:
        print(sentence)

if __name__ == "__main__":
    main()
