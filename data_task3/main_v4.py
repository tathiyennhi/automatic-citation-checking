"""
Task 3 generation - VERSION 4: THE GOLD STANDARD (SENTENCE-LEVEL)

KEY IMPROVEMENTS:
1. ✅ ATOMIC SENTENCE LOGIC: Always extract the full sentence containing the citation.
2. ✅ NO FRAGMENTATION: Solves the ", lower-limb" error by including the context (Subject+Verb).
3. ✅ ROBUST BOUNDARIES: Improved abbreviations handling (Dr., Fig., et al.).
4. ✅ EXACT ALIGNMENT: Minimal cleaning to ensure exact substring matching.

PHILOSOPHY:
- A citation, regardless of its position (start/mid/end), supports the semantic unit (Sentence) it lives in.
- In a list (e.g., "A [1], B [2]"), both [1] and [2] share the full sentence context to preserve meaning.

Usage:
  python3 data_task3/main_v4.py --task2-dir data_outputs/task2 --output-dir data_outputs/task3_v4 --limit 10
"""

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_API_KEY = "AIzaSyBd12_HA7Uf0LtfYpLYnzD9QWOoFTXjaQU"


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_json_from_text(text: str) -> Optional[List[Dict]]:
    """Extract JSON array from model text."""
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
        return None


def build_prompt(text: str, markers: List[str]) -> str:
    # Prompt is kept for Gemini generation, though Fallback V4 is the star here.
    return (
        "You are a citation extraction expert. Extract the text span that each citation marker supports.\n\n"
        "INSTRUCTIONS:\n"
        "1. Identify the FULL SENTENCE that contains the citation marker.\n"
        "2. Extract the complete text of that sentence.\n"
        "3. Do not chop the sentence into fragments. Keep the Subject and Verb.\n"
        "4. If multiple citations are in the same sentence, they can share the same span text.\n"
        "5. Exclude the citation marker itself from the span text, but keep all other punctuation.\n\n"
        "OUTPUT FORMAT:\n"
        'Return ONLY a valid JSON array: [{"citation_id": "[CITATION_X]", "span_text": "..."}]\n'
        f"MARKERS TO EXTRACT: {markers}\n\n"
        "TEXT:\n"
        f"{text}\n\n"
        "Return the JSON array now:"
    )


def clean_span_text_preservative(span_text: str) -> str:
    """
    V4 CLEANING: HIGHLY PRESERVATIVE.
    Only strips leading/trailing whitespace.
    Does NOT collapse internal spaces.
    Does NOT remove spaces before punctuation.
    """
    return span_text.strip()


def find_sentence_boundaries_v4(text: str, citation_idx: int) -> tuple:
    """
    V4.1 BOUNDARY DETECTION (FIXED):
    - Added '[' to the lookahead regex so citations starting a sentence are detected.
    - Added a safety max_length to prevent grabbing whole paragraphs.
    """
    
    # Abbreviations check (Keep this)
    abbreviations = [
        r'Fig\.', r'Figs\.', r'et al\.', r'i\.e\.', r'e\.g\.', r'etc\.', 
        r'vs\.', r'cf\.', r'Dr\.', r'Mr\.', r'Mrs\.', r'Ms\.', r'Prof\.', 
        r'Ph\.D\.', r'M\.D\.', r'U\.S\.', r'U\.K\.', r'No\.', r'Vol\.', r'pp\.',
        r'[A-Z]\.'
    ]
    
    # --- SEARCH BACKWARDS (Start of Sentence) ---
    sentence_start = 0
    before_text = text[:citation_idx]
    
    # FIX: Added \[ to the character class allowing sentence starts
    # Also look for double newline (\n\n) as a hard paragraph break
    matches = list(re.finditer(r"(?:[.!?]\s+(?=[A-Z\"'•\d\[])|[\r\n]{2,})", before_text))
    
    if matches:
        # Check matches in reverse order (closest to citation first)
        for match in reversed(matches):
            pos = match.start()
            # If it's a newline break, that's a hard stop
            if "\n\n" in match.group(0) or "\r\n\r\n" in match.group(0):
                sentence_start = match.end()
                break

            # If it's punctuation, check abbreviation
            context = before_text[max(0, pos-10):pos+1]
            is_abbreviation = False
            for abbrev in abbreviations:
                if re.search(abbrev + r'$', context):
                    is_abbreviation = True
                    break
            
            if not is_abbreviation:
                sentence_start = match.end()
                break

    # --- SEARCH FORWARDS (End of Sentence) ---
    sentence_end = len(text)
    after_text = text[citation_idx:]
    
    # Look for [.!?] followed by (whitespace + Capital/Bracket) OR (End of String)
    # FIX: Added \[ here too, just in case
    match_iter = re.finditer(r"([.!?])(?:\s+[A-Z\"'•\[]|\s*$)", after_text)
    
    for match in match_iter:
        local_end = match.start()
        full_pos_in_text = citation_idx + local_end
        context = text[max(0, full_pos_in_text-10):full_pos_in_text+1]
        
        is_abbreviation = False
        for abbrev in abbreviations:
             if re.search(abbrev + r'$', context):
                is_abbreviation = True
                break
        
        if not is_abbreviation:
            sentence_end = citation_idx + match.start() + 1
            break
            
    # SAFETY VALVE: If sentence is > 500 chars, it's probably wrong. 
    # Cut it down to a window around the citation.
    if (sentence_end - sentence_start) > 500:
        sentence_start = max(0, citation_idx - 150)
        sentence_end = min(len(text), citation_idx + 150)
        # Snap to nearest space to avoid cutting words
        while sentence_start < citation_idx and text[sentence_start] != ' ':
            sentence_start += 1
        while sentence_end > citation_idx and text[sentence_end-1] != ' ':
            sentence_end -= 1

    return sentence_start, sentence_end


