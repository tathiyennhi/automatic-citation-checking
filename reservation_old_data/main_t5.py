import os
from dotenv import load_dotenv
import requests

# Tải các biến môi trường từ tệp .env
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

if not API_TOKEN:
    raise ValueError("API_TOKEN không được tìm thấy trong biến môi trường.")

headers = {
    'Authorization': f'Bearer {API_TOKEN}'
}

# Danh sách câu hỏi
questions = ["which is the content of citation: Giles  and  Councill  (2004)"]

# Ngữ cảnh văn bản
context =   """
            We are aware of several works on automated information extraction from acknowledg-
            ments.  Giles  and  Councill  (2004)  developed  an  automated  method  for  the  extraction  and  
            analysis  of  acknowledgment  texts  using  regular  expressions  and  SVM.  Computer  science  
            research papers from the CiteSeer digital library were used as a data source. Extracted enti-
            ties were analysed and manually assigned to the following four categories: funding agen-
            cies, corporations, universities, and individuals.
            """

# URL của mô hình T5 trên Hugging Face
url = "https://api-inference.huggingface.co/models/t5-large"

# Gửi yêu cầu cho từng câu hỏi
for question in questions:
    data = {
        "inputs": f"question: {question} context: {context}"
    }

    response = requests.post(url, headers=headers, json=data)
    answer = response.json()

    print(f"Câu trả lời cho câu hỏi '{question}':", answer)
