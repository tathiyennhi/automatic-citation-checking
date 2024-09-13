import re
import PyPDF2
import torch
from transformers import pipeline, BertForTokenClassification, BertTokenizer

# Load SciBERT model and tokenizer for token classification
def load_scibert_model():
    model = BertForTokenClassification.from_pretrained("allenai/scibert_scivocab_uncased")
    tokenizer = BertTokenizer.from_pretrained("allenai/scibert_scivocab_uncased")
    
    # Load the NER pipeline with the model and tokenizer
    nlp = pipeline(
        "ner", 
        model=model, 
        tokenizer=tokenizer, 
        device=0 if torch.cuda.is_available() else -1,  # GPU nếu có, nếu không thì dùng CPU
        aggregation_strategy="simple"
    )
    return nlp, tokenizer

# Extract citations using SciBERT for Named Entity Recognition (NER)
def extract_citations_with_scibert(sentences):
    nlp, tokenizer = load_scibert_model()
    citation_results = []
    
    for sentence in sentences:
        # Chia câu thành các phần nhỏ nếu cần thiết
        chunks = [sentence[i:i+512] for i in range(0, len(sentence), 512)]  # Tối đa 512 tokens
        
        for chunk in chunks:
            # Đưa trực tiếp chuỗi văn bản vào pipeline thay vì tokenized inputs
            results = nlp(chunk)  
            citation_results.extend(results)
    
    return citation_results

# Extract text from a PDF
def extract_text_from_pdf(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    text = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()
    return text

# Split text into sentences
def split_text_into_sentences(text):
    from nltk.tokenize import sent_tokenize
    return sent_tokenize(text)

# Process the PDF and extract citations
def process_pdf_for_citations(pdf_path):
    # Extract text from the PDF
    text = extract_text_from_pdf(pdf_path)
    
    # Split the text into sentences
    sentences = split_text_into_sentences(text)
    
    # Extract citations using SciBERT
    citation_data = extract_citations_with_scibert(sentences)
    
    return citation_data

# Đường dẫn đến file PDF
pdf_path = "paper.pdf"

# Xử lý PDF và trích xuất citations
citation_results = process_pdf_for_citations(pdf_path)

# In kết quả trích xuất citation
for citation in citation_results:
    print(citation)
