import re
import spacy
import docx
import json
import logging
from pdf2docx import Converter

# Thiết lập logging để theo dõi quá trình trích xuất
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Tải mô hình ngôn ngữ SpaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logging.info("Mô hình SpaCy 'en_core_web_sm' chưa được tải. Đang tải mô hình...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def convert_pdf_to_docx(pdf_file, docx_file):
    """Chuyển đổi tệp PDF thành DOCX."""
    logging.info(f"Bắt đầu chuyển đổi {pdf_file}")
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        logging.info(f"Đã chuyển đổi {pdf_file} thành {docx_file}.")
    except Exception as e:
        logging.error(f"Lỗi trong quá trình chuyển đổi PDF sang DOCX: {e}")
        raise

def remove_hyphenation(text):
    """Loại bỏ các dấu gạch ngang ở cuối dòng và nối các từ lại."""
    return re.sub(r'-\s*\n\s*', '', text)

def extract_text_from_docx(docx_file):
    """Trích xuất toàn bộ văn bản từ tệp DOCX, loại trừ phần tham khảo."""
    try:
        doc = docx.Document(docx_file)
    except Exception as e:
        logging.error(f"Lỗi khi mở tệp DOCX: {e}")
        raise

    full_text = []
    references_found = False
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        # Kiểm tra xem đoạn văn có phải là tiêu đề Tham khảo không
        if re.match(r'^\s*(References|Bibliography|Works Cited)\s*$', text, re.IGNORECASE):
            logging.info("Đã tìm thấy phần Tham khảo. Dừng trích xuất văn bản.")
            references_found = True
            break
        full_text.append(text)
    if not references_found:
        logging.warning("Không tìm thấy phần Tham khảo. Toàn bộ tài liệu sẽ được xử lý.")
    # Hợp nhất các dòng và loại bỏ hyphenation
    combined_text = '\n'.join(full_text)
    combined_text = remove_hyphenation(combined_text)
    return combined_text

def clean_text(text):
    """Loại bỏ ký tự xuống dòng, dấu gạch ngang ở cuối dòng và thay thế bằng dấu cách."""
    text = text.replace('\n', ' ').replace('\r', ' ').strip()
    text = remove_hyphenation(text)
    return text

def extract_sentences(text):
    """Tách văn bản thành các câu riêng lẻ."""
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]


def is_special_entity(noun_chunk):
    """
    Kiểm tra nếu noun_chunk chứa các token là thực thể đặc biệt (ORG, PRODUCT, WORK_OF_ART, EVENT, LANGUAGE, LAW).
    """
    for token in noun_chunk:
        if token.ent_type_ in {"ORG", "PRODUCT", "WORK_OF_ART", "EVENT", "LANGUAGE", "LAW"}:
            return True
    return False


def clean_author(author):
    """
    Làm sạch chuỗi tác giả bằng cách chỉ giữ lại tên tác giả trong trích dẫn, loại bỏ các phần văn bản thừa.
    """
    # Loại bỏ các cụm từ không liên quan như "Additional previous work in this area includes"
    author = re.sub(r'^(?:additional previous work in this area includes|the work of|the special issue by|cited in)\s+', '', author, flags=re.IGNORECASE)
    
    # Tách tác giả dựa trên ' and ', ' & ', hoặc ','
    split_authors = re.split(r'\s+(?:and|&)\s+|,\s*', author)
    
    # Loại bỏ chuỗi rỗng và khoảng trắng thừa
    split_authors = [a.strip() for a in split_authors if a.strip()]
    
    return ' & '.join(split_authors)


