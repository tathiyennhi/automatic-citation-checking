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

# def extract_sentences(text):
#     """Tách văn bản thành các câu riêng lẻ."""
#     # Sử dụng regex để tách câu dựa trên dấu chấm câu và dấu xuống dòng
#     sentence_endings = re.compile(r'(?<=[.!?])\s+|\n+')
#     sentences = sentence_endings.split(text)
#     sentences = [sent.strip() for sent in sentences if sent.strip()]
#     return sentences
def extract_sentences(text):
    """Tách văn bản thành các câu riêng lẻ, xử lý ngoại lệ như 'et al.' và 'Sr.'. Ghi kết quả vào tệp."""
    
    # Danh sách các từ viết tắt phổ biến và trích dẫn học thuật
    citation_patterns = r'(?P<citation>(et al\.|[A-Z][a-z]{1,3}\.)\s*\((?P<year>\d{4})\))'
    abbreviation_patterns = r'(Mr\.|Mrs\.|Dr\.|Prof\.|Inc\.|Ltd\.|Jr\.|Sr\.)'
    
    # Thay thế các từ viết tắt và trích dẫn để tránh tách câu sai
    placeholders = []  # Lưu giữ các thông tin tạm
    placeholder_citation = "<CITATION_{}>"
    placeholder_abbr = "<ABBR_{}>"
    placeholder_count = 0

    # Thay thế citation bằng placeholder và lưu thông tin
    def replace_citation(match):
        nonlocal placeholder_count
        placeholders.append((placeholder_count, match.group("citation"), match.group("year")))
        result = placeholder_citation.format(placeholder_count)
        placeholder_count += 1
        return result

    text = re.sub(citation_patterns, replace_citation, text)

    # Thay thế các từ viết tắt bằng placeholder
    def replace_abbreviation(match):
        nonlocal placeholder_count
        placeholders.append((placeholder_count, match.group(0), None))  # Không cần lưu year cho abbreviations
        result = placeholder_abbr.format(placeholder_count)
        placeholder_count += 1
        return result

    text = re.sub(abbreviation_patterns, replace_abbreviation, text)
    
    # Sau đó tách câu dựa trên dấu chấm câu (.!?)
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text)

    # Khôi phục lại các từ viết tắt và trích dẫn đã thay thế trước đó
    corrected_sentences = []
    for sent in sentences:
        for placeholder in placeholders:
            placeholder_id, original_text, year = placeholder
            if year:
                sent = sent.replace(placeholder_citation.format(placeholder_id), f"{original_text}")
            else:
                sent = sent.replace(placeholder_abbr.format(placeholder_id), original_text)
        corrected_sentences.append(sent.strip())

    # In từng câu và ghi vào tệp
    with open("output_file.txt", 'w', encoding='utf-8') as f:
        for sentence in corrected_sentences:
            # print(sentence)
            print("\n")  # In ra màn hình
            f.write(sentence + "\n\n")  # Ghi vào tệp với dòng trống giữa các câu

    return corrected_sentences


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
    has_year = re.search(r'\b\d{4}\b', content)
    has_author = re.search(r'\b[A-Z][a-zA-Z]+', content)
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
    # narrative_citation_regex = r'\b(?P<author>[A-Z][a-zA-Z\'’\-]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-zA-Z\'’\-]+)?)\s*\((?P<year>\d{4}(?:,\s*\d{4})?)\)'
    # narrative_citation_regex = r'\b(?P<author>[A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-zA-Z]+)*)\s*\((?P<year>\d{4})\)'
    narrative_citation_regex = r'\b(?P<author>[A-Z][a-zA-Z\'’\-]+(?:\s+(?:et\s+al\.?|and|&)\s*(?:[A-Z][a-zA-Z\'’\-]+)?)*)\s*\((?P<year>\d{4})\)'

    # Mẫu regex cho trích dẫn parenthetical
    parenthetical_citation_regex = r'\(([^()]+)\)'
    
    # Mẫu regex cho trích dẫn trực tiếp bao gồm dấu ngoặc kép
    direct_quote_regex = r'“(.*?)”\s*\(([^()]+)\)'

    # Tìm trích dẫn trực tiếp trong câu
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

    # Loại bỏ các trích dẫn trực tiếp khỏi câu để tránh trùng lặp
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
        content = match.group(1).strip()
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

