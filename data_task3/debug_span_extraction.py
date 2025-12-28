"""Debug script to test span extraction logic"""
import re

def clean_span_text(span_text: str) -> str:
    """
    Normalize whitespace and punctuation spacing in span_text.
    """
    span_text = re.sub(r"\s+", " ", span_text)
    span_text = re.sub(r"\s+([.,!?;:])", r"\1", span_text)
    return span_text.strip()

def fallback_spans_current(text: str, markers: list) -> list:
    """Current fallback logic from main.py"""
    spans = []

    for m in markers:
        idx = text.find(m)
        if idx == -1:
            clean_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())
            clean_text = clean_span_text(clean_text[:200])
            spans.append({"citation_id": m, "span_text": clean_text})
            continue

        # Find sentence start
        start = 0
        before_text = text[:idx]
        for match in re.finditer(r"[.!?]\s+", before_text):
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

        print(f"DEBUG: Initial span length: {len(span_text)}")
        print(f"DEBUG: Initial span: '{span_text[:100]}...'")

        # If span is too short, try to get more context
        if len(span_text) < 20:
            print(f"DEBUG: Span too short, using 150-char context window")
            print(f"DEBUG: marker idx={idx}, context_start={max(0, idx - 150)}")

            context_start = max(0, idx - 150)
            context_end = min(len(text), idx + len(m) + 150)
            span_text = text[context_start:context_end].strip()

            print(f"DEBUG: Context span before citation removal: '{span_text[:100]}...'")

            span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()

        # Final fallback - ensure non-empty
        if not span_text:
            span_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())[:200]

        # Clean spacing & punctuation
        span_text = clean_span_text(span_text)

        spans.append({"citation_id": m, "span_text": span_text})

    return spans


# Test with the actual text from file 70
test_text = "• The matching procedure calculates a matrix for any set of moments without indicating if the matrix (together with the predefined initial and final vectors) corresponds to a matrix exponential distribution or not. When the procedure is called with the moments of a matrix exponential distribution of order N it results in a true matrix exponential distribution of order N , but when it is called with an invalid set of moments it results in a matrix which does not correspond to a real distribution. Unfortunately, it is hard to check if a given matrix corresponds to a real matrix exponential distribution; see Ref. [CITATION_1] ."

print("=" * 80)
print("TESTING CURRENT LOGIC WITH FILE 70")
print("=" * 80)
print(f"Full text length: {len(test_text)}")
print(f"Marker position: {test_text.find('[CITATION_1]')}")
print()

result = fallback_spans_current(test_text, ["[CITATION_1]"])
print()
print("=" * 80)
print("RESULT:")
print("=" * 80)
print(f"span_text: '{result[0]['span_text']}'")
print()
print("PROBLEMS:")
print("1. Starts with 'rrespond' - cut mid-word!")
print("2. Ends with 'Ref..' - double period after cleaning")
