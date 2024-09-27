#chỉ lấy được cụm danh từ trước PARENTHESES
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
    """Loại bỏ các dấu gạch nối trong từ."""
    # Loại bỏ dấu gạch nối ở cuối dòng
    text = re.sub(r'-\s*\n\s*', '', text)
    # Loại bỏ dấu gạch nối giữa các chữ cái trong từ (do ngắt dòng)
    text = re.sub(r'(\w+)-\s*(\w+)', r'\1\2', text)
    return text

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
        if re.match(r'^\s*(References|Bibliography|Works Cited)\s*$',
                    text, re.IGNORECASE):
            logging.info("Đã tìm thấy phần Tham khảo. Dừng trích xuất văn bản.")
            references_found = True
            break
        full_text.append(text)
    if not references_found:
        logging.warning("Không tìm thấy phần Tham khảo. "
                        "Toàn bộ tài liệu sẽ được xử lý.")
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
    # Sử dụng regex để tách câu dựa trên dấu chấm câu và dấu xuống dòng
    sentence_endings = re.compile(r'(?<=[.!?])\s+|\n+')
    sentences = sentence_endings.split(text)
    sentences = [sent.strip() for sent in sentences if sent.strip()]
    return sentences

def clean_author(author):
    """Làm sạch chuỗi tác giả bằng cách loại bỏ các phần không cần thiết."""
    # Loại bỏ các cụm từ không liên quan
    author = re.sub(r'^(?:additional previous work in this area includes|'
                    r'the work of|the special issue by|cited in|as cited in)\s+',
                    '', author, flags=re.IGNORECASE)
    # Loại bỏ các ký tự không cần thiết
    author = re.sub(r'\s+', ' ', author)
    author = author.strip()
    return author

def sentence_contains_citation(sentence):
    """Kiểm tra xem câu có chứa trích dẫn hợp lệ hay không."""
    if extract_citations_from_sentence(sentence):
        return True
    return False

def determine_citation_validity(content):
    """Xác định xem nội dung có phải là trích dẫn hợp lệ hay không."""
    # Kiểm tra xem có năm (4 chữ số) trong nội dung hay không
    has_year = re.search(r'\b\d{4}\b', content)
    # Kiểm tra xem có tên tác giả hay không
    has_author = re.search(r'\b[A-Z][a-zA-Z]+', content)
    # Loại bỏ các nội dung quá ngắn hoặc chỉ chứa một ký tự
    is_too_short = len(content.strip()) < 3
    is_single_char = re.match(r'^[a-zA-Z0-9]$', content.strip())

    if has_year and has_author and not is_single_char and not is_too_short:
        return True  # Là trích dẫn hợp lệ
    else:
        return False  # Không phải trích dẫn hợp lệ

