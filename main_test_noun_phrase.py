import spacy

# Tải mô hình ngôn ngữ SpaCy lớn
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("Mô hình SpaCy 'en_core_web_lg' chưa được tải. Đang tải mô hình...")
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

def contains_relevant_entity(noun_phrase):
    """
    Kiểm tra xem noun_phrase có chứa thực thể đặc biệt (PRODUCT, MODEL, ORG, WORK_OF_ART) hay không.
    In ra tất cả các thực thể và vị trí của chúng.

    Args:
        noun_phrase (str): Văn bản được phân tích.

    Returns:
        bool: True nếu có ít nhất một thực thể đặc biệt.
    """
    if not noun_phrase:  # Kiểm tra nếu noun_phrase rỗng
        return False

    # Phân tích noun_phrase bằng SpaCy NER
    doc = nlp(noun_phrase)

    # Biến để theo dõi xem có thực thể đặc biệt không
    has_special_entity = False

    # Duyệt qua các thực thể trong noun_phrase để kiểm tra loại thực thể
    print("Danh sách các thực thể trong câu:")
    for ent in doc.ents:
        print(f" - Thực thể: '{ent.text}', Nhãn: {ent.label_}, Vị trí: {ent.start_char}-{ent.end_char}")
        if ent.label_ in ['PRODUCT', 'MODEL', 'ORG', 'WORK_OF_ART']:
            has_special_entity = True
            print(f"   -> Thực thể đặc biệt được tìm thấy: '{ent.text}', Vị trí: {ent.start_char}-{ent.end_char}")

    return has_special_entity  # Trả về True nếu có thực thể đặc biệt

if __name__ == "__main__":
    # Test câu ví dụ
    test_sentence = "On the one hand, Flair developers claimed Transformers to be the most efficient algorithm (Schweter & Akbik, 2020)."

    # Kiểm tra xem câu có chứa thực thể đặc biệt không
    if contains_relevant_entity(test_sentence):
        print("The sentence contains a relevant entity.")
    else:
        print("The sentence does not contain a relevant entity.")