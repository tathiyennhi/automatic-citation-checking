import os
from dotenv import load_dotenv
import requests

# Tải các biến môi trường từ tệp .env
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

headers = {
    'Authorization': f'Bearer {API_TOKEN}'
}

# questions = ["Giles  and  Councill  (2004)"]
questions = ["Extract the citation from the given sentence."]


for question in questions:
    data = {
        "inputs": {
            "question": question,
            "context": """
            We are aware of several works on automated information extraction from acknowledg-
            ments.  Giles  and  Councill  (2004)  developed  an  automated  method  for  the  extraction  and  
            analysis  of  acknowledgment  texts  using  regular  expressions  and  SVM.  Computer  science  
            research papers from the CiteSeer digital library were used as a data source. Extracted enti-
            ties were analysed and manually assigned to the following four categories: funding agen-
            cies, corporations, universities, and individuals.
            """
        }
    }

    response = requests.post(
        'https://api-inference.huggingface.co/models/bert-large-uncased-whole-word-masking-finetuned-squad',
        headers=headers,
        json=data
    )

    answer = response.json()
    print(f"Câu trả lời cho câu hỏi '{question}':", answer)