# def get_preceding_noun_phrase(sentence, citation_start):
#     """Trả về cụm danh từ chứa danh từ riêng hoặc thực thể tên ngay trước vị trí citation_start."""
#     doc = nlp(sentence)
#     noun_phrases = [chunk for chunk in doc.noun_chunks if chunk.end_char <= citation_start]
#     if not noun_phrases:
#         return None
#     for np in reversed(noun_phrases):
#         if np.end_char == citation_start:
#             contains_propn = any(token.pos_ == 'PROPN' for token in np)
#             contains_named_entity = any(ent.label_ != 'PERSON' for ent in np.ents)
#             if contains_propn or contains_named_entity:
#                 return np.text.strip()
#     return None
def get_preceding_noun_phrase(sentence, citation_start):
    """
    Trả về cụm danh từ đứng ngay trước vị trí citation_start, nhưng chỉ áp dụng trong các trường hợp đặc biệt.
    
    Args:
        sentence (str): Câu chứa trích dẫn.
        citation_start (int): Vị trí bắt đầu của trích dẫn trong câu.

    Returns:
        str: Cụm danh từ trích xuất được, hoặc chuỗi rỗng nếu không tìm thấy.
    """
    doc = nlp(sentence[:citation_start])  # Lấy phần văn bản trước trích dẫn
    noun_chunks = list(doc.noun_chunks)  # Lấy tất cả các cụm danh từ

    if not noun_chunks:
        return ''  # Không có cụm danh từ nào

    # Tìm cụm danh từ gần nhất với vị trí citation_start
    closest_noun_chunk = None
    for chunk in noun_chunks:
        if chunk.end_char <= citation_start:
            closest_noun_chunk = chunk
        else:
            break

    # Nếu cụm danh từ quá xa citation_start, không sử dụng cụm danh từ này
    if closest_noun_chunk and citation_start - closest_noun_chunk.end_char > 2:
        return ''  # Trả về chuỗi rỗng nếu cụm danh từ quá xa

    # Loại bỏ các từ chỉ định (determiners) và dấu câu thừa
    tokens = [token.text for token in closest_noun_chunk if token.dep_ != "det"]
    noun_phrase = ' '.join(tokens).rstrip(".,;:'\"!?()")

    return noun_phrase

