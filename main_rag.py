import os
import platform
import torch
import logging
from datasets import load_dataset
from transformers import RagTokenizer, RagRetriever, RagSequenceForGeneration

# Phát hiện hệ điều hành
current_os = platform.system()

if current_os == "Windows":
    # Đường dẫn cho Windows
    os.environ["TRANSFORMERS_CACHE"] = "D:/transformers_cache"
    os.environ["HF_HOME"] = "D:/hf_home"
elif current_os == "Darwin":  # macOS
    # Đường dẫn cho macOS Sonoma
    os.environ["TRANSFORMERS_CACHE"] = "/Users/tathiyennhi/transformers_cache"
    os.environ["HF_HOME"] = "/Users/tathiyennhi/hf_home"
else:
    # Đường dẫn cho hệ điều hành khác (Linux, v.v.)
    os.environ["TRANSFORMERS_CACHE"] = "/home/tathiyennhi/transformers_cache"
    os.environ["HF_HOME"] = "/home/tathiyennhi/hf_home"

# Thiết lập biến môi trường để bỏ qua lỗi OpenMP
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Tắt cảnh báo không cần thiết (nếu cần)
logging.getLogger("transformers").setLevel(logging.ERROR)

# Thử tải tập dữ liệu `wiki_dpr` với `trust_remote_code=True`
try:
    dataset = load_dataset("wiki_dpr", "psgs_w100.nq.exact", trust_remote_code=True)
    print("Tải dữ liệu thành công!")
except ValueError as e:
    print(f"Lỗi khi tải dữ liệu: {e}")

# Tải tokenizer và mô hình RAG
tokenizer = RagTokenizer.from_pretrained("facebook/rag-token-base")

# Tải retriever với `trust_remote_code=True` để cho phép chạy mã tùy chỉnh
retriever = RagRetriever.from_pretrained(
    "facebook/rag-token-base",
    index_name="exact",
    use_dummy_dataset=True,
    trust_remote_code=True
)

# Tải mô hình RAG
model = RagSequenceForGeneration.from_pretrained("facebook/rag-token-base", retriever=retriever)

# Thiết lập thiết bị
device = torch.device("cpu")
model.to(device)

# Câu hỏi tìm kiếm trích dẫn cụ thể
question = "Trích dẫn từ Schweter và Akbik năm 2020?"
context = """
We used a standard approach, where only a linear classifier layer was added on the 
top of the transformer, as adding the additional CRF decoder between the transformer and 
linear classifier did not increase accuracy compared with this standard approach (Schweter 
&  Akbik,  2020).
"""

# Tokenize đầu vào
input_ids = tokenizer(question, return_tensors="pt").input_ids.to(device)

# Tạo câu trả lời từ mô hình RAG
with torch.no_grad():
    generated_ids = model.generate(input_ids)

# Giải mã đầu ra
output = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(f"Trích dẫn được trích xuất: {output}")