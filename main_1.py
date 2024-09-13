import re
import spacy
import docx
import json
import logging
from pdf2docx import Converter

# Set up logging to track the extraction process
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Load SpaCy language model
nlp = spacy.load("en_core_web_sm")

def convert_pdf_to_docx(pdf_file, docx_file):
    """Convert PDF file to DOCX."""
    logging.info(f"Start to convert {pdf_file}")
    cv = Converter(pdf_file)
    cv.convert(docx_file, start=0, end=None)
    cv.close()
    logging.info(f"Converted {pdf_file} to {docx_file}.")

def extract_text_from_docx(docx_file):
    """Extract full text from DOCX file, excluding the references section."""
    doc = docx.Document(docx_file)
    full_text = []
    references_found = False
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        # Debugging: Output the paragraph text
        logging.debug(f"Processing paragraph: '{text}'")
        # Check if the paragraph is the References heading
        if re.match(r'^\s*(References|Bibliography|Works Cited)\s*$', text, re.IGNORECASE):
            logging.info("References section found. Stopping text extraction.")
            references_found = True
            break
        # Alternatively, check for headings that include numbering or other text
        elif re.match(r'^\s*(\d+\.\s*)?(References|Bibliography|Works Cited)\s*$', text, re.IGNORECASE):
            logging.info("References section found with numbering. Stopping text extraction.")
            references_found = True
            break
        full_text.append(text)
    if not references_found:
        logging.warning("References section not found. Entire document will be processed.")
    return '\n'.join(full_text)

def clean_text(text):
    """Remove newline characters and replace them with spaces."""
    return text.replace('\n', ' ').replace('\r', ' ')

def extract_sentences(text):
    """Split text into individual sentences."""
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]

def extract_citations_with_context(text):
    """Extract citations from each sentence."""
    text = clean_text(text)
    sentences = extract_sentences(text)

    results = []

    for sentence in sentences:
        citations = []
        citation_content = sentence  # The sentence containing the citation

        # Regex pattern to find all citations within parentheses
        parenthetical_pattern = re.compile(r'\(([^)]+?\d{4}[^)]*?)\)')
        parenthetical_matches = parenthetical_pattern.finditer(sentence)

        for match in parenthetical_matches:
            citation_text = match.group(1)
            # Split multiple citations separated by ';'
            individual_citations = [cite.strip() for cite in re.split(r';\s*', citation_text)]
            for citation in individual_citations:
                # Match patterns like "Author et al., Year", "Author & Author, Year", etc.
                author_year_match = re.match(r'^(.*?)(?:,\s*(\d{4})(?:,\s*p\.?\s*(\d+))?)?$', citation)
                if author_year_match:
                    author_part, year, page = author_year_match.groups()
                    # Remove phrases like "as cited in" if present
                    author_part = re.sub(r'(?i)as cited in\s+', '', author_part)
                    author_part = author_part.strip()
                    # If publication year is present, add to the list
                    if year:
                        citation_dict = {
                            'citation_content': citation_content,
                            'author': author_part,
                            'year_published': year
                        }
                        if page:
                            citation_dict['page'] = page
                        citations.append(citation_dict)
                    else:
                        logging.warning(f"Cannot extract year from citation: '{citation}' in sentence: '{sentence}'")
                else:
                    logging.warning(f"Cannot extract author and year from citation: '{citation}' in sentence: '{sentence}'")

        # Regex pattern to match in-text citations: Author's (Year)
        in_text_pattern = re.compile(r'\b([A-Z][a-zA-Z\'’`.-]+(?:\s+(?:et al\.|and|&)\s+[A-Z][a-zA-Z\'’`.-]+)*(?:\s+et al\.)?)(?:’s|\'s)?\s*\((\d{4})(?:,\s*p\.?\s*(\d+))?\)')
        in_text_matches = in_text_pattern.finditer(sentence)
        for match in in_text_matches:
            author_part, year, page = match.groups()
            author_part = author_part.strip()
            citation_dict = {
                'citation_content': citation_content,
                'author': author_part,
                'year_published': year
            }
            if page:
                citation_dict['page'] = page
            citations.append(citation_dict)

        if citations:
            # Remove duplicate citations
            unique_citations = { (c['author'], c['year_published']): c for c in citations }
            results.append({
                'original_sentence': sentence,
                'citations': list(unique_citations.values())
            })

    return results

if __name__ == "__main__":
    # Convert PDF to DOCX
    convert_pdf_to_docx("paper.pdf", "paper.docx")

    # Extract text from DOCX for processing
    docx_text = extract_text_from_docx("paper.docx")

    # Extract citations
    citations = extract_citations_with_context(docx_text)

    # Output results to JSON file
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(citations, f, ensure_ascii=False, indent=4)

    logging.info("Data has been exported to output.json.")
