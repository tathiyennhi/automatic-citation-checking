import re
import spacy

# Tải mô hình ngôn ngữ SpaCy lớn
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("Mô hình SpaCy 'en_core_web_lg' chưa được tải. Đang tải mô hình...")
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

# def contains_relevant_entity(sentence):
#     """
#     Kiểm tra xem câu có chứa thực thể đặc biệt hay không và liệu last_noun_phrase có bằng với thực thể đặc biệt nào không.

#     Args:
#         sentence (str): Câu cần kiểm tra.

#     Returns:
#         bool: True nếu last_noun_phrase bằng với một thực thể đặc biệt, ngược lại trả về False.
#     """
#     print(sentence)
#     if not sentence:
#         return False
#     else:
#         # Phân tích câu bằng spaCy
#         doc = nlp(sentence)

#         # Lấy danh sách các cụm danh từ trong câu
#         noun_phrases = [chunk.text.strip() for chunk in doc.noun_chunks]
#         if not noun_phrases:
#             return False  # Không có cụm danh từ nào trong câu
#         last_noun_phrase = noun_phrases[-1]
#         print("Cụm danh từ cuối cùng:", last_noun_phrase)

#         # Lấy danh sách các thực thể đặc biệt trong câu
#         science_entity_labels = [
#             'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT',
#             'WORK_OF_ART', 'LAW', 'LANGUAGE', 'DATE', 'TIME',
#             'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL', 'CARDINAL',
#         ]

#         special_entities = [(ent.text.strip(), ent.label_) for ent in doc.ents if ent.label_ in science_entity_labels]
#         print("Các thực thể đặc biệt:")
#         for entity_text, entity_label in special_entities:
#             print(f" - '{entity_text}' thuộc loại thực thể '{entity_label}'")

#             if compare_strings_with_regex_any_word(entity_text, last_noun_phrase):
#                 print(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' là một thực thể đặc biệt.")
#                 return True
#             else:
#                 print(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' không là một thực thể đặc biệt.")
#                 return False
#         # Tạo danh sách các văn bản của thực thể đặc biệt
#         special_entity_texts = [entity_text for entity_text, _ in special_entities]

#         # Kiểm tra nếu last_noun_phrase có bằng với bất kỳ văn bản thực thể đặc biệt nào
def contains_relevant_entity(sentence):
    """
    Kiểm tra xem câu có chứa thực thể đặc biệt hay không và liệu last_noun_phrase có bằng với thực thể đặc biệt nào không.

    Args:
        sentence (str): Câu cần kiểm tra.

    Returns:
        bool: True nếu last_noun_phrase bằng với một thực thể đặc biệt, ngược lại trả về False.
    """
    print(sentence)
    if not sentence:
        return False
    else:
        # Phân tích câu bằng spaCy
        doc = nlp(sentence)

        # Lấy danh sách các cụm danh từ trong câu
        noun_phrases = [chunk.text.strip() for chunk in doc.noun_chunks]
        if not noun_phrases:
            return False  # Không có cụm danh từ nào trong câu
        last_noun_phrase = noun_phrases[-1]
        print("Cụm danh từ cuối cùng:", last_noun_phrase)

        # Lấy danh sách các thực thể đặc biệt trong câu
        science_entity_labels = [
            'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT',
            'WORK_OF_ART', 'LAW', 'LANGUAGE', 'DATE', 'TIME',
            'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL', 'CARDINAL',
        ]

        special_entities = [(ent.text.strip(), ent.label_) for ent in doc.ents if ent.label_ in science_entity_labels]
        print("Các thực thể đặc biệt:")
        for entity_text, entity_label in special_entities:
            print(f" - '{entity_text}' thuộc loại thực thể '{entity_label}'")

        # Kiểm tra nếu có thực thể đặc biệt nào trùng với cụm danh từ cuối cùng
        for entity_text, entity_label in special_entities:
            if compare_strings_with_regex_any_word(entity_text, last_noun_phrase):
                print(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' là một thực thể đặc biệt.")
                return True
            else:
                print(f"   -> Cụm danh từ cuối cùng '{last_noun_phrase}' không là một thực thể đặc biệt.")

        # Kiểm tra thực thể đặc biệt cuối cùng nếu không tìm thấy cụm danh từ trùng khớp
        if special_entities:
            last_special_entity = special_entities[-1][0]
            print(f"Thực thể đặc biệt cuối cùng: {last_special_entity}")
            if compare_strings_with_regex_any_word(last_special_entity, sentence):
                return True

        return False


def compare_strings_with_regex_any_word(str1, str2):
    """
    Kiểm tra xem có bất kỳ từ nào trong str1 xuất hiện trong str2 hay không.

    Args:
        str1 (str): Chuỗi thứ nhất.
        str2 (str): Chuỗi thứ hai.

    Returns:
        bool: True nếu có ít nhất một từ trong str1 xuất hiện trong str2, ngược lại trả về False.
    """
    str1 = str1.lower()
    str2 = str2.lower()

    words_str1 = re.findall(r'\b\w+\b', str1)

    for word in words_str1:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, str2):
            # Nếu tìm thấy từ trong str2, trả về True
            return True
    # Nếu không tìm thấy từ nào, trả về False
    return False  

if __name__ == "__main__":
    # Test câu ví dụ
    test_sentence = "For instance, PGRA"
    # Kiểm tra xem câu có chứa thực thể đặc biệt không
    if contains_relevant_entity(test_sentence):
        print("The sentence contains a relevant entity.")
    else:
        print("The sentence does not contain a relevant entity.")

# import spacy

# # Tải mô hình ngôn ngữ của spaCy
# nlp = spacy.load("en_core_web_sm")

# # Câu cần phân tích
# text = "This model employs PubMedBERT"

# # Phân tích văn bản với spaCy
# doc = nlp(text)

# # In các thực thể và loại thực thể
# for ent in doc.ents:
#     print("Từ:", ent.text, "thuộc: ", ent.label_)
