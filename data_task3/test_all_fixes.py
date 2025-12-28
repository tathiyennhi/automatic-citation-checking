"""Test all fixes"""
import re
from typing import List, Dict

def clean_span_text(span_text: str) -> str:
    span_text = re.sub(r"\s+", " ", span_text)
    span_text = re.sub(r"\s+([.,!?;:])", r"\1", span_text)
    # Fix double periods
    span_text = re.sub(r"\.\.+", ".", span_text)
    return span_text.strip()


def fallback_spans(text: str, markers: List[str]) -> List[Dict]:
    """FIXED version with all improvements"""
    spans: List[Dict] = []

    for m in markers:
        idx = text.find(m)
        if idx == -1:
            clean_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())
            clean_text = clean_span_text(clean_text[:200])
            spans.append({"citation_id": m, "span_text": clean_text})
            continue

        # FIXED: Pattern with lookahead for capital letter
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

        # Extract sentence
        span_text = text[start:end].strip()

        # Remove citations
        span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()

        # FIXED: Keep only first sentence after removing citations
        first_sentence_match = re.search(r"[.!?]", span_text)
        if first_sentence_match:
            span_text = span_text[: first_sentence_match.end()].strip()

        # If span is too short, get more context
        if len(span_text) < 20:
            context_start = max(0, idx - 150)
            context_end = min(len(text), idx + len(m) + 150)
            span_text = text[context_start:context_end].strip()
            span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()

        # Final fallback
        if not span_text:
            span_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())[:200]

        # FIXED: Clean with double-period fix
        span_text = clean_span_text(span_text)

        spans.append({"citation_id": m, "span_text": span_text})

    return spans


print("=" * 80)
print("TEST 1: File 70 - Ref. abbreviation + double period")
print("=" * 80)
text1 = "• The matching procedure calculates a matrix for any set of moments without indicating if the matrix (together with the predefined initial and final vectors) corresponds to a matrix exponential distribution or not. When the procedure is called with the moments of a matrix exponential distribution of order N it results in a true matrix exponential distribution of order N , but when it is called with an invalid set of moments it results in a matrix which does not correspond to a real distribution. Unfortunately, it is hard to check if a given matrix corresponds to a real matrix exponential distribution; see Ref. [CITATION_1] ."

result1 = fallback_spans(text1, ["[CITATION_1]"])
print(f"Result: '{result1[0]['span_text']}'")
print(f"✅ Starts with 'Unfortunately': {result1[0]['span_text'].startswith('Unfortunately')}")
print(f"✅ No 'rrespond': {'rrespond' not in result1[0]['span_text']}")
print(f"✅ No double periods: {'..' not in result1[0]['span_text']}")
print()

print("=" * 80)
print("TEST 2: Multiple citations sát nhau")
print("=" * 80)
text2 = "This is a claim [CITATION_1] [CITATION_2] [CITATION_3]. Another sentence here."

result2 = fallback_spans(text2, ["[CITATION_1]", "[CITATION_2]", "[CITATION_3]"])
print("Results:")
for r in result2:
    print(f"  {r['citation_id']}: '{r['span_text']}'")

all_same = all(r['span_text'] == 'This is a claim.' for r in result2)
no_extra = all('Another sentence' not in r['span_text'] for r in result2)
print(f"✅ All have same span: {all_same}")
print(f"✅ No extra sentence: {no_extra}")
print()

print("=" * 80)
print("TEST 3: Fig. abbreviation")
print("=" * 80)
text3 = "The results are shown in Fig. 2. The model achieved 95% accuracy [CITATION_1]."

result3 = fallback_spans(text3, ["[CITATION_1]"])
print(f"Result: '{result3[0]['span_text']}'")
print(f"✅ Doesn't include 'Fig. 2': {'Fig. 2' not in result3[0]['span_text']}")
print(f"✅ Correct span: {result3[0]['span_text'] == 'The model achieved 95% accuracy.'}")
print()

print("=" * 80)
print("SUMMARY: All fixes working!" if all([
    result1[0]['span_text'].startswith('Unfortunately'),
    'rrespond' not in result1[0]['span_text'],
    '..' not in result1[0]['span_text'],
    all_same,
    no_extra,
    'Fig. 2' not in result3[0]['span_text']
]) else "SUMMARY: Some tests failed!")
print("=" * 80)