def extract_citations_from_sentence(sentence):
    """Trích xuất tất cả các trích dẫn từ một câu."""
    citations = []
    # Mẫu regex cho trích dẫn narrative
    narrative_citation_regex = r'\b(?P<author>[A-Z][a-zA-Z]*(?:\s+(?:and|&|et\ al\.?|[A-Z][a-zA-Z]*))*?)\s*\((?P<year>\d{4}(?:,\s*\d{4})?)\)'
    # Mẫu regex cho trích dẫn parenthetical
    parenthetical_citation_regex = r'\(([^()]+)\)'
    # Mẫu regex cho trích dẫn trực tiếp
    direct_quote_regex = r'"(.*?)"\s*\(([^()]+)\)'

    # Tìm trích dẫn trực tiếp
    for match in re.finditer(direct_quote_regex, sentence):
        quote = match.group(1).strip()
        citation_content = quote
        citation_text = match.group(0)
        citation_info = match.group(2).strip()
        start = match.start()
        end = match.end()

        # Xử lý thông tin trích dẫn
        refs = re.split(r';\s*', citation_info)
        ref_citations = []
        for ref in refs:
            ref = ref.strip()
            # Tách tác giả và năm
            parts = re.split(r',\s*', ref)
            if len(parts) >= 2:
                author = ', '.join(parts[:-1]).strip()
                year = parts[-1].strip()
            else:
                author = ref
                year = ''
            ref_citations.append({
                'author': clean_author(author),
                'year_published': year
            })
        citations.append({
            'type': 'direct_quote',
            'citation_content': citation_content,
            'ref_citations': ref_citations,
            'original_citation_text': citation_text,
            'start': start,
            'end': end
        })

    # Loại bỏ các trích dẫn trực tiếp khỏi câu để tránh trùng lặp khi xử lý các trích dẫn khác
    sentence_without_direct_quotes = re.sub(direct_quote_regex, '', sentence)

    # Tìm trích dẫn narrative trong câu đã loại bỏ trích dẫn trực tiếp
    for match in re.finditer(narrative_citation_regex, sentence_without_direct_quotes):
        author = match.group('author').strip()
        year = match.group('year').strip()
        citation_text = match.group(0)
        start = match.start()
        end = match.end()
        citations.append({
            'type': 'narrative',
            'author': author,
            'year': year,
            'citation_text': citation_text,
            'start': start,
            'end': end
        })

    # Tìm trích dẫn parenthetical trong câu đã loại bỏ trích dẫn trực tiếp
    for match in re.finditer(parenthetical_citation_regex, sentence_without_direct_quotes):
        content = match.group(1)
        start = match.start()
        end = match.end()
        if not determine_citation_validity(content):
            continue
        # Tách các trích dẫn bên trong dấu ngoặc đơn
        refs = re.split(r';\s*', content)
        ref_citations = []
        for ref in refs:
            ref = ref.strip()
            # Tách tác giả và năm
            parts = re.split(r',\s*', ref)
            if len(parts) >= 2:
                author = ', '.join(parts[:-1]).strip()
                year = parts[-1].strip()
            else:
                author = ref
                year = ''
            ref_citations.append({
                'author': clean_author(author),
                'year_published': year
            })
        citations.append({
            'type': 'parenthetical',
            'ref_citations': ref_citations,
            'original_citation_text': match.group(0),
            'start': start,
            'end': end
        })
    # Sắp xếp các trích dẫn theo vị trí trong câu
    citations.sort(key=lambda x: x['start'])
    return citations

def get_following_content(sentence, citation_end):
    """Trả về nội dung sau vị trí citation_end trong câu."""
    return sentence[citation_end:].strip()

def is_insignificant_text(text):
    """Kiểm tra xem văn bản chỉ chứa các từ không mang nhiều ý nghĩa."""
    doc = nlp(text)
    insignificant_pos = ['CCONJ', 'SCONJ', 'ADP', 'PART', 'PUNCT', 'SPACE', 'ADV']
    for token in doc:
        if token.pos_ not in insignificant_pos:
            return False
    return True

def get_preceding_entity(sentence, citation_start):
    """Trả về thực thể tên ngay trước vị trí citation_start trong câu, loại trừ tên người."""
    doc = nlp(sentence)
    # Tìm các thực thể trước vị trí citation_start
    entities = [ent for ent in doc.ents if ent.end_char <= citation_start]
    if not entities:
        return None
    # Duyệt ngược danh sách thực thể
    for ent in reversed(entities):
        if ent.end_char == citation_start and ent.label_ != 'PERSON':
            return ent.text.strip()
    return None

