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
    nlp = spacy.load("en_core_web_lg")
except OSError:
    logging.info("Mô hình SpaCy 'en_core_web_lg' chưa được tải. Đang tải mô hình...")
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

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
        for idx, citation in enumerate(citations_in_sentence):
            citation_type = citation['type']
            start = citation['start']
            end = citation['end']
            needs_manual_check = False

            if citation_type == 'narrative':
                # Check if citation is at the end of the sentence
                if end == len(sentence.strip()):
                    # If citation is at the end, take the preceding text
                    citation_content = sentence[:start].strip()
                # Check if citation is at the beginning of the sentence
                elif start == 0:
                    # If citation is at the beginning, take the following text
                    citation_content = get_following_content(sentence, end)
                else:
                    # If citation is in the middle, take the entire sentence
                    citation_content = sentence.strip()

                # Ensure there's no irrelevant or insignificant text
                if len(citation_content.strip().split()) < 2 or is_insignificant_text(citation_content):
                    needs_manual_check = True
                else:
                    needs_manual_check = False

                # Extract author and year from the citation
                author = clean_author(citation['author'])
                year = citation['year']
                citation_text = citation['citation_text']

                # Create the citation entry
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
                if idx == 0:
                    preceding_text = sentence[:start].strip()
                    has_entity = contains_relevant_entity(preceding_text)
                    if has_entity:
                        citation_content = get_last_special_phrase(preceding_text)
                        needs_manual_check = False
                    else:
                        citation_content = preceding_text
                        needs_manual_check = False
                else:
                    prev_end = citations_in_sentence[idx - 1]['end']
                    preceding_text = sentence[prev_end:start].strip()
                    has_entity = contains_relevant_entity(preceding_text)
                    if has_entity:
                        citation_content = get_last_special_phrase(preceding_text)
                        needs_manual_check = False
                    else:
                        citation_content = preceding_text
                        needs_manual_check = False

                # Kiểm tra nếu nội dung trích dẫn quá ngắn
                if len(citation_content.strip().split()) < 2 and not needs_manual_check:
                    needs_manual_check = True

                # **Gán giá trị cho ref_citations và citation_text**
                ref_citations = citation.get('ref_citations', [])
                citation_text = citation.get('original_citation_text', '')

                # Tạo citation_entry
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

def get_last_special_phrase(sentence):
    """
    Trả về cụm danh từ cuối cùng trong câu.

    Args:
        sentence (str): Câu cần phân tích.

    Returns:
        str: Cụm danh từ cuối cùng, hoặc chuỗi rỗng nếu không tìm thấy.
    """
    doc = nlp(sentence)
    noun_phrases = [chunk.text.strip() for chunk in doc.noun_chunks]
    if not noun_phrases:
        return ''
    return noun_phrases[-1]


def contains_relevant_entity(sentence):
    """
    Kiểm tra xem câu có chứa thực thể đặc biệt hay không và liệu last_noun_phrase có bằng với thực thể đặc biệt nào không.

    Args:
        sentence (str): Câu cần kiểm tra.
        log_file_path (str): Đường dẫn tới file log để ghi các thông tin in ra.

    Returns:
        bool: True nếu last_noun_phrase bằng với một thực thể đặc biệt, ngược lại trả về False.
    """
    with open("parenthetical_output.txt", 'a', encoding='utf-8') as log_file:
        # In và ghi nội dung của câu
        print(f"Sentence: {sentence}")
        log_file.write(f"Sentence: {sentence}\n")
        
        if not sentence:
            print("Sentence is empty.")
            log_file.write("Sentence is empty.\n")
            return False
        else:
            # Phân tích câu bằng spaCy
            doc = nlp(sentence)

            # Lấy danh sách các cụm danh từ trong câu
            noun_phrases = [chunk.text.strip() for chunk in doc.noun_chunks]
            if not noun_phrases:
                print("No noun phrases in the sentence.")
                log_file.write("No noun phrases in the sentence.\n")
                return False  # Không có cụm danh từ nào trong câu
            last_noun_phrase = noun_phrases[-1]
            print(f"Cụm danh từ cuối cùng: {last_noun_phrase}")
            log_file.write(f"Cụm danh từ cuối cùng: {last_noun_phrase}\n")

            # Lấy danh sách các thực thể đặc biệt trong câu
            science_entity_labels = [
                'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT',
                'WORK_OF_ART', 'LAW', 'LANGUAGE', 'DATE', 'TIME',
                'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL', 
            ]

            special_entities = [(ent.text.strip(), ent.label_) for ent in doc.ents if ent.label_ in science_entity_labels]
            print("Các thực thể đặc biệt:")
            log_file.write("Các thực thể đặc biệt:\n")
            for entity_text, entity_label in special_entities:
                print(f" - '{entity_text}' thuộc loại thực thể '{entity_label}'")
                log_file.write(f" - '{entity_text}' thuộc loại thực thể '{entity_label}'\n")

                if compare_strings_with_regex_any_word(entity_text, last_noun_phrase):
                    print(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' là một thực thể đặc biệt.")
                    log_file.write(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' là một thực thể đặc biệt.\n")
                    log_file.write(f'---------------------------- \n')


                    return True
                else:
                    print(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' không là một thực thể đặc biệt.")
                    log_file.write(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' không là một thực thể đặc biệt.\n")
                    log_file.write(f'---------------------------- \n')
                    return False

def compare_strings_with_regex_any_word(str1, str2):
    """
    Kiểm tra xem có bất kỳ từ nào trong str1 xuất hiện trong str2 hay không.

    Args:
        str1 (str): Chuỗi thứ nhất.
        str2 (str): Chuỗi thứ hai.

    Returns:
        bool: True nếu có ít nhất một từ trong str1 xuất hiện trong str2, ngược lại trả về False.
    """
    str1 = str1.lower()
    str2 = str2.lower()

    words_str1 = re.findall(r'\b\w+\b', str1)

    for word in words_str1:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, str2):
            # Nếu tìm thấy từ trong str2, trả về True
            return True
    # Nếu không tìm thấy từ nào, trả về False
    return False  
    
def count_total_citations(citations_data):
    """Hàm đếm tổng số lượng trích dẫn từ mảng citations."""
    total_citations = 0

    # Duyệt qua mỗi câu và đếm số lượng mục trong mảng citations
    for sentence_data in citations_data:
        total_citations += len(sentence_data['citations'])
    return total_citations