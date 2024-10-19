import requests
from bs4 import BeautifulSoup

def download_pdf_from_doi(doi):
    # Đường dẫn đến DOI resolver
    doi_url = f"https://doi.org/{doi}"

    try:
        # Gửi request để lấy URL thực từ DOI
        response = requests.get(doi_url, allow_redirects=True)
        response.raise_for_status()
        final_url = response.url
    except requests.exceptions.HTTPError as err:
        print(f"Error resolving DOI: {err}")
        return

    # Gửi request để truy cập trang bài báo
    try:
        page = requests.get(final_url)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, 'html.parser')
    except requests.exceptions.HTTPError as err:
        print(f"Error accessing article page: {err}")
        return

    # Xử lý riêng cho MDPI
    pdf_link = None
    if 'mdpi.com' in final_url:
        # Tìm link PDF từ thẻ chứa từ "PDF" trong href hoặc text
        pdf_link_tag = soup.find('a', href=True, text='PDF Full-Text')
        if not pdf_link_tag:
            pdf_link_tag = soup.find('a', href=True, text=lambda x: x and 'PDF' in x)
        if pdf_link_tag:
            pdf_link = pdf_link_tag['href']
            if not pdf_link.startswith('http'):
                pdf_link = 'https://www.mdpi.com' + pdf_link

    if not pdf_link:
        print("Không tìm thấy link PDF trên MDPI.")
        return

    # Tải file PDF
    try:
        pdf_response = requests.get(pdf_link, stream=True)
        pdf_response.raise_for_status()

        pdf_filename = f"{doi.replace('/', '_')}.pdf"
        with open(pdf_filename, 'wb') as pdf_file:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                pdf_file.write(chunk)

        print(f"Tải PDF thành công: {pdf_filename}")
    except requests.exceptions.HTTPError as err:
        print(f"Error downloading PDF: {err}")

if __name__ == "__main__":
    doi = input("Nhập DOI của bài báo: ")
    download_pdf_from_doi(doi)
