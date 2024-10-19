import requests
import os
import logging
import time

def download_paper_pdf(doi, download_dir="downloaded_papers", email="test@gmail.com"):
    """
    Tải xuống tệp PDF của bài báo sử dụng DOI và Unpaywall API.

    Args:
        doi (str): DOI của bài báo.
        download_dir (str): Thư mục lưu trữ tệp PDF.
        email (str): Địa chỉ email của bạn để sử dụng với Unpaywall API.

    Returns:
        str: Đường dẫn đến tệp PDF đã tải xuống, hoặc None nếu không tải được.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    # Sử dụng Unpaywall API để tìm URL PDF mở
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"

    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            oa_location = data.get('best_oa_location', {})
            pdf_url = oa_location.get('url_for_pdf', None)
            title = data.get('title', 'unknown_title').replace('/', '_').replace('\\', '_')
            pdf_path = os.path.join(download_dir, f"{title}.pdf")

            if pdf_url:
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0"
                    }
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=10)
                    if pdf_response.status_code == 200:
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_response.content)
                        logging.info(f"Tải xuống PDF: {pdf_path}")
                        return pdf_path
                    else:
                        logging.warning(f"Không thể tải xuống PDF từ {pdf_url} (Status Code: {pdf_response.status_code})")
                        return None
                except Exception as e:
                    logging.error(f"Lỗi khi tải xuống PDF từ {pdf_url}: {e}")
                    return None
            else:
                logging.warning(f"Không có URL PDF mở cho bài báo với DOI: {doi}")
                return None
        elif response.status_code == 422:
            logging.error(f"Lỗi 422: Unprocessable Content. DOI không hợp lệ hoặc dữ liệu bị thiếu. URL: {api_url}")
            return None
        else:
            logging.error(f"Lỗi khi truy cập Unpaywall API: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Lỗi khi sử dụng Unpaywall API với DOI '{doi}': {e}")
        return None
    finally:
        time.sleep(1)

#usage
#curl "https://api.unpaywall.org/v2/10.18653/v1/2023.emnlp-main.948?email=test@gmail.com"