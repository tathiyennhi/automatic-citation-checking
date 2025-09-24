# app/services/citations_service.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional  
import re
import xml.etree.ElementTree as ET

# NLTK for robust sentence splitting
import nltk
from nltk.tokenize import sent_tokenize
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# style utils (optional)
try:
    from services.citation_style_service import detect_citation_style  # noqa: F401
except Exception:
    pass

# ============================= Namespaces ==============================

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
XML_NS = "{http://www.w3.org/XML/1998/namespace}"  # for xml:id  # CHANGED: remove bad XML_NS line

# ============================ XML helpers ==============================

def _parse_xml(tei: str) -> ET.Element:
    try:
        return ET.fromstring(tei)
    except Exception as e:
        raise ValueError(f"Invalid TEI XML: {e}")

def _text_of(el: ET.Element) -> str:
    """Render text of an element (text + descendants + tails)."""
    parts: List[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(_text_of(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)

def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

# ======================= Reference Processing =======================

def _build_biblio_title_map(root: ET.Element) -> Dict[str, str]:
    id2title: Dict[str, str] = {}
    for bibl in root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS):
        bid = bibl.get(f"{XML_NS}id")
        if not bid:
            continue
        t1 = bibl.find(".//tei:analytic/tei:title", TEI_NS)
        t2 = bibl.find(".//tei:monogr/tei:title", TEI_NS)
        if t1 is not None and _text_of(t1).strip():
            title = _norm_space(_text_of(t1))
        elif t2 is not None and _text_of(t2).strip():
            title = _norm_space(_text_of(t2))
        else:
            title = "(untitled reference)"
        id2title[bid] = title
    return id2title

# ======================= Paragraph selection =======================

def _get_citation_paragraphs(root: ET.Element) -> List[ET.Element]:
    seen: set[int] = set()
    out: List[ET.Element] = []
    for p in root.findall(".//tei:text/tei:front//tei:p", TEI_NS):
        pid = id(p)
        if pid not in seen:
            seen.add(pid); out.append(p)
    for p in root.findall(".//tei:text/tei:body//tei:p", TEI_NS):
        pid = id(p)
        if pid not in seen:
            seen.add(pid); out.append(p)
    return out

# ======================= Sentence splitting =======================

def _protect_abbrev(text: str) -> str:
    pairs = [
        (r"\bet al\.", "et al§"),
        (r"\be\.g\.", "e§g§"),
        (r"\bi\.e\.", "i§e§"),
        (r"\bcc\.", "c§c§"),
        (r"\bpp\.", "pp§"),
        (r"\bp\.", "p§"),
        (r"\bFig\.", "Fig§"),
        (r"\bEq\.", "Eq§"),
        (r"\bDr\.", "Dr§"),
        (r"\bProf\.", "Prof§"),
        (r"\bcf\.", "cf§"),
    ]
    out = text
    for pat, repl in pairs:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def _unprotect_abbrev(text: str) -> str:
    return text.replace("§", ".")

def _split_sentences_with_spans(paragraph_text: str) -> List[Dict[str, Any]]:
    protected = _protect_abbrev(paragraph_text)
    raw_sents = sent_tokenize(protected)

    sents: List[Dict[str, Any]] = []
    cursor = 0
    for s in raw_sents:
        s_restore = _unprotect_abbrev(s).strip()
        if not s_restore:
            continue
        m = re.search(re.escape(s_restore), paragraph_text[cursor:])
        if m:
            start = cursor + m.start(); end = cursor + m.end()
        else:
            pos = paragraph_text.find(s_restore, cursor)
            if pos == -1:
                pos = paragraph_text.find(s_restore)
            start = pos if pos != -1 else cursor
            end = start + len(s_restore)
        sents.append({"text": s_restore, "start": start, "end": end})
        cursor = end
    return sents

def _sentence_by_offset(paragraph_text: str, span_start: int, span_end: int) -> Tuple[str, int, int]:
    sents = _split_sentences_with_spans(paragraph_text)
    if not sents:
        t = _norm_space(paragraph_text)
        return t, 0, len(paragraph_text)
    for s in sents:
        if s["start"] <= span_start < s["end"]:
            return s["text"], s["start"], s["end"]
    nearest = min(sents, key=lambda x: abs(x["start"] - span_start))
    return nearest["text"], nearest["start"], nearest["end"]

# ==================== Index <ref> and group inside a sentence ===================

_ALLOWED_GAP_RE = re.compile(
    r"^\s*[,;:–—\-]*\s*(?:&(?!\w)|and)?\s*[,;:–—\-]*\s*$",
    re.IGNORECASE,
)

def _index_ref_spans_in_paragraph(p: ET.Element, para_text: str) -> List[Dict[str, Any]]:
    refs = p.findall(".//tei:ref[@type='bibr']", TEI_NS)
    out: List[Dict[str, Any]] = []
    cursor = 0
    for ref in refs:
        span = _norm_space(_text_of(ref))
        if not span:
            continue
        m = re.search(re.escape(span), para_text[cursor:])
        if m:
            start = cursor + m.start(); end = cursor + m.end(); cursor = end
        else:
            m2 = re.search(re.escape(span), para_text)
            if m2:
                start, end = m2.start(), m2.end(); cursor = max(cursor, end)
            else:
                start, end = cursor, cursor + len(span); cursor = end
        raw_target = ref.get("target", "")
        ids = [t.lstrip("#") for t in raw_target.split() if t.strip()]
        out.append({"span": span, "start": start, "end": end, "targets": ids})
    return out

def _group_runs_in_sentence(indexed: List[Dict[str, Any]],
                            para_text: str,
                            sent_start: int,
                            sent_end: int) -> List[Dict[str, Any]]:
    items = [it for it in indexed if it["start"] < sent_end and it["end"] > sent_start]
    items.sort(key=lambda x: x["start"])
    groups: List[Dict[str, Any]] = []
    if not items:
        return groups

    cur_items = [items[0]]
    cur_start = max(items[0]["start"], sent_start)
    cur_end = min(items[0]["end"], sent_end)

    for i in range(1, len(items)):
        prev = items[i - 1]; curr = items[i]
        if curr["start"] >= sent_end or prev["end"] <= sent_start:
            citation = _norm_space(para_text[cur_start:cur_end])
            groups.append({
                "start": cur_start, "end": cur_end,
                "items": [{"span": it["span"], "start": it["start"], "end": it["end"], "targets": it["targets"]}
                          for it in cur_items],
                "citation": citation
            })
            if curr["start"] < sent_end and curr["end"] > sent_start:
                cur_items = [curr]
                cur_start = max(curr["start"], sent_start)
                cur_end = min(curr["end"], sent_end)
            else:
                cur_items = []
            continue

        gap = para_text[prev["end"]:curr["start"]]
        if any(ch in gap for ch in [".", "!", "?", ")", "("]) or not _ALLOWED_GAP_RE.match(gap):
            citation = _norm_space(para_text[cur_start:cur_end])
            groups.append({
                "start": cur_start, "end": cur_end,
                "items": [{"span": it["span"], "start": it["start"], "end": it["end"], "targets": it["targets"]}
                          for it in cur_items],
                "citation": citation
            })
            cur_items = [curr]
            cur_start = max(curr["start"], sent_start)
            cur_end = min(curr["end"], sent_end)
        else:
            cur_items.append(curr)
            cur_end = min(curr["end"], sent_end)

    if cur_items:
        citation = _norm_space(para_text[cur_start:cur_end])
        groups.append({
            "start": cur_start, "end": cur_end,
            "items": [{"span": it["span"], "start": it["start"], "end": it["end"], "targets": it["targets"]}
                      for it in cur_items],
            "citation": citation
        })
    return groups

# --------------------- Enhance single-item display text ---------------------

_SINGLE_RIGHT_TAIL_RE = re.compile(
    r"""^\s*,\s*(?:p{1,2}\.)\s*\d+(?:\s*[–-]\s*\d+)?\s*\)?""",
    re.IGNORECASE | re.VERBOSE,
)

def _render_single_item_text_in_sentence(sentence_text: str,
                                         group_local: Dict[str, Any]) -> str:
    start = group_local["start"]; end = group_local["end"]
    left_char = sentence_text[start - 1] if start - 1 >= 0 else ""
    right_tail = sentence_text[end:end + 80]
    m = _SINGLE_RIGHT_TAIL_RE.match(right_tail)
    if left_char == "(" and m:
        return _norm_space("(" + sentence_text[start:end] + m.group(0))
    if m:
        return _norm_space(sentence_text[start:end] + m.group(0))
    if left_char == "(":
        after = sentence_text[end:end + 80]
        close = after.find(")")
        if close != -1:
            return _norm_space("(" + sentence_text[start:end] + after[:close + 1])
    return _norm_space(sentence_text[start:end])

# ===================== IEEE helpers (strict) =====================

# CHANGED: strict bracket pattern for IEEE; NO care for ()
_IEEE_BRACKET_RE = re.compile(r"^\s*\[(?P<body>[^\]]+)\]\s*$")

def _expand_numeric_tokens(body: str) -> List[int]:
    nums: List[int] = []
    tokens = re.split(r"\s*,\s*", body)  # supports: 3, 4-7, 8–10
    for t in tokens:
        t = t.strip()
        m_range = re.match(r"^(\d+)\s*[–-]\s*(\d+)$", t)
        if m_range:
            a, b = int(m_range.group(1)), int(m_range.group(2))
            lo, hi = (a, b) if a <= b else (b, a)
            nums.extend(range(lo, hi + 1))
            continue
        m_single = re.match(r"^\d+$", t)
        if m_single:
            nums.append(int(t))
    return nums

def _ieee_numbers_from_surfaces(surfaces: List[str]) -> List[int]:
    out: List[int] = []
    for s in surfaces:
        m = _IEEE_BRACKET_RE.match(s.strip())
        if not m:
            continue
        out.extend(_expand_numeric_tokens(m.group("body")))
    return sorted(set(out))

def _normalize_numeric_item_text(span: str) -> str:
    """Normalize EACH numeric item to [a, b, c] form (expand ranges)."""
    m = _IEEE_BRACKET_RE.match(span.strip())
    if not m:
        return span.strip()
    nums = _expand_numeric_tokens(m.group("body"))
    return f"[{', '.join(str(n) for n in nums)}]"

# ===================== Citation Processing =====================

def _render_citation_from_items(items: List[Dict[str, Any]],
                                force_style: Optional[str] = None
                                ) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Return (citation_text, style, filtered_items)
    - force_style='numeric'     : only [ ... ], render from numbers (list+range)
    - force_style='author_year' : only author–year
    - force_style=None          : auto-detect
    """
    surfaces = [it["span"].strip() for it in items]

    if force_style == "numeric":  # CHANGED
        nums = _ieee_numbers_from_surfaces(surfaces)
        filtered = [it for it in items if _IEEE_BRACKET_RE.match(it["span"].strip())]
        return f"[{', '.join(str(n) for n in nums)}]" if nums else "[]", "numeric", filtered

    if force_style == "author_year":  # CHANGED
        ay_pat = re.compile(r"^\([A-Z][A-Za-z\-\s]+,\s*\d{4}[a-z]?\)$|^[A-Z][A-Za-z\-\s]+ \(\d{4}[a-z]?\)$")
        filtered = [it for it in items if ay_pat.match(it["span"].strip())]
        return "; ".join(it["span"].strip() for it in filtered), "author_year", filtered

    # Auto-detect
    nums = _ieee_numbers_from_surfaces(surfaces)
    if nums:
        filtered = [it for it in items if _IEEE_BRACKET_RE.match(it["span"].strip())]
        return f"[{', '.join(str(n) for n in nums)}]", "numeric", filtered

    ay_pat = re.compile(r"^\([A-Z][A-Za-z\-\s]+,\s*\d{4}[a-z]?\)$|^[A-Z][A-Za-z\-\s]+ \(\d{4}[a-z]?\)$")
    ay_items = [s for s in surfaces if ay_pat.match(s)]
    if ay_items:
        filtered = [it for it in items if ay_pat.match(it["span"].strip())]
        return "; ".join(ay_items), "author_year", filtered

    return "; ".join(surfaces), "unknown", items

# ============================== Public APIs ==============================

def count_intext_citations_from_tei(tei: str) -> Dict[str, Any]:
    root = _parse_xml(tei)
    total = 0
    for p in _get_citation_paragraphs(root):
        para_text = _norm_space(_text_of(p))
        if not para_text:
            continue
        indexed = _index_ref_spans_in_paragraph(p, para_text)
        if not indexed:
            continue
        sent_spans = _split_sentences_with_spans(para_text)
        for s in sent_spans:
            groups = _group_runs_in_sentence(indexed, para_text, s["start"], s["end"])
            total += len(groups)
    return {"total": total}

def extract_intext_citations_task1b(
    tei: str,
    drop_unlinked: bool = True,
    force_style: Optional[str] = None  # CHANGED
) -> Dict[str, Any]:
    """
    Return grouped citations by sentence with items filtered by style.
    - numeric: only [], author_year: only author–year, unknown: keep all.
    - force_style: allow FE to enforce (e.g., IEEE).
    """
    root = _parse_xml(tei)
    id2title = _build_biblio_title_map(root)
    out: List[Dict[str, Any]] = []
    counter = 1

    for p in _get_citation_paragraphs(root):
        para_text = _norm_space(_text_of(p))
        if not para_text:
            continue

        indexed = _index_ref_spans_in_paragraph(p, para_text)
        if not indexed:
            continue

        sent_spans = _split_sentences_with_spans(para_text)
        if not sent_spans:
            continue

        for s in sent_spans:
            claim = s["text"]
            sent_start, sent_end = s["start"], s["end"]
            groups = _group_runs_in_sentence(indexed, para_text, sent_start, sent_end)
            if not groups:
                continue

            for g in groups:
                # Detect/force style + filter items
                citation_text, style, relevant_items = _render_citation_from_items(
                    g["items"], force_style=force_style
                )  # CHANGED

                # Build valid_items ONLY from filtered items
                valid_items: List[Dict[str, Any]] = []
                seen: set[str] = set()
                ref_ids: List[str] = []
                titles: List[str] = []

                for it in relevant_items:  
                    ids = it.get("targets") or []
                    # Normalize per-style
                    if style == "numeric":
                        item_text = _normalize_numeric_item_text(it["span"]) 
                    else:
                        item_text = it["span"]
                    if ids:
                        first_id = ids[0]
                        valid_items.append({
                            "text": item_text,
                            "ref_id": first_id,
                            "title": id2title.get(first_id, "—"),
                        })
                    for rid in ids:
                        if rid not in seen:
                            seen.add(rid)
                            ref_ids.append(rid)
                            titles.append(id2title.get(rid, f"(missing: {rid})"))

                if drop_unlinked and not ref_ids:
                    continue

                # Pretty only when NOT numeric
                if len(valid_items) == 1 and style != "numeric": 
                    local = {
                        "start": max(0, g["start"] - sent_start),
                        "end": max(0, g["end"] - sent_start),
                    }
                    local["start"] = max(0, min(local["start"], len(claim)))
                    local["end"] = max(local["start"], min(local["end"], len(claim)))
                    pretty = _render_single_item_text_in_sentence(claim, local)
                    valid_items[0]["text"] = pretty
                    citation_text = pretty

                out.append({
                    "marker": f"[CITATION_{counter}]",
                    "claim": claim,
                    "citation": citation_text,
                    "citation_items": valid_items,  
                    "ref_paper": ref_ids,
                    "references": titles,
                    "style": style,
                })
                counter += 1

    return {"total": len(out), "citations": out}

def make_rows_for_fe_task1b(
    tei: str,
    explode_groups: bool = False,
    drop_unlinked: bool = True,
    force_style: Optional[str] = None  
) -> Dict[str, Any]:
    data = extract_intext_citations_task1b(
        tei, drop_unlinked=drop_unlinked, force_style=force_style
    )  
    rows: List[Dict[str, Any]] = []

    if not explode_groups:
        for i, it in enumerate(data["citations"], 1):
            rows.append({
                "key": f"r{i}",
                "cite": it["marker"],
                "location": "—",
                "type": "other",
                "claim": it["claim"],
                "citation": it["citation"],
                "citation_items": it["citation_items"],
                "ref": "; ".join(it["references"]) if it["references"] else "—",
                "ref_paper": it["ref_paper"],
                "style": it.get("style", "unknown"),
                "status": "Unverified",
                "score": 0.0,
                "issues": []
            })
    else:
        r = 1
        for it in data["citations"]:
            if not it["citation_items"]:
                continue
            for k, ci in enumerate(it["citation_items"], 1):
                rows.append({
                    "key": f"r{r}",
                    "cite": f"{it['marker']}-{k}",
                    "location": "—",
                    "type": "other",
                    "claim": it["claim"],
                    "citation": it["citation"],
                    "citation_item": ci["text"],
                    "ref": ci["title"],
                    "ref_paper": [ci["ref_id"]] if ci.get("ref_id") else [],
                    "style": it.get("style", "unknown"),
                    "status": "Unverified",
                    "score": 0.0,
                    "issues": []
                })
                r += 1

    return {"total": len(rows), "rows": rows}
