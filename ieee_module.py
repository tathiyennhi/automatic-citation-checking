# ieee_module.py

import re
import logging
from docx import Document
from helper import clean_text, remove_hyphenation


def extract_references(docx_file):
    """
    Trích xuất danh sách các tham chiếu từ tệp DOCX và ánh xạ số tham chiếu tới tiêu đề bài báo.

    Args:
        docx_file (str): Đường dẫn tới tệp DOCX.

    Returns:
        tuple: (references_map, reference_list)
            - references_map (dict): Bản đồ từ số tham chiếu tới nội dung tham chiếu.
            - reference_list (list): Danh sách các từ điển chứa tham chiếu và tiêu đề bài báo.
    """
    logging.info(f"Đang đọc tệp DOCX để trích xuất tham chiếu: {docx_file}")

    doc = Document(docx_file)

    references_started = False
    references_map = {}
    reference_list = []
    current_ref_number = None
    current_ref_content = ""

    ref_start_pattern = re.compile(r'^\s*\[(\d+)\]\s*(.*)')

    for para in doc.paragraphs:
        para_text = para.text.strip()

        if not references_started:
            if re.match(r'^references$', para_text, re.IGNORECASE):
                references_started = True
            continue

        if references_started:
            # Kiểm tra nếu gặp tiêu đề 'Appendix' thì dừng lại
            if re.match(r'^appendix', para_text, re.IGNORECASE):
                break

            ref_start_match = ref_start_pattern.match(para_text)
            if ref_start_match:
                if current_ref_number is not None:
                    title = extract_title_from_ref_content(current_ref_content)
                    reference_entry = {'reference': title}
                    reference_list.append(reference_entry)
                    references_map[current_ref_number] = title

                current_ref_number = ref_start_match.group(1)
                current_ref_content = ref_start_match.group(2).strip()
            else:
                if current_ref_number is not None:
                    current_ref_content += ' ' + para_text
                else:
                    continue

    if current_ref_number is not None:
        title = extract_title_from_ref_content(current_ref_content)
        reference_entry = {'reference': title}
        reference_list.append(reference_entry)
        references_map[current_ref_number] = title

    logging.info(f"Đã trích xuất {len(reference_list)} tham chiếu.")
    return references_map, reference_list

def extract_title_from_ref_content(ref_content):
    """
    Trích xuất tiêu đề từ nội dung tham chiếu.

    Args:
        ref_content (str): Nội dung của tham chiếu.

    Returns:
        str: Tiêu đề trích xuất được.
    """
    ref_content = remove_hyphenation(ref_content)

    if "In " in ref_content:
        matches = re.search(r'\.\s*(.*?In\s.*?)(?:,|\.|\s*$)', ref_content)
    else:
        matches = re.search(r'\.\s*(.*?)\.\s+', ref_content)

    if matches:
        title = matches.group(1).strip()
        title = re.sub(r'arXiv preprint.*$', '', title, flags=re.IGNORECASE).strip()
        title = clean_text(title)
        print("TITLE: ", title, '\n')
        return title
    else:
        print("Không tìm thấy tiêu đề\n")
        return "Title not found"

def is_citation_sentence(sentence):
    """
    Kiểm tra xem một câu có chứa trích dẫn IEEE hay không và không bắt đầu bằng số tham chiếu hoặc chứa từ 'Appendix'.

    Args:
        sentence (str): Câu cần kiểm tra.

    Returns:
        bool: True nếu câu chứa trích dẫn IEEE và không bắt đầu bằng số tham chiếu hoặc chứa từ 'Appendix', ngược lại False.
    """
    # Kiểm tra nếu câu chứa từ 'Appendix' hoặc bắt đầu bằng số trang
    if re.search(r'\bAppendix\b', sentence, re.IGNORECASE):
        return False

    if re.match(r'^\d+\s+', sentence):
        return False

    # Sử dụng negative lookbehind để tránh bắt '[number]' nếu chúng được theo sau bởi một số
    ieee_pattern = re.compile(r'(?<!\d)\[(\d+)(?:,\s*p\.?\s*(\d+))?\]')
    leading_citation_pattern = re.compile(r'^\s*\[\d+\]')

    if leading_citation_pattern.match(sentence):
        return False

    return bool(ieee_pattern.search(sentence))


