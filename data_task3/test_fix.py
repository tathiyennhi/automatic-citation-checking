"""Test the fixed fallback_spans function"""
import re
from typing import List, Dict

def clean_span_text(span_text: str) -> str:
    span_text = re.sub(r"\s+", " ", span_text)
    span_text = re.sub(r"\s+([.,!?;:])", r"\1", span_text)
    return span_text.strip()


def fallback_spans(text: str, markers: List[str]) -> List[Dict]:
    """FIXED: extract complete sentence containing citation marker."""
    spans: List[Dict] = []

    for m in markers:
        idx = text.find(m)
        if idx == -1:
            clean_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())
            clean_text = clean_span_text(clean_text[:200])
            spans.append({"citation_id": m, "span_text": clean_text})
            continue

        # FIXED: Find sentence start - pattern now requires capital letter after punctuation
        start = 0
        before_text = text[:idx]
        for match in re.finditer(r"[.!?]\s+(?=[A-Z•])", before_text):
            start = match.end()

        # Find sentence end
        end = len(text)
        after_text = text[idx + len(m):]
        match = re.search(r"[.!?]", after_text)
        if match:
            end = idx + len(m) + match.end()

        # Extract COMPLETE sentence
        span_text = text[start:end].strip()

        # Remove ALL citation markers from span
        span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()

        # If span is too short, try to get more context
        if len(span_text) < 20:
            context_start = max(0, idx - 150)
            context_end = min(len(text), idx + len(m) + 150)
            span_text = text[context_start:context_end].strip()
            span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()

        # Final fallback
        if not span_text:
            span_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())[:200]

        # Clean spacing
        span_text = clean_span_text(span_text)

        spans.append({"citation_id": m, "span_text": span_text})

    return spans


# Test case 1: File 70
print("=" * 80)
print("TEST CASE 1: File 70 (Ref. abbreviation problem)")
print("=" * 80)

text1 = "• The matching procedure calculates a matrix for any set of moments without indicating if the matrix (together with the predefined initial and final vectors) corresponds to a matrix exponential distribution or not. When the procedure is called with the moments of a matrix exponential distribution of order N it results in a true matrix exponential distribution of order N , but when it is called with an invalid set of moments it results in a matrix which does not correspond to a real distribution. Unfortunately, it is hard to check if a given matrix corresponds to a real matrix exponential distribution; see Ref. [CITATION_1] ."

result1 = fallback_spans(text1, ["[CITATION_1]"])
print(f"span_text: '{result1[0]['span_text']}'")
print()
print("✅ EXPECTED: Start with 'Unfortunately' (not 'rrespond')")
print("✅ EXPECTED: No double periods")
print()

# Test case 2: Multiple citations close together
print("=" * 80)
print("TEST CASE 2: Multiple citations sát nhau")
print("=" * 80)

text2 = "This is a claim [CITATION_1] [CITATION_2] [CITATION_3]. Another sentence here."

result2 = fallback_spans(text2, ["[CITATION_1]", "[CITATION_2]", "[CITATION_3]"])
for r in result2:
    print(f"{r['citation_id']}: '{r['span_text']}'")

print()
print("✅ EXPECTED: Cả 3 citations đều share cùng span 'This is a claim.'")
print()

# Test case 3: Fig. abbreviation
print("=" * 80)
print("TEST CASE 3: Fig. abbreviation")
print("=" * 80)

text3 = "The results are shown in Fig. 2. The model achieved 95% accuracy [CITATION_1]."

result3 = fallback_spans(text3, ["[CITATION_1]"])
print(f"span_text: '{result3[0]['span_text']}'")
print()
print("✅ EXPECTED: 'The model achieved 95% accuracy' (không bao gồm 'Fig. 2')")
