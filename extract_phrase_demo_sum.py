import re
import spacy
from spacy.matcher import Matcher

# Tải mô hình ngôn ngữ của SpaCy
nlp = spacy.load("en_core_web_sm")

def extract_citations_with_context(text):
    doc = nlp(text)
    
    matcher = Matcher(nlp.vocab)

    # Mẫu nhận diện tác giả
    author_pattern = [
        {"ENT_TYPE": "PERSON"},
        {"IS_SPACE": True, "OP": "*"},
        {"LOWER": {"IN": ["and", "&"]}, "OP": "?"},
        {"ENT_TYPE": "PERSON", "OP": "+"},
    ]
    
    matcher.add("AUTHOR_PATTERN", [author_pattern])

    # Tìm các thực thể có tên
    matches = matcher(doc)
    author_tokens = []
    for match_id, start, end in matches:
        span = doc[start:end]
        author_tokens.append((span.text, start, end))
    
    # Xử lý các trích dẫn trong dấu ngoặc đơn
    citation_matches = list(re.finditer(r'\((.*?)\)', text))
    results = []
    previous_end = 0
    
    for i, match in enumerate(citation_matches):
        start, end = match.span()
        citation_content = match.group(1).strip()

        # Tìm tên tác giả gần nhất trước dấu ngoặc đơn
        author = ""
        preceding_text = text[previous_end:start].strip()
        following_text = text[end:].strip()

        for (author_text, author_start, author_end) in reversed(author_tokens):
            if author_end <= start:
                author = author_text
                break
        
        # Xử lý phần nội dung trích dẫn trực tiếp (có số trang/chương)
        citation_parts = citation_content.split(',')
        if len(citation_parts) >= 3:
            year = citation_parts[1].strip()
            page_chapter_info = citation_parts[2].strip()
            citation_full = f"{author}, {year}, {page_chapter_info}"
            citation_type = 'direct'
        elif len(citation_parts) == 2:
            year = citation_parts[1].strip()
            citation_full = f"{author}, {year}"
            citation_type = 'regular'
        else:
            citation_full = f"{author} {citation_content}"
            citation_type = 'regular'

        # Kiểm tra nếu đây là trích dẫn lồng
        is_nested = False
        for j, other_match in enumerate(citation_matches):
            if i != j:
                other_start, other_end = other_match.span()
                if start > other_start and end < other_end:
                    is_nested = True
                    break

        citation_type = 'nested' if is_nested else citation_type

        # Nếu là trích dẫn trực tiếp, lấy cả phần trước và sau dấu ngoặc đơn
        if citation_type == 'direct':
            content = f"{preceding_text} {following_text}".strip()
        else:
            # Nếu không, chỉ lấy phần trước hoặc sau tùy vào vị trí trích dẫn
            content = preceding_text if preceding_text else following_text

        # Lưu kết quả
        results.append({
            'citation': citation_full,
            'content': content.strip(),
            'type': citation_type
        })
        
        previous_end = end
    
    return results

# Ví dụ về câu văn với các loại trích dẫn khác nhau
sentence = """Thomer and Weber (2014, p. 23) used the 4-class Stanford Entity Recognizer (Finkel et al., 2005, ch. 2) 
in their study. 'This method is highly effective' (Smith, 2020). Several studies (Johnson, 2018; Doe, 2019) have shown similar results.
Another study (Miller, 2021; Brown, 2022) also supports this claim. Nested citation example: (Doe, 2023 (Smith, 2020))."""

# Gọi hàm xử lý
citations = extract_citations_with_context(sentence)

# In kết quả
for i, citation in enumerate(citations):
    print(f"Citation {i+1}: {citation['citation']}")
    print(f"Content: {citation['content']}")
    print(f"Type: {citation['type']}\n")
