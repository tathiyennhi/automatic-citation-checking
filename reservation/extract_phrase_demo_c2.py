import spacy

# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def extract_citation(sentence):
    doc = nlp(sentence)
    relevant_phrase = ""
    citation = ""
    in_citation = False
    last_quote_start = None
    last_quote_end = None

    for i, token in enumerate(doc):
        # Xác định vị trí dấu ngoặc kép mở cuối cùng
        if token.text == "“":
            last_quote_start = i
        
        # Xác định vị trí dấu ngoặc kép đóng cuối cùng
        if token.text == "”":
            last_quote_end = i

        # Bắt đầu trích dẫn nếu phát hiện dấu ngoặc mở "("
        if token.text == "(":
            in_citation = True
            if last_quote_start is not None and last_quote_end is not None:
                # Chỉ lấy nội dung trong dấu ngoặc kép gần nhất trước dấu ngoặc tròn mở, bỏ qua dấu ngoặc kép mở
                relevant_phrase = "".join([doc[j].text_with_ws for j in range(last_quote_start + 1, last_quote_end + 1)])
            citation += token.text  # Bắt đầu thêm vào phần trích dẫn
            continue

        # Kết thúc trích dẫn khi phát hiện dấu ngoặc đóng ")"
        if token.text == ")" and in_citation:
            in_citation = False
            citation += token.text
            relevant_phrase += citation.strip()
            citation = ""
            continue

        # Xử lý nội dung của trích dẫn trong ngoặc đơn
        if in_citation:
            if token.text in [".", ",", ";"]:
                citation = citation.strip() + token.text + " "
            else:
                citation += token.text + " "
            continue

    return relevant_phrase.strip()

# Các ví dụ câu để kiểm tra
sentences = [
    "Acknowledgments in scientific papers are short texts where the author(s) “identify those who made special intellectual or technical contribution to a study that are not sufficient to qualify them for authorship” (Kassirer & Angell, 1991, p. 1511)."
]

results = []

for sentence in sentences:
    result = extract_citation(sentence)
    results.append((sentence, result))

# In kết quả theo định dạng mong muốn
for original, extracted in results:
    print("----------")
    print(f"sentence: \"{original}\"")
    print(f"citation: \"{extracted}\"")
    print("----------")
