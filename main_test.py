# import re

# def extract_title_from_reference(reference):
#     """
#     Trích xuất tiêu đề từ một tham chiếu dựa trên việc nó nằm giữa dấu chấm đầu tiên và dấu chấm thứ hai.
#     """
#     # Tách nội dung giữa hai dấu chấm đầu tiên
#     matches = re.search(r'\.\s*(.*?)\.\s+', reference)
    
#     if matches:
#         title = matches.group(1).strip()
#         return title
#     else:
#         return "Title not found"

# # Ví dụ sử dụng
# references = [
#     "Satanjeev Banerjee and Alon Lavie. METEOR: An automatic metric for MT evaluation with improved correlation with human judgments. In Proceedings of the acl workshop on intrinsic and extrinsic evaluation measures for machine translation and/or summarization, pages 65–72, 2005.",
#     "Matthew Edgar. Schema and structured data markup. In Tech SEO Guide: A Reference Guide for Developers and Marketers Involved in Technical SEO, pages 67–78. Springer, 2023.",
#     "Abdullah Al Foysal and Ronald B¨ock. Who Needs External References?—Text Summarization Evaluation Using Original Documents. AI, 4(4):970–995, 2023."
# ]

# for reference in references:
#     title = extract_title_from_reference(reference)
#     print(f"Title: {title}")

# import re

# def extract_title_from_reference(reference):
#     """
#     Trích xuất tiêu đề từ một tham chiếu, bao gồm xử lý các trường hợp sách và bài báo khác nhau.

#     Args:
#         reference (str): Tham chiếu nguồn.

#     Returns:
#         str: Tiêu đề trích xuất được.
#     """
#     # Kiểm tra xem tham chiếu có chứa cụm từ "In " không (gợi ý đây là một phần của sách)
#     if "In " in reference:
#         # Tách tiêu đề bao gồm cả phần tên sách
#         matches = re.search(r'\.\s*(.*?In\s.*?)(?:,|\.)', reference)
#     else:
#         # Tách tiêu đề chỉ giữa hai dấu chấm đầu tiên
#         matches = re.search(r'\.\s*(.*?)\.\s+', reference)

#     if matches:
#         title = matches.group(1).strip()
#         return title
#     else:
#         return "Title not found"

# # Ví dụ sử dụng
# references = [
#     "Satanjeev Banerjee and Alon Lavie. METEOR: An automatic metric for MT evaluation with improved correlation with human judgments. In Proceedings of the acl workshop on intrinsic and extrinsic evaluation measures for machine translation and/or summarization, pages 65–72, 2005.",
#     "Matthew Edgar. Schema and structured data markup. In Tech SEO Guide: A Reference Guide for Developers and Marketers Involved in Technical SEO, pages 67–78. Springer, 2023.",
#     "Abdullah Al Foysal and Ronald B¨ock. Who Needs External References?—Text Summarization Evaluation Using Original Documents. AI, 4(4):970–995, 2023.",
#     "Neil Jethani, Simon Jones, Nicholas Genes, Vincent J Major, Ian S Jaffe, Anthony B Cardillo, Noah Heilenbach, Nadia Fazal Ali, Luke J Bonanni, Andrew J Clayburn, et al. Evaluating ChatGPT in Information Extraction: A Case Study of Extracting Cognitive Exam Dates and Scores. 2023.",
#     "Yuri Kuratov, Aydar Bulatov, Petr Anokhin, Dmitry Sorokin, Artyom Sorokin, and Mikhail Burtsev. In Search of Needles in a 11M Haystack: Recurrent Memory Finds What LLMs Miss. arXiv preprint arXiv:2402.10790v2, 2024.",
#     "Dong-Ho Lee, Jay Pujara, Mohit Sewak, Ryen W White, and Sujay Kumar Jauhar. Making large language models better data creators. arXiv preprint arXiv:2310.20111, 2023.",
#     "Nelson F Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, and Percy Liang. Lost in the middle: How language models use long contexts. arXiv preprint arXiv:2307.03172, 2023.",
#     "Derong Xu, Wei Chen, Wenjun Peng, Chao Zhang, Tong Xu, Xiangyu Zhao, Xian Wu, Yefeng Zheng, and Enhong Chen. Large language models for generative information extraction: A survey. arXiv preprint arXiv:2312.17617, 2023."
# ]

# for reference in references:
#     title = extract_title_from_reference(reference)
#     print(f"Title: {title}")


#hàm test trích xuất câu chứa trích dẫn
# import re

# def clean_text(text):
#     """
#     Làm sạch văn bản bằng cách loại bỏ các ký tự xuống dòng, dấu gạch ngang,
#     khoảng trắng không cần thiết và các ký tự đặc biệt.
#     """
#     # Thay thế ký tự xuống dòng, tab, và khoảng trắng dư thừa bằng dấu cách
#     text = re.sub(r'[\n\t\r]+', ' ', text)

#     # Loại bỏ khoảng trắng dư thừa
#     text = re.sub(r'\s+', ' ', text).strip()

