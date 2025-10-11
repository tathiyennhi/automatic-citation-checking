# -*- coding: utf-8 -*-
"""
Fetch full text from any PDF via the GROBID API and export to a .txt file.

Requirements:
- GROBID server running (docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0)
- pip install requests lxml
"""

import os
import requests
from lxml import etree
import re

GROBID_URL = os.environ.get("GROBID_URL", "http://localhost:8070")
API_ENDPOINT = f"{GROBID_URL}/api/processFulltextDocument"


def fetch_tei(pdf_path: str) -> bytes:
    """Call the GROBID API to extract TEI XML from a PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"input": f}
        resp = requests.post(API_ENDPOINT, files=files, timeout=120)
    resp.raise_for_status()
    return resp.content


def parse_general_document(tei_bytes: bytes):
    """Parse TEI XML for an arbitrary document (no assumptions about academic papers)."""
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    root = etree.fromstring(tei_bytes)

    # ----- Metadata (optional) -----
    title = root.xpath("string(//tei:titleStmt/tei:title)", namespaces=ns)
    if not title.strip():
        # Fallback: retrieve from fileDesc
        title = root.xpath("string(//tei:fileDesc//tei:title)", namespaces=ns)
    
    authors = root.xpath("//tei:titleStmt/tei:author//tei:surname/text()", namespaces=ns)
    if not authors:
        # Fallback: retrieve from other locations
        authors = root.xpath("//tei:fileDesc//tei:author//tei:surname/text()", namespaces=ns)

    # ----- Abstract (optional, may be missing) -----
    abstract = root.xpath("string(//tei:abstract)", namespaces=ns)

    # ----- Main Content -----
    # Collect all paragraph texts from the body
    paragraphs = root.xpath("//tei:text/tei:body//tei:p", namespaces=ns)
    body_texts = []
    
    for p in paragraphs:
        text = " ".join(p.itertext()).strip()
        if text and len(text) > 10:  # Skip overly short paragraphs
            body_texts.append(text)

    # ----- Headers/Sections (if present) -----
    headers = []
    for head in root.xpath("//tei:text/tei:body//tei:head", namespaces=ns):
        header_text = " ".join(head.itertext()).strip()
        if header_text:
            headers.append(header_text)

    # ----- Tables (if present) -----
    tables = []
    for table in root.xpath("//tei:table", namespaces=ns):
        table_text = " ".join(table.itertext()).strip()
        if table_text:
            tables.append(table_text)

    # ----- Figures/Captions (if present) -----
    figures = []
    for fig in root.xpath("//tei:figure", namespaces=ns):
        fig_text = " ".join(fig.itertext()).strip()
        if fig_text:
            figures.append(fig_text)

    # ----- References (optional) -----
    refs = []
    for bibl in root.xpath("//tei:text/tei:back//tei:listBibl//tei:biblStruct", namespaces=ns):
        ref_title = bibl.xpath("string(.//tei:title)", namespaces=ns)
        ref_authors = bibl.xpath(".//tei:surname/text()", namespaces=ns)
        ref_date = bibl.xpath("string(.//tei:date/@when | .//tei:date)", namespaces=ns)
        
        if ref_title.strip():  # Only add references that have a title
            refs.append({
                "title": ref_title.strip(),
                "authors": ref_authors,
                "year": ref_date.strip()
            })

    # ----- Raw text fallback -----
    # If structured extraction yields nothing, fall back to all text
    if not body_texts and not abstract:
        all_text = " ".join(root.itertext()).strip()
        if all_text:
            # Cleanup and split into paragraphs
            cleaned = re.sub(r'\s+', ' ', all_text)
            # Split by sentence-like boundaries to form pseudo-paragraphs
            sentences = re.split(r'[.!?]+\s+', cleaned)
            
            current_para = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                if len(current_para) + len(sentence) > 500:  # Max paragraph length
                    if current_para:
                        body_texts.append(current_para)
                    current_para = sentence
                else:
                    current_para += (" " + sentence if current_para else sentence)
            
            if current_para:
                body_texts.append(current_para)

    return {
        "title": title.strip() if title else "Untitled Document",
        "authors": authors,
        "abstract": abstract.strip(),
        "headers": headers,
        "body": body_texts,
        "tables": tables,
        "figures": figures,
        "references": refs,
        "has_structure": bool(headers or abstract or refs)  # Whether the document appears structured
    }


def export_to_txt(document: dict, output_path: str):
    """Export parsed document data to a text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        # Title
        f.write("=" * 50 + "\n")
        f.write("DOCUMENT TITLE\n")
        f.write("=" * 50 + "\n")
        f.write(document["title"] + "\n\n")

        # Authors (if any)
        if document["authors"]:
            f.write("=" * 50 + "\n")
            f.write("AUTHORS\n")
            f.write("=" * 50 + "\n")
            f.write(", ".join(document["authors"]) + "\n\n")

        # Abstract (if any)
        if document["abstract"]:
            f.write("=" * 50 + "\n")
            f.write("ABSTRACT/SUMMARY\n")
            f.write("=" * 50 + "\n")
            f.write(document["abstract"] + "\n\n")

        # Headers (if any)
        if document["headers"]:
            f.write("=" * 50 + "\n")
            f.write("SECTION HEADERS\n")
            f.write("=" * 50 + "\n")
            for i, header in enumerate(document["headers"], 1):
                f.write(f"{i}. {header}\n")
            f.write("\n")

        # Main content
        f.write("=" * 50 + "\n")
        f.write("MAIN CONTENT\n")
        f.write("=" * 50 + "\n")
        
        if document["body"]:
            for i, para in enumerate(document["body"], 1):
                f.write(f"[Paragraph {i}]\n{para}\n\n")
        else:
            f.write("(No main content extracted)\n\n")

        # Tables (if any)
        if document["tables"]:
            f.write("=" * 50 + "\n")
            f.write("TABLES\n")
            f.write("=" * 50 + "\n")
            for i, table in enumerate(document["tables"], 1):
                f.write(f"[Table {i}]\n{table}\n\n")

        # Figures (if any)
        if document["figures"]:
            f.write("=" * 50 + "\n")
            f.write("FIGURES/CAPTIONS\n")
            f.write("=" * 50 + "\n")
            for i, fig in enumerate(document["figures"], 1):
                f.write(f"[Figure {i}]\n{fig}\n\n")

        # References (if any)
        if document["references"]:
            f.write("=" * 50 + "\n")
            f.write("REFERENCES\n")
            f.write("=" * 50 + "\n")
            for i, ref in enumerate(document["references"], 1):
                authors_str = ", ".join(ref['authors']) if ref['authors'] else "Unknown"
                year_str = f" ({ref['year']})" if ref['year'] else ""
                f.write(f"{i}. {authors_str}{year_str}: {ref['title']}\n")
            f.write("\n")

        # Document info
        f.write("=" * 50 + "\n")
        f.write("EXTRACTION INFO\n")
        f.write("=" * 50 + "\n")
        f.write(f"Structured document: {'Yes' if document['has_structure'] else 'No'}\n")
        f.write(f"Paragraphs extracted: {len(document['body'])}\n")
        f.write(f"Tables found: {len(document['tables'])}\n")
        f.write(f"Figures found: {len(document['figures'])}\n")
        f.write(f"References found: {len(document['references'])}\n")


