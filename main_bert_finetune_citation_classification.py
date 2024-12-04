import torch
from transformers import BertTokenizerFast, BertForSequenceClassification, Trainer, TrainingArguments
import pandas as pd 
from datasets import Dataset
import numpy as np
from evaluate import load as load_metric


data = [
    # Câu có trích dẫn
    {'text': "Giles and Councill (2004) argue that acknowledgments to individuals, in the same way as citations, may be used as a metric to measure an individual's intellectual contribution to scientific work.", 'label': 1},
    {'text': "Acknowledgments of technical and instrumental support may reveal 'indirect contributions of research laboratories and universities to research activities' (Giles & Councill, 2004, p. 17599).", 'label': 1},
    {'text': "Smith et al. (2010) found that collaboration between institutions significantly increases research output.", 'label': 1},
    {'text': "According to Johnson (2015), early childhood education has a profound impact on cognitive development.", 'label': 1},
    {'text': "The study conducted by Brown and Taylor (2012) demonstrated the importance of proper nutrition in early childhood.", 'label': 1},
    {'text': "As highlighted by Lee (2018), advancements in AI technology are rapidly transforming industries.", 'label': 1},

    # Câu không có trích dẫn
    {'text': "In recent years, there has been an increasing interest in the study of acknowledgments.", 'label': 0},
    {'text': "Scientific research often requires a substantial amount of collaboration and support.", 'label': 0},
    {'text': "Many universities offer grants and funding to support innovative research projects.", 'label': 0},
    {'text': "Technology has evolved rapidly over the past decade, influencing almost every industry.", 'label': 0},
    {'text': "Proper nutrition and regular exercise are crucial for maintaining a healthy lifestyle.", 'label': 0},
    {'text': "The impact of climate change is becoming more evident, with rising global temperatures and melting ice caps.", 'label': 0},
]


# Tạo DataFrame từ dữ liệu
df = pd.DataFrame(data)

# Chuyển đổi DataFrame thành tập dữ liệu của Hugging Face
dataset = Dataset.from_pandas(df)

# Tải tokenizer và mô hình BERT từ Hugging Face
bert_tokenizer = BertTokenizerFast.from_pretrained('bert-base-uncased')
bert_model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)

# Hàm để tokenize dữ liệu
def tokenize_function(examples):
    return bert_tokenizer(examples['text'], padding='max_length', truncation=True, max_length=128)

# Tokenize tập dữ liệu
tokenized_dataset = dataset.map(tokenize_function, batched=True)

# Chia tập dữ liệu thành tập huấn luyện và tập kiểm tra
split_dataset = tokenized_dataset.train_test_split(test_size=0.5)

# Thiết lập các thông số huấn luyện
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    evaluation_strategy='epoch',
    save_strategy='epoch',
    logging_dir='./logs',
)

# Tải metric để đánh giá
metric = load_metric("accuracy")

# Hàm tính toán các metric
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)

# Khởi tạo Trainer
trainer = Trainer(
    model=bert_model,
    args=training_args,
    train_dataset=split_dataset['train'],
    eval_dataset=split_dataset['test'],
    compute_metrics=compute_metrics,
)

# Huấn luyện mô hình
trainer.train()

# Đánh giá mô hình
eval_result = trainer.evaluate()
print(f"Kết quả đánh giá: {eval_result}")

# Lưu mô hình đã được tinh chỉnh
bert_model.save_pretrained("./trained_model")
bert_tokenizer.save_pretrained("./trained_model")
