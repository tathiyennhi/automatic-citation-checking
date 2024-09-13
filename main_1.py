import re
import spacy
import docx
import json
from spacy.matcher import Matcher
from pdf2docx import Converter

# Load the SpaCy language model
nlp = spacy.load("en_core_web_sm")

def convert_pdf_to_docx(pdf_file, docx_file):
    """Convert PDF file to DOCX."""
    cv = Converter(pdf_file)
    cv.convert(docx_file, start=0, end=None)
    cv.close()
    print(f"Converted {pdf_file} to {docx_file}.")

def extract_text_from_docx(docx_file):
    """Extract the full text from a DOCX file."""
    doc = docx.Document(docx_file)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return '\n'.join(full_text)

def clean_text(text):
    """Remove newline characters and replace with space."""
    return text.replace('\n', ' ')

def extract_sentences(text):
    """Split text into individual sentences."""
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]

def contains_valid_citation(sentence):
    """Check if the sentence contains a valid citation."""
    patterns = [
        r'\(\s*[A-Za-z]+(?:\s+[A-Za-z]+)*\s*,\s*\d{4}\s*\)',  # Standard Citation (Author, Year)
        r'\(\s*[A-Za-z]+(?:\s+[A-Za-z]+)*\s*,\s*\d{4}(?:,\s*p\.\s*\d+)?\s*\)',  # Complex Citation (Author, Year, pp.)
        r'\([A-Za-z]+(?:\s+[A-Za-z]+)*,\s*\d{4};\s*[A-Za-z]+(?:\s+[A-Za-z]+)*,\s*\d{4}\)',  # Multiple sources (Author, Year; Author, Year)
        r'\([A-Za-z]+\s+et al\.\s*,\s*\d{4}\)',  # Citation with 'et al.' (Author et al., Year)
        # r'\([^\)]+\s+cited in\s+[^\)]+\)',  # Nested Citations (e.g., cited in)
        r'[A-Za-z]+(?:\s+[A-Za-z]+)*\s+\(\d{4}\)',  # In-text Citation (Author (Year))
        r'\([A-Za-z]+\s+et al\.\s*,\s*\d{4},\s*p\.\s*\d+\)'  # Citation with 'et al.' and pages (Author et al., Year, p.)
    ]
    
    for pattern in patterns:
        if re.search(pattern, sentence):
            return True
    return False

def extract_citations_with_context(text):
    """Extract citations from each sentence."""
    text = clean_text(text)
    sentences = extract_sentences(text)
    
    results = []
    
    for sentence in sentences:
        if not contains_valid_citation(sentence):
            continue  # Skip sentences without valid citations

        citations = []
        citation_content = sentence  # Fix: Set the citation_content to the whole sentence containing the citation

        # Trích dẫn trong ngoặc đơn: (Author, Year)
        citation_pattern = re.compile(r'\(([^)]+)\)')
        matches = citation_pattern.findall(sentence)

        for match in matches:
            # Tách từng cặp (Author, Year) trong dấu ngoặc
            individual_citations = match.split(';')
            for citation in individual_citations:
                author_year_match = re.match(r'([A-Za-z\s&]+),\s*(\d{4})', citation.strip())
                if author_year_match:
                    author, year = author_year_match.groups()
                    # Xử lý loại bỏ các cụm từ không liên quan như 'the work of'
                    author = re.sub(r'^[Tt]he work of\s+', '', author).strip()
                    citations.append({
                        'citation_content': citation_content,
                        'author': author.strip(),
                        'year_published': year.strip()
                    })
        
        # Trích dẫn có cụm từ "et al." và số trang
        et_al_pattern = re.compile(r'([A-Za-z\s]+ et al\.\s*),\s*(\d{4})(?:,\s*p\.\s*(\d+))?')
        et_al_matches = et_al_pattern.findall(sentence)

        for et_al_match in et_al_matches:
            author, year, page = et_al_match
            citation = {
                'citation_content': citation_content,
                'author': author.strip(),
                'year_published': year.strip()
            }
            if page:
                citation['page'] = page.strip()
            citations.append(citation)

        # Trích dẫn gián tiếp (e.g., "as cited in")
        indirect_citation_pattern = re.compile(r'\(as cited in\s+([A-Za-z\s&]+),\s*(\d{4})\)')
        indirect_matches = indirect_citation_pattern.findall(sentence)
        
        for indirect_match in indirect_matches:
            author, year = indirect_match
            citations.append({
                'citation_content': citation_content,
                'author': author.strip(),
                'year_published': year.strip()
            })

        # Xử lý in-text citation: "Author (Year)"
        # Cải tiến để tách riêng phần tên tác giả mà không dính vào phần trước đó
        in_text_pattern = re.compile(r'\b([A-Za-z\s&]+(?: and [A-Za-z\s&]+)*)\s*\(\s*(\d{4})\s*\)')
        in_text_matches = in_text_pattern.findall(sentence)

        # Kiểm tra nếu chuỗi trước tên tác giả có những cụm từ không liên quan, ta có thể bỏ qua
        ignore_phrases = ['According to', 'As mentioned in']


        for in_text_match in in_text_matches:
            author, year = in_text_match
            # Lọc bỏ các cụm từ không liên quan trước tên tác giả
            if any(phrase in sentence for phrase in ignore_phrases):
                sentence = re.sub(r'^(.*?\b(?:{}))'.format('|'.join(ignore_phrases)), '', sentence).strip()

            # Loại bỏ trường hợp đặc biệt sở hữu như "Giles and Councill’s (2004)"
            author = re.sub(r'’s$', '', author)

            citations.append({
                'citation_content': citation_content,
                'author': author.strip(),
                'year_published': year.strip()
            })
        
        if citations:
            results.append({
                'original_sentence': sentence,
                'citations': citations
            })
    
    return results

def extract_citation_content(sentence):
    """Extract the noun phrase before the citation."""
    doc = nlp(sentence)
    
    # Find the citation (Author, Year) using regex
    citation_match = re.search(r'\([A-Za-z\s]+,\s*\d{4}(?:,\s*pp?\.\s*\d+)?(?:;\s*[A-Za-z\s]+,\s*\d{4})*\)', sentence)
    
    if citation_match:
        citation_start = citation_match.start()
        preceding_tokens = [token.text for token in doc if token.idx < citation_start]
        
        # Extract noun phrase (NOUN/PROPN) just before the citation
        noun_phrase = []
        for token in reversed(doc):
            if token.idx >= citation_start:
                continue
            if token.pos_ in ["NOUN", "PROPN", "ADJ"]:
                noun_phrase.insert(0, token.text)
            else:
                break
        
        return ' '.join(noun_phrase)
    
    # Default to whole sentence if no noun phrase is found
    return sentence

# Convert PDF to DOCX
convert_pdf_to_docx("paper.pdf", "paper.docx")

# Extract text from DOCX for processing
docx_text = extract_text_from_docx("paper.docx")

# Extract citations
citations = extract_citations_with_context(docx_text)

# Output results to JSON
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(citations, f, ensure_ascii=False, indent=4)

print("Output data to output.json.")
