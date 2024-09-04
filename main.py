import spacy
import PyPDF2
import pandas as pd

# Tải mô hình ngôn ngữ của spaCy
nlp = spacy.load("en_core_web_sm")

def extract_citations(sentence):
    doc = nlp(sentence)
    relevant_phrases = []

    def extract_full_phrase_or_noun(doc, start_index):
        phrases = []
        current_phrase = ""
        i = start_index
        
        # Kiểm tra nếu câu bắt đầu bằng tên riêng hoặc đại từ thì lấy cả mệnh đề
        if doc[0].ent_type_ in ["PERSON", "ORG"] or doc[0].pos_ == "PRON":
            return doc[:start_index+1].text
        
        while i >= 0:
            token = doc[i]
            if token.pos_ in ["NOUN", "PROPN", "ADJ", "DET"]:
                current_phrase = token.text_with_ws + current_phrase
            elif token.dep_ in ["amod", "compound"]:
                current_phrase = token.text_with_ws + current_phrase
            else:
                if current_phrase:
                    phrases.insert(0, current_phrase.strip())
                    current_phrase = ""
                if token.dep_ in ["ROOT", "nsubj", "csubj", "csubjpass", "nsubjpass"] or token.pos_ == "VERB" or token.dep_ == "prep":
                    break
            i -= 1
        
        if current_phrase:
            phrases.insert(0, current_phrase.strip())
        
        return " ".join(phrases)

    citations = []
    for i, token in enumerate(doc):
        if token.text == "(":
            phrase = extract_full_phrase_or_noun(doc, i - 1)
            current_phrase = phrase + " " + token.text

            j = i + 1
            while j < len(doc) and doc[j].text != ")":
                current_phrase += doc[j].text_with_ws
                j += 1

            if j < len(doc):
                current_phrase += doc[j].text

            if current_phrase.strip() not in citations:
                citations.append(current_phrase.strip())

    return citations

def get_phrase_near_citation(sentence):
    doc = nlp(sentence)
    start_idx = 0
    for i, token in reversed(list(enumerate(doc))):
        if token.text == "(":
            for j in range(i, -1, -1):
                if doc[j].dep_ == "ROOT" or doc[j].pos_ == "VERB":
                    start_idx = j
                    break
            return doc[start_idx:i].text.strip()
    return sentence.strip()

def extract_authors_and_years(citation):
    doc = nlp(citation)
    authors = []
    years = []

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            authors.append(ent.text)
        elif ent.label_ == "DATE" and len(ent.text) == 4:
            years.append(ent.text)

    return authors, years

def process_pdf_to_csv(pdf_path, csv_path):
    # Mở và đọc tệp PDF
    pdf_file = open(pdf_path, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""

    for page in pdf_reader.pages:
        text += page.extract_text()

    pdf_file.close()

    # Tìm vị trí của phần "References" và cắt phần văn bản trước đó
    references_position = text.lower().find("references")
    if references_position != -1:
        text = text[:references_position]

    # Chuyển đổi văn bản thành đối tượng spaCy Doc
    doc = nlp(text)

    # Sử dụng spaCy để phân tách câu
    sentences = list(doc.sents)
    data = []
    seen_sentences = set()

    for sentence in sentences:
        sentence_text = sentence.text.strip()
        if sentence_text in seen_sentences:
            continue

        seen_sentences.add(sentence_text)
        citations = extract_citations(sentence_text)
        if citations:
            phrase = get_phrase_near_citation(sentence_text)
            for citation in citations:
                authors, years = extract_authors_and_years(citation)
                if not authors or not years:
                    # Bỏ qua các trích dẫn không có tác giả hoặc năm
                    continue
                for author, year in zip(authors, years):
                    row = {
                        "Sentence": sentence_text,
                        "Citation": citation,
                        "Author": author,
                        "Year": year
                    }
                    if row not in data:
                        data.append(row)

    # Chuyển dữ liệu thành DataFrame và lưu vào CSV
    df = pd.DataFrame(data, columns=["Sentence", "Citation", "Author", "Year"])
    df.to_csv(csv_path, index=False)

# Đường dẫn tệp PDF và CSV
pdf_path = "paper.pdf"  # Thay bằng đường dẫn thực tế của bạn
csv_path = "apa_citation.csv"

# Xử lý tệp PDF và lưu kết quả vào CSV
process_pdf_to_csv(pdf_path, csv_path)
