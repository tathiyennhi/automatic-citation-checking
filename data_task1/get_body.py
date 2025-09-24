import os
import requests
from lxml import etree

# Cấu hình endpoint GROBID
GROBID_URL = os.environ.get("GROBID_URL", "http://localhost:8070")
GROBID_ENDPOINT = f"{GROBID_URL}/api/processFulltextDocument"

def fetch_tei(pdf_path: str) -> bytes:
    """Gọi GROBID lấy TEI XML."""
    with open(pdf_path, "rb") as f:
        files = {"input": f}
        params = {"consolidateHeader": 1}
        resp = requests.post(GROBID_ENDPOINT, files=files, params=params, timeout=120)
    resp.raise_for_status()
    return resp.content

def extract_body_without_references(tei_bytes: bytes) -> str:
    """Lấy phần body text, bỏ References."""
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    root = etree.fromstring(tei_bytes)

    # lấy tất cả đoạn trong <body>
    p_nodes = root.xpath("//tei:text/tei:body//tei:p", namespaces=ns)
    paras = []
    for p in p_nodes:
        text = " ".join(p.itertext()).strip()
        if text:
            paras.append(text)

    return "\n\n".join(paras)

def main():
    pdf_file = "sci-ner.pdf"       # đổi thành đường dẫn PDF của bạn
    output_file = "body_text.txt"

    # 1) Gọi GROBID
    tei = fetch_tei(pdf_file)

    # 2) Lấy body text
    body_text = extract_body_without_references(tei)

    # 3) Ghi ra file .txt
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(body_text)

    print(f"Đã xuất body text (từ Introduction tới trước References) ra file: {output_file}")

if __name__ == "__main__":
    main()