def fallback_spans_v4(text: str, markers: List[str]) -> List[Dict]:
    """
    FALLBACK V4: THE GOLD STANDARD
    
    Logic:
    1. Locate the marker.
    2. Identify the FULL SENTENCE boundaries surrounding it.
    3. Extract exact substring.
    4. Remove ONLY the citation tags from the string (to leave pure text).
    """
    spans: List[Dict] = []

    for m in markers:
        idx = text.find(m)
        if idx == -1:
            # Marker missing? Fallback to whole text or first chunk
            clean_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())
            spans.append({"citation_id": m, "span_text": clean_text[:300]})
            continue

        # 1. Find Atomic Sentence
        start, end = find_sentence_boundaries_v4(text, idx)
        
        # 2. Extract Raw Span
        raw_span = text[start:end]
        
        # 3. Clean tags but PRESERVE content/formatting
        # We remove [CITATION_X] so the training data is just text.
        # But we DO NOT squash spaces or remove punctuation.
        span_text = re.sub(r"\[CITATION_\d+\]", "", raw_span)
        
        # 4. Minimal trim
        span_text = clean_span_text_preservative(span_text)
        
        # Safety net: if empty, expand context
        if not span_text:
             span_text = text[max(0, idx-50):min(len(text), idx+50)]

        spans.append({"citation_id": m, "span_text": span_text})

    return spans


def call_gemini(
    api_key: str,
    prompt: str,
    retries: int = 3,
    backoff: float = 0.2,
    max_backoff: float = 2.0,
) -> Optional[List[Dict]]:
    url = GEMINI_ENDPOINT.format(model=MODEL)
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 1024}, # Increased token limit
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                url,
                params={"key": api_key},
                headers=headers,
                json=payload,
                timeout=120,
            )
        except Exception as e:
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            continue

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates: return None

            try:
                text_out = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
            except Exception: continue

            parsed = extract_json_from_text(text_out)
            if parsed: return parsed
        elif resp.status_code == 429:
            return None # Fallback on rate limit
        else:
            time.sleep(backoff)
            
    return None


def normalize_and_merge_spans(spans: List[Dict], markers: List[str], text: str) -> List[Dict]:
    """
    Merge Gemini output with Fallback V4 for robustness.
    """
    markers_set = set(markers)
    span_by_id: Dict[str, Dict] = {}

    for span in spans:
        cid = span.get("citation_id")
        raw_text = span.get("span_text", "")
        if cid in markers_set and raw_text and cid not in span_by_id:
            span_by_id[cid] = {"citation_id": cid, "span_text": clean_span_text_preservative(raw_text)}

    # Fill missing with V4 Fallback
    missing = [m for m in markers if m not in span_by_id]
    if missing:
        print(f"  Filling {len(missing)} missing spans via Fallback V4")
        fb_spans = fallback_spans_v4(text, missing)
        for fb in fb_spans:
            cid = fb["citation_id"]
            span_by_id[cid] = fb

    return [span_by_id[m] for m in markers if m in span_by_id]


def process_file(api_key: str, label_path: Path, out_dir: Path, force_reprocess: bool = False) -> str:
    data = load_json(label_path)
    doc_id = label_path.stem
    text = data.get("text", "")
    correct_citation = data.get("correct_citation", {})
    markers = list(correct_citation.keys())
    
    # Write .in file
    save_json(out_dir / f"{doc_id}.in", data)
    label_out = out_dir / f"{doc_id}.label"

    if label_out.exists() and not force_reprocess:
        # Check if existing file has empty spans
        existing = load_json(label_out)
        if not any(not s.get("span_text", "").strip() for s in existing.get("citation_spans", [])):
            return "skipped"

    # Try Gemini first, then Fallback V4
    prompt = build_prompt(text, markers)
    spans_from_model = call_gemini(api_key, prompt)

    if spans_from_model:
        spans = normalize_and_merge_spans(spans_from_model, markers, text)
        generator = "gemini_w_fallback_v4"
    else:
        print(f"  Using Fallback V4 for {doc_id}")
        spans = fallback_spans_v4(text, markers)
        generator = "fallback_v4"

    record = {
        "doc_id": doc_id,
        "text": text,
        "correct_citation": correct_citation,
        "citation_spans": spans,
        "bib_entries": data.get("bib_entries", {}),
        "generator": generator,
    }
    save_json(label_out, record)
    return "processed"


def main():
    base = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Generate Task3 V4 labels (Sentence-Level Gold Standard).")
    parser.add_argument("--task2-dir", type=Path, default=base / "data_outputs" / "task2")
    parser.add_argument("--output-dir", type=Path, default=base / "data_outputs" / "task3_v4")
    parser.add_argument("--limit", type=int, default=-1)
    parser.add_argument("--force-reprocess", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", DEFAULT_API_KEY)
    if not api_key: raise SystemExit("Missing API key.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    files = sorted(list(args.task2_dir.glob("*.label")), key=lambda p: int(p.stem) if p.stem.isdigit() else p.stem)
    if args.limit > 0: files = files[:args.limit]

    print(f"Processing {len(files)} files -> {args.output_dir}")
    print("VERSION: V4 (Sentence-Level Gold Standard)")
    
    stats = {"skipped": 0, "processed": 0, "error": 0}
    for i, path in enumerate(files, 1):
        try:
            status = process_file(api_key, path, args.output_dir, args.force_reprocess)
            stats[status] += 1
            if i % 50 == 0: print(f"[{i}/{len(files)}] Stats: {stats}")
        except Exception as e:
            stats["error"] += 1
            print(f"Error {path.name}: {e}")

    print(f"\nDone. {stats}")

if __name__ == "__main__":
    main()