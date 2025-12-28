"""Analyze the real problem"""
import re

text = "• The matching procedure calculates a matrix for any set of moments without indicating if the matrix (together with the predefined initial and final vectors) corresponds to a matrix exponential distribution or not. When the procedure is called with the moments of a matrix exponential distribution of order N it results in a true matrix exponential distribution of order N , but when it is called with an invalid set of moments it results in a matrix which does not correspond to a real distribution. Unfortunately, it is hard to check if a given matrix corresponds to a real matrix exponential distribution; see Ref. [CITATION_1] ."

marker = "[CITATION_1]"
idx = text.find(marker)

print("=" * 80)
print("PHÂN TÍCH VẤN ĐỀ THỰC SỰ")
print("=" * 80)
print(f"Text length: {len(text)}")
print(f"Marker position: {idx}")
print()

# Current logic: tìm sentence start
print("CURRENT LOGIC - Tìm sentence start:")
print("Pattern: [.!?]\\s+")
print()

before_text = text[:idx]
matches = list(re.finditer(r"[.!?]\s+", before_text))
print(f"Found {len(matches)} matches in before_text:")
for i, match in enumerate(matches[-3:], 1):  # Show last 3
    start_pos = match.end()
    snippet = before_text[match.start():min(match.end()+30, len(before_text))]
    print(f"  Match {len(matches)-3+i}: pos={match.start()}-{match.end()}, snippet='{snippet}'")

if matches:
    last_match = matches[-1]
    print()
    print(f"❌ LAST match (được chọn làm sentence start): position={last_match.end()}")
    print(f"   Text at that position: '{before_text[last_match.start():last_match.end()+50]}'")
    print()
    print("VẤN ĐỀ: 'Ref. ' match pattern [.!?]\\s+ → sentence start SAI!")

print()
print("=" * 80)
print("SENTENCE THỰC SỰ:")
print("=" * 80)
# Find actual sentence containing citation
# Should start after "distribution. " (before "Unfortunately")
actual_sentence_start = text.find("Unfortunately")
actual_sentence_end = text.rfind(".")
actual_sentence = text[actual_sentence_start:actual_sentence_end+1]
print(f"Start position: {actual_sentence_start}")
print(f"Sentence: '{actual_sentence}'")
print()

print("=" * 80)
print("GIẢI PHÁP:")
print("=" * 80)
print("1. Phải phân biệt: 'Ref.' (abbreviation) vs 'distribution.' (sentence ending)")
print("2. Cải thiện pattern: [.!?]\\s+(?=[A-Z]) - dấu chấm + space + CHỮ HOA")
print("   → 'Ref. [' không match ([ không phải chữ hoa)")
print("   → 'distribution. U' match (U là chữ hoa)")
print()

# Test improved pattern
print("TEST IMPROVED PATTERN: [.!?]\\s+(?=[A-Z])")
improved_matches = list(re.finditer(r"[.!?]\s+(?=[A-Z])", before_text))
print(f"Found {len(improved_matches)} matches:")
for i, match in enumerate(improved_matches, 1):
    snippet = before_text[max(0, match.start()-10):match.end()+30]
    print(f"  Match {i}: '...{snippet}...'")

if improved_matches:
    last_match = improved_matches[-1]
    print()
    print(f"✅ LAST match: position={last_match.end()}")
    extracted = text[last_match.end():idx+len(marker)+5]
    print(f"   Extracted span: '{extracted}'")
