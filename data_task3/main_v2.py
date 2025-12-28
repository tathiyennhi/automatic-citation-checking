"""
Task 3 generation - VERSION 2 with IMPROVED LOGIC

KEY IMPROVEMENTS:
1. Fix duplicate spans for adjacent citations
2. Better clause detection for multiple citations
3. Unique span for each citation

Usage:
  python3 data_task3/main_v2.py --task2-dir data_outputs/task2 --output-dir data_outputs/task3_v2 --limit 100
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


def clean_span_text(span_text: str) -> str:
    """
    Normalize whitespace and punctuation spacing in span_text.
    This avoids artifacts like 'normal  .' or 'questioned       ).'.
    """
    # Collapse all whitespace sequences to single space
    span_text = re.sub(r"\s+", " ", span_text)
    # Remove space before punctuation
    span_text = re.sub(r"\s+([.,!?;:])", r"\1", span_text)
    # Fix double periods (e.g., "Ref.." -> "Ref.")
    span_text = re.sub(r"\.\.+", ".", span_text)
    return span_text.strip()


def find_clause_boundaries(text: str, start: int, end: int) -> tuple:
    """
    Find natural clause boundaries (comma, semicolon, conjunction).
    Used for splitting multiple citations in same sentence.
    """
    # Look backward for clause start
    clause_start = start
    for i in range(start - 1, max(0, start - 100), -1):
        if text[i] in '.,;:':
            clause_start = i + 1
            break
        # Also break at conjunctions
        if i > 2 and text[i-4:i] in [' and', ' or ', 'but ']:
            clause_start = i
            break

    # Look forward for clause end
    clause_end = end
    for i in range(end, min(len(text), end + 100)):
        if text[i] in '.,;:':
            clause_end = i
            break

    return clause_start, clause_end


def fallback_spans_v2(text: str, markers: List[str]) -> List[Dict]:
    """
    IMPROVED fallback strategy - VERSION 2

    KEY CHANGES:
    1. Fix duplicate spans for adjacent citations
    2. Better handling of multiple citations in same sentence
    3. Each citation gets unique context

    Strategy:
    - Citation at sentence START → take full sentence
    - Citation at sentence END → take text before it
    - Multiple ADJACENT citations → extract specific clause for each
    - Multiple NON-ADJACENT citations → take text between citations
    """
    spans: List[Dict] = []

    # Sort markers by their position for easier handling
    marker_positions = [(m, text.find(m)) for m in markers if text.find(m) != -1]
    marker_positions.sort(key=lambda x: x[1])

    for m in markers:
        idx = text.find(m)
        if idx == -1:
            # Marker not found - use first 200 chars as fallback
            clean_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())
            clean_text = clean_span_text(clean_text[:200])
            spans.append({"citation_id": m, "span_text": clean_text})
            continue

        # Find sentence boundaries
        sentence_start = 0
        before_text = text[:idx]
        for match in re.finditer(r"[.!?]\s+(?=[A-Z•])", before_text):
            sentence_start = match.end()

        sentence_end = len(text)
        after_text = text[idx + len(m):]
        match = re.search(r"[.!?](?:\s+[A-Z•]|\s*$)", after_text)
        if match:
            sentence_end = idx + len(m) + match.start() + 1

        # Get sentence and check for multiple citations
        sentence_text = text[sentence_start:sentence_end]
        citations_in_sentence = re.findall(r"\[CITATION_\d+\]", sentence_text)

        # NEW LOGIC: Better handling of multiple citations
        if len(citations_in_sentence) > 1:
            # Multiple citations in sentence

            # Check if current citation is adjacent to others
            text_before_marker = text[sentence_start:idx]
            text_after_marker = text[idx + len(m):sentence_end]

            has_adjacent_before = re.search(r"\[CITATION_\d+\]\s*$", text_before_marker)
            has_adjacent_after = re.match(r"^\s*\[CITATION_\d+\]", text_after_marker)

            if has_adjacent_before or has_adjacent_after:
                # ADJACENT CITATIONS - extract clause/phrase specific to this citation
                # This is the FIX for duplicate issue!

                # Find the current citation's position in the list
                current_pos = None
                for i, (marker, pos) in enumerate(marker_positions):
                    if marker == m and pos == idx:
                        current_pos = i
                        break

                if current_pos is not None:
                    # Determine span boundaries based on adjacent citations
                    if current_pos > 0:
                        # Has previous citation
                        prev_marker, prev_idx = marker_positions[current_pos - 1]
                        if prev_idx >= sentence_start:  # In same sentence
                            span_start = prev_idx + len(prev_marker)
                        else:
                            span_start = sentence_start
                    else:
                        span_start = sentence_start

                    if current_pos < len(marker_positions) - 1:
                        # Has next citation
                        next_marker, next_idx = marker_positions[current_pos + 1]
                        if next_idx < sentence_end:  # In same sentence
                            span_end = next_idx
                        else:
                            span_end = sentence_end
                    else:
                        span_end = sentence_end

                    # Extract span
                    span_text = text[span_start:idx].strip()

                    # If too short, try to expand to clause boundaries
                    if len(span_text) < 20:
                        clause_start, clause_end = find_clause_boundaries(text, span_start, idx)
                        span_text = text[clause_start:clause_end].strip()

                    # Clean
                    span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
                    span_text = clean_span_text(span_text)

                else:
                    # Fallback: take full sentence
                    span_text = sentence_text
                    span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
                    span_text = clean_span_text(span_text)

            else:
                # NON-ADJACENT multiple citations
                # Take text before current marker, after previous marker

                prev_citation_idx = -1
                for other_m, other_idx in marker_positions:
                    if other_idx < idx and other_idx >= sentence_start:
                        prev_citation_idx = other_idx

                if prev_citation_idx != -1:
                    prev_marker = [m2 for m2, pos in marker_positions if pos == prev_citation_idx][0]
                    span_start = prev_citation_idx + len(prev_marker)
                    span_text = text[span_start:idx].strip()
                    span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
                    span_text = clean_span_text(span_text)
                else:
                    span_text = text[sentence_start:idx].strip()
                    span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
                    span_text = clean_span_text(span_text)

        else:
            # Single citation in sentence - use position-based logic
            text_before_marker = text[sentence_start:idx]
            text_before_clean = re.sub(r"\[CITATION_\d+\]", "", text_before_marker).strip()

            sentence_clean = re.sub(r"\[CITATION_\d+\]", "", sentence_text).strip()
            sentence_length = len(sentence_clean)

            if sentence_length > 0:
                position_ratio = len(text_before_clean) / sentence_length
            else:
                position_ratio = 0.5

            if position_ratio < 0.15:
                # Citation at START → full sentence
                span_text = sentence_text
                span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
            elif position_ratio > 0.85:
                # Citation at END → text before it
                span_text = text[sentence_start:idx].strip()
                span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
            else:
                # Citation in MIDDLE → full sentence
                span_text = sentence_text
                span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()

            span_text = clean_span_text(span_text)

        # Fallback for too short spans
        if len(span_text) < 5:
            context_start = max(0, sentence_start - 50)
            context_end = min(len(text), sentence_end + 50)
            span_text = text[context_start:context_end].strip()
            span_text = re.sub(r"\[CITATION_\d+\]", "", span_text).strip()
            span_text = clean_span_text(span_text)

        # Final validation
        if not span_text:
            span_text = re.sub(r"\[CITATION_\d+\]", "", text.strip())[:200]
            span_text = clean_span_text(span_text)

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
    - Normalize span_text formatting
    - Ensure every marker has a span (missing ones use fallback)
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
        cleaned = clean_span_text(raw_text)
        if not cleaned:
            continue
        if cid not in span_by_id:
            span_by_id[cid] = {"citation_id": cid, "span_text": cleaned}

    # 2) Find missing markers and fill via fallback V2
    missing = [m for m in markers if m not in span_by_id]
    if missing:
        print(f"  Filling {len(missing)} missing spans via fallback V2: {missing}")
        fb_spans = fallback_spans_v2(text, missing)
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
        print(f"  Using fallback V2 for {doc_id}")
        spans = fallback_spans_v2(text, markers)
        generator = "fallback_v2"

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
    parser = argparse.ArgumentParser(description="Generate Task3 V2 labels using improved logic.")
    parser.add_argument(
        "--task2-dir",
        type=Path,
        default=base / "data_outputs" / "task2",
        help="Path to Task 2 labels (.label).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=base / "data_outputs" / "task3_v2",
        help="Output directory for Task 3 V2.",
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
    print("VERSION: V2 with improved duplicate-free logic")
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
    print("PROCESSING COMPLETE - VERSION 2")
    print("="*80)
    print(f"Total files: {len(files)}")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped (already done): {stats['skipped']}")
    print(f"Errors: {stats['error']}")
    print("="*80)


if __name__ == "__main__":
    main()