def get_preceding_noun_phrase(sentence, citation_start):
    """Trả về cụm danh từ ngay trước vị trí citation_start trong câu, loại trừ tên người."""
    # Ưu tiên sử dụng thực thể tên
    entity = get_preceding_entity(sentence, citation_start)
    if entity:
        return entity

    doc = nlp(sentence)
    # Tìm token trước vị trí citation_start
    tokens = [token for token in doc if token.idx < citation_start]
    if not tokens:
        return None

    # Tạo danh sách các thực thể PERSON trong câu
    person_entities = [(ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == 'PERSON']

    # Duyệt ngược từ vị trí trước citation_start để tìm danh từ hoặc danh từ riêng
    for i in range(len(tokens)-1, -1, -1):
        token = tokens[i]
        # Kiểm tra xem token có thuộc thực thể PERSON không
        is_person = any(token.idx >= start and token.idx < end for start, end in person_entities)
        if is_person:
            continue  # Bỏ qua tên người

        if token.pos_ in ['NOUN', 'PROPN']:
            # Lấy các token liên tiếp là danh từ hoặc tính từ
            start = i
            while start > 0:
                prev_token = tokens[start-1]
                prev_is_person = any(prev_token.idx >= start_ and prev_token.idx < end_ for start_, end_ in person_entities)
                if prev_is_person or prev_token.pos_ not in ['NOUN', 'PROPN', 'ADJ', 'DET']:
                    break
                start -= 1
            phrase = doc[tokens[start].i:tokens[i].i+1].text.strip()
            return phrase
    return None

def extract_citations_with_context(text):
    """Trích xuất trích dẫn từ mỗi câu."""
    text = clean_text(text)
    sentences = extract_sentences(text)
    results = []

    for sentence in sentences:
        citations_in_sentence = extract_citations_from_sentence(sentence)
        if not citations_in_sentence:
            continue  # Bỏ qua câu không chứa trích dẫn

        citation_entries = []
        citation_count = len(citations_in_sentence)

        # Sử dụng spaCy để phân tích cú pháp câu
        doc = nlp(sentence)

        for idx, citation in enumerate(citations_in_sentence):
            citation_type = citation['type']
            start = citation['start']
            end = citation['end']
            needs_manual_check = False

            if citation_type == 'narrative':
                # Nếu trích dẫn narrative
                if idx == 0:
                    preceding_text = sentence[:start].strip()
                    if preceding_text == '' or is_insignificant_text(preceding_text):
                        # Nếu trích dẫn nằm ở đầu câu hoặc trước nó chỉ có từ không mang nhiều ý nghĩa
                        citation_content = get_following_content(sentence, end)
                    else:
                        # Nếu có nội dung trước trích dẫn
                        citation_content = preceding_text
                else:
                    # Nếu không phải trích dẫn đầu tiên trong câu
                    prev_end = citations_in_sentence[idx - 1]['end']
                    citation_content = sentence[prev_end:start].strip()

                # Kiểm tra nếu citation_content quá ngắn hoặc không đủ ý nghĩa
                if len(citation_content.strip().split()) < 2:
                    needs_manual_check = True

                author = clean_author(citation['author'])
                year = citation['year']
                citation_text = citation['citation_text']
                citation_entry = {
                    'citation_content': citation_content,
                    'author': author,
                    'year_published': year,
                    'original_citation_text': citation_text,
                    'citation_type': citation_type,
                    'needs_manual_check': needs_manual_check
                }

            elif citation_type == 'direct_quote':
                citation_content = citation.get('citation_content', '')
                ref_citations = citation.get('ref_citations', [])
                citation_text = citation['original_citation_text']
                citation_entry = {
                    'citation_content': citation_content,
                    'ref_citations': ref_citations,
                    'original_citation_text': citation_text,
                    'citation_type': citation_type,
                    'needs_manual_check': needs_manual_check
                }

            else:  # parenthetical
                # Trường hợp câu chỉ có một trích dẫn gián tiếp
                if idx == 0:
                    preceding_text = sentence[:start].strip()
                    noun_phrase = get_preceding_noun_phrase(sentence, start)
                    if noun_phrase:
                        citation_content = noun_phrase
                        # Đặt cờ needs_manual_check là True khi sử dụng thực thể tên
                        needs_manual_check = True
                    else:
                        citation_content = preceding_text
                else:
                    prev_end = citations_in_sentence[idx - 1]['end']
                    preceding_text = sentence[prev_end:start].strip()
                    noun_phrase = get_preceding_noun_phrase(sentence, start)
                    if noun_phrase:
                        citation_content = noun_phrase
                        # Đặt cờ needs_manual_check là True khi sử dụng thực thể tên
                        needs_manual_check = True
                    else:
                        citation_content = preceding_text

                # Kiểm tra nếu citation_content quá ngắn hoặc không đủ ý nghĩa
                if len(citation_content.strip().split()) < 2 and not needs_manual_check:
                    needs_manual_check = True

                ref_citations = citation.get('ref_citations', [])
                citation_text = citation['original_citation_text']
                citation_entry = {
                    'citation_content': citation_content,
                    'ref_citations': ref_citations,
                    'original_citation_text': citation_text,
                    'citation_type': citation_type,
                    'needs_manual_check': needs_manual_check
                }

            citation_entries.append(citation_entry)

        results.append({
            'original_sentence': sentence,
            'citation_count': citation_count,
            'citations': citation_entries
        })

    return results

if __name__ == "__main__":
    try:
        # Chuyển đổi PDF sang DOCX (nếu cần)
        # convert_pdf_to_docx("paper_citation_matching_APA.pdf",
        #                     "paper_citation_matching_APA.docx")

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
