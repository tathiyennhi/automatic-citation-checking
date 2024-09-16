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

def clean_author(author):
    """
    Làm sạch chuỗi tác giả bằng cách tách dựa trên 'and', '&', hoặc ',', và nối các tác giả bằng ' & '.
    Loại bỏ các cụm từ như 'as cited in', 'The special issue by', 'the work of', nếu có.
    """
    # Loại bỏ các cụm từ như 'as cited in', 'cited in', 'The special issue by', 'the work of'
    author = re.sub(r'^(?:as\s+cited\s+in|cited\s+in|the\s+special\s+issue\s+by|the\s+work\s+of)\s+', '', author, flags=re.IGNORECASE)
    
    # Tách tác giả dựa trên ' and ', ' & ', hoặc ','
    split_authors = re.split(r'\s+(?:and|&)\s+|,\s*', author)
    
    # Loại bỏ các chuỗi rỗng và khoảng trắng thừa
    split_authors = [a.strip() for a in split_authors if a.strip()]
    
    return ' & '.join(split_authors)

def determine_citation_content(sentence, citation, is_at_end):
    """
    Xác định nội dung trích dẫn cho mỗi trích dẫn theo quy tắc.
    
    Parameters:
    - sentence (str): Câu chứa trích dẫn.
    - citation (dict): Thông tin về trích dẫn, bao gồm 'author' và 'year'.
    - is_at_end (bool): Có phải trích dẫn nằm ở cuối câu hay không.
    
    Returns:
    - list: Danh sách các dictionary chứa 'citation_content', 'author', và 'year_published'.
    """
    citation_contents = []

    # Kiểm tra sự tồn tại của 'author' hoặc 'authors' trong citation
    if 'author' in citation or 'authors' in citation:
        # Sử dụng 'author' nếu có, nếu không thì sử dụng 'authors'
        author_field = citation.get('author', citation.get('authors', ''))

        if citation['in_text_citation']:
            # Trích dẫn trực tiếp, lấy toàn bộ câu
            citation_content = sentence.strip()
            logging.info("Direct citation detected. Citation content set to entire sentence.")
        else:
            # Trích dẫn gián tiếp
            start_idx = citation['start']
            text_before_citation = sentence[:start_idx].strip()

            logging.info(f"Processing citation: {author_field} ({citation['year']})")
            logging.info(f"Text before citation: '{text_before_citation}'")

            # Tìm tất cả nội dung trong dấu ngoặc kép ngay trước trích dẫn
            quoted_content_matches = re.findall(r'“([^”]+)”|\"([^\"]+)\"', text_before_citation)
            if quoted_content_matches:
                # Lấy nội dung trong dấu ngoặc kép cuối cùng nếu có nhiều
                last_match = quoted_content_matches[-1]
                citation_content = last_match[0] if last_match[0] else last_match[1]
                logging.info(f"Quoted content found and adjacent to citation. Citation content set to: '{citation_content}'")
            elif is_at_end:
                # Trích dẫn ở cuối câu, kiểm tra cụm danh từ cuối cùng có phải là thuật ngữ hoặc tên sản phẩm không
                # CHECK THÊM CÀ CỤM DANH TỪ KẾ CUỐI NỮA, VÍ DỤ NHƯ GPT MODEL, MODEL KHÔNG PHẢI THUẬT NGỮ NHƯNG GPT THÌ CÓ  
                doc_before = nlp(text_before_citation)
                noun_chunks = list(doc_before.noun_chunks)
                valid_noun_phrase = None

                if noun_chunks:
                    last_noun = noun_chunks[-1]
                    # Kiểm tra xem cụm danh từ cuối cùng có phải là một thực thể đặc biệt
                    ent_label = None
                    for ent in doc_before.ents:
                        if ent.start_char <= last_noun.start_char and ent.end_char >= last_noun.end_char:
                            ent_label = ent.label_
                            break

                    if ent_label in {"ORG", "PRODUCT", "WORK_OF_ART", "EVENT", "LANGUAGE", "LAW"}:
                        # Kiểm tra khoảng cách ký tự từ cuối cụm danh từ đến dấu ngoặc
                        char_distance = len(text_before_citation) - last_noun.end_char
                        if char_distance <= 5:
                            valid_noun_phrase = last_noun.text.strip()
                            logging.info(f"Special term or product found near citation: '{valid_noun_phrase}'")

                if valid_noun_phrase:
                    # Nếu có cụm danh từ hợp lệ trước trích dẫn, dùng nó làm citation_content
                    citation_content = valid_noun_phrase
                    logging.info(f"Citation content set to special term/product: '{citation_content}'")
                else:
                    # Nếu không có cụm danh từ hợp lệ, đặt citation_content là toàn bộ câu trước trích dẫn
                    citation_content = text_before_citation
                    logging.info(f"No special term found. Citation content set to full sentence before citation: '{citation_content}'")
            else:
                # Trích dẫn nằm giữa câu, trích xuất cụm danh từ riêng trước trích dẫn
                doc_before = nlp(text_before_citation)
                # Trích xuất các thực thể được gán nhãn là PERSON
                person_entities = [ent.text.strip() for ent in doc_before.ents if ent.label_ == "PERSON"]
                if person_entities:
                    # Lấy tên người cuối cùng làm citation_content
                    citation_content = person_entities[-1]
                    logging.info(f"Extracted person name as citation_content: '{citation_content}'")
                else:
                    # Nếu không có tên người, đặt citation_content là toàn bộ văn bản trước trích dẫn
                    citation_content = text_before_citation
                    logging.info(f"No person name found. Citation content set to: '{citation_content}'")

        citation_dict = {
            'citation_content': citation_content,
            'author': clean_author(author_field),
            'year_published': citation['year']
        }
        citation_contents.append(citation_dict)
    else:
        logging.error("Citation object missing 'author' or 'authors' field.")

    return citation_contents


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
    Làm sạch tên tác giả để phù hợp với định dạng yêu cầu.
    """
    return author.strip()



def extract_citations_with_context(text):
    """Trích xuất trích dẫn từ mỗi câu."""
    text = clean_text(text)
    sentences = extract_sentences(text)

    results = []

    for sentence in sentences:
        # Tìm tất cả trích dẫn trong câu
        citation_positions = []
        # Mẫu regex để tìm trích dẫn theo định dạng (Author, Year)
        parenthetical_citation_pattern = re.compile(
            r'\((?P<author>[A-Z][A-Za-z&.\s\-]+?),\s*(?P<year>\d{4})\)'
        )
        
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
                'in_text_citation': False  # Đây là trích dẫn gián tiếp
            })
        
        # Kiểm tra trích dẫn trực tiếp (tác giả nằm ngoài dấu ngoặc đơn)
        # Mẫu: Author (Year)
        # Sử dụng finditer để tìm trích dẫn ở bất kỳ vị trí nào trong câu
        in_text_citation_pattern = re.compile(
            r'([A-Z][A-Za-z&.\s\-]*?)\s*\((\d{4})\)'
        )
        for match in in_text_citation_pattern.finditer(sentence):
            author, year = match.groups()
            author = author.strip()
            # Kiểm tra không bắt đầu bằng các từ nối hoặc từ không liên quan
            preceding_text = sentence[:match.start()].strip()
            if preceding_text.endswith(('.', ',', ';', ':', '!', '?')) or not preceding_text:
                citation_positions.append({
                    'start': match.start(2) - 1,  # Vị trí bắt đầu '('
                    'end': match.end(2) + 1,      # Vị trí kết thúc ')'
                    'author': author,
                    'year': year,
                    'in_text_citation': True  # Đây là trích dẫn trực tiếp
                })

        if citation_positions:
            # Xác định xem có bao nhiêu trích dẫn trong câu
            is_unique = len(citation_positions) == 1
            # Xác định nội dung trích dẫn theo quy tắc cho từng trích dẫn
            citation_contents = []
            for citation in citation_positions:
                # Xác định xem trích dẫn có nằm ở cuối câu không
                post_citation_text = sentence[citation['end']:].strip()
                # Nếu sau trích dẫn chỉ còn lại dấu câu hoặc không có gì
                is_at_end = re.fullmatch(r'[.,;:!?]*', post_citation_text) is not None
                citation_contents.extend(determine_citation_content(sentence, citation, is_at_end))
            results.append({
                'original_sentence': sentence,
                'citations': citation_contents
            })

    return results

if __name__ == "__main__":
    try:
        # Chuyển đổi PDF sang DOCX (nếu cần)
        convert_pdf_to_docx("paper.pdf", "paper.docx")

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
