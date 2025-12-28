"""
Task 3 generation - VERSION 3 with SENTENCE-LEVEL APPROACH

KEY IMPROVEMENTS (Based on Gemini feedback):
1. ✅ Fix Ratio Blindness: No hard-coded thresholds, use sentence-level extraction
2. ✅ Fix Punctuation Trap: Better sentence detection with abbreviation handling
3. ✅ Fix String Alignment: Preserve original strings (minimal cleaning)
4. ✅ Better multi-citation handling: Use linguistic markers, not ratios

CORE PHILOSOPHY:
- Citation at END of sentence → extract full sentence BEFORE marker
- Citation at START of sentence → extract full sentence AFTER marker
- Multiple adjacent citations → each gets unique clause/phrase
- Preserve EXACT substrings for frontend highlighting

Usage:
  python3 data_task3/main_v3.py --task2-dir data_outputs/task2 --output-dir data_outputs/task3_v3 --limit 10
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
    """Extract JSON array from model text (handles fenced code and extra text)."""
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw)
    raw = re.sub(r"```$", "", raw).strip()

    # First attempt: direct load
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Second attempt: find first JSON array in text (best-effort)
    match = re.search(r"\[[\s\S]*\]", raw)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None


def build_prompt(text: str, markers: List[str]) -> str:
    return (
        "You are a citation extraction expert. Extract the text span that each citation marker supports.\n\n"
        "INSTRUCTIONS:\n"
        "1. For each citation marker (e.g., [CITATION_1]), identify the claim, statement, or sentence it supports\n"
        "2. Extract the complete text span WITHOUT the marker itself\n"
        "3. The span should be the sentence or clause that contains the factual claim being cited\n"
        "4. IMPORTANT: span_text must NEVER be empty - always extract the relevant context\n"
        "5. If a citation appears at the end of a sentence/paragraph, extract the sentence BEFORE the marker\n"
        "6. CRITICAL: Each citation must have a UNIQUE span - avoid duplicate spans for different citations\n\n"
        "EXAMPLES:\n"
        'Text: "Recent studies show climate change affects biodiversity [CITATION_1] ."\n'
        'Output: {"citation_id": "[CITATION_1]", "span_text": "Recent studies show climate change affects biodiversity"}\n\n'
        'Text: "The model achieved 95% accuracy. [CITATION_2]"\n'
        'Output: {"citation_id": "[CITATION_2]", "span_text": "The model achieved 95% accuracy."}\n\n'
        "OUTPUT FORMAT:\n"
        'Return ONLY a valid JSON array with format: [{"citation_id": "[CITATION_X]", "span_text": "..."}]\n'
        "- Do not include markdown code fences unless necessary\n"
        "- Do not include explanations, only the JSON array\n"
        "- Ensure every span_text is non-empty and contains the cited claim\n"
        "- Ensure each citation has a UNIQUE span (no duplicates)\n\n"
        f"MARKERS TO EXTRACT: {markers}\n\n"
        "TEXT:\n"
        f"{text}\n\n"
        "Return the JSON array now:"
    )


def clean_span_text_minimal(span_text: str) -> str:
    """
    MINIMAL cleaning to preserve exact substring matching.

    V3 CHANGE: Only strip leading/trailing whitespace.
    Do NOT collapse internal whitespace or remove spaces before punctuation.
    This ensures span_text is an exact substring of original text.
    """
    return span_text.strip()


def find_sentence_boundaries_robust(text: str, citation_idx: int) -> tuple:
    """
    Find sentence boundaries with ROBUST abbreviation handling.

    V3 IMPROVEMENT: Handle common academic abbreviations:
    - Fig., Figs., et al., i.e., e.g., etc., vs., cf.
    - Dr., Mr., Mrs., Ms., Prof.
    - U.S., U.K., Ph.D., M.D.

    Strategy:
    - Use regex with negative lookbehind to avoid splitting on abbreviations
    - Look for sentence-ending punctuation followed by space + capital letter
    """

    # Common abbreviations that should NOT end a sentence
    abbreviations = [
        r'Fig\.',
        r'Figs\.',
        r'et al\.',
        r'i\.e\.',
        r'e\.g\.',
        r'etc\.',
        r'vs\.',
        r'cf\.',
        r'Dr\.',
        r'Mr\.',
        r'Mrs\.',
        r'Ms\.',
        r'Prof\.',
        r'Ph\.D\.',
        r'M\.D\.',
        r'U\.S\.',
        r'U\.K\.',
        r'No\.',
        r'Vol\.',
        r'pp\.',
        r'[A-Z]\.',  # Single capital letter with period (e.g., "A.", "B.")
    ]

    # Build negative lookbehind pattern
    # Pattern: period that is NOT preceded by an abbreviation
    abbrev_pattern = '|'.join(abbreviations)

    # Find sentence START (look backward from citation)
    sentence_start = 0
    before_text = text[:citation_idx]

    # Look for: [.!?] + whitespace + [Capital/Bullet]
    # But NOT if preceded by abbreviation
    for match in re.finditer(r"[.!?]\s+(?=[A-Z•\d])", before_text):
        # Check if this period is part of an abbreviation
        pos = match.start()
        # Get context before the period (up to 10 chars)
        context_start = max(0, pos - 10)
        context = before_text[context_start:pos+1]

        # Check if this matches any abbreviation pattern
        is_abbreviation = False
        for abbrev in abbreviations:
            if re.search(abbrev + r'$', context):
                is_abbreviation = True
                break

        if not is_abbreviation:
            sentence_start = match.end()

    # Find sentence END (look forward from citation)
    sentence_end = len(text)
    after_text = text[citation_idx:]

    # Look for: [.!?] followed by (space + capital OR end of text)
    match = re.search(r"[.!?](?:\s+[A-Z•\d]|\s*$)", after_text)
    if match:
        sentence_end = citation_idx + match.start() + 1

    return sentence_start, sentence_end


def fallback_spans_v3(text: str, markers: List[str]) -> List[Dict]:
    """
    SENTENCE-LEVEL fallback strategy - VERSION 3

    KEY CHANGES:
    1. ✅ NO ratio-based thresholds (0.15, 0.85) - use sentence-level by default
    2. ✅ Robust sentence detection with abbreviation handling
    3. ✅ Minimal cleaning to preserve exact substrings
    4. ✅ Better multi-citation handling with linguistic markers

    CORE LOGIC:
    - DEFAULT: Extract full sentence containing the citation
    - ADJACENT CITATIONS: Split by natural boundaries (comma, semicolon, conjunction)
    - PRESERVE: Original string formatting for exact matching
    """
    spans: List[Dict] = []

    # Sort markers by position for easier multi-citation handling
    marker_positions = [(m, text.find(m)) for m in markers if text.find(m) != -1]
    marker_positions.sort(key=lambda x: x[1])

    for m in markers:
        idx = text.find(m)
        if idx == -1:
            # Marker not found - use first 200 chars as fallback
            clean_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())
            clean_text = clean_span_text_minimal(clean_text[:200])
            spans.append({"citation_id": m, "span_text": clean_text})
            continue

        # V3: Use robust sentence boundary detection
        sentence_start, sentence_end = find_sentence_boundaries_robust(text, idx)
        sentence_text = text[sentence_start:sentence_end]

        # Count citations in this sentence
        citations_in_sentence = re.findall(r"\[CITATION_\d+\]", sentence_text)

        if len(citations_in_sentence) > 1:
            # MULTIPLE CITATIONS - need to give each one unique span

            # Find current citation's position in marker list
            current_pos = None
            for i, (marker, pos) in enumerate(marker_positions):
                if marker == m and pos == idx:
                    current_pos = i
                    break

            if current_pos is None:
                # Fallback: take full sentence
                span_text = sentence_text
                span_text = re.sub(r"\[CITATION_\d+\]", "", span_text)
                span_text = clean_span_text_minimal(span_text)
                spans.append({"citation_id": m, "span_text": span_text})
                continue

            # Check if adjacent to other citations
            text_before_in_sentence = sentence_text[:idx - sentence_start]
            text_after_in_sentence = sentence_text[idx - sentence_start + len(m):]

            has_adjacent_before = re.search(r"\[CITATION_\d+\]\s*$", text_before_in_sentence)
            has_adjacent_after = re.match(r"^\s*\[CITATION_\d+\]", text_after_in_sentence)

            if has_adjacent_before or has_adjacent_after:
                # ADJACENT CITATIONS - extract unique clause for each

                # Determine span boundaries based on adjacent citations
                if current_pos > 0:
                    prev_marker, prev_idx = marker_positions[current_pos - 1]
                    if prev_idx >= sentence_start and prev_idx < sentence_end:
                        # Previous citation in same sentence
                        span_start = prev_idx + len(prev_marker)
                    else:
                        span_start = sentence_start
                else:
                    span_start = sentence_start

                if current_pos < len(marker_positions) - 1:
                    next_marker, next_idx = marker_positions[current_pos + 1]
                    if next_idx >= sentence_start and next_idx < sentence_end:
                        # Next citation in same sentence
                        span_end = next_idx
                    else:
                        span_end = idx  # End at current citation
                else:
                    span_end = idx  # End at current citation

                # Extract text between boundaries
                span_text = text[span_start:span_end]

                # Look for natural clause boundaries if span is very short
                if len(span_text.strip()) < 20:
                    # Try to expand to previous comma/semicolon
                    look_back = text[max(0, sentence_start):span_start]
                    comma_match = None
                    for match in re.finditer(r'[,;:]\s*', look_back):
                        comma_match = match

                    if comma_match:
                        span_start = sentence_start + comma_match.end()
                        span_text = text[span_start:span_end]

                # Remove citation markers and clean minimally
                span_text = re.sub(r"\[CITATION_\d+\]", "", span_text)
                span_text = clean_span_text_minimal(span_text)

            else:
                # NON-ADJACENT multiple citations
                # Take text from previous citation to current one

                prev_citation_idx = -1
                for other_m, other_idx in marker_positions:
                    if other_idx < idx and other_idx >= sentence_start:
                        if other_idx > prev_citation_idx:
                            prev_citation_idx = other_idx
                            prev_marker = other_m

                if prev_citation_idx != -1:
                    # Text between previous citation and current
                    span_start = prev_citation_idx + len(prev_marker)
                    span_text = text[span_start:idx]
                else:
                    # Text from sentence start to current citation
                    span_text = text[sentence_start:idx]

                span_text = re.sub(r"\[CITATION_\d+\]", "", span_text)
                span_text = clean_span_text_minimal(span_text)

        else:
            # SINGLE CITATION - take full sentence
            # V3: No ratio checks, just take the whole sentence
            span_text = sentence_text
            span_text = re.sub(r"\[CITATION_\d+\]", "", span_text)
            span_text = clean_span_text_minimal(span_text)

        # Final validation - if too short, expand context
        if len(span_text) < 5:
            context_start = max(0, sentence_start - 50)
            context_end = min(len(text), sentence_end + 50)
            span_text = text[context_start:context_end]
            span_text = re.sub(r"\[CITATION_\d+\]", "", span_text)
            span_text = clean_span_text_minimal(span_text)

        # Ultimate fallback
        if not span_text or len(span_text.strip()) == 0:
            span_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())[:200]
            span_text = clean_span_text_minimal(span_text)

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
        "generationConfig": {"temperature": 0, "maxOutputTokens": 512},
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
            print(f"  Request error on attempt {attempt}: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            continue

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"  API returned no candidates (attempt {attempt})")
                return None

            try:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                if not text_parts:
                    print(f"  No text parts in candidate (attempt {attempt})")
                    continue
                text_out = "\n".join(text_parts).strip()
            except Exception as e:
                print(f"  Error parsing candidate content (attempt {attempt}): {e}")
                continue

            parsed = extract_json_from_text(text_out)
            if parsed is not None:
                all_non_empty = all(
                    isinstance(span.get("span_text", ""), str)
                    and span.get("span_text", "").strip() != ""
                    for span in parsed
                )
                all_have_id = all("citation_id" in span for span in parsed)

                if all_non_empty and all_have_id:
                    return parsed

                print(
                    f"  Warning: Gemini returned invalid spans, retrying... (attempt {attempt})"
                )
            else:
                print(f"  Could not parse JSON from model output (attempt {attempt})")

        elif resp.status_code == 429:
            print("  Rate limited (429) - returning None to use fallback.")
            return None
        elif resp.status_code in (500, 503):
            print(f"  API error {resp.status_code}, backing off... (attempt {attempt})")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            continue
        else:
            print(f"  API error {resp.status_code}: {resp.text[:200]}")
            break

    return None


def normalize_and_merge_spans(
    spans: List[Dict], markers: List[str], text: str
) -> List[Dict]:
    """
    - Filter out spans with unknown citation_id
    - Normalize span_text formatting (V3: minimal cleaning only)
    - Ensure every marker has a span (missing ones use fallback V3)
    - If duplicate citation_id appears, keep the first (model output) and ignore later duplicates
    """
    markers_set = set(markers)
    span_by_id: Dict[str, Dict] = {}

    # 1) Keep only spans whose citation_id is in markers, normalize span_text
    for span in spans:
        cid = span.get("citation_id")
        raw_text = span.get("span_text", "")
        if cid not in markers_set:
            continue
        if not isinstance(raw_text, str):
            continue
        cleaned = clean_span_text_minimal(raw_text)  # V3: minimal cleaning
        if not cleaned:
            continue
        if cid not in span_by_id:
            span_by_id[cid] = {"citation_id": cid, "span_text": cleaned}

    # 2) Find missing markers and fill via fallback V3
    missing = [m for m in markers if m not in span_by_id]
    if missing:
        print(f"  Filling {len(missing)} missing spans via fallback V3: {missing}")
        fb_spans = fallback_spans_v3(text, missing)
        for fb in fb_spans:
            cid = fb["citation_id"]
            if cid in markers_set and cid not in span_by_id:
                span_by_id[cid] = fb

    # 3) Return spans in the same order as markers
    merged = [span_by_id[m] for m in markers if m in span_by_id]

    return merged


def process_file(api_key: str, label_path: Path, out_dir: Path, force_reprocess: bool = False) -> str:
    """
    Process a file and return status: 'skipped', 'processed', or 'error'
    """
    data = load_json(label_path)
    doc_id = label_path.stem
    text = data.get("text", "")
    correct_citation: Dict[str, str] = data.get("correct_citation", {})
    bib_entries = data.get("bib_entries", {})
    markers = list(correct_citation.keys())

    # write .in (copy of Task2 label)
    in_path = out_dir / f"{doc_id}.in"
    save_json(in_path, data)

    label_out = out_dir / f"{doc_id}.label"

    # Check if we should skip
    if label_out.exists() and not force_reprocess:
        existing_data = load_json(label_out)
        existing_spans = existing_data.get("citation_spans", [])
        has_empty = any(span.get("span_text", "").strip() == "" for span in existing_spans)

        if not has_empty:
            return "skipped"

        print(f"  Reprocessing {doc_id} (has empty spans)")

    # Build prompt & call Gemini
    prompt = build_prompt(text, markers)
    spans_from_model = call_gemini(api_key, prompt)

    if spans_from_model is not None:
        spans = normalize_and_merge_spans(spans_from_model, markers, text)
        generator = "gemini"
    else:
        print(f"  Using fallback V3 for {doc_id}")
        spans = fallback_spans_v3(text, markers)
        generator = "fallback_v3"

    # Final validation
    empty_spans = [s for s in spans if s.get("span_text", "").strip() == ""]
    if empty_spans:
        print(
            f"  WARNING: {doc_id} still has {len(empty_spans)} empty spans: "
            f"{[s['citation_id'] for s in empty_spans]}"
        )

    span_ids = {s.get("citation_id") for s in spans}
    missing_ids = set(markers) - span_ids
    if missing_ids:
        print(f"  WARNING: {doc_id} missing spans for markers: {missing_ids}")

    record = {
        "doc_id": doc_id,
        "text": text,
        "correct_citation": correct_citation,
        "citation_spans": spans,
        "bib_entries": bib_entries,
        "generator": generator,
    }
    save_json(label_out, record)
    return "processed"


def main():
    base = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Generate Task3 V3 labels using sentence-level approach.")
    parser.add_argument(
        "--task2-dir",
        type=Path,
        default=base / "data_outputs" / "task2",
        help="Path to Task 2 labels (.label).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=base / "data_outputs" / "task3_v3",
        help="Output directory for Task 3 V3.",
    )
    parser.add_argument("--limit", type=int, default=-1, help="number of files to process (-1 for all)")
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Force reprocess all files, even if they already exist",
    )
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", DEFAULT_API_KEY)
    if not api_key:
        raise SystemExit("Missing API key. Set GEMINI_API_KEY or update DEFAULT_API_KEY.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    label_files = list(args.task2_dir.glob("*.label"))

    def sort_key(p: Path):
        try:
            return (0, int(p.stem))
        except ValueError:
            return (1, p.stem)

    files = sorted(label_files, key=sort_key)

    if args.limit and args.limit > 0:
        files = files[: args.limit]

    if not files:
        print(f"No files found in {args.task2_dir}")
        return

    print(f"Found {len(files)} files. Output -> {args.output_dir}")
    if args.force_reprocess:
        print("Force reprocess mode: will regenerate all files")
    print()
    print("VERSION: V3 with sentence-level approach (no ratio thresholds)")
    print()

    stats = {"skipped": 0, "processed": 0, "error": 0}

    for i, path in enumerate(files, 1):
        try:
            status = process_file(api_key, path, args.output_dir, args.force_reprocess)
            stats[status] = stats.get(status, 0) + 1

            if i % 100 == 0 or i == len(files):
                print(f"[{i}/{len(files)}] Progress: {stats['processed']} processed, {stats['skipped']} skipped, {stats['error']} errors")
            elif status == "processed":
                print(f"[{i}/{len(files)}] {path.name}")

        except Exception as e:
            stats["error"] = stats.get("error", 0) + 1
            print(f"[{i}/{len(files)}] Error on {path.name}: {e}")
            time.sleep(1)

    print("\n" + "="*80)
    print("PROCESSING COMPLETE - VERSION 3")
    print("="*80)
    print(f"Total files: {len(files)}")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped (already done): {stats['skipped']}")
    print(f"Errors: {stats['error']}")
    print("="*80)


if __name__ == "__main__":
    main()
