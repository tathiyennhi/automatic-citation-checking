# apa_module.py

import re
import spacy
from helper import clean_text

# Tải mô hình spaCy
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

def extract_citations_from_sentence(sentence):
    """
    Trích xuất tất cả các trích dẫn từ một câu.

    Args:
        sentence (str): Câu cần xử lý.

    Returns:
        list: Danh sách các trích dẫn tìm thấy trong câu.
    """
    citations = []

    # Mẫu regex cho trích dẫn narrative với negative lookbehind
    narrative_citation_regex = r'\b(?<!\d)(?P<author>[A-Z][a-zA-Z\'’\-]+(?:\s+(?:et\s+al\.?|and|&)\s*(?:[A-Z][a-zA-Z\'’\-]+)?)*)\s*\((?P<year>\d{4})\)'

    # Mẫu regex cho trích dẫn parenthetical với negative lookbehind
    parenthetical_citation_regex = r'\((?!\d)[^()]+\)'

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

        refs = re.split(r';\s*', citation_info)
        ref_citations = []
        for ref in refs:
            ref = ref.strip()
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

        refs = re.split(r';\s*', content)
        ref_citations = []
        for ref in refs:
            ref = ref.strip()
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

    citations.sort(key=lambda x: x['start'])

    return citations

def clean_author(author):
    """
    Làm sạch chuỗi tác giả bằng cách loại bỏ các phần không cần thiết.

    Args:
        author (str): Chuỗi tên tác giả.

    Returns:
        str: Chuỗi tên tác giả đã được làm sạch.
    """
    author = re.sub(r'^(?:additional previous work in this area includes|the work of|the special issue by|cited in|as cited in)\s+', '', author, flags=re.IGNORECASE)
    author = re.sub(r'\s+', ' ', author)
    author = author.strip()
    return author

def determine_citation_validity(content):
    """
    Xác định xem nội dung có phải là trích dẫn hợp lệ hay không.

    Args:
        content (str): Nội dung bên trong dấu ngoặc đơn.

    Returns:
        bool: True nếu là trích dẫn hợp lệ, ngược lại False.
    """
    has_year = re.search(r'\b\d{4}\b', content)
    has_author = re.search(r'\b[A-Z][a-zA-Z]+', content)
    is_too_short = len(content.strip()) < 3
    is_single_char = re.match(r'^[a-zA-Z0-9]$', content.strip())

    if has_year and has_author and not is_single_char and not is_too_short:
        return True
    else:
        return False

def extract_apa_citations_with_context(sentence):
    """
    Trích xuất trích dẫn APA từ một câu và kèm theo ngữ cảnh.

    Args:
        sentence (str): Câu cần xử lý.

    Returns:
        list: Danh sách các mục trích dẫn với ngữ cảnh.
    """
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
            if end == len(sentence.strip()):
                citation_content = sentence[:start].strip()
            elif start == 0:
                citation_content = get_following_content(sentence, end)
            else:
                citation_content = sentence.strip()

            if len(citation_content.strip().split()) < 2 or is_insignificant_text(citation_content):
                needs_manual_check = True
            else:
                needs_manual_check = False

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

            if len(citation_content.strip().split()) < 2 and not needs_manual_check:
                needs_manual_check = True

            ref_citations = citation.get('ref_citations', [])
            citation_text = citation.get('original_citation_text', '')

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

def get_following_content(sentence, citation_end):
    """
    Trả về nội dung sau vị trí kết thúc của trích dẫn trong câu.

    Args:
        sentence (str): Câu cần xử lý.
        citation_end (int): Vị trí kết thúc của trích dẫn.

    Returns:
        str: Nội dung phía sau trích dẫn.
    """
    return sentence[citation_end:].strip()

def is_insignificant_text(text):
    """
    Kiểm tra xem văn bản có chỉ chứa các từ không mang nhiều ý nghĩa hay không.

    Args:
        text (str): Văn bản cần kiểm tra.

    Returns:
        bool: True nếu văn bản không đáng kể, ngược lại False.
    """
    doc = nlp(text)
    insignificant_pos = ['CCONJ', 'SCONJ', 'ADP', 'PART', 'PUNCT', 'SPACE', 'ADV']
    for token in doc:
        if token.pos_ not in insignificant_pos:
            return False
    return True

def contains_relevant_entity(sentence):
    """
    Kiểm tra xem câu có chứa thực thể đặc biệt hay không.

    Args:
        sentence (str): Câu cần kiểm tra.

    Returns:
        bool: True nếu chứa thực thể đặc biệt, ngược lại False.
    """
    if not sentence:
        return False
    else:
        doc = nlp(sentence)
        noun_phrases = [chunk.text.strip() for chunk in doc.noun_chunks]
        if not noun_phrases:
            return False
        last_noun_phrase = noun_phrases[-1]

        science_entity_labels = [
            'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT',
            'WORK_OF_ART', 'LAW', 'LANGUAGE', 'DATE', 'TIME',
            'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL',
        ]

        special_entities = [(ent.text.strip(), ent.label_) for ent in doc.ents if ent.label_ in science_entity_labels]

        for entity_text, entity_label in special_entities:
            if compare_strings_with_regex_any_word(entity_text, last_noun_phrase):
                return True
        return False

def compare_strings_with_regex_any_word(str1, str2):
    """
    Kiểm tra xem có bất kỳ từ nào trong str1 xuất hiện trong str2 hay không.

    Args:
        str1 (str): Chuỗi thứ nhất.
        str2 (str): Chuỗi thứ hai.

    Returns:
        bool: True nếu có từ trùng khớp, ngược lại False.
    """
    str1 = str1.lower()
    str2 = str2.lower()

    words_str1 = re.findall(r'\b\w+\b', str1)

    for word in words_str1:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, str2):
            return True
    return False

def get_last_special_phrase(sentence):
    """
    Trả về cụm danh từ cuối cùng trong câu.

    Args:
        sentence (str): Câu cần xử lý.

    Returns:
        str: Cụm danh từ cuối cùng hoặc chuỗi rỗng nếu không tìm thấy.
    """
    doc = nlp(sentence)
    noun_phrases = [chunk.text.strip() for chunk in doc.noun_chunks]
    if not noun_phrases:
        return ''
    return noun_phrases[-1]
