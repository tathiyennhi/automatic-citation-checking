from flask import Flask, request, jsonify
from transformers import BertTokenizer, BertModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import os
from pdfminer.high_level import extract_text

app = Flask(__name__)

# Tải tokenizer và model BERT
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

# Hàm chuyển đổi văn bản thành embedding
def get_embedding(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

# Hàm chuyển đổi nội dung PDF thành văn bản
def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

# Hàm chia văn bản thành các đoạn văn nhỏ
def split_text_into_chunks(text, chunk_size=200):
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# API: So sánh trích dẫn với nội dung của một tài liệu PDF
@app.route('/compare_citation', methods=['POST'])
def compare_citation():
    data = request.get_json()
    citation = data.get('citation')
    pdf_path = data.get('pdf_path')
    
    if citation and pdf_path and os.path.exists(pdf_path):
        # Trích xuất văn bản từ PDF
        paper_text = extract_text_from_pdf(pdf_path)
        chunks = split_text_into_chunks(paper_text)
        
        # Tạo embedding cho trích dẫn
        citation_embedding = get_embedding(citation)
        
        # Tạo embedding cho từng đoạn văn trong tài liệu
        chunk_embeddings = [get_embedding(chunk) for chunk in chunks]
        
        # Tính toán độ tương đồng cosine giữa trích dẫn và từng đoạn văn
        similarity_scores = [cosine_similarity([citation_embedding], [chunk_embedding]).item() for chunk_embedding in chunk_embeddings]
        
        # Tìm độ tương đồng cao nhất
        max_similarity_score = max(similarity_scores) if similarity_scores else 0.0
        
        # Ngưỡng để quyết định khớp hay không (có thể điều chỉnh)
        threshold = 0.8
        result = max_similarity_score >= threshold
        
        return jsonify({
            'citation': citation,
            'pdf_path': pdf_path,
            'similarity_score': max_similarity_score,
            'match': result
        }), 200
    else:
        return jsonify({"error": "Citation and valid pdf_path are required."}), 400

if __name__ == '__main__':
    app.run(debug=True)