def extract_citations_with_context(text):
    """Trích xuất trích dẫn từ mỗi câu."""
    text = clean_text(text)
    sentences = extract_sentences(text)
    results = []

    for sentence in sentences:
        citations_in_sentence = extract_citations_from_sentence(sentence)
        if not citations_in_sentence:
            continue

        citation_entries = []
        citation_count = len(citations_in_sentence)

        doc = nlp(sentence)

        for idx, citation in enumerate(citations_in_sentence):
            citation_type = citation['type']
            start = citation['start']
            end = citation['end']
            needs_manual_check = False

            if citation_type == 'narrative':
                if idx == 0:
                    preceding_text = sentence[:start].strip()
                    if preceding_text == '' or is_insignificant_text(preceding_text):
                        citation_content = get_following_content(sentence, end)
                    else:
                        citation_content = preceding_text
                else:
                    prev_end = citations_in_sentence[idx - 1]['end']
                    citation_content = sentence[prev_end:start].strip()

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
                with open('output_paren.txt', 'a', encoding='utf-8') as f:

                    if idx == 0:

                        preceding_text = sentence[:start].strip()
                        noun_phrase = get_preceding_noun_phrase(sentence, start)
                        # Ghi thông tin vào file thay vì print
                        
                        if noun_phrase:
                            citation_content = noun_phrase
                            needs_manual_check = True
                        else:
                            citation_content = preceding_text
        
                    else:
                        prev_end = citations_in_sentence[idx - 1]['end']
                        preceding_text = sentence[prev_end:start].strip()
                        noun_phrase = get_preceding_noun_phrase(sentence, start)
                        # Ví dụ vòng lặp đang xử lý các trích dẫn trong câu
                        for idx, citation in enumerate(citations_in_sentence):
                            start = citation['start']  # Vị trí bắt đầu của trích dẫn
                            noun_phrase = get_preceding_noun_phrase(sentence, start)
                            
                            
                        # if noun_phrase:
                        #     citation_content = noun_phrase if contains_relevant_entity(noun_phrase) else preceding_text
                        #     needs_manual_check = contains_relevant_entity(noun_phrase)
                        # else:
                        #     citation_content = preceding_text
                            
                            if noun_phrase:
                                with open('output_noun_phrase.txt', 'a', encoding='utf-8') as f:
                                    # Ghi noun_phrase vào file
                                    with open('output_noun_phrase.txt', 'a', encoding='utf-8') as f:
                                        f.write(f"Preceding Text: {preceding_text}\n")
                                        f.write("================================================================\n")

                                # Kiểm tra vị trí kết thúc của noun_phrase so với vị trí bắt đầu của trích dẫn trong dấu ngoặc đơn
                                noun_phrase_end_pos = sentence.index(noun_phrase) + len(noun_phrase)  # Vị trí kết thúc của noun_phrase
                                if noun_phrase_end_pos <= start and contains_relevant_entity(noun_phrase):
                                # Nếu noun_phrase kết thúc trước hoặc tại vị trí bắt đầu của trích dẫn và chứa thực thể đặc biệt
                                    citation_content = noun_phrase
                                    needs_manual_check = True
                                # else:
                                #     # Nếu không có thực thể đặc biệt, sử dụng logic cũ với preceding_text
                                #     citation_content = preceding_text
                                #     needs_manual_check = False
                            else:
                                with open('output_noun_phrase.txt', 'a', encoding='utf-8') as f:
                                  
                                    f.write(f"Preceding Text: {preceding_text}\n")
                                    f.write("================================================================\n")
                                # Nếu không có noun_phrase, sử dụng preceding_text
                                citation_content = preceding_text
                                needs_manual_check = False

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
def contains_relevant_entity(noun_phrase):
    """
    Kiểm tra xem noun_phrase có chứa từ nào là danh từ riêng hoặc thực thể đặc biệt (PRODUCT, MODEL, ORG, WORK_OF_ART).

    Args:
        noun_phrase (str): Cụm danh từ được phân tích.

    Returns:
        bool: True nếu có ít nhất một từ trong noun_phrase thuộc loại thực thể đặc biệt.
    """
    if not noun_phrase:  # Kiểm tra nếu noun_phrase rỗng
        return False

    doc = nlp(noun_phrase)  # Phân tích toàn bộ noun_phrase bằng SpaCy

    # Duyệt qua các token trong noun_phrase để kiểm tra thực thể
    for token in doc:
        # Kiểm tra nếu token là danh từ riêng hoặc thuộc các loại thực thể đặc biệt
        if token.pos_ == 'PROPN' or token.ent_type_ in ['PRODUCT', 'MODEL', 'ORG', 'WORK_OF_ART']:
            return True
    
    return False  # Không tìm thấy từ nào thuộc các loại thực thể đặc biệt


if __name__ == "__main__":
    try:
        # Chuyển đổi PDF sang DOCX (nếu cần)
        # convert_pdf_to_docx("paper_citation_matching_APA.pdf", "paper_citation_matching_APA.docx")

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
