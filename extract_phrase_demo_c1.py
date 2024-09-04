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
        # Chấp nhận các POS là VERB nếu DEP là amod
        if (token.pos_ in ["NOUN", "PROPN", "ADJ", "DET"] or
            (token.pos_ == "VERB" and token.dep_ == "amod")):
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

    # Print each token and its details
    print("Tokens and their details:")
    for token in doc:
        print(f"Token: '{token.text}' | POS: {token.pos_} | DEP: {token.dep_}")

    def extract_full_noun_phrases_before_parenthesis(doc, start_index):
        phrases = []
        current_phrase = ""
        i = start_index
        
        while i >= 0:
            token = doc[i]
            # Chấp nhận các POS là VERB nếu DEP là amod
            if (token.pos_ in ["NOUN", "PROPN", "ADJ", "DET", "PUNCT", "CCONJ"] or
                (token.pos_ == "VERB" and token.dep_ == "amod")):
                current_phrase = token.text_with_ws + current_phrase
            # elif token.pos_ == "CCONJ" and current_phrase:
            #     current_phrase = token.text_with_ws + current_phrase
            # else:
            #     if current_phrase:
            #         phrases.insert(0, current_phrase.strip())
            #         current_phrase = ""
            #     if token.pos_ == "CCONJ" or token.dep_ == "ROOT":
            #         break
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
sentence = """collaboration patterns, and hidden research trends (Giles & Councill, 2004; Diaz-Faes & Bordons, 2017)."""

result = extract_citation(sentence)

# Print results
print("----------")
print(f"sentence: \"{sentence}\"")
print(f"citations: {result}")
print("----------")
