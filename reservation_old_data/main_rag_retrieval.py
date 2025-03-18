#this use the RagRetriever instead of DPRRetriever
from transformers import RagTokenizer, RagRetriever

# Tải tokenizer và retriever từ Hugging Face
tokenizer = RagTokenizer.from_pretrained("facebook/rag-sequence-nq")
retriever = RagRetriever.from_pretrained(
    "facebook/rag-sequence-nq",
    index_name="wiki_dpr",  
)

# Văn bản truy vấn mẫu để tìm kiếm
input_text = "What is the contribution of Giles and Councill (2004) to scientific metrics?"
input_ids = tokenizer(input_text, return_tensors="pt").input_ids

# Sử dụng retriever để truy xuất thông tin
question_hidden_states = tokenizer(input_text, return_tensors="pt")['input_ids']
retrieved_docs = retriever(input_ids.numpy())

# Hiển thị các đoạn văn bản được truy xuất
print("Các đoạn văn bản được truy xuất:")
for doc in retrieved_docs:
    print(doc)
