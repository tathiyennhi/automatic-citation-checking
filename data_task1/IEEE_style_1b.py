# IEEE_style_1b.py
# Task 1b (TEI-first) for IEEE numeric
# - Uses GROBID TEI <ref type="bibr"> to identify citations (no regex detection)
# - Each sentence -> one .in/.label pair
# - text_norm: remove IEEE brackets, replace each NUMBER with [CITATION_i] in order;
#               normalize so that only a single space separates markers (no commas, no dashes)
# - mask: LIST of citation substrings (verbatim) in the sentence (each may contain multiple adjacent <ref> tags)
# - citation_references: each number is a mention (expand ranges like 5–7 → 5,6,7)

import os
import json
import requests
from typing import List, Dict, Any, Tuple, Optional
from xml.etree import ElementTree as ET

TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}
DELIMS = {";", ",", " ", "\t", "\n", "\r"}

# ----------------- helpers -----------------
def clean_ws(s: str) -> str:
    return " ".join((s or "").split())

def only_delims(s: str) -> bool:
    return all(ch in DELIMS for ch in (s or ""))

def is_digit(ch: str) -> bool:
    return '0' <= ch <= '9'

def expand_range(a: int, b: int) -> List[int]:
    return list(range(min(a, b), max(a, b) + 1))

def strip_outer_square_or_round_brackets(s: str) -> str:
    """Remove outer [] or () if present."""
    t = (s or "").strip()
    if len(t) >= 2:
        if (t[0] == '[' and t[-1] == ']') or (t[0] == '(' and t[-1] == ')'):
            return t[1:-1].strip()
    return t

def parse_ieee_numbers(inner_text: str) -> Tuple[List[int], List[Tuple[str, Optional[int]]]]:
    """
    Parse inner_text into tokens (string, optional int) + list of numbers (expanded if ranges).
    Does not use regex to detect citation — just splits numeric vs non-numeric and interprets dashes as ranges.
    """
    s = inner_text.strip()
    tokens: List[Tuple[str, Optional[int]]] = []
    i, n = 0, len(s)
    while i < n:
        if is_digit(s[i]):
            j = i
            while j < n and is_digit(s[j]):
                j += 1
            num_str = s[i:j]
            tokens.append((num_str, int(num_str)))
            i = j
        else:
            j = i + 1
            while j < n and not is_digit(s[j]):
                j += 1
            tokens.append((s[i:j], None))
            i = j

    numbers: List[int] = []
    k = 0
    while k < len(tokens):
        _s, v = tokens[k]
        if v is not None and k + 2 < len(tokens):
            dash_s, _ = tokens[k + 1]
            _s2, v2 = tokens[k + 2]
            if v2 is not None and dash_s in ('-', '–'):
                numbers.extend(expand_range(v, v2))
                k += 3
                continue
        if v is not None:
            numbers.append(v)
        k += 1

    return numbers, tokens

def tokens_to_plain_markers(tokens: List[Tuple[str, Optional[int]]], marker_iter) -> str:
    """
    Rebuild the string but:
      - each number -> next marker from marker_iter
      - all non-numeric characters (comma, space, dash) become ' '
    Final string is collapsed to single spaces.
    """
    out: List[str] = []
    k = 0
    while k < len(tokens):
        s, v = tokens[k]
        if v is not None and k + 2 < len(tokens):
            dash_s, _ = tokens[k + 1]
            _s2, v2 = tokens[k + 2]
            if v2 is not None and dash_s in ('-', '–'):
                out.append(next(marker_iter))  # start of range
                out.append(' ')
                out.append(next(marker_iter))  # end of range
                k += 3
                continue
        if v is not None:
            out.append(next(marker_iter))
        else:
            out.append(' ')
        k += 1

    plain = " ".join("".join(out).split())
    return plain

# --- normalize: ensure one space between markers ---
def normalize_markers_spaces(s: str) -> str:
    """
    '[CITATION_1],[CITATION_2]' or ';' or '–' -> '[CITATION_1] [CITATION_2]'
    Does not touch non-marker text.
    """
    import re
    s = re.sub(r'(\[CITATION_\d+\])\s*[,;–-]?\s*(?=\[CITATION_\d+\])', r'\1 ', s)
    return " ".join(s.split())

# --- XML-aware sentence split (no NLTK) ---
_ABBR_TAIL = ('e.g.', 'i.e.', 'etc.', 'al.')
_END_PUNCT = {'.', '?', '!'}

