import spacy

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

            relevant_phrases.append(current_phrase.strip())

    return relevant_phrases

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

def needs_manual_review(sentence):
    doc = nlp(sentence)
    
    citation_count = sum(1 for token in doc if token.text == "(")
    if citation_count > 1:
        return True
    
    clause_count = sum(1 for token in doc if token.dep_ in ["ccomp", "advcl", "relcl", "xcomp", "acl", "pcomp", "csubj", "csubjpass"])
    if clause_count > 1:
        return True
    
    special_keywords = ["according to", "as stated by", "compared with", "this method", "based on"]
    if any(keyword in sentence.lower() for keyword in special_keywords):
        return True
    
    if doc[-1].text == "." and any(token.text == "(" for token in doc[-10:]):
        return True

    if len(doc) > 1:
        first_token = doc[0]
        if first_token.text.lower() in ["that", "shows", "states", "indicates", "suggests"] or first_token.pos_ == "VERB":
            return True

    return False

def process_text(text):
    sentences = text.split('. ')
    for sentence in sentences:
        citations = extract_citations(sentence)
        if citations:
            phrase = get_phrase_near_citation(sentence)
            print(f"Câu có trích dẫn: \"{sentence}\"")
            print(f"Phần liên quan đến trích dẫn: \"{phrase}\"")
            print(f"Trích dẫn: {citations}")
            if needs_manual_review(sentence):
                print(f"=> Câu này cần kiểm tra thủ công.\n")
            else:
                print(f"=> Câu này không cần kiểm tra thủ công.\n")

# Ví dụ văn bản để kiểm tra
text = """The training for the few-shot approach was initiated with the TARS NER model (Halder et al., 2020). We used a standard approach, where only a linear classifier layer was added on the top of the transformer, as adding the additional CRF decoder between the transformer and linear classifier did not increase accuracy compared with this standard approach (Schweter & Akbik, 2020). Another study showed improvements in downstream tasks using embedding models (Smith et al., 2021)."""

# Xử lý văn bản
process_text(text)