def extract_ieee_citations_from_sentence(sentence):
    """
    Trích xuất các trích dẫn IEEE từ một câu.

    Args:
        sentence (str): Câu cần xử lý.

    Returns:
        list: Danh sách các trích dẫn IEEE trong câu.
    """
    citations = []
    # Sử dụng negative lookbehind để tránh bắt '[number]' nếu chúng được theo sau bởi một số
    ieee_pattern = re.compile(r'(?<!\d)\[(\d+)(?:,\s*p\.?\s*(\d+))?\]')
    if is_citation_sentence(sentence):
        for match in re.finditer(ieee_pattern, sentence):
            citation_number = match.group(1)
            page_number = match.group(2) if match.group(2) else None
            citations.append({
                'sentence': sentence,
                'citation_number': citation_number,
                'page_number': page_number,
                'original_text': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        if citations:
            print_citations(citations)
    return citations

def extract_ieee_citations_with_context(sentences, references_map):
    """
    Trích xuất các trích dẫn IEEE từ danh sách câu và ánh xạ chúng tới tham chiếu.

    Args:
        sentences (list): Danh sách các câu.
        references_map (dict): Bản đồ từ số tham chiếu tới nội dung tham chiếu.

    Returns:
        list: Danh sách các mục trích dẫn với ngữ cảnh.
    """
    citation_entries = []

    for sentence in sentences:
        cleaned_sentence = clean_text(sentence)
        ieee_citations = extract_ieee_citations_from_sentence(cleaned_sentence)

        for citation in ieee_citations:
            citation_number = citation['citation_number']
            page_number = citation['page_number']
            original_text = citation['original_text']

            # Kiểm tra nếu câu chứa từ 'Appendix' hoặc bắt đầu bằng số trang
            if re.match(r'^\d+\s+Appendix', sentence, re.IGNORECASE):
                continue  # Bỏ qua câu này

            reference_entry = references_map.get(citation_number, "Reference not found.")

            quote = extract_direct_quote(cleaned_sentence, citation)

            citation_entry = {
                'original_sentence': cleaned_sentence,
                'citation_number': f"[{citation_number}]",
                'page_number': page_number,
                'citation_content': quote,
                'reference': reference_entry
            }
            citation_entries.append(citation_entry)
    return citation_entries

def print_citations(citations):
    """
    In thông tin các trích dẫn ra màn hình.

    Args:
        citations (list): Danh sách các trích dẫn.
    """
    if not citations:
        return

    for citation in citations:
        print(f"--- Trích dẫn ---")
        print(f"Câu chứa trích dẫn: {citation['sentence']}")
        print(f"Số trích dẫn: [{citation['citation_number']}]")
        print(f"Nội dung trích dẫn: {citation['original_text']}")
        print("-----------------\n")

def extract_direct_quote(sentence, citation):
    """
    Trích xuất trích dẫn trực tiếp liên quan đến một trích dẫn trong câu.

    Args:
        sentence (str): Câu chứa trích dẫn.
        citation (dict): Thông tin về trích dẫn.

    Returns:
        str: Nội dung trích dẫn trực tiếp nếu có, ngược lại trả về chuỗi rỗng.
    """
    # Sử dụng dấu ngoặc kép thông minh và dấu ngoặc kép thông thường
    quote_pattern = re.compile(r'"(.*?)"|“(.*?)”')

    quotes = quote_pattern.findall(sentence)
    if quotes:
        # Làm phẳng danh sách các tuples và loại bỏ chuỗi rỗng
        quotes = [q for pair in quotes for q in pair if q]
        if quotes:
            return quotes[-1]  # Trả về trích dẫn cuối cùng tìm thấy
    return ""
