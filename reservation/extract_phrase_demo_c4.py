import spacy

# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def extract_citations(sentence):
    doc = nlp(sentence)
    relevant_phrases = []
    start_index = 0
    current_phrase = ""

    def extract_full_phrase(start_index, end_index):
        """Extract full phrase up to end_index."""
        phrase = ""
        for i in range(start_index, end_index):
            token = doc[i]
            phrase += token.text_with_ws
        return phrase.strip()

    for i, token in enumerate(doc):
        if token.text == "(":
            # Lưu lại phần nội dung trước dấu ngoặc mở
            if start_index < i:
                current_phrase = extract_full_phrase(start_index, i).strip()
            start_index = i + 1

        elif token.text == ")":
            # Trích xuất nội dung bên trong dấu ngoặc đơn
            citation_content = extract_full_phrase(start_index, i).strip()
            full_citation = current_phrase.strip() + " (" + citation_content + ")"
            relevant_phrases.append(full_citation.strip())
            current_phrase = ""  # Đặt lại current_phrase để bắt đầu trích dẫn mới
            start_index = i + 1

    # Xử lý phần nội dung còn lại sau trích dẫn cuối cùng
    if start_index < len(doc):
        remaining_content = extract_full_phrase(start_index, len(doc)).strip()
        if relevant_phrases:
            relevant_phrases[0] += " " + remaining_content
        else:
            relevant_phrases.append(remaining_content)

    # Xóa từ liên kết khỏi trích dẫn thứ hai nếu cần
    if len(relevant_phrases) > 1:
        linking_words = ["used", "employed", "utilized"]
        first_word = relevant_phrases[1].split()[0]
        if first_word in linking_words:
            relevant_phrases[1] = relevant_phrases[1][len(first_word):].strip()

    return relevant_phrases

# Case cụ thể để kiểm tra
sentence = """Thomer and Weber (2014, p. 23) used the 4-class Stanford Entity Recognizer (Finkel et al., 2005, ch. 2) 
to extract persons, locations, organizations, and miscellaneous entities from the collection of bioinformatics texts from PubMed Central’s Open Access corpus."""

result = extract_citations(sentence)

# In kết quả
print("----------")
print(f"sentence: \"{sentence}\"")
print(f"citations: {result}")
print("----------")
