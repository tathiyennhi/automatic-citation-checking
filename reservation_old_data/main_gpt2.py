from transformers import GPT2Tokenizer, GPT2LMHeadModel
import torch

# Tải tokenizer và mô hình GPT-2
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
model = GPT2LMHeadModel.from_pretrained("gpt2")

# Thêm pad_token nếu chưa có
if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': '[PAD]'})
    model.resize_token_embeddings(len(tokenizer))

# Thiết lập thiết bị
device = torch.device("cpu")
model.to(device)

# Đặt pad_token_id để tránh cảnh báo
model.config.pad_token_id = tokenizer.pad_token_id

# Câu chứa trích dẫn
sentence = """
We are aware of several works on automated information extraction from acknowledgments.
Giles and Councill (2004) developed an automated method for the extraction and analysis of acknowledgment texts using regular expressions and SVM.
Computer science research papers from the CiteSeer digital library were used as a data source.
Extracted entities were analysed and manually assigned to the following four categories: funding agencies, corporations, universities, and individuals.
"""

# Câu hỏi để trích xuất trích dẫn
question = "What did Giles and Councill (2004) do?"

# Kết hợp câu hỏi và ngữ cảnh
input_text = f"{question} {sentence}"

# Tokenize đầu vào với attention mask
inputs = tokenizer(input_text, return_tensors='pt', padding=True, truncation=True).to(device)

# Tạo câu trả lời từ mô hình GPT-2
outputs = model.generate(
    input_ids=inputs['input_ids'],
    attention_mask=inputs['attention_mask'],
    max_new_tokens=50,  # Giới hạn số lượng token mới được sinh ra
    do_sample=False,
    no_repeat_ngram_size=2,
    num_return_sequences=1
)

answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

print(f"Trả lời từ GPT-2: {answer}")
