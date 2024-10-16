import spacy

# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def extract_integrated_citation(sentence):
    doc = nlp(sentence)
    citation = None
    content = []
    
    # Duyệt qua các token để xác định trích dẫn
    for token in doc:
        if "(" in token.text and ")" in token.text:  # Kiểm tra nếu token chứa tên tác giả và năm
            citation = token.text
        else:
            content.append(token.text)

    if citation:
        return f"Citation: {citation}, Content before citation: {' '.join(content)}"
    else:
        return "No citation found."

# Ví dụ câu
sentence = "The study conducted by Smith (2020) shows significant results."
result = extract_integrated_citation(sentence)
print(result)
