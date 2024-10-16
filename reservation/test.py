from sentence_transformers import SentenceTransformer, util
from transformers import BertTokenizer, BertModel
import torch

# Khởi tạo mô hình sentence embedding và word embedding
sentence_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
bert_model = BertModel.from_pretrained('bert-base-uncased')

# Citation và các câu trong tài liệu gốc
citation = "Smith et al. (2020) báo cáo rằng phương pháp mới cải thiện hiệu suất lên 195% so với phương pháp truyền thống."
document_sentences = [
    "Nghiên cứu của Smith et al. (2020) cho thấy rằng phương pháp mới cải thiện hiệu suất lên 19.5% so với phương pháp truyền thống.",
    "Jones (2019) đã chỉ ra rằng các kỹ thuật mới có thể tăng năng suất đáng kể.",
    "Kết quả cho thấy sự cải thiện 20% trong hiệu suất tổng thể (Smith et al., 2020).",
    "Các phương pháp truyền thống vẫn được sử dụng rộng rãi trong ngành."
]

# Bước 1: Tính toán độ tương đồng sentence embedding
citation_embedding = sentence_model.encode(citation, convert_to_tensor=True)
document_embeddings = sentence_model.encode(document_sentences, convert_to_tensor=True)

# Tìm các câu có độ tương đồng trên 0.8
similarity_scores = util.pytorch_cos_sim(citation_embedding, document_embeddings)[0]
high_similarity_indices = torch.where(similarity_scores > 0.8)[0]

# Bước 2: Áp dụng word embedding cho các câu có độ tương đồng cao
def get_word_embedding(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
    outputs = bert_model(**inputs)
    return outputs.last_hidden_state

# Lấy word embedding cho citation và các câu có độ tương đồng cao
citation_word_embedding = get_word_embedding(citation)
high_similarity_sentences = [document_sentences[i] for i in high_similarity_indices]
high_similarity_word_embeddings = [get_word_embedding(sentence) for sentence in high_similarity_sentences]

# So sánh word embedding chi tiết
for i, sentence_embedding in enumerate(high_similarity_word_embeddings):
    # Tính toán độ tương đồng word embedding trung bình cho từng câu
    similarity = torch.cosine_similarity(
        citation_word_embedding.mean(dim=1).squeeze(),
        sentence_embedding.mean(dim=1).squeeze(),
        dim=0
    )
    print(f"Câu: {high_similarity_sentences[i]}")
    print(f"Độ tương đồng (word embedding): {similarity.item()}\n")
