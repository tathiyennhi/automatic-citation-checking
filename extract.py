import re
import csv
import spacy
from pdfminer.high_level import extract_text
from fuzzywuzzy import fuzz

nlp = spacy.load("en_core_web_sm")

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_citations_from_text(text, style='default'):
    doc = nlp(text)
    citations = []
    if style == 'ieee':
        citation_pattern = r'\[(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\]'
    else:  # default style
        citation_pattern = r'\(([^()]*,[^()]*\b\d{4}\b[^()]*)\)'

    for sent in doc.sents:
        matches = re.findall(citation_pattern, sent.text)
        for match in matches:
            context = clean_text(sent.text)
            full_citation = clean_text(match)
            citations.append((full_citation, context))
    return citations

def split_citation(citation):
    parts = re.split(r';|\(|\)', citation)
    return [clean_text(part) for part in parts if re.search(r'\b\d{4}\b', part)]

def extract_references(text, style='default'):
    references = []
    lines = text.split('\n')
    current_ref = ''
    for line in lines:
        if style == 'ieee' and re.match(r'^\[\d+\]', line.strip()):
            if current_ref:
                references.append(clean_text(current_ref))
            current_ref = line
        # elif style == 'default' and re.match(r'^[A-Z]', line.strip()):
        #     if current_ref:
        #         references.append(clean_text(current_ref))
        #     current_ref = line
        elif style == 'default':
            # Check for uppercase letter OR continuation of multi-line reference
            if re.match(r'^[A-Z]', line.strip()) or current_ref:
                current_ref += ' ' + line.strip()
            else:
                # Line is not a reference, reset current_ref
                current_ref = ''
        else:
            current_ref += ' ' + line.strip()
    if current_ref:
        # print("DAIIIII", current_ref)
        # print('CURRENT: ', current_ref, '\n')
        # print('*' * 8)
        references.append(clean_text(current_ref))
        print("Current len, ", len(references))
    
    parsed_refs = []
    for ref in references:
        print("THAM CHIE^U ", ref, '\n')
        if style == 'ieee':
            match = re.match(r'\[(\d+)\]\s(.+?)(?:,|\.)(.+)', ref)
            if match:
                ref_number = match.group(1)
                authors = clean_text(match.group(2))
                title_and_source = clean_text(match.group(3))
                parsed_refs.append((ref_number, authors, '', title_and_source, ref))
        else:
            match = re.match(r'(.+?)\((\d{4})\)\.\s*(.+?)\.', ref)
            if match:
                authors = clean_text(match.group(1))
                year = match.group(2)
                title = clean_text(match.group(3))
                key = authors.split(',')[0].lower()
                parsed_refs.append((key, authors, year, title, ref))
                print(key, "----", year, '----')
            
    return parsed_refs

def find_best_match(citation, references, style='default'):
    if style == 'ieee':
        citation_numbers = re.findall(r'\d+', citation)
        for ref in references:
            if ref[0] in citation_numbers:
                return ref
    else:
        citation_parts = citation.lower().split(',')
        citation_authors = [author.strip() for author in re.split(r'&|\sand\s', citation_parts[0])]
        citation_year = re.search(r'\d{4}', citation).group() if re.search(r'\d{4}', citation) else ''
        
        best_match = None
        max_similarity = 0
        
        for ref in references:
            ref_authors = [author.strip().lower() for author in re.split(r',|\sand\s', ref[1])]
            ref_year = ref[2]
            
            # Xử lý trường hợp "et al."
            # if 'et al' in citation.lower():
            #     print("et al nè: ", ref[1], ref_year)
            #     author_similarity = fuzz.partial_ratio(citation_authors[0], ref_authors[0])
            # else:
            #     author_similarity = max(fuzz.token_sort_ratio(ca, ra) for ca in citation_authors for ra in ref_authors)
            author_similarity = max(fuzz.token_sort_ratio(ca, ra) for ca in citation_authors for ra in ref_authors)

            year_similarity = 100 if citation_year == ref_year else 0
            
            # Tăng trọng số cho việc khớp năm
            similarity = (author_similarity * 0.55 + year_similarity * 0.45) / 100
            
            # Kiểm tra xem child citation có chứa tên tác giả trong danh sách tham chiếu không
            if any(author.lower() in citation.lower() for author in ref_authors):
                similarity += 0.1  # Tăng thêm trọng số nếu có tên tác giả xuất hiện
                
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = ref
        
        return best_match if max_similarity > 0 else None

def process_pdf(pdf_path, style='default'):
    text = extract_text(pdf_path)
    parts = text.split("References", 1)
    main_text = parts[0]
    ref_text = parts[1] if len(parts) > 1 else ""
    
    citations = extract_citations_from_text(main_text, style)
    references = extract_references(ref_text, style)
    
    output_file = f'citations_with_references_{style}.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Citation', 'Child Citation', 'Context', 'Full Reference', 'Paper Title', 'Authors', 'Year', 'Matched'])
        for i, (citation, context) in enumerate(citations, 1):
            child_citations = split_citation(citation)
            for j, child_citation in enumerate(child_citations, 1):
                if not child_citation:  # Bỏ qua child_citation rỗng
                    continue
                matched_ref = find_best_match(child_citation, references, style)
                if matched_ref:
                    citation_year = re.search(r'\d{4}', child_citation).group() if re.search(r'\d{4}', child_citation) else ''
                    if citation_year and citation_year != matched_ref[2]:
                        matched_ref = None  # Không khớp nếu năm không trùng
                
                if matched_ref:
                    if style == 'ieee':
                        writer.writerow([f"{i}.{j}", citation, child_citation, context, matched_ref[4], matched_ref[3], matched_ref[1], '', 'Yes'])
                    else:
                        writer.writerow([f"{i}.{j}", citation, child_citation, context, matched_ref[4], matched_ref[3], matched_ref[1], matched_ref[2], 'Yes'])
                else:
                    writer.writerow([f"{i}.{j}", citation, child_citation, context, 'Not found', '', '', '', 'No'])                   

    
    print(f"Results exported to {output_file}")

if __name__ == "__main__":
    pdf_path = 'paper.pdf'
    style = 'default'  # Change to 'ieee' if needed
    process_pdf(pdf_path, style)
