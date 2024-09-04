import spacy

# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def get_largest_meaningful_phrase(sentence):
    doc = nlp(sentence)
    citation_index = None
    largest_phrase = []

    # Xác định vị trí của dấu ngoặc đơn mở '('
    for token in doc:
        if token.text == "(":
            citation_index = token.i
            break

    if citation_index is not None:
        # Duyệt ngược từ vị trí dấu ngoặc đơn để tìm cụm từ lớn nhất có nghĩa
        for token in reversed(doc[:citation_index]):
            # Thêm từ vào cụm từ nếu nó là một phần của cụm danh từ hoặc tính từ
            if token.dep_ in ("compound", "amod", "nmod", "appos", "poss", "det", "nsubj", "dobj", "pobj", "attr"):
                largest_phrase.insert(0, token.text)  # Thêm từ vào đầu danh sách để giữ đúng thứ tự
            elif token.dep_ in ("ROOT", "prep", "punct"):
                break  # Dừng khi gặp từ gốc hoặc dấu câu vì đó là giới hạn cụm từ
            else:
                largest_phrase.insert(0, token.text)  # Thêm từ vào cụm từ

    if largest_phrase:
        return " ".join(largest_phrase)
    else:
        return "No meaningful phrase found"

# Ví dụ câu có trích dẫn
# sentence = "The new approach is based on the GPT model (Radford et al., 2018)."
sentence = """
Acknowledgments of 
technical and instrumental support may reveal “indirect contributions of research labora-
tories and universities to research activities” (Giles & Councill, 2004, p. 17599).
"""


largest_phrase = get_largest_meaningful_phrase(sentence)
print(f"Largest meaningful phrase before the citation: {largest_phrase}")
