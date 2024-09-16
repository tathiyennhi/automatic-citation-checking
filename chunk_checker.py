import spacy

# Tải mô hình Spacy
nlp = spacy.load("en_core_web_sm")

# Hàm kiểm tra thực thể đặc biệt cho từng token trong noun_chunk
def check_special_entities(noun_chunk):
    special_entities = []
    for token in noun_chunk:
        if token.ent_type_ in {"ORG", "PRODUCT", "WORK_OF_ART", "EVENT", "LANGUAGE", "LAW"}:
            special_entities.append(token.text)
    return special_entities

# Văn bản mẫu
text = "Acknowledged universities, interactions, knowledge exchange, industry, RoBERTA model."

# Xử lý văn bản
doc = nlp(text)

# Lấy các noun chunks từ văn bản
chunks = list(doc.noun_chunks)

# Lấy chunk cuối cùng
last_chunk = chunks[-1]  # Chunk cuối cùng

# Kiểm tra từng token trong chunk cuối cùng
special_tokens = check_special_entities(last_chunk)

if special_tokens:
    print(f"Các token đặc biệt trong chunk cuối cùng '{last_chunk}': {special_tokens}")
else:
    print(f"Không có token đặc biệt nào trong chunk cuối cùng '{last_chunk}'.")

# Lặp qua các token trong chunk cuối cùng và kiểm tra với special cases
special_cases = ["industry", "exchange", "RoBERTA"]
for token in last_chunk:
    if token.text in special_cases:
        print(f"Found special case: {token.text}")