def _is_abbr_tail(text: str, pos: int) -> bool:
    """Check if just before pos the text ends with an abbreviation (e.g., i.e., etc., al.)."""
    for ab in _ABBR_TAIL:
        L = len(ab)
        if pos >= L and text[pos - L:pos] == ab:
            return True
    return False

def xml_sentence_spans(para_text: str, ref_spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Sentence segmentation using a small state machine:
      - Iterate char by char; track parentheses/bracket depth.
      - Treat <ref> spans as atomic tokens (skip over them).
      - Cut only at '.', '?', '!' when depth==0, not after abbreviations,
        and followed by whitespace or end of string.
    Returns a list of (start, end) spans in para_text.
    """
    n = len(para_text)
    i = 0
    spans = []
    start = 0
    paren = 0
    bracket = 0

    ref_at = {s: e for (s, e) in ref_spans}

    while i < n:
        if i in ref_at:
            i = ref_at[i]
            continue

        ch = para_text[i]

        if ch == '(':
            paren += 1
        elif ch == ')':
            paren = max(0, paren - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)

        if ch in _END_PUNCT and paren == 0 and bracket == 0:
            j = i + 1
            if _is_abbr_tail(para_text, j):
                i += 1
                continue
            if j == n or para_text[j].isspace():
                end = j
                while end < n and para_text[end].isspace():
                    end += 1
                spans.append((start, end))
                start = end
                i = end
                continue

        i += 1

    if start < n:
        spans.append((start, n))
    spans = [(s, e) for (s, e) in spans if clean_ws(para_text[s:e])]
    return spans

# ----------------- IEEE 1b -----------------
class IEEE1B:
    def __init__(self, grobid_url: str = "http://localhost:8070", output_dir: str = "task1b_output"):
        self.grobid_url = grobid_url
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ---- GROBID ----
    def grobid_fulltext(self, pdf_path: str) -> str:
        url = f"{self.grobid_url}/api/processFulltextDocument"
        with open(pdf_path, 'rb') as f:
            r = requests.post(url, files={'input': f}, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f"GROBID error {r.status_code}: {r.text[:500]}")
        return r.text

    # ---- TEI ----
    def iter_body_paragraphs(self, root: ET.Element):
        # BODY only, skip reference list
        for p in root.findall('.//tei:text/tei:body//tei:p', TEI_NS):
            yield p

    @staticmethod
    def is_bibl_ref(el: ET.Element) -> bool:
        if el is None:
            return False
        if el.tag.endswith('ref'):
            if el.get('type') == 'bibr':
                return True
            tgt = el.get('target') or ""
            return tgt.startswith("#b")
        return False

    def paragraph_runs_with_spans(self, p: ET.Element) -> Tuple[str, List[Dict[str, Any]]]:
        pieces: List[str] = []
        refs: List[Dict[str, Any]] = []
        cursor = 0

        def push_text(txt: Optional[str]):
            nonlocal cursor
            t = txt or ""
            if t:
                pieces.append(t)
                cursor += len(t)

        def walk(node: ET.Element):
            nonlocal cursor
            if node.text:
                push_text(node.text)
            for child in list(node):
                tag = child.tag.split('}', 1)[1] if '}' in child.tag else child.tag
                if tag == 'ref' and self.is_bibl_ref(child):
                    inner = ''.join(child.itertext())
                    start = cursor
                    pieces.append(inner)
                    cursor += len(inner)
                    refs.append({
                        "inner_text": inner,
                        "target": child.get("target"),
                        "span": {"start": start, "end": start + len(inner)}
                    })
                else:
                    walk(child)
                if child.tail:
                    push_text(child.tail)

        walk(p)
        full_text = ''.join(pieces)
        return full_text, refs

    # ---- sentence split + map refs ----
    def split_sentences_with_ref_mapping(self, para_text: str, refs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ref_spans = [(r["span"]["start"], r["span"]["end"]) for r in refs]
        sent_spans = xml_sentence_spans(para_text, ref_spans)

        out = []
        for (s0, s1) in sent_spans:
            sent_text = para_text[s0:s1]
            sent_refs = []
            for r in refs:
                rs, re = r["span"]["start"], r["span"]["end"]
                if rs >= s0 and re <= s1:
                    sent_refs.append({
                        "inner_text": r["inner_text"],
                        "target": r.get("target"),
                        "span_in_sent": {"start": rs - s0, "end": re - s0}
                    })
            out.append({"text": sent_text, "refs": sent_refs})
        return out

    # ---- group adjacent <ref> (for mask) ----
    @staticmethod
    def group_adjacent_in_sentence(sent_text: str, sent_refs: List[Dict[str, Any]]) -> List[List[int]]:
        if not sent_refs:
            return []
        groups: List[List[int]] = []
        cur = [0]
        for i in range(1, len(sent_refs)):
            prev_end = int(sent_refs[i - 1]["span_in_sent"]["end"])
            next_start = int(sent_refs[i]["span_in_sent"]["start"])
            middle = sent_text[prev_end:next_start]
            if only_delims(middle):
                cur.append(i)
            else:
                groups.append(cur)
                cur = [i]
        groups.append(cur)
        return groups

    # ---- build label for one sentence ----
    def build_1b_for_sentence(self, sent_text: str, sent_refs: List[Dict[str, Any]]) -> Dict[str, Any]:
        citation_refs: List[Dict[str, str]] = []
        parts: List[str] = []
        cursor = 0
        next_idx = 1  # citation index within sentence

        groups = self.group_adjacent_in_sentence(sent_text, sent_refs)
        group_masks = []
        for g in groups:
            s0 = sent_refs[g[0]]["span_in_sent"]["start"]
            eN = sent_refs[g[-1]]["span_in_sent"]["end"]
            group_masks.append(sent_text[s0:eN])

        for r in sent_refs:
            rs, re = r["span_in_sent"]["start"], r["span_in_sent"]["end"]
            inner_raw = r["inner_text"]
            parts.append(sent_text[cursor:rs])

            inner = strip_outer_square_or_round_brackets(inner_raw)
            numbers, tokens = parse_ieee_numbers(inner)

            if numbers:
                start_seq = next_idx
                for _ in numbers:
                    citation_refs.append({
                        "reference_text": str(_),
                        "citation_marker": f"[CITATION_{next_idx}]"
                    })
                    next_idx += 1

                def marker_iter():
                    i = 0
                    while i < len(numbers):
                        yield f"[CITATION_{start_seq + i}]"
                        i += 1

                rebuilt_plain = tokens_to_plain_markers(tokens, marker_iter())
                parts.append(rebuilt_plain)
            else:
                m = f"[CITATION_{next_idx}]"
                parts.append(m)
                citation_refs.append({
                    "reference_text": clean_ws(inner),
                    "citation_marker": m
                })
                next_idx += 1

            cursor = re

        parts.append(sent_text[cursor:])
        text_norm = clean_ws("".join(parts))
        text_norm = normalize_markers_spaces(text_norm)

        return {
            "style": "IEEE",
            "text": sent_text,
            "text_norm": text_norm,
            "mask": [m.strip() for m in group_masks if m.strip()],
            "citation_references": citation_refs
        }

    # ---- run ----
    def run_pdf(self, pdf_path: str):
        print(f"[1b-IEEE] Processing: {pdf_path}")
        tei = self.grobid_fulltext(pdf_path)
        root = ET.fromstring(tei)

        out_idx = 0
        total_mentions = 0

        for p in self.iter_body_paragraphs(root):
            para_text, refs = self.paragraph_runs_with_spans(p)
            if not para_text.strip():
                continue

            sent_records = self.split_sentences_with_ref_mapping(para_text, refs)
            for rec in sent_records:
                obj = self.build_1b_for_sentence(rec["text"], rec["refs"])
                self._write_pair(obj, out_idx)   # always write (even without citations)
                out_idx += 1
                total_mentions += len(obj["citation_references"])

        print(f"\n✅ Done. Sentences: {out_idx} | Mentions: {total_mentions}")
        print(f"Output: {self.output_dir}/")

    # ---- I/O ----
    def _write_pair(self, obj: Dict[str, Any], idx: int):
        in_path = os.path.join(self.output_dir, f"citation_{idx:03d}.in")
        lb_path = os.path.join(self.output_dir, f"citation_{idx:03d}.label")
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump({"text": obj["text"]}, f, ensure_ascii=False, indent=2)
        with open(lb_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

# convenience
def run(pdf_path: str, output_dir: str = "task1b_output", grobid_url: str = "http://localhost:8070"):
    IEEE1B(grobid_url=grobid_url, output_dir=output_dir).run_pdf(pdf_path)
