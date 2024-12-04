# import torch
# import warnings
# from transformers import DPRContextEncoder, DPRContextEncoderTokenizerFast, DPRQuestionEncoder, DPRQuestionEncoderTokenizerFast

# # Tắt cảnh báo không cần thiết
# warnings.filterwarnings("ignore")

# # Khởi tạo thiết bị
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# # Khởi tạo mô hình và tokenizer của DPR
# ctx_encoder = DPRContextEncoder.from_pretrained('facebook/dpr-ctx_encoder-single-nq-base').to(device)
# ctx_tokenizer = DPRContextEncoderTokenizerFast.from_pretrained('facebook/dpr-ctx_encoder-single-nq-base')
# question_encoder = DPRQuestionEncoder.from_pretrained('facebook/dpr-question_encoder-single-nq-base').to(device)
# question_tokenizer = DPRQuestionEncoderTokenizerFast.from_pretrained('facebook/dpr-question_encoder-single-nq-base')

# # Trích dẫn mẫu cần tìm nội dung liên quan
# citation = "According to the Intergovernmental Panel on Climate Change (IPCC) report in 2021"

# # Nội dung từ graph PDF (được tổ chức thành các câu)
# pdf_content = [
#     "According to the Intergovernmental Panel on Climate Change (IPCC) report in 2021, global temperatures are expected to rise by 1.5 degrees Celsius by 2030.",
#     "The report emphasizes the urgent need for immediate action to reduce greenhouse gas emissions.",
#     "Renewable energy sources, such as solar and wind power, are essential for achieving a sustainable future.",
#     "Increased carbon dioxide levels have been linked to severe weather patterns and natural disasters.",
#     "Mitigation strategies include reforestation, energy efficiency improvements, and transitioning to a circular economy."
# ]

# # Mã hóa trích dẫn
# question_inputs = question_tokenizer(citation, return_tensors='pt').to(device)
# with torch.no_grad():
#     question_embedding = question_encoder(**question_inputs).pooler_output

# # Mã hóa nội dung PDF và lưu trữ embeddings
# context_embeddings = []
# for content in pdf_content:
#     ctx_inputs = ctx_tokenizer(content, return_tensors='pt').to(device)
#     with torch.no_grad():
#         context_embedding = ctx_encoder(**ctx_inputs).pooler_output
#         context_embeddings.append(context_embedding)

# # Tính độ tương đồng và trích xuất nội dung liên quan
# related_contents = []
# similarity_threshold = 0.6  # Ngưỡng tương đồng

# main_content = None
# supplementary_contents = []

# for idx, context_embedding in enumerate(context_embeddings):
#     # Tính cosine similarity giữa trích dẫn và từng đoạn văn bản
#     similarity = torch.nn.functional.cosine_similarity(question_embedding, context_embedding)
    
#     # Nếu độ tương đồng lớn hơn ngưỡng
#     if similarity.item() > similarity_threshold:
#         # Kiểm tra xem câu có chứa citation hay không
#         if citation in pdf_content[idx]:
#             # Lấy toàn bộ câu làm nội dung trích dẫn
#             main_content = pdf_content[idx]
#             break  # Dừng lại khi đã tìm thấy câu chứa citation

# # In ra kết quả cuối cùng
# print(f"Nội dung liên quan đến trích dẫn '{citation}':")
# if main_content:
#     print(f"Trích dẫn: {main_content}")
# else:
#     print("Không tìm thấy nội dung trích dẫn chính xác.")

import torch
import warnings
from transformers import DPRContextEncoder, DPRContextEncoderTokenizerFast, DPRQuestionEncoder, DPRQuestionEncoderTokenizerFast

# Tắt cảnh báo không cần thiết
warnings.filterwarnings("ignore")

# Khởi tạo thiết bị
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Khởi tạo mô hình và tokenizer của DPR
ctx_encoder = DPRContextEncoder.from_pretrained('facebook/dpr-ctx_encoder-single-nq-base').to(device)
ctx_tokenizer = DPRContextEncoderTokenizerFast.from_pretrained('facebook/dpr-ctx_encoder-single-nq-base')
question_encoder = DPRQuestionEncoder.from_pretrained('facebook/dpr-question_encoder-single-nq-base').to(device)
question_tokenizer = DPRQuestionEncoderTokenizerFast.from_pretrained('facebook/dpr-question_encoder-single-nq-base')

# Trích dẫn mẫu cần tìm nội dung liên quan
citation = "According to the Intergovernmental Panel on Climate Change (IPCC) report in 2021"

# Nội dung từ graph PDF (được tổ chức thành các câu)
pdf_content = [
    "According to the Intergovernmental Panel on Climate Change (IPCC) report in 2021, global temperatures are expected to rise by 1.5 degrees Celsius by 2030.",
    "The report emphasizes the urgent need for immediate action to reduce greenhouse gas emissions.",
    "Renewable energy sources, such as solar and wind power, are essential for achieving a sustainable future.",
    "Increased carbon dioxide levels have been linked to severe weather patterns and natural disasters.",
    "Mitigation strategies include reforestation, energy efficiency improvements, and transitioning to a circular economy."
]

# Mã hóa trích dẫn
question_inputs = question_tokenizer(citation, return_tensors='pt').to(device)
with torch.no_grad():
    question_embedding = question_encoder(**question_inputs).pooler_output

# Mã hóa nội dung PDF và lưu trữ embeddings
context_embeddings = []
for content in pdf_content:
    ctx_inputs = ctx_tokenizer(content, return_tensors='pt').to(device)
    with torch.no_grad():
        context_embedding = ctx_encoder(**ctx_inputs).pooler_output
        context_embeddings.append(context_embedding)

# Tính độ tương đồng và trích xuất nội dung liên quan
similarity_threshold = 0.5  # Ngưỡng tương đồng

main_content = None
highest_similarity = float('-inf')  # Khởi tạo với giá trị âm vô cùng

for idx, context_embedding in enumerate(context_embeddings):
    # Tính cosine similarity giữa trích dẫn và từng đoạn văn bản
    similarity = torch.nn.functional.cosine_similarity(question_embedding, context_embedding)
    
    # Kiểm tra nếu độ tương đồng cao hơn giá trị đã lưu
    if similarity.item() > highest_similarity:
        highest_similarity = similarity.item()
        main_content = pdf_content[idx]  # Cập nhật nội dung trích dẫn

# In ra kết quả cuối cùng
print(f"Nội dung liên quan đến trích dẫn '{citation}':")
if main_content:
    print(f"Trích dẫn: {main_content}")
else:
    print("Không tìm thấy nội dung trích dẫn chính xác.")