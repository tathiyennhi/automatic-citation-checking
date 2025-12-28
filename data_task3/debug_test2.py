"""Debug test case 2"""
import re

text = "This is a claim [CITATION_1] [CITATION_2] [CITATION_3]. Another sentence here."
m = "[CITATION_1]"

print("=" * 80)
print("DEBUG TEST 2")
print("=" * 80)
print(f"Text: '{text}'")
print(f"Text length: {len(text)}")
print()

idx = text.find(m)
print(f"Marker '{m}' at position: {idx}")
print()

# Find start
start = 0
before_text = text[:idx]
print(f"before_text: '{before_text}'")
matches = list(re.finditer(r"[.!?]\s+(?=[A-Z•])", before_text))
print(f"Sentence boundaries before marker: {len(matches)}")
if matches:
    for match in matches:
        start = match.end()
print(f"start = {start}")
print()

# Find end
end = len(text)
after_text = text[idx + len(m):]
print(f"after_text: '{after_text}'")
match = re.search(r"[.!?]", after_text)
if match:
    print(f"First punctuation in after_text at position {match.start()}: '{after_text[match.start()]}'")
    print(f"Context: '{after_text[max(0, match.start()-5):match.end()+5]}'")
    end = idx + len(m) + match.end()
    print(f"end = {idx} + {len(m)} + {match.end()} = {end}")
print()

# Extract
span_text = text[start:end].strip()
print(f"Extracted span: '{span_text}'")
print()

# Remove citations
span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
print(f"After removing citations: '{span_text}'")
print()

# Keep first sentence
print("Finding first sentence in cleaned span...")
first_sentence_match = re.search(r"[.!?]", span_text)
if first_sentence_match:
    print(f"First punctuation at position {first_sentence_match.start()}: '{span_text[first_sentence_match.start()]}'")
    print(f"Context: '{span_text[max(0, first_sentence_match.start()-5):first_sentence_match.end()+10]}'")
    span_text = span_text[: first_sentence_match.end()].strip()
    print(f"After keeping first sentence: '{span_text}'")
