import json
import re
from collections import Counter
from typing import Dict, List, Tuple

_CITATION_RE = re.compile(r"\[CITATION_(\d+)\]")


def _sort_marker_key(marker: str) -> Tuple[int, object]:
    m = _CITATION_RE.match(marker or "")
    if not m:
        return (1, marker)
    return (0, int(m.group(1)))


def normalize_spans(model_spans) -> List[Dict[str, str]]:
    if not isinstance(model_spans, list):
        return []
    norm = []
    for s in model_spans:
        if not isinstance(s, dict):
            continue
        cid = s.get("citation_id")
        st = s.get("span_text")
        if not isinstance(cid, str) or not isinstance(st, str):
            continue
        if not cid.strip() or not st.strip():
            continue
        norm.append({"citation_id": cid, "span_text": st})
    return norm


def validate_spans(text: str, markers: List[str], spans) -> List[str]:
    """
    Hard constraints:
    - For each citation_id in markers, there must be exactly one (first kept) span entry.
    - span_text MUST contain its citation_id tag.
    - span_text MUST be an exact substring of text.
    - No extra/unknown citation_id entries.

    Returns list of error strings (empty = valid).
    """
    errors: List[str] = []
    if not isinstance(text, str) or not text:
        return ["missing_or_empty_text"]

    markers_sorted = sorted(list(markers or []), key=_sort_marker_key)
    normalized = normalize_spans(spans)

    by_id = {}
    seen_ids = []
    for s in normalized:
        cid = s["citation_id"]
        st = s["span_text"]
        seen_ids.append(cid)
        if cid not in by_id:
            by_id[cid] = st

    missing = [cid for cid in markers_sorted if cid not in by_id]
    if missing:
        errors.append(f"missing_markers:{missing}")

    for cid in markers_sorted:
        if cid not in by_id:
            continue
        st = by_id[cid]
        if cid not in st:
            errors.append(f"{cid}:span_missing_tag")
        if text.find(st) == -1:
            errors.append(f"{cid}:span_not_substring")

    extras = sorted([cid for cid in by_id.keys() if cid not in set(markers_sorted)], key=_sort_marker_key)
    if extras:
        errors.append(f"extra_markers:{extras}")

    dup = [cid for cid, c in Counter(seen_ids).items() if c > 1]
    if dup:
        # not fatal, but indicates sloppy output; treat as error to keep dataset clean
        errors.append(f"duplicate_citation_ids:{sorted(dup, key=_sort_marker_key)}")

    return errors


def resume_safe_has_valid_label(existing_label_path) -> bool:
    try:
        if not existing_label_path.exists() or existing_label_path.stat().st_size <= 0:
            return False
        _ = json.loads(existing_label_path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False

