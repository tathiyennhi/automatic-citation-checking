from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
import torch
import os
from pdfminer.high_level import extract_text

app = Flask(__name__)

# Tải các mô hình cần thiết
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
bert_model = BertModel.from_pretrained('bert-base-uncased')
nlp = spacy.load('en_core_web_sm')

# Hàm tiền xử lý văn bản
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Hàm chuyển đổi văn bản thành embedding sử dụng Sentence Transformer
def get_sentence_embedding(text):
    preprocessed_text = preprocess_text(text)
    return sentence_model.encode(preprocessed_text)

# Hàm chuyển đổi văn bản thành embedding sử dụng BERT
def get_word_embedding(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
    with torch.no_grad():
        outputs = bert_model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

# Trích xuất số liệu và từ khóa từ văn bản
def extract_numbers(text):
    return re.findall(r'\b\d+(?:\.\d+)?\b', text)

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
    return [sent.text.strip() for sent in doc.sents]

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
        citation_sentence_embedding = get_sentence_embedding(citation)
        citation_word_embedding = get_word_embedding(citation)
        citation_numbers = extract_numbers(citation)
        
        # Tạo embedding cho từng câu trong tài liệu
        sentence_embeddings = [get_sentence_embedding(sentence) for sentence in sentences]
        word_embeddings = [get_word_embedding(sentence) for sentence in sentences]
        
        # Tính toán độ tương đồng cosine giữa trích dẫn và từng câu
        similarity_scores_sentence = [cosine_similarity([citation_sentence_embedding], [sentence_embedding]).item() for sentence_embedding in sentence_embeddings]
        similarity_scores_word = [cosine_similarity([citation_word_embedding], [word_embedding]).item() for word_embedding in word_embeddings]
        
        # Tìm độ tương đồng cao nhất và thấp nhất
        max_similarity_sentence = max(similarity_scores_sentence) if similarity_scores_sentence else 0.0
        max_similarity_word = max(similarity_scores_word) if similarity_scores_word else 0.0
        
        # Kiểm tra sự khác biệt cụ thể về số liệu hoặc thuật ngữ
        discrepancies = []
        for i, sentence in enumerate(sentences):
            sentence_numbers = extract_numbers(sentence)
            if set(citation_numbers) != set(sentence_numbers):
                discrepancies.append({
                    'sentence': sentence,
                    'citation_numbers': citation_numbers,
                    'sentence_numbers': sentence_numbers
                })
        
        return jsonify({
            'citation': citation,
            'pdf_path': pdf_path,
            'max_similarity_sentence': max_similarity_sentence,
            'max_similarity_word': max_similarity_word,
            'similarity_scores_sentence': similarity_scores_sentence,
            'similarity_scores_word': similarity_scores_word,
            'discrepancies': discrepancies
        }), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
