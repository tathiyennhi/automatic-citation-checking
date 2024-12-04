import torch
from transformers import BertTokenizerFast, BertForSequenceClassification
import spacy

# Tải lại tokenizer từ mô hình gốc và lưu vào thư mục checkpoint
# Đường dẫn đến checkpoint đã fine-tune
model_path = './results/checkpoint-9'

# Tải tokenizer từ mô hình gốc 'bert-base-uncased'
bert_tokenizer = BertTokenizerFast.from_pretrained('bert-base-uncased')

# Lưu tokenizer vào thư mục checkpoint
bert_tokenizer.save_pretrained(model_path)

# Tải mô hình đã fine-tune từ checkpoint
bert_model = BertForSequenceClassification.from_pretrained(model_path).to('cpu')

# Tải mô hình spaCy để chia câu
nlp = spacy.load("en_core_web_sm")

# Chia câu từ văn bản
def split_into_sentences(text):
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]

# Văn bản mẫu
article_text = """
Giles and Councill (2004) argue that acknowledgments to individuals, in the same way as citations...
Acknowledgments of technical and instrumental support may reveal...
In recent years, there has been an increasing interest in the study of acknowledgments.
Kayal  et  al.  (2017)  introduced  a  method  for  extraction  of  funding  organizations  and  
grants from acknowledgment texts using a combination of sequential learning models: con-
ditional random fields (CRF), hidden markov models (HMM), and maximum entropy mod-
els (MaxEnt). Previous  works  showed  improvements  in  downstream  tasks  using  embedding  models  
fine-tuned  for  the  domain  used  (Shen  et  al.,  2022;  Beltagy  et  al..,  2019). Flair  is  an  open-sourced  NLP  framework  built  on  PyTorch  (Paszke  et  al.,  2019),  which  
is  an  open-source  machine  learning  library.  “The  core  idea  of  the  framework  is  to  pre-
sent a simple, unified interface for conceptually very different types of word and document 
embeddings”  (Akbik  et  al.,  2019,  p.  54).  Flair  has  three  default  training  algorithms  for  
NER which were used for the first experiment in the present research: a) NER Model with 
Flair  Embeddings  (later  on  Flair  Embeddings)  (Akbik  et  al.,  2018),  b)  NER  Model  with  
Transformers  (later  on  Transformers)  (Schweter  &  Akbik,  2020),  and  c)  Zero-shot  NER  
with TARS (later on TARS) (Halder et al., 2020) 8.
"""

# Chia văn bản thành các câu
sentences = split_into_sentences(article_text)

# Tokenize các câu và dự đoán nhãn
inputs = bert_tokenizer(sentences, padding=True, truncation=True, return_tensors="pt").to('cpu')
with torch.no_grad():
    outputs = bert_model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=1).cpu().numpy()

# Lọc các câu chứa trích dẫn
cited_sentences = [sentences[i] for i, label in enumerate(predictions) if label == 1]

# In các câu có trích dẫn
print('\nCác câu chứa trích dẫn được phát hiện:')
for idx, sentence in enumerate(cited_sentences):
    print(f'Câu {idx+1}: {sentence}')
