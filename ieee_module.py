import re
import logging
from docx import Document

def extract_references(docx_file):
    """
    Trích xuất danh sách references từ file DOCX và ánh xạ số tham chiếu với tiêu đề bài báo.

    Args:
        docx_file (str): Đường dẫn đến file DOCX.

    Returns:
        dict: Bản đồ từ số tham chiếu tới tiêu đề bài báo.
    """
    logging.info(f"Đang đọc file DOCX: {docx_file}")

    # Mở tài liệu DOCX
    doc = Document(docx_file)

    references_started = False
    references = {}
    current_ref_number = None
    current_ref_content = ""

    # Biểu thức chính quy để nhận diện tham chiếu bắt đầu
    ref_start_pattern = re.compile(r'^\s*\[(\d+)\]\s*(.*)')

    # Duyệt qua các đoạn văn để tìm phần References
    for para in doc.paragraphs:
        para_text = para.text.strip()

        # Bắt đầu phần "References" nếu phát hiện từ khóa "References"
        if not references_started:
            if re.match(r'^references$', para_text, re.IGNORECASE):
                references_started = True
            continue

        if references_started:
            # Kiểm tra xem đoạn văn này có bắt đầu một tham chiếu mới không
            ref_start_match = ref_start_pattern.match(para_text)
            if ref_start_match:
                # Nếu có tham chiếu hiện tại, lưu lại nó
                if current_ref_number is not None:
                    # Xử lý nội dung tham chiếu để trích xuất tiêu đề
                    title = extract_title_from_ref_content(current_ref_content)
                    references[current_ref_number] = title

                # Bắt đầu tham chiếu mới
                current_ref_number = ref_start_match.group(1)
                current_ref_content = ref_start_match.group(2).strip()
            else:
                # Thêm nội dung vào tham chiếu hiện tại
                if current_ref_number is not None:
                    current_ref_content += ' ' + para_text
                else:
                    # Bỏ qua bất kỳ văn bản nào trước tham chiếu đầu tiên
                    continue

    # Sau khi kết thúc vòng lặp, lưu lại tham chiếu cuối cùng
    if current_ref_number is not None:
        title = extract_title_from_ref_content(current_ref_content)
        references[current_ref_number] = title

    logging.info(f"Đã trích xuất {len(references)} references.")
    return references

def extract_title_from_ref_content(ref_content):
    """
    Trích xuất tiêu đề từ nội dung tham chiếu.

    Args:
        ref_content (str): Nội dung của tham chiếu.

    Returns:
        str: Tiêu đề trích xuất được.
    """
    # Tách nội dung thành tác giả và phần còn lại
    author_split = re.split(r'\.\s+', ref_content, maxsplit=1)
    if len(author_split) < 2:
        title = "Title not found"
        print("Title not found\n")
    else:
        rest_content = author_split[1]
        # Tách phần còn lại thành tiêu đề và phần còn lại
        title_split = re.split(r'\.\s+', rest_content, maxsplit=1)
        if len(title_split) < 1:
            title = "Title not found"
            print("Title not found\n")
        else:
            title = title_split[0].strip()
            # Áp dụng hàm làm sạch tiêu đề
            title = clean_text(title)
            print("TITLE: ", title, '\n')
    return title

def clean_text(text):
    """
    Làm sạch văn bản bằng cách loại bỏ các ký tự xuống dòng, dấu gạch ngang,
    khoảng trắng không cần thiết và các ký tự đặc biệt.
    """
    # Loại bỏ dấu gạch ngang ngắt dòng
    text = remove_hyphenation(text)

    # Thay thế ký tự xuống dòng, tab, và khoảng trắng dư thừa bằng dấu cách
    text = re.sub(r'[\n\t\r]+', ' ', text)

    # Loại bỏ khoảng trắng dư thừa
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def remove_hyphenation(text):
    """
    Loại bỏ các dấu gạch ngang được sử dụng để ngắt dòng mà không làm mất dấu gạch ngang hợp lệ trong từ.
    """
    # Loại bỏ dấu gạch ngang ở cuối dòng hoặc giữa từ do ngắt dòng
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)

    return text

def extract_ieee_citations_from_sentence(sentence):
    """
    Trích xuất các trích dẫn IEEE từ một câu.

    Args:
        sentence (str): Câu cần xử lý.

    Returns:
        list: Danh sách các trích dẫn IEEE trong câu.
    """
    citations = []
    # Mẫu trích dẫn IEEE: [số], [số, p. số]
    ieee_pattern = re.compile(r'\[(\d+)(?:,\s*p\.?\s*(\d+))?\]')

    for match in re.finditer(ieee_pattern, sentence):
        citation_number = match.group(1)
        page_number = match.group(2) if match.group(2) else None
        citations.append({
            'citation_number': citation_number,
            'page_number': page_number,
            'original_text': match.group(0),
            'start': match.start(),
            'end': match.end()
        })
    return citations

def extract_ieee_citations_with_context(sentences, references_map):
    """
    Trích xuất các trích dẫn IEEE từ các câu và ánh xạ chúng tới references.

    Args:
        sentences (list): Danh sách các câu đã trích xuất.
        references_map (dict): Bản đồ từ số tham chiếu tới nội dung tham chiếu.

    Returns:
        list: Danh sách các trích dẫn với thông tin liên quan.
    """
    citation_entries = []

    for sentence in sentences:
        cleaned_sentence = clean_text(sentence)
        ieee_citations = extract_ieee_citations_from_sentence(cleaned_sentence)

        for citation in ieee_citations:
            citation_number = citation['citation_number']
            page_number = citation['page_number']
            original_text = citation['original_text']

            reference_entry = references_map.get(citation_number, "Reference not found.")

            # Trích xuất nội dung trích dẫn trực tiếp nếu có
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

def extract_direct_quote(sentence, citation):
    """
    Trích xuất trích dẫn trực tiếp liên quan đến một citation trong câu.

    Args:
        sentence (str): Câu chứa trích dẫn.
        citation (dict): Thông tin citation.

    Returns:
        str: Nội dung trích dẫn trực tiếp hoặc chuỗi rỗng nếu không tìm thấy.
    """
    # Tìm kiếm dấu ngoặc kép hoặc dấu ngoặc kép thông minh
    quote_pattern = re.compile(r'"(.*?)"|“(.*?)”')

    quotes = quote_pattern.findall(sentence)
    if quotes:
        # Làm phẳng danh sách các tuples và loại bỏ chuỗi rỗng
        quotes = [q for pair in quotes for q in pair if q]
        # Liên kết gần nhất với citation
        if quotes:
            return quotes[-1]  # Trả về trích dẫn cuối cùng tìm thấy
    return ""
