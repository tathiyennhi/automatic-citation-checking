import requests

# đường dẫn tới file PDF
pdf_file = "sci-ner.pdf"

# endpoint của GROBID (fulltext -> trả về TEI XML)
grobid_url = "http://localhost:8070/api/processFulltextDocument"

# gửi request với file PDF
with open(pdf_file, "rb") as f:
    files = {"input": f}
    response = requests.post(grobid_url, files=files)

if response.status_code == 200:
    # lưu ra file .txt để nhìn raw TEI
    with open("paper_raw.xml", "w", encoding="utf-8") as out:
        out.write(response.text)
    print("✅ Done! Raw TEI XML saved to paper_raw.xml")
else:
    print(f"❌ Error {response.status_code}: {response.text}")