def determine_citation_content(sentence, citation, is_at_end, previous_end_index=0):
    """
    Xác định nội dung trích dẫn cho mỗi trích dẫn theo quy tắc.

    Parameters:
    - sentence (str): Câu chứa trích dẫn.
    - citation (dict): Thông tin về trích dẫn, bao gồm 'author', 'year', và 'in_text_citation'.
    - is_at_end (bool): Có phải trích dẫn nằm ở cuối câu hay không.
    - previous_end_index (int): Chỉ số kết thúc của trích dẫn trước đó trong câu.

    Returns:
    - list: Danh sách các dictionary chứa 'citation_content', 'author', và 'year_published'.
    """
    citation_contents = []

    # Sử dụng 'author' nếu có, nếu không thì sử dụng 'authors'
    author_field = citation.get('author', citation.get('authors', ''))

    if citation['in_text_citation']:
        # Trích dẫn trực tiếp, lấy toàn bộ câu
        citation_content = sentence.strip()
        logging.info("Direct citation detected. Citation content set to entire sentence.")
    else:
        # Trích dẫn gián tiếp, lấy phần text giữa previous_end_index và current citation start
        start_idx = citation['start']
        text_before_citation = sentence[previous_end_index:start_idx].strip()

        logging.info(f"Processing citation: {author_field} ({citation['year']})")
        logging.info(f"Text before citation: '{text_before_citation}'")

        # 1. Kiểm tra xem có dấu ngoặc kép ngay trước trích dẫn không (Absolute Citation)
        # Tìm dấu ngoặc kép gần nhất trước trích dẫn
        quote_match = re.search(r'["“”](?P<quoted>[^"“”]+)["“”]\s*$', text_before_citation)
        if quote_match:
            citation_content = quote_match.group('quoted').strip()
            logging.info(f"Absolute citation detected. Citation content set to: '{citation_content}'")
        else:
            # 2. Kiểm tra xem có cụm danh từ đặc biệt ngay trước trích dẫn không (Special Noun Phrase)
            doc_before = nlp(text_before_citation)
            noun_chunks = list(doc_before.noun_chunks)
            valid_noun_phrase = None

            if len(noun_chunks) >= 1:
                print("CHUNKS", noun_chunks)
                last_noun = noun_chunks[-1]
                print("Noun", last_noun)
                # breakpoint
                # Now we will iterate over each token in the 'last_noun' chunk
                doc = nlp(last_noun)
                print("DOC", doc)
                tokens_as_text = [token.text for token in doc]
                for item in tokens_as_text:
                    print(item, "Có phải là SPECIAL", is_special_entity(item))
                    
                    if is_special_entity(item):
                        # Kiểm tra khoảng cách ký tự từ cuối cụm danh từ đến dấu ngoặc
                        char_distance = len(text_before_citation) - last_noun.end_char
                        if char_distance <= 5:
                            # Loại bỏ các determiners như "the"
                            tokens_noun = [tok.text for tok in last_noun if tok.dep_ != "det"]
                            citation_content = ' '.join(tokens_noun).strip()
                            logging.info(f"Special term or product found near citation: '{citation_content}'")
                            valid_noun_phrase = citation_content
                            break

                
            if valid_noun_phrase:
                # Nếu có cụm danh từ hợp lệ trước trích dẫn, dùng nó làm citation_content
                pass  # citation_content đã được thiết lập ở trên
            else:
                # 3. Xử lý theo logic hiện tại: kiểm tra danh từ cuối cùng hoặc lấy toàn bộ text_before_citation
                last_token = doc_before[-1] if len(doc_before) > 0 else None

                if last_token and last_token.pos_ not in {"NOUN", "PROPN"}:
                    citation_content = text_before_citation
                    logging.info(f"Last token before citation is not a noun. Citation content set to: '{citation_content}'")
                else:
                    # Kiểm tra các thực thể PERSON
                    person_entities = [ent.text.strip() for ent in doc_before.ents if ent.label_ == "PERSON"]
                    if person_entities:
                        citation_content = person_entities[-1]
                        logging.info(f"Extracted person name as citation_content: '{citation_content}'")
                    else:
                        # Nếu không có tên người, đặt citation_content là toàn bộ phần text_before_citation
                        citation_content = text_before_citation
                        logging.info(f"No person name found. Citation content set to: '{citation_content}'")

    citation_dict = {
        'citation_content': citation_content,
        'author': clean_author(author_field),
        'year_published': citation['year']
    }
    citation_contents.append(citation_dict)

    return citation_contents




def extract_citations_with_context(text):
    """Trích xuất trích dẫn từ mỗi câu và tách riêng nội dung trích dẫn nếu có nhiều."""
    text = clean_text(text)
    sentences = extract_sentences(text)
    results = []

    for sentence in sentences:
        citation_positions = []
        # Mẫu regex để tìm trích dẫn gián tiếp (Author, Year)
        parenthetical_citation_pattern = re.compile(r'\((?P<author>[A-Z][A-Za-z&.\s\-]+?),\s*(?P<year>\d{4})\)')

        for match in parenthetical_citation_pattern.finditer(sentence):
            author = match.group('author').strip()
            year = match.group('year').strip()
            start = match.start()
            end = match.end()

            citation_positions.append({
                'start': start,
                'end': end,
                'author': author,
                'year': year,
                'in_text_citation': False  # Trích dẫn gián tiếp
            })

        # Mẫu regex để tìm trích dẫn trực tiếp (Author (Year))
        in_text_citation_pattern = re.compile(r'([A-Z][A-Za-z&.\s\-]*?)\s*\((\d{4})\)')
        for match in in_text_citation_pattern.finditer(sentence):
            author, year = match.groups()
            author = author.strip()
            preceding_text = sentence[:match.start()].strip()

            if preceding_text.endswith(('.', ',', ';', ':', '!', '?')) or not preceding_text:
                citation_positions.append({
                    'start': match.start(2) - 1,  # Vị trí bắt đầu '('
                    'end': match.end(2) + 1,      # Vị trí kết thúc ')'
                    'author': author,
                    'year': year,
                    'in_text_citation': True  # Trích dẫn trực tiếp
                })

        if citation_positions:
            # Sắp xếp các trích dẫn theo thứ tự xuất hiện trong câu
            citation_positions.sort(key=lambda x: x['start'])

            citation_contents = []
            previous_end_index = 0  # Khởi đầu từ đầu câu

            for citation in citation_positions:
                # Xác định xem trích dẫn có nằm ở cuối câu không
                post_citation_text = sentence[citation['end']:].strip()
                is_at_end = re.fullmatch(r'[.,;:!?]*', post_citation_text) is not None

                # Gọi hàm xác định nội dung trích dẫn, truyền previous_end_index
                citation_dict_list = determine_citation_content(
                    sentence, citation, is_at_end, previous_end_index
                )
                citation_contents.extend(citation_dict_list)

                # Cập nhật previous_end_index cho trích dẫn tiếp theo
                previous_end_index = citation['end']

            results.append({
                'original_sentence': sentence,
                'citations': citation_contents
            })

    return results



if __name__ == "__main__":
    try:
        # Chuyển đổi PDF sang DOCX (nếu cần)
        # convert_pdf_to_docx("paper_ciation_matching_APA.pdf", "paper_ciation_matching_APA.docx")

        # Trích xuất văn bản từ DOCX để xử lý
        docx_text = extract_text_from_docx("paper.docx")

        # Trích xuất trích dẫn
        citations = extract_citations_with_context(docx_text)

        # Xuất kết quả ra tệp JSON
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(citations, f, ensure_ascii=False, indent=4)

        logging.info("Dữ liệu đã được xuất ra tệp output.json.")
    except Exception as e:
        logging.error(f"Đã xảy ra lỗi: {e}")