#     return text

# def extract_ieee_citations_from_sentence(sentence):
#     """
#     Trích xuất các trích dẫn IEEE từ một câu.

#     Args:
#         sentence (str): Câu cần xử lý.

#     Returns:
#         list: Danh sách các trích dẫn IEEE trong câu.
#     """
#     citations = []
#     # Mẫu trích dẫn IEEE: [số], [số, p. số]
#     ieee_pattern = re.compile(r'\[(\d+)(?:,\s*p\.?\s*(\d+))?\]')

#     for match in re.finditer(ieee_pattern, sentence):
#         citation_number = match.group(1)
#         page_number = match.group(2) if match.group(2) else None
#         citations.append({
#             'citation_number': citation_number,
#             'page_number': page_number,
#             'original_text': match.group(0),
#             'start': match.start(),
#             'end': match.end()
#         })
#     return citations

# def extract_ieee_citations_with_context(sentences):
#     """
#     Trích xuất các trích dẫn IEEE từ các câu và trả về nội dung trích dẫn.

#     Args:
#         sentences (list): Danh sách các câu đã trích xuất.

#     Returns:
#         list: Danh sách các trích dẫn với thông tin liên quan.
#     """
#     citation_entries = []

#     for sentence in sentences:
#         cleaned_sentence = clean_text(sentence)
#         ieee_citations = extract_ieee_citations_from_sentence(cleaned_sentence)

#         for citation in ieee_citations:
#             citation_start = citation['start']
#             citation_end = citation['end']
            
#             # Lấy nội dung trước và sau trích dẫn, loại bỏ số trích dẫn
#             citation_content = (cleaned_sentence[:citation_start].rstrip() + " " + cleaned_sentence[citation_end:].lstrip()).strip()

#             # Loại bỏ dấu chấm thừa nếu có
#             citation_content = re.sub(r'\.\s*$', '', citation_content)

#             citation_entry = {
#                 'original_sentence': cleaned_sentence,
#                 'citation_number': f"[{citation['citation_number']}]",
#                 'page_number': citation['page_number'],
#                 'citation_content': citation_content.strip()  # Xóa khoảng trắng dư thừa
#             }
#             citation_entries.append(citation_entry)

#     return citation_entries

# # Test câu với trích dẫn
# sentences = ["LLMs are rather effective with the creation of structured data with predefined types and attributes (properties), cf. [8]."]
# citation_entries = extract_ieee_citations_with_context(sentences)

# # In ra kết quả
# for entry in citation_entries:
#     print(f"Câu chứa trích dẫn: {entry['original_sentence']}")
#     print(f"Số trích dẫn: {entry['citation_number']}")
#     print(f"Nội dung trích dẫn: {entry['citation_content']}")

import re

def is_references_section(sentence):
    """
    Kiểm tra xem câu có phải là phần 'References' không.
    """
    return re.match(r'^references$', sentence.strip(), re.IGNORECASE)

def is_reference_entry(sentence):
    """
    Kiểm tra xem câu có phải là một mục tham chiếu trong phần 'References' không.
    """
    return re.match(r'^\[\d+\]', sentence.strip())

def extract_ieee_citations_from_sentence(sentence, in_references_section=False):
    """
    Trích xuất các trích dẫn IEEE từ một câu nếu không phải là mục tham chiếu trong phần 'References'.
    """
    if in_references_section and is_reference_entry(sentence):
        return []  # Bỏ qua mục tham chiếu trong phần 'References'

    citations = []
    ieee_pattern = re.compile(r'\[(\d+)(?:,\s*p\.?\s*(\d+))?\]')

    for match in re.finditer(ieee_pattern, sentence):
        citation_number = match.group(1)
        page_number = match.group(2) if match.group(2) else None
        citations.append({
            'sentence': sentence,
            'citation_number': citation_number,
            'page_number': page_number,
            'original_text': match.group(0),
            # 'start': match.start(),
            # 'end': match.end()
        })
    
    if citations:
        print("Citations:", citations)
    return citations

def process_sentences(sentences):
    """
    Xử lý các câu trong tài liệu, phát hiện trích dẫn và phần 'References'.
    """
    in_references_section = False

    for sentence in sentences:
        # Kiểm tra xem có phải là phần 'References' không
        if is_references_section(sentence):
            in_references_section = True
            continue

        # Trích xuất trích dẫn nếu không nằm trong mục tham chiếu phần 'References'
        citations = extract_ieee_citations_from_sentence(sentence, in_references_section)

# Ví dụ sử dụng
sentences = [
    "This is an introduction.",
    "A survey by [8] details the progress of LLMs on IE tasks.",
    "References",
    "[1] Satanjeev Banerjee and Alon Lavie.",
    "Appendix",
    "[8] Derong Xu, Wei Chen, Wenjun Peng, Chao Zhang, Tong Xu, Xiangyu Zhao, Xian Wu, Yefeng Zheng, and Enhong Chen."
]

process_sentences(sentences)

