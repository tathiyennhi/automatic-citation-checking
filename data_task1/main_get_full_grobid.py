# -*- coding: utf-8 -*-
"""
Fetch the full content of a paper via GROBID API and export it as a .txt file

Requirements:
- GROBID server is running (docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0)
- pip install requests lxml
"""

import os
import requests
from lxml import etree

GROBID_URL = os.environ.get("GROBID_URL", "http://localhost:8070")
API_ENDPOINT = f"{GROBID_URL}/api/processFulltextDocument"


def fetch_tei(pdf_path: str) -> bytes:
    """Send PDF to GROBID and get back TEI XML bytes."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"input": f}
        resp = requests.post(API_ENDPOINT, files=files, timeout=120)
    resp.raise_for_status()
    return resp.content


def parse_paper(tei_bytes: bytes):
    """Parse TEI XML to extract title, authors, abstract, body, and references."""
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    root = etree.fromstring(tei_bytes)

    # ----- Metadata -----
    title = root.xpath("string(//tei:titleStmt/tei:title)", namespaces=ns)
    authors = root.xpath("//tei:titleStmt/tei:author//tei:surname/text()", namespaces=ns)

    # ----- Abstract -----
    abstract = root.xpath("string(//tei:abstract)", namespaces=ns)

    # ----- Body -----
    paragraphs = root.xpath("//tei:text/tei:body//tei:p", namespaces=ns)
    body_texts = [" ".join(p.itertext()).strip() for p in paragraphs if p.text or len(p)]

    # ----- References -----
    refs = []
    for bibl in root.xpath("//tei:text/tei:back//tei:listBibl//tei:biblStruct", namespaces=ns):
        ref_title = bibl.xpath("string(.//tei:title)", namespaces=ns)
        ref_authors = bibl.xpath(".//tei:surname/text()", namespaces=ns)
        ref_date = bibl.xpath("string(.//tei:date/@when | .//tei:date)", namespaces=ns)
        refs.append({
            "title": ref_title.strip(),
            "authors": ref_authors,
            "year": ref_date.strip()
        })

    return {
        "title": title.strip(),
        "authors": authors,
        "abstract": abstract.strip(),
        "body": body_texts,
        "references": refs
    }


def export_to_txt(paper: dict, output_path: str):
    """Export extracted data to a formatted .txt file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("===== TITLE =====\n")
        f.write(paper["title"] + "\n\n")

        f.write("===== AUTHORS =====\n")
        f.write(", ".join(paper["authors"]) + "\n\n")

        f.write("===== ABSTRACT =====\n")
        f.write(paper["abstract"] + "\n\n")

        f.write("===== BODY =====\n")
        for para in paper["body"]:
            f.write(para + "\n\n")

        f.write("===== REFERENCES =====\n")
        for ref in paper["references"]:
            f.write(f"- {', '.join(ref['authors'])} ({ref['year']}): {ref['title']}\n")


def main():
    pdf_file = "sci-ner.pdf"  
    output_txt = "TEST.txt"

    tei = fetch_tei(pdf_file)
    paper = parse_paper(tei)
    export_to_txt(paper, output_txt)

    print(f"✅ Done! Exported to file: {output_txt}")


if __name__ == "__main__":
    main()