def process_pdf(pdf_path: str, output_txt: str = None):
    """Main function to process a PDF."""
    if output_txt is None:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_txt = f"{base_name}_extracted.txt"

    print(f"Processing PDF: {pdf_path}")
    print(f"Output will be saved to: {output_txt}")

    try:
        # Call GROBID
        print("Calling GROBID API...")
        tei = fetch_tei(pdf_path)
        
        # Parse document
        print("Parsing document structure...")
        document = parse_general_document(tei)
        
        # Export
        print("Exporting to text file...")
        export_to_txt(document, output_txt)
        
        # Summary
        print("\n" + "="*50)
        print("EXTRACTION SUMMARY")
        print("="*50)
        print(f"Title: {document['title']}")
        print(f"Authors: {len(document['authors'])} found")
        print(f"Abstract: {'Yes' if document['abstract'] else 'No'}")
        print(f"Paragraphs: {len(document['body'])}")
        print(f"Tables: {len(document['tables'])}")
        print(f"Figures: {len(document['figures'])}")
        print(f"References: {len(document['references'])}")
        print(f"Structured: {'Yes' if document['has_structure'] else 'No'}")
        print(f"\nDone! Output saved to: {output_txt}")
        
        return document
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling GROBID API: {e}")
        print("Make sure the GROBID server is running:")
        print("docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0")
        return None
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None


def main():
    """Example usage."""
    # Replace with your PDF path
    pdf_file = input("Enter PDF file path: ").strip()
    if not pdf_file:
        pdf_file = "test.pdf"  # default
    
    # Optional: custom output name
    output_name = input("Enter output text file name (or press Enter for auto): ").strip()
    output_name = output_name if output_name else None
    
    result = process_pdf(pdf_file, output_name)
    
    if result:
        print("\nExtraction completed successfully!")
    else:
        print("\nExtraction failed!")


if __name__ == "__main__":
    main()
