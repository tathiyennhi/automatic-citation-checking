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

            # Sử dụng hàm mới để trích xuất nội dung trích dẫn dựa trên loại trích dẫn
            citation_content = extract_citation_content_by_type(cleaned_sentence, citation)

            citation_entry = {
                'original_sentence': cleaned_sentence,
                'citation_number': f"[{citation_number}]",
                'page_number': page_number,
                'citation_content': citation_content,
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


def extract_citation_content(sentence, citation):
    """
    Trích xuất nội dung trích dẫn dựa trên vị trí của trích dẫn trong câu.

    Args:
        sentence (str): Câu chứa trích dẫn.
        citation (dict): Thông tin về trích dẫn.

    Returns:
        str: Nội dung trích dẫn được trích xuất.
    """
    citation_number = f"[{citation['citation_number']}]"
    citation_pos = sentence.find(citation_number)
    
    if citation_pos == -1:
        return ""

    # Xác định vị trí: bắt đầu, giữa hoặc cuối
    if citation_pos == 0:
        # Trích dẫn ở đầu câu
        citation_content = sentence[citation_pos + len(citation_number):].strip(' .')
    elif citation_pos + len(citation_number) == len(sentence):
        # Trích dẫn ở cuối câu
        citation_content = sentence[:citation_pos].strip(' .')
    else:
        # Trích dẫn ở giữa câu
        citation_content = sentence.strip(' .')
    
    return citation_content

def detect_citation_type(sentence, citation_number):
    """
    Xác định loại trích dẫn trong câu dựa trên vị trí và dấu ngoặc kép.

    Args:
        sentence (str): Câu chứa trích dẫn.
        citation_number (str): Số trích dẫn (vd: "8" cho [8]).

    Returns:
        str: Loại trích dẫn ('direct_quote', 'paraphrase', 'combined').
    """
    citation_tag = f"[{citation_number}]"
    citation_pos = sentence.find(citation_tag)

    if citation_pos == -1:
        return "unknown"

    # Kiểm tra xem có dấu ngoặc kép ngay trước trích dẫn không
    if citation_pos >= 1 and sentence[citation_pos - 1] == '"':
        return "direct_quote"

    # Kiểm tra xem trích dẫn có nằm giữa dấu ngoặc kép không
    # Ví dụ: "This is a quote [8]."
    if citation_pos > 0 and sentence[citation_pos - 1] == '"' and sentence[citation_pos + len(citation_tag)] == '"':
        return "direct_quote"

    # Nếu không có dấu ngoặc kép, coi như là paraphrase
    return "paraphrase"


def extract_citation_content_by_type(sentence, citation):
    """
    Trích xuất nội dung trích dẫn dựa trên loại trích dẫn.

    Args:
        sentence (str): Câu chứa trích dẫn.
        citation (dict): Thông tin về trích dẫn.

    Returns:
        str: Nội dung trích dẫn được trích xuất.
    """
    citation_number = citation['citation_number']
    citation_type = detect_citation_type(sentence, citation_number)

    if citation_type == "direct_quote":
        # Sử dụng hàm hiện tại để trích xuất trích dẫn trực tiếp
        return extract_direct_quote(sentence, citation)
    elif citation_type == "paraphrase":
        # Sử dụng hàm mới để trích xuất dựa trên vị trí
        return extract_citation_content(sentence, citation)
    elif citation_type == "combined":
        # Có thể kết hợp cả hai phương pháp nếu cần
        direct_quote = extract_direct_quote(sentence, citation)
        paraphrase_content = extract_citation_content(sentence, citation)
        return f"{paraphrase_content} \"{direct_quote}\"" if direct_quote else paraphrase_content
    else:
        return ""


def standalize_citation_content(sentence, authors, title):
    """
    Chuẩn hóa nội dung trích dẫn trong câu bằng cách thay thế hoặc loại bỏ các thẻ trích dẫn [x].
    
    Args:
        sentence (str): Câu chứa trích dẫn.
        authors (str): Tên tác giả để thay thế [x] khi từ đứng trước là "by".
        title (str): Tiêu đề bài báo để thay thế [x] khi từ đứng trước là "in" hoặc "from".
    
    Returns:
        str: Câu đã được chuẩn hóa với các trích dẫn đã được thay thế hoặc loại bỏ.
    """
    # Định nghĩa regex để tìm tất cả các thẻ trích dẫn [x]
    pattern = re.compile(r'\[(\d+)\]')
    
    # Tìm tất cả các thẻ trích dẫn trong câu
    matches = list(pattern.finditer(sentence))
    
    # Xử lý các thẻ trích dẫn từ cuối câu về đầu để tránh ảnh hưởng đến chỉ số khi thay thế
    for match in reversed(matches):
        citation_number = match.group(1)
        start, end = match.start(), match.end()
        
        # Tìm từ đứng trước thẻ trích dẫn
        preceding_substr = sentence[:start].rstrip()
        preceding_word_match = re.search(r'(\b\w+\b)\s*$', preceding_substr)
        
        if preceding_word_match:
            preceding_word = preceding_word_match.group(1).lower()
        else:
            preceding_word = ''
        
        # Xác định nội dung thay thế dựa trên từ đứng trước
        if preceding_word == "by":
            replacement = authors
        elif preceding_word in ["in", "from"]:
            replacement = f'"{title}"'
        else:
            replacement = ''
        
        # Thay thế thẻ trích dẫn [x] bằng nội dung phù hợp
        sentence = sentence[:start] + replacement + sentence[end:]
    
    return sentence
