import spacy

# Load the spaCy language model
nlp = spacy.load("en_core_web_sm")

def extract_citations(sentence):
    raw_citations = []
    cleaned_citations = []

    # First, split the sentence into parts based on parentheses
    parts = sentence.split('(')
    for part in parts:
        if ')' in part:
            before_parenthesis, after_parenthesis = part.split(')', 1)
            raw_citations.append(before_parenthesis.strip() + ')')
            raw_citations.append(after_parenthesis.strip())
        else:
            raw_citations.append(part.strip())

    # Print raw citations for debugging
    print("Raw Citations:", raw_citations)

    # Process each raw citation using while loop
    i = 0
    while i < len(raw_citations):
        if i + 1 < len(raw_citations):
            # Combine the phrase before and after the parenthesis
            citation_part = raw_citations[i].replace('\n', ' ').strip() + ' (' + raw_citations[i+1].strip() + ')'
            
            # Extract the most relevant phrase before the parenthesis
            doc = nlp(raw_citations[i].replace('\n', ' ').strip())
            last_phrase = ""
            j = len(doc) - 1
            while j >= 0:
                token = doc[j]
                # Collect full noun phrases or conjunctions leading to relevant content
                if token.pos_ in ["NOUN", "PROPN", "ADJ", "CCONJ", "PUNCT"] or (token.pos_ == "VERB" and token.dep_ == "amod"):
                    last_phrase = token.text_with_ws + last_phrase
                elif last_phrase:  # Stop once we have collected the relevant part
                    break
                j -= 1
            
            if last_phrase:
                citation_part = last_phrase.strip() + " (" + raw_citations[i+1].strip() + ')'
            
            # Strip trailing periods and commas after parentheses
            citation_part = citation_part.rstrip('.').replace('(', '(', 1).replace(', ', ' ', 1)
            
            # Remove any extra closing parentheses
            citation_part = citation_part.replace('))', ')')
            
            cleaned_citations.append(citation_part.strip())
        else:
            cleaned_citations.append(raw_citations[i].replace('\n', ' ').strip().rstrip('.'))
        
        # Move to the next pair of citations
        i += 2

    # Remove any empty citations
    cleaned_citations = [citation for citation in cleaned_citations if citation]

    # Print cleaned citations for debugging
    print("Cleaned Citations:", cleaned_citations)

    return cleaned_citations

# Test sentence
sentence = """The analysis of acknowledgments is particularly interesting as acknowledgments may give an insight into aspects of the scientific community, 
such as reward systems (Dzieżyc & Kazienko, 2022), collaboration patterns, and hidden research trends (Giles & Councill, 2004; Diaz-Faes & Bordons, 2017)."""

result = extract_citations(sentence)

# Print results
print("----------")
print(f"sentence: \"{sentence}\"")
print(f"citations: {result}")
print("----------")
