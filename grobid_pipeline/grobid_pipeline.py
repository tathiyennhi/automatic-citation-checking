import requests

def extract_references_grobid(pdf_path, output_xml_path):
    url = "http://localhost:8070/api/processReferences"
    
    with open(pdf_path, 'rb') as pdf_file:
        files = {
            'input': (pdf_path, pdf_file, 'application/pdf')
        }
        response = requests.post(url, files=files)

    if response.status_code == 200:
        # Ghi output XML ra file
        with open(output_xml_path, 'w', encoding='utf-8') as out_file:
            out_file.write(response.text)
        print(f"✔ Đã ghi file: {output_xml_path}")
    else:
        print(f"❌ Lỗi khi gọi Grobid API: {response.status_code}")
        print(response.text)

# ---- Thực thi ----
pdf_path = "paper.pdf"  # <-- đổi thành file của bạn
output_xml_path = "references_grobid.xml"
extract_references_grobid(pdf_path, output_xml_path)
