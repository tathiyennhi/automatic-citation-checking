from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
from pdfminer.high_level import extract_text
import spacy
import re

app = Flask(__name__)

# Tải mô hình Sentence Transformer
model = SentenceTransformer('all-MiniLM-L6-v2')

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Hàm tiền xử lý văn bản
def preprocess_text(text):
    text = text.lower()  # Chuyển thành chữ thường
    # text = re.sub(r'\d+', '', text)  # Loại bỏ số
    text = re.sub(r'\W+', ' ', text)  # Loại bỏ ký tự đặc biệt
    text = re.sub(r'\s+', ' ', text)  # Loại bỏ khoảng trắng thừa
    return text

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

# Hàm chia văn bản thành các câu có nghĩa
def split_text_into_sentences(text):
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    return sentences

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
        
        sentences = split_text_into_sentences(paper_text)
        
        # Tạo embedding cho trích dẫn
        citation_embedding = get_embedding(citation)
        
        # Tạo embedding cho từng câu trong tài liệu
        sentence_embeddings = [get_embedding(sentence) for sentence in sentences]
        
        # Tính toán độ tương đồng cosine giữa trích dẫn và từng câu
        similarity_scores = [cosine_similarity([citation_embedding], [sentence_embedding]).item() for sentence_embedding in sentence_embeddings]
        
        # Tìm độ tương đồng cao nhất và thấp nhất
        max_similarity_score = max(similarity_scores) if similarity_scores else 0.0
        min_similarity_score = min(similarity_scores) if similarity_scores else 0.0
        
        # Ngưỡng để quyết định khớp hay không (có thể điều chỉnh)
        threshold = 0.5  # Điều chỉnh ngưỡng để tránh các điểm số cao không hợp lý
        result = max_similarity_score >= threshold
        
        return jsonify({
            'citation': citation,
            'pdf_path': pdf_path,
            'max_similarity_score': max_similarity_score,
            'min_similarity_score': min_similarity_score,
            'match': result
        }), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
