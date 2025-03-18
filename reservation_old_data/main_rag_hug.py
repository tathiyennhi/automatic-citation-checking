import requests

headers = {"Authorization": "Bearer API_HUGGING_FACE_KEY"}

question = "Trích dẫn từ Schweter và Akbik năm 2020?"
context = """
We used a standard approach, where only a linear classifier layer was added on the 
top of the transformer, as adding the additional CRF decoder between the transformer and 
linear classifier did not increase accuracy compared with this standard approach (Schweter 
& Akbik, 2020).
"""

payload = {
    "inputs": {
        "question": question,
        "context": context
    }
}

# Gửi yêu cầu đến Hugging Face API
response = requests.post(
    "https://api-inference.huggingface.co/models/facebook/rag-token-base", 
    headers=headers, 
    json=payload
)

# Kiểm tra trạng thái phản hồi HTTP
if response.status_code == 200:
    try:
        result = response.json()
        # In ra toàn bộ phản hồi để kiểm tra cấu trúc dữ liệu
        print("Phản hồi từ API:", result)

        # Nếu có key 'answer', in kết quả ra
        if 'answer' in result:
            print(f"Trích dẫn được trích xuất: {result['answer']}")
        else:
            print("Không tìm thấy key 'answer' trong phản hồi.")
    except Exception as e:
        print("Lỗi khi xử lý dữ liệu phản hồi:", e)
else:
    print(f"Lỗi khi gửi yêu cầu đến API. Mã lỗi: {response.status_code}")
    print("Chi tiết lỗi:", response.text)
