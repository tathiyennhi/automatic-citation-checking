import re

def extract_title_from_reference(reference):
    """
    Trích xuất tiêu đề từ một tham chiếu dựa trên việc nó nằm giữa dấu chấm đầu tiên và dấu chấm thứ hai.
    """
    # Tách nội dung giữa hai dấu chấm đầu tiên
    matches = re.search(r'\.\s*(.*?)\.\s+', reference)
    
    if matches:
        title = matches.group(1).strip()
        return title
    else:
        return "Title not found"

# Ví dụ sử dụng
references = [
    "Satanjeev Banerjee and Alon Lavie. METEOR: An automatic metric for MT evaluation with improved correlation with human judgments. In Proceedings of the acl workshop on intrinsic and extrinsic evaluation measures for machine translation and/or summarization, pages 65–72, 2005.",
    "Matthew Edgar. Schema and structured data markup. In Tech SEO Guide: A Reference Guide for Developers and Marketers Involved in Technical SEO, pages 67–78. Springer, 2023.",
    "Abdullah Al Foysal and Ronald B¨ock. Who Needs External References?—Text Summarization Evaluation Using Original Documents. AI, 4(4):970–995, 2023."
]

for reference in references:
    title = extract_title_from_reference(reference)
    print(f"Title: {title}")
