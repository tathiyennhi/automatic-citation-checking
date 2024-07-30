from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
from pdfminer.high_level import extract_text
import spacy
import re

app = Flask(__name__)

# Tải mô hình Sentence Transformer
model = SentenceTransformer('allenai/scibert_scivocab_uncased')

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Hàm tiền xử lý văn bản
def preprocess_text(text):
    text = text.lower()  # Chuyển thành chữ thường
    text = re.sub(r'[^\w\s]', '', text)  # Loại bỏ ký tự đặc biệt nhưng giữ lại chữ và số
    text = re.sub(r'\s+', ' ', text)  # Loại bỏ khoảng trắng thừa
    return text.strip()

# Hàm chuyển đổi văn bản thành embedding
def get_embedding(text):
    preprocessed_text = preprocess_text(text)
    embedding = model.encode(preprocessed_text)
    return embedding

# Hàm chuyển đổi nội dung PDF thành văn bản
def extract_text_from_pdf(pdf_path):
    try:
        return extract_text(pdf_path)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

# Hàm chia văn bản thành các đoạn văn hợp lý
def split_text_into_paragraphs(text, paragraph_size=150):
    words = text.split()
    paragraphs = [' '.join(words[i:i + paragraph_size]) for i in range(0, len(words), paragraph_size)]
    return paragraphs

# API: So sánh trích dẫn với nội dung của một tài liệu PDF
@app.route('/compare_citation', methods=['POST'])
def compare_citation():
    data = request.get_json()
    citation = data.get('citation')
    pdf_path = data.get('pdf_path')
    
    if not citation:
        return jsonify({"error": "Citation is required."}), 400
    
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "Valid pdf_path is required."}), 400
    
    try:
        # Trích xuất văn bản từ PDF
        paper_text = extract_text_from_pdf(pdf_path)
        if not paper_text:
            return jsonify({"error": "Failed to extract text from PDF."}), 500
        
        paragraphs = split_text_into_paragraphs(paper_text)
        
        # Tạo embedding cho trích dẫn
        citation_embedding = get_embedding(citation)
        
        # Tạo embedding cho từng đoạn văn trong tài liệu
        paragraph_embeddings = [get_embedding(paragraph) for paragraph in paragraphs]
        
        # Tính toán độ tương đồng cosine giữa trích dẫn và từng đoạn văn
        similarity_scores = [cosine_similarity([citation_embedding], [paragraph_embedding]).item() for paragraph_embedding in paragraph_embeddings]
        
        # Tìm độ tương đồng cao nhất và thấp nhất
        max_similarity_score = max(similarity_scores) if similarity_scores else 0.0
        min_similarity_score = min(similarity_scores) if similarity_scores else 0.0
        
        # Kết quả cuối cùng là độ tương đồng cao nhất
        result = max_similarity_score
        
        return jsonify({
            'citation': citation,
            'pdf_path': pdf_path,
            'max_similarity_score': max_similarity_score,
            'min_similarity_score': min_similarity_score,
            'similarity_scores': similarity_scores,
            'match': result
        }), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
