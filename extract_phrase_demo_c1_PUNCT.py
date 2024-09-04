import spacy

# Load the spaCy language model
nlp = spacy.load("en_core_web_sm")

def extract_phrases(doc):
    """
    Extract noun phrases and keep conjunctions connecting them.
    """
    phrases = []
    current_phrase = ""
    
    for token in doc:
        if token.pos_ in ["NOUN", "PROPN", "ADJ", "DET"] and token.dep_ not in ["amod", "prep", "advmod", "punct"]:
            current_phrase += token.text_with_ws
        elif token.pos_ == "CCONJ" and current_phrase:
            current_phrase += token.text_with_ws
        elif token.pos_ == "PUNCT" and current_phrase:
            phrases.append(current_phrase.strip())
            current_phrase = ""
        else:
            if current_phrase:
                phrases.append(current_phrase.strip())
                current_phrase = ""
    
    if current_phrase:
        phrases.append(current_phrase.strip())
    
    return phrases

def extract_citation(sentence):
    doc = nlp(sentence)
    relevant_phrases = []

    def extract_full_noun_phrases_before_parenthesis(doc, start_index):
        phrases = []
        current_phrase = ""
        i = start_index
        
        while i >= 0:
            token = doc[i]
            if token.pos_ in ["AMOD", "NOUN", "PROPN", "ADJ", "DET", "CCONJ", 'PUNCT']:
                current_phrase = token.text_with_ws + current_phrase
            # elif token.pos_ == "CCONJ" and current_phrase:
            #     current_phrase = token.text_with_ws  + current_phrase
            # elif token.pos_ in ['PUNCT'] and current_phrase:
            #     current_phrase = token.text_with_ws + current_phrase
            else:
                if current_phrase:
                    phrases.insert(0, current_phrase.strip())
                    current_phrase = ""
                if token.pos_ == "CCONJ" or token.dep_ == "ROOT" or token.dep_ in ["prep", "advmod"]:
                    break
            i -= 1
        
        if current_phrase:
            phrases.insert(0, current_phrase.strip())
        
        return " ".join(phrases)

    for i, token in enumerate(doc):
        if token.text == "(":
            noun_phrases = extract_full_noun_phrases_before_parenthesis(doc, i - 1)
            current_phrase = noun_phrases + " " + token.text

            j = i + 1
            while j < len(doc) and doc[j].text != ")":
                current_phrase += doc[j].text_with_ws
                j += 1

            if j < len(doc):
                current_phrase += doc[j].text

            relevant_phrases.append(current_phrase.strip())

    return relevant_phrases

# Test sentence
sentence = """collaboration patterns, hidden research trends (Giles & Councill, 2004; Diaz-Faes & Bordons, 2017)."""

result = extract_citation(sentence)

# Print results
print("----------")
print(f"sentence: \"{sentence}\"")
print(f"citations: {result}")
print("----------")
