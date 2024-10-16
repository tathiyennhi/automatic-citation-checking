import spacy
# USED FOR NESTED CITATION CASE 
# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def extract_citations(sentence):
    doc = nlp(sentence)
    relevant_phrases = []
    current_phrase = ""
    start_index = 0

    def extract_full_phrase(start_index, end_index):
        """Trích xuất toàn bộ cụm từ từ start_index đến end_index."""
        phrase = ""
        for i in range(start_index, end_index):
            token = doc[i]
            phrase += token.text_with_ws
        return phrase.strip()

    for i, token in enumerate(doc):
        if token.text == "(":
            if start_index < i:
                current_phrase = extract_full_phrase(start_index, i).strip()
            start_index = i + 1
        elif token.text == ")":
            citation_content = extract_full_phrase(start_index, i).strip()
            full_citation = current_phrase.strip() + " (" + citation_content + ")"
            relevant_phrases.append(full_citation.strip())
            current_phrase = ""  # Reset current_phrase
            start_index = i + 1

    # Ghép nội dung còn lại sau trích dẫn cuối cùng vào trích dẫn trước đó
    if start_index < len(doc):
        remaining_content = extract_full_phrase(start_index, len(doc)).strip()
        if remaining_content:
            last_phrase = relevant_phrases[-1]
            relevant_phrases[-1] = last_phrase + " " + remaining_content

    # Loại bỏ từ đầu không phù hợp trong trích dẫn thứ hai
    if len(relevant_phrases) > 1:
        doc_second_phrase = nlp(relevant_phrases[1])
        first_important_token_index = next((i for i, token in enumerate(doc_second_phrase) if token.pos_ in ["NOUN", "PROPN", "PRON", "DET"]), None)
        
        if first_important_token_index is not None:
            relevant_phrases[1] = ' '.join([token.text_with_ws for token in doc_second_phrase[first_important_token_index:]]).strip()

    return relevant_phrases

# Ví dụ cụ thể để kiểm tra
# sentence = """The study (Smith, 2019; Johnson, 2020) shows that the model performs well (Lee, 2021)."""
# sentence = """collaboration patterns, and hidden research trends (Giles & Councill, 2004; Diaz-Faes & Bordons, 2017)."""
sentence = """We used a standard approach, where only a linear classifier layer was added on the top of the transformer, as adding the additional CRF decoder between the transformer and linear classifier did not increase accuracy compared with this standard approach (Schweter & Akbik, 2020)."""
result = extract_citations(sentence)

# In kết quả
print("----------")
print(f"sentence: \"{sentence}\"")
print(f"citations: {result}")
print("----------")
