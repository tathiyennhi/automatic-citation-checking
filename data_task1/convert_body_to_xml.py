import os
import requests
from lxml import etree

# Config
PDF_PATH = "sci-ner.pdf"
OUTPUT_XML = "sci-ner.xml"
GROBID_URL = "http://localhost:8070"

def pdf_to_xml_without_references(pdf_path: str, output_xml: str, grobid_url: str = "http://localhost:8070"):
    """Convert PDF to XML, remove References section"""
    
    # 1. Gọi Grobid API
    url = f"{grobid_url}/api/processFulltextDocument"
    
    print(f"Processing {pdf_path} with Grobid...")
    
    with open(pdf_path, 'rb') as f:
        files = {'input': f}
        params = {'consolidateHeader': 1}
        response = requests.post(url, files=files, params=params, timeout=120)
    
    if response.status_code != 200:
        raise Exception(f"Grobid error: {response.status_code}")
    
    # 2. Parse XML và remove References
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    root = etree.fromstring(response.content)
    
    # Tìm và xóa phần <listBibl> (bibliography/references)
    listbibl_nodes = root.xpath('//tei:listBibl', namespaces=ns)
    for node in listbibl_nodes:
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    
    # Tìm và xóa <div> có head="References" hoặc "Bibliography"
    ref_divs = root.xpath('//tei:div[tei:head[contains(text(), "References") or contains(text(), "Bibliography")]]', namespaces=ns)
    for div in ref_divs:
        parent = div.getparent()
        if parent is not None:
            parent.remove(div)
    
    # 3. Lưu XML đã clean
    xml_bytes = etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    with open(output_xml, 'wb') as f:
        f.write(xml_bytes)
    
    print(f"✅ Successfully saved XML (without References) to: {output_xml}")
    print(f"   File size: {len(xml_bytes)} bytes")

if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF file not found: {PDF_PATH}")
    else:
        pdf_to_xml_without_references(PDF_PATH, OUTPUT_XML, GROBID_URL)