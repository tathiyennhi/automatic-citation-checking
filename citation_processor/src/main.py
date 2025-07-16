import os
import json
import re
import spacy
from dotenv import load_dotenv

def split_into_sections(text):
    """Split text into sections based on section numbers and titles"""
    sections = []
    current_section = {"title": "Introduction", "paragraphs": []}
    
    # Split text into lines
    lines = text.split('\n')
    
    for line in lines:
        # Check if line is a section header
        if re.match(r'^\d+\.\s+[A-Z]', line):
            if current_section["paragraphs"]:
                sections.append(current_section)
            current_section = {
                "title": line.strip(),
                "paragraphs": []
            }
        elif line.strip():
            current_section["paragraphs"].append({
                "text": line.strip(),
                "citations": []
            })
    
    if current_section["paragraphs"]:
        sections.append(current_section)
    
    return sections

def extract_citations(text):
    """Extract citations from text using basic patterns"""
    citations = []
    
    # Pattern for (Author, Year) citations
    author_year_pattern = r'\(([^)]+?,\s*\d{4})\)'
    for match in re.finditer(author_year_pattern, text):
        citations.append({
            "text": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "type": "author_year"
        })
    
    # Pattern for [1] citations
    number_pattern = r'\[(\d+)\]'
    for match in re.finditer(number_pattern, text):
        citations.append({
            "text": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "type": "number"
        })
    
    return citations

def extract_references(text):
    """Extract references section and parse individual references"""
    references = []
    
    # Find references section
    ref_section = re.search(r'References\n(.*)', text, re.DOTALL)
    if ref_section:
        ref_text = ref_section.group(1)
        # Split into individual references
        ref_entries = re.split(r'\n\d+\.\s+', ref_text)
        
        for i, ref in enumerate(ref_entries, 1):
            if ref.strip():
                references.append({
                    "id": f"r{i}",
                    "text": ref.strip(),
                    "citations": []  # Will be filled later
                })
    
    return references

def link_citations_to_references(citations, references):
    """Link citations to their corresponding references"""
    for citation in citations:
        if citation["type"] == "number":
            ref_id = f"r{citation['text']}"
            citation["ref_ids"] = [ref_id]
            # Add citation to reference's citations list
            for ref in references:
                if ref["id"] == ref_id:
                    ref["citations"].append(citation["id"])
        else:
            # For author-year citations, we'll need more sophisticated matching
            # This is a simplified version
            citation["ref_ids"] = []

def process_paper(pdf_path: str):
    """Process a paper and extract its structure, citations and references"""
    
    # Read PDF text (assuming this function exists)
    with open(pdf_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Extract paper metadata
    title_match = re.search(r'^(.+?)\n', text)
    authors_match = re.search(r'^.+?\n(.+?)\n', text)
    
    metadata = {
        "title": title_match.group(1) if title_match else "",
        "authors": authors_match.group(1).split(', ') if authors_match else [],
        "year": re.search(r'\d{4}', text).group() if re.search(r'\d{4}', text) else ""
    }
    
    # Process paper structure
    sections = split_into_sections(text)
    
    # Extract citations and references
    citations = extract_citations(text)
    references = extract_references(text)
    
    # Link citations to references
    link_citations_to_references(citations, references)
    
    # Create output structure
    output = {
        "paper_id": os.path.splitext(os.path.basename(pdf_path))[0],
        "metadata": metadata,
        "sections": sections,
        "references": references
    }
    
    # Save output
    output_dir = os.path.join(os.path.dirname(os.path.dirname(pdf_path)), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(pdf_path))[0] + ".json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved result to {output_file}")

def main():
    load_dotenv()
    
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "input")
    for filename in os.listdir(input_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            try:
                process_paper(pdf_path)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    main()
