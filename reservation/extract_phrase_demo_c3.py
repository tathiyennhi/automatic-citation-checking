import spacy

# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def extract_citation(sentence):
    doc = nlp(sentence)
    relevant_phrases = []
    current_phrase = ""
    start_index = 0

    def extract_full_phrase(start_index, end_index):
        """Extract full phrase starting with DET, NOUN, or PRONOUN."""
        phrase = ""
        found_noun = False
        for i in range(start_index, end_index):
            token = doc[i]
            if token.pos_ in ["DET", "NOUN", "PROPN", "ADJ"]:
                found_noun = True
            if found_noun:
                phrase += token.text_with_ws
        return phrase.strip()

    for i, token in enumerate(doc):
        if token.text == "(":
            # Trích xuất cụm từ trước dấu ngoặc mở
            if start_index < i:
                current_phrase = extract_full_phrase(start_index, i).strip()
                current_phrase += " " + token.text
            start_index = i + 1

        elif token.text == ")":
            # Ghép nội dung trong ngoặc và thêm vào danh sách
            current_phrase += extract_full_phrase(start_index, i + 1).strip()
            relevant_phrases.append(current_phrase.strip())
            current_phrase = ""
            start_index = i + 1

    return relevant_phrases

# Case cụ thể để kiểm tra
sentence = "The study (Smith, 2019; Johnson, 2020) shows that the model performs well (Lee, 2021)."

result = extract_citation(sentence)

# In kết quả
print("----------")
print(f"sentence: \"{sentence}\"")
print(f"citations: {result}")
print("----------")
