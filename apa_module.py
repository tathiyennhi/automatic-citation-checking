import re
import spacy

try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    # logging.info("Mô hình SpaCy 'en_core_web_lg' chưa được tải. Đang tải mô hình...")
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")


def clean_text(text):
    """
    Loại bỏ ký tự xuống dòng, tab, carriage return, dấu gạch ngang ở cuối dòng
    và thay thế bằng dấu cách. Đồng thời loại bỏ các dấu gạch ngang không hợp lệ.
    """
    # Bước 1: Loại bỏ dấu gạch ngang từ ngắt dòng trước khi thay thế các ký tự đặc biệt
    text = remove_hyphenation(text)
    
    # Bước 2: Thay thế \n, \r, \t bằng dấu cách
    text = re.sub(r'[\n\r\t]+', ' ', text)
    
    # Bước 3: Thay thế các khoảng trắng liên tiếp bằng một dấu cách duy nhất
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def remove_hyphenation(text):
    """
    Loại bỏ các dấu gạch ngang được sử dụng để ngắt dòng mà không làm mất dấu gạch ngang hợp lệ trong từ.
    """
    # Loại bỏ dấu gạch ngang ở cuối dòng (hyphenation)
    # Giả sử dấu gạch ngang này luôn theo sau bởi xuống dòng hoặc khoảng trắng
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # Loại bỏ dấu gạch ngang giữa các chữ cái nếu chúng được ngắt dòng
    # Ví dụ: "co-\noperation" thành "cooperation"
    text = re.sub(r'(\w+)-\s*(\w+)', r'\1\2', text)
    
    return text


def extract_citations_from_sentence(sentence):
    """Trích xuất tất cả các trích dẫn từ một câu."""
    sentence = clean_text(sentence)
    citations = []
    
    # Mẫu regex cho trích dẫn narrative
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


def extract_apa_citations_with_context(sentence):
    """Trích xuất trích dẫn từ một câu."""
    # Trích xuất các trích dẫn từ câu
    citations_in_sentence = extract_citations_from_sentence(sentence)
    results = []

    if not citations_in_sentence:
        return results

    citation_entries = []
    citation_count = len(citations_in_sentence)

    for idx, citation in enumerate(citations_in_sentence):
        citation_type = citation['type']
        start = citation['start']
        end = citation['end']
        needs_manual_check = False

        if citation_type == 'narrative':
            # Kiểm tra nếu trích dẫn ở cuối câu
            if end == len(sentence.strip()):
                # Nếu trích dẫn ở cuối câu, lấy nội dung trước trích dẫn
                citation_content = sentence[:start].strip()
            # Kiểm tra nếu trích dẫn ở đầu câu
            elif start == 0:
                # Nếu trích dẫn ở đầu câu, lấy nội dung sau trích dẫn
                citation_content = get_following_content(sentence, end)
            else:
                # Nếu trích dẫn ở giữa, lấy toàn bộ câu
                citation_content = sentence.strip()

            # Đảm bảo không có văn bản không liên quan hoặc không đáng kể
            if len(citation_content.strip().split()) < 2 or is_insignificant_text(citation_content):
                needs_manual_check = True
            else:
                needs_manual_check = False

            # Trích xuất thông tin tác giả và năm từ trích dẫn
            author = clean_author(citation['author'])
            year = citation['year']
            citation_text = citation['citation_text']

            # Tạo entry cho citation
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

        else:  # parenthetical citation
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

    # Thêm thông tin về câu và số lượng trích dẫn
    results.append({
        'original_sentence': sentence,
        'citation_count': citation_count,
        'citations': citation_entries
    })

    return results

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