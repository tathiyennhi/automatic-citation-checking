# main.py

import logging
from helper import (
    extract_sentences_from_docx,
    detect_citation_format,
    extract_text_from_docx,
    crawl_references,
    generate_json_output,
    convert_pdf_to_docx
)
from ieee_module import (
    extract_references as extract_ieee_references,
    extract_ieee_citations_with_context,
)
import apa_module

def main():
    """
    Hàm chính của chương trình. Thực hiện việc đọc tệp DOCX, xác định định dạng trích dẫn,
    và gọi các module tương ứng để xử lý trích dẫn.
    """
    logging.basicConfig(level=logging.INFO)
    pdf_file = "paper.pdf" 
    docx_file = "paper.docx"
    output_sentences_file = "paper_spacy_sentences.txt"

    try:
        # Chuyển đổi PDF sang DOCX nếu cần
        docx_file = convert_pdf_to_docx(pdf_file, docx_file)

        # Đọc văn bản từ DOCX
        text = extract_text_from_docx(docx_file)
        citation_type = detect_citation_format(text)

        if citation_type == "IEEE":
            # Trích xuất câu từ DOCX, loại bỏ chỉ phần 'References'
            sentences = extract_sentences_from_docx(
                docx_file, output_sentences_file, exclude_sections=['References']
            )

            # Trích xuất references từ DOCX
            references_map, references_list = extract_ieee_references(docx_file)

            # Trích xuất các trích dẫn IEEE với ngữ cảnh
            citation_entries = extract_ieee_citations_with_context(sentences, references_map)

            # Crawl các tài liệu tham khảo để lấy thông tin bổ sung
            reference_crawl_info = crawl_references(references_list)

            # Cập nhật các mục trích dẫn với thông tin crawl được
            for entry in citation_entries:
                reference = entry.get('reference', '')
                crawled_info = reference_crawl_info.get(reference, {})
                entry['doi'] = crawled_info.get('doi')
                crossref_info = crawled_info.get('crossref_info', {})
                entry['crossref_authors'] = crossref_info.get('authors', '')
                entry['crossref_title'] = crossref_info.get('title', '')
                entry['crossref_year'] = crossref_info.get('year', '')
                entry['pdf_path'] = crawled_info.get('pdf_path')

            # Tạo tệp JSON với kết quả
            generate_json_output(citation_entries, "ieee_output.json")

        elif citation_type == "APA":
            # Trích xuất câu từ DOCX
            sentences = extract_sentences_from_docx(
                docx_file, output_sentences_file
            )

            # Xử lý từng câu để trích xuất trích dẫn APA
            all_citation_entries = []
            for sentence in sentences:
                apa_citations = apa_module.extract_citations_with_context(sentence)
                if apa_citations:
                    all_citation_entries.extend(apa_citations)

            # Bạn có thể thêm việc crawl references và xử lý bổ sung ở đây

            # Tạo tệp JSON với kết quả
            generate_json_output(all_citation_entries, "apa_output.json")

        elif citation_type == "Chicago":
            print("Định dạng trích dẫn Chicago chưa được hỗ trợ.")
        else:
            print("Không nhận diện được định dạng trích dẫn.")

    except Exception as e:
        logging.error(f"Có lỗi trong quá trình thực thi: {e}")

if __name__ == "__main__":
    main()
