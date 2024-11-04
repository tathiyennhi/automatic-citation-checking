from transformers import BertTokenizer, BertForQuestionAnswering
import torch
import logging

# Tắt cảnh báo từ thư viện transformers
logging.getLogger("transformers").setLevel(logging.ERROR)

# Tải tokenizer và mô hình BERT
tokenizer = BertTokenizer.from_pretrained("bert-large-uncased-whole-word-masking-finetuned-squad")
model = BertForQuestionAnswering.from_pretrained("bert-large-uncased-whole-word-masking-finetuned-squad")

# Thiết lập thiết bị
device = torch.device("cpu")
model.to(device)

# Câu hỏi và ngữ cảnh
question = "(Halder et al., 2020)"
context = """
The training for the few-shot approach was initiated 
with the TARS NER model (Halder et al., 2020).
"""

# Tokenize đầu vào
inputs = tokenizer(question, context, return_tensors='pt', truncation=True).to(device)

# Tạo câu trả lời từ mô hình BERT
with torch.no_grad():
    outputs = model(**inputs)

# Xác định đoạn văn bản chứa câu trả lời
answer_start = torch.argmax(outputs.start_logits)
answer_end = torch.argmax(outputs.end_logits) + 1
answer = tokenizer.decode(inputs['input_ids'][0][answer_start:answer_end], skip_special_tokens=True)

print(f"Trích dẫn được trích xuất: {answer}")
