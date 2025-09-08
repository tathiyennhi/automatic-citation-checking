#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified pipeline for academic PDFs (TEI-first, strict-bib version):
  1) GROBID → TEI (processReferences)
  2) Parse TEI → strict bib_entries (keys are exactly xml:id like b0..b42)
     - Title = <title level="a" type="main"> else <title level="m" ...>
     - DOI pulled only from idno[@type="DOI"] (normalized) or arXiv id (kept as-is)
  3) Enrich ABSTRACTS (Title → DOI order):
     - Try Title against Crossref / OpenAlex / S2 / CORE
     - If still empty and DOI present → Crossref / OpenAlex by DOI
  4) TEXT:
     - Extract only BEFORE "References/Bibliography/Works Cited"
     - Replace any in-text citations with [CITATION_i] (no bib mutation, no pseudo-keys)
       * Handles numeric [1], ranges [2–4], superscripts {5,6}, author-year, "as cited in ..."
       * Strong guards to avoid metrics/fig/eq refs
     - Smart sentence split (protect abbrev/DOI/markers), normalize/mend tails
  5) OUTPUT: N chunks (*.in), each with K sentences (default 5)
     - citation_candidates = ONLY the TEI keys (e.g., b0..b42)
     - bib_entries = ONLY the TEI-derived entries (title + abstract)

CLI:
  python unified_pipeline.py --pdf paper.pdf --grobid-url http://localhost:8070 \
    --sentences-per-file 5 --subset-bib --outdir out
"""
from __future__ import annotations
import os, re, sys, time, unicodedata, random, json, argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import requests

# ---------- Optional NER (non-breaking) ----------
def try_load_ner(disable_ner: bool):
    if disable_ner:
        return False, None
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
            return True, nlp
        except Exception:
            return False, None
    except Exception:
        return False, None

# ---------------- Helpers ----------------
UA_LIST = [
    "Academic Research Bot - Reference Pipeline v1.4 (mailto:your-real-email@university.edu)",
    "Mozilla/5.0 (compatible; Academic Research; +mailto:your-real-email@university.edu)",
    "Graduate Student Research Bot v1.4 - Thesis Project - Contact: your-real-email@university.edu",
]
API_UA = "Academic Research Pipeline/1.4 (Graduate Thesis Project; mailto:your-real-email@university.edu)"

def _get_random_ua(): return random.choice(UA_LIST)

def _slug(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt or "").lower()
    return re.sub(r"\W+", " ", txt).strip()

def _normalize_doi(raw: Optional[str]) -> Optional[str]:
    if not raw: return None
    t = raw.strip()
    m = re.search(r"(10\.\S+?)(?=[\s\"<>)]|$)", t, flags=re.I)
    return m.group(1).rstrip(".,;") if m else None

def _fuzzy_match(gold: str, candidate: str, threshold: float = 0.6) -> bool:
    if not gold or not candidate: return False
    gw, cw = set(gold.split()), set(candidate.split())
    if not gw or not cw: return False
    inter, uni = len(gw & cw), len(gw | cw)
    return (inter / uni) >= threshold if uni else False

# ---------------- GROBID ----------------
TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def grobid_process_references(pdf_path: Path, out_tei: Path, grobid_url: str) -> bool:
    grobid_url = grobid_url.rstrip("/")
    try:
        r = requests.get(f"{grobid_url}/api/isalive", timeout=5)
        if not (r.ok and "true" in r.text.lower()):
            print(f"❌ GROBID not alive at {grobid_url}"); return False
    except requests.RequestException:
        print(f"❌ Cannot reach GROBID at {grobid_url}"); return False
    url = f"{grobid_url}/api/processReferences"
    with pdf_path.open('rb') as f:
        r = requests.post(url, files={'input': (pdf_path.name, f, 'application/pdf')},
                          headers={'User-Agent': _get_random_ua()})
    if r.ok:
        out_tei.write_text(r.text, encoding='utf-8')
        print(f"✔ GROBID XML → {out_tei}"); return True
    print(f"❌ GROBID HTTP {r.status_code}"); return False

# ---------------- TEI → STRICT bib ----------------
def _pick_title(el: ET.Element) -> Optional[str]:
    # Prefer analytic/article title 'a' main, else monograph 'm'
    t_a = el.find('.//tei:analytic/tei:title[@level="a"][@type="main"]', TEI_NS)
    if t_a is not None:
        text = ''.join(t_a.itertext()).strip()
        if text: return text
    t_m = el.find('.//tei:monogr/tei:title[@level="m"]', TEI_NS)
    if t_m is not None:
        text = ''.join(t_m.itertext()).strip()
        if text: return text
    # As last resort, any title under analytic/monogr (keep strictness)
    t_any = el.find('.//tei:title', TEI_NS)
    return (''.join(t_any.itertext()).strip() if t_any is not None else None) or None

def _pick_year(el: ET.Element) -> Optional[str]:
    d = el.find('.//tei:monogr/tei:imprint/tei:date[@type="published"]', TEI_NS)
    if d is not None:
        when = (d.get('when') or '').strip()
        if when:
            m = re.match(r'(19|20)\d{2}', when)
            if m: return m.group(0)
        dtxt = ''.join(d.itertext()).strip()
        m = re.search(r'(19|20)\d{2}', dtxt)
        if m: return m.group(0)
    return None

def _pick_authors(el: ET.Element) -> List[str]:
    authors = []
    # analaytic/author or monogr/author
    auth_nodes = el.findall('.//tei:analytic/tei:author', TEI_NS) or el.findall('.//tei:monogr/tei:author', TEI_NS)
    for a in auth_nodes:
        s = a.find('.//tei:surname', TEI_NS)
        if s is not None and s.text:
            authors.append(s.text.strip())
        else:
            pn = ''.join(a.itertext()).strip()
            if pn:
                # best-effort: last token as surname (non-destructive)
                parts = [p for p in pn.split() if p]
                if parts: authors.append(parts[-1])
    return authors

def parse_tei_build_entries(tei_path: Path) -> Dict[str, Dict]:
    root = ET.parse(tei_path).getroot()
    bib_entries: Dict[str, Dict] = {}
    for bibl in root.findall('.//tei:biblStruct', TEI_NS):
        key = bibl.get('{http://www.w3.org/XML/1998/namespace}id')
        if not key:  # should not happen, but skip if no id
            continue
        title = _pick_title(bibl) or "No title"
        # DOI (strict)
        doi_el = bibl.find('.//tei:idno[@type="DOI"]', TEI_NS)
        doi = _normalize_doi(doi_el.text if doi_el is not None else None)
        # arXiv id – keep if present
        arxiv_el = bibl.find('.//tei:idno[@type="arXiv"]', TEI_NS)
        arxiv_id = arxiv_el.text.strip() if (arxiv_el is not None and arxiv_el.text) else None
        authors = _pick_authors(bibl)
        year = _pick_year(bibl)
        bib_entries[key] = {
            "title": title,
            "doi": doi,
            "arxiv": arxiv_id,
            "abstract": None,
            "authors": authors,
            "year": year,
        }
    return bib_entries

# ---------------- Enrich (Title → DOI) ----------------
def crossref_by_title(title: str) -> Optional[str]:
    try:
        r = requests.get("https://api.crossref.org/works",
                         params={'query.title': title, 'rows': 5},
                         headers={'User-Agent': API_UA}, timeout=12)
        if not r.ok: return None
        gold = _slug(title)
        for item in r.json().get('message', {}).get('items', []):
            it = (item.get('title') or [''])[0]
            if _slug(it) == gold or _fuzzy_match(gold, _slug(it), 0.85):
                abs_raw = item.get('abstract')
                if abs_raw:
                    return re.sub(r'<[^>]+>', '', abs_raw).strip()
    except Exception:
        pass
    return None

def crossref_by_doi(doi: str) -> Optional[str]:
    try:
        r = requests.get(f"https://api.crossref.org/works/{requests.utils.quote(doi)}",
                         headers={'User-Agent': API_UA}, timeout=12)
        if r.ok:
            abs_raw = r.json().get('message', {}).get('abstract')
            if abs_raw and 'withheld' not in abs_raw.lower():
                return re.sub(r'<[^>]+>', '', abs_raw).strip()
    except Exception:
        pass
    return None

def openalex_by_title(title: str) -> Optional[str]:
    try:
        r = requests.get("https://api.openalex.org/works",
                         params={'search': title, 'per_page': 5},
                         headers={'User-Agent': API_UA}, timeout=12)
        if not r.ok: return None
        gold = _slug(title)
        for work in r.json().get('results', []):
            wt = work.get('title', '')
            if wt and (_slug(wt) == gold or _fuzzy_match(gold, _slug(wt), 0.8)):
                inv = work.get('abstract_inverted_index')
                if inv:
                    words = [''] * (max(max(p) for p in inv.values()) + 1)
                    for w, poss in inv.items():
                        for pos in poss: words[pos] = w
                    txt = ' '.join(words).strip()
                    if len(txt) > 50: return txt
    except Exception:
        pass
    return None

def openalex_by_doi(doi: str) -> Optional[str]:
    try:
        doi_url = doi if doi.lower().startswith('http') else f"https://doi.org/{doi}"
        r = requests.get(f"https://api.openalex.org/works/{doi_url}",
                         headers={'User-Agent': API_UA}, timeout=12)
        if not r.ok: return None
        inv = r.json().get('abstract_inverted_index')
        if inv:
            words = [''] * (max(max(p) for p in inv.values()) + 1)
            for w, poss in inv.items():
                for pos in poss: words[pos] = w
            txt = ' '.join(words).strip()
            if len(txt) > 50: return txt
    except Exception:
        pass
    return None

def s2_by_title(title: str) -> Optional[str]:
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
                         params={'query': title, 'fields': 'title,abstract', 'limit': 5},
                         headers={'User-Agent': API_UA}, timeout=12)
        if not r.ok: return None
        gold = _slug(title)
        for it in r.json().get('data', []):
            t = it.get('title') or ''
            a = it.get('abstract') or ''
            if a and (_slug(t) == gold or _fuzzy_match(gold, _slug(t), 0.8)):
                return a.strip()
    except Exception:
        pass
    return None

def s2_by_doi(doi: str) -> Optional[str]:
    try:
        r = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                         params={'fields': 'abstract'}, headers={'User-Agent': API_UA}, timeout=12)
        if r.ok and r.json().get('abstract'):
            return r.json()['abstract'].strip()
    except Exception:
        pass
    return None

def arxiv_by_id(arxiv_id: str) -> Optional[str]:
    try:
        r = requests.get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
                         headers={'User-Agent': API_UA}, timeout=12)
        if r.ok:
            root = ET.fromstring(r.text)
            s = root.find('.//{http://www.w3.org/2005/Atom}summary')
            return (s.text or '').strip() if s is not None else None
    except Exception:
        pass
    return None

def core_by_title(title: str) -> Optional[str]:
    try:
        r = requests.get("https://api.core.ac.uk/v3/search/works",
                         params={'q': title, 'limit': 5},
                         headers={'User-Agent': API_UA}, timeout=12)
        if not r.ok: return None
        gold = _slug(title)
        for w in r.json().get('results', []):
            wt = w.get('title', '')
            ab = w.get('abstract') or ''
            if ab and (_slug(wt) == gold or _fuzzy_match(gold, _slug(wt), 0.8)):
                ab = ab.strip()
                if len(ab) > 30: return ab
    except Exception:
        pass
    return None

def enrich_entries(bib_entries: Dict[str, Dict]) -> None:
    if not bib_entries: return
    print("🔍 Enriching entries (Title → DOI)…")
    items = list(bib_entries.items())
    for i, (key, entry) in enumerate(items, 1):
        title = entry.get('title') or ''
        doi = entry.get('doi')
        arxiv_id = entry.get('arxiv')

        abs_text = None
        # 1) Try by TITLE
        if title and title != "No title":
            for fn in (crossref_by_title, openalex_by_title, s2_by_title, core_by_title):
                abs_text = fn(title)
                if abs_text and len(abs_text.strip()) > 30:
                    break

        # 2) If still empty, try by arXiv id (if present)
        if not abs_text and arxiv_id:
            abs_text = arxiv_by_id(arxiv_id)

        # 3) If still empty and DOI present, try by DOI
        if not abs_text and doi:
            for fn in (crossref_by_doi, openalex_by_doi, s2_by_doi):
                abs_text = fn(doi)
                if abs_text and len(abs_text.strip()) > 30:
                    break

        if abs_text:
            entry['abstract'] = abs_text.strip()
        # polite pacing
        time.sleep(min(1.0 + i * 0.03, 1.6))

# ---------------- TEXT: extract, trim, clean ----------------
def extract_text_from_pdf(pdf_path: Path) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t: pages.append(t)
    return "\n".join(pages)

def trim_before_references(text: str) -> str:
    pattern = re.compile(r"(^|\n)\s*(REFERENCES|Reference List|Reference|Bibliography|Works Cited)\s*($|\n)", flags=re.I)
    m = pattern.search(text)
    return text[:m.start()] if m else text

def pre_clean_text(text: str) -> str:
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)  # de-hyphen across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"([\)\]])\s*\d+\b", r"\1", text)       # footnotes like ")…2"
    text = re.sub(r"(?<=\w)\.(\d{1,2})(?!\d)", ".", text) # trailing footnote digits
    return text.strip()

# ---------------- Citation Detection & Replacement ----------------
SURNAME = r"[A-Z\u00C0-\u017F][A-Za-z\u00C0-\u017F'\-]{1,40}"
AND = r"(?:and|&|\+)"
ETAL = r"(?:et\s+al\.?)"
AUTHOR_ETAL = rf"(?:{SURNAME}(?:\s+{ETAL})?)"
MULTI_AUTHORS = rf"{SURNAME}(?:\s*,\s*{SURNAME})*(?:\s*,?\s*{AND}\s+{SURNAME})"
AUTHOR_SEQ = rf"(?:{AUTHOR_ETAL}|{MULTI_AUTHORS}|{SURNAME}\s+{AND}\s+{SURNAME}|{SURNAME})"
YEAR = r"(?:19|20)\d{2}[a-z]?"
LOC = r"(?:\s*,\s*(?:p+\.|pp\.|chap\.|sec\.|§)\s*\d+(?:[-–—]\d+)?(?:\s*,\s*\d+)*)?"

def _normalize_existing_markers_case_insensitive(t: str) -> str:
    return re.sub(r'\[(\s*)citation_(\d+)(\s*)\]', r'[CITATION_\2]', t, flags=re.I)

def _protect_existing_markers(t: str):
    t = _normalize_existing_markers_case_insensitive(t)
    placeholders = {}
    def repl(m):
        token = f"§CIT§{len(placeholders)+1}§"
        placeholders[token] = m.group(0)
        return token
    protected = re.sub(r'\[CITATION_\d+\]', repl, t)
    return protected, placeholders

def _restore_markers(t: str, placeholders: dict):
    for tok, val in placeholders.items(): t = t.replace(tok, val)
    return t

def looks_like_metric_context(text: str, start: int, end: int) -> bool:
    before = text[max(0, start-8):start]
    after  = text[end:end+12]
    if re.search(r'(?:F\d+|BLEU(?:-\d+)?|ROUGE(?:-[L12])?|mAP@?\d*\.?\d*|Top-\d+)$', before): return True
    if re.search(r'(?i)(eq\.?|fig\.?|table|tab\.?|sec\.?|ch\.?)\s*\d+(\.\d+)*\s*$', before): return True
    if re.search(r'^(?:-?score|-\w+)', after): return True
    return False

class CitationMarkerGenerator:
    """Global citation counter to maintain consistent numbering across all text processing"""
    def __init__(self, start_counter: int = 0):
        self.counter = start_counter
    
    def new_marker(self) -> str:
        self.counter += 1
        return f"[CITATION_{self.counter}]"
    
    def get_current_counter(self) -> int:
        return self.counter

def replace_citations(text: str, nlp, marker_generator: CitationMarkerGenerator) -> Tuple[str, int]:
    """
    IMPORTANT: This function never mutates the bibliography.
    It only emits [CITATION_n] markers when patterns are detected.
    Uses global marker generator to maintain consistent numbering.
    """
    start_count = marker_generator.get_current_counter()

    # protect existing markers
    orig_text = text
    text, ph = _protect_existing_markers(text)

    # (A) IEEE numeric [1], [1,2], [4–6]
    NUMERIC_BRACKETS = re.compile(r'\[(?!\s*CITATION_)\s*([0-9\s,;–—-]+)\s*\]')
    def repl_numeric(m):
        s, e = m.span()
        if looks_like_metric_context(text, s, e): return m.group(0)
        content = m.group(1).strip()
        parts = re.split(r'[,;]\s*', content)
        all_nums = []
        for part in parts:
            part = part.strip()
            if re.fullmatch(r'\d+', part): all_nums.append(int(part))
            else:
                rm = re.fullmatch(r'(\d+)\s*[-–—]\s*(\d+)', part)
                if rm:
                    s0, e0 = int(rm.group(1)), int(rm.group(2))
                    step = 1 if s0 <= e0 else -1
                    all_nums.extend(list(range(s0, e0+step, step)))
        if not all_nums: return m.group(0)
        markers = [marker_generator.new_marker() for _ in all_nums]
        return ' '.join(markers) if markers else m.group(0)
    text = NUMERIC_BRACKETS.sub(repl_numeric, text)

    # (B) "as cited in X, 1995" → append a marker
    AS_CITED = re.compile(r'\bas\s+cited\s+in\s+[A-Z][A-Za-z\-\s&]+?\s*,\s*(' + YEAR + r')\b', re.I)
    def repl_as_cited(m):
        s, e = m.span()
        if looks_like_metric_context(text, s, e): return m.group(0)
        return m.group(0) + " " + marker_generator.new_marker()
    text = AS_CITED.sub(repl_as_cited, text)

    # (C) MULTI-CITATION parentheses: if it looks like author-year inside, replace the whole block with markers
    PAREN_BLOCK = re.compile(r'\(([^()]*)\)')
    INNER_CITE = re.compile(rf'({AUTHOR_SEQ})\s*,?\s*({YEAR}){LOC}?', flags=re.U)
    def replace_one_pass(t: str) -> Tuple[str, bool]:
        changed = False
        def repl_block(m):
            nonlocal changed
            s, e = m.span()
            inner = m.group(1)
            if looks_like_metric_context(t, s, e): return m.group(0)
            if not re.search(YEAR, inner): return m.group(0)
            markers = []
            for _ in INNER_CITE.finditer(inner):
                markers.append(marker_generator.new_marker())
            if markers:
                changed = True
                return " " + " ".join(markers) + " "
            return m.group(0)
        return PAREN_BLOCK.sub(repl_block, t), changed
    for _ in range(3):
        text, ch = replace_one_pass(text)
        if not ch: break

    # (D) Narrative "Author (1999)" or "(Author, 1999)"
    surnames_for_dyn = []
    if nlp:
        try:
            doc = nlp(text[:160000])
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    parts = [p for p in ent.text.strip().split() if p]
                    if parts and re.match(r"^[A-Z][A-Za-z\-']{1,}$", parts[-1]):
                        surnames_for_dyn.append(parts[-1])
        except Exception:
            surnames_for_dyn = []
    surnames_for_dyn = list(dict.fromkeys(surnames_for_dyn))  # dedupe, keep order
    DYN_SURNAME = r"(?:%s|%s)" % ("|".join(map(re.escape, surnames_for_dyn)) if surnames_for_dyn else SURNAME, SURNAME)
    DYN_AUTHOR_SEQ = rf"(?:{DYN_SURNAME}(?:\s+{ETAL})?|{DYN_SURNAME}(?:\s*,\s*{DYN_SURNAME})*(?:\s*,?\s*{AND}\s+{DYN_SURNAME})|{DYN_SURNAME}\s+{AND}\s+{DYN_SURNAME}|{DYN_SURNAME})"

    AY_PATTERNS = [
        re.compile(rf'\(({DYN_AUTHOR_SEQ})\s*,\s*({YEAR}){LOC}\s*\)'),
        re.compile(rf'({DYN_AUTHOR_SEQ})\s*\(\s*({YEAR}){LOC}\s*\)'),
    ]
    def valid_ctx(t: str, s: int, e: int) -> bool:
        if looks_like_metric_context(t, s, e): return False
        before = t[max(0, s-30):s].lower()
        for tok in ['figure','fig.','table','tab.','equation','eq.','section','sec.',
                    'algorithm','alg.','theorem','lemma','definition','example',
                    'appendix','app.','chapter','ch.','page','p.','line']:
            if tok in before: return False
        return True
    def repl_ay(m):
        s, e = m.span()
        if not valid_ctx(text, s, e): return m.group(0)
        return marker_generator.new_marker()
    for p in AY_PATTERNS: text = p.sub(repl_ay, text)

    # (E) Superscript-like {5,6}
    def repl_super(m):
        s, e = m.span()
        if looks_like_metric_context(text, s, e): return m.group(0)
        nums = re.findall(r'\d+', m.group(1))
        if not nums: return m.group(0)
        markers = [marker_generator.new_marker() for _ in nums]
        return ' '.join(markers)
    text = re.sub(r'\^?\{(\d+(?:[,;]\s*\d+)*)\}(?!\s*(?:st|nd|rd|th)\b)', repl_super, text)

    # restore markers (and normalize nested [[CITATION_n]])
    text = re.sub(r'\[\s*(\[\s*CITATION_\d+\s*\])\s*\]', r'\1', text)
    text = _restore_markers(text, ph)
    
    total_markers_added = marker_generator.get_current_counter() - start_count
    return text, total_markers_added

# ---------------- Sentence split & normalize ----------------
ABBREV = [
    "e.g.", "i.e.", "etc.", "Fig.", "Figs.", "Eqs.", "Eq.", "Sec.", "Secs.", "No.", "Nos.",
    "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Inc.", "Ltd.", "Co.", "St.", "J.",
    "U.S.", "U.K.", "U.N.", "Ph.D.", "Jr.", "Sr.", "cf.", "al.", "vs.", "ca."
]

def sentence_split(text: str) -> List[str]:
    protects: List[str] = []
    def protect(pattern: str):
        nonlocal text, protects
        rx = re.compile(pattern)
        def repl(m):
            tok = f"§P{len(protects)}§"
            protects.append(m.group(0)); return tok
        text = rx.sub(repl, text)
    abbrev = r'\b(?:' + '|'.join([re.escape(x) for x in ABBREV]) + r')\b'
    protect(abbrev); protect(r'\bet\s+al\.\b'); protect(r'10\.\d{4,}/\S+'); protect(r'(?<=\d)\.(?=\d)')
    protect(r'\[CITATION_\d+\]')

    txt = re.sub(r"[ \t]+", " ", text); txt = re.sub(r"\s*\n\s*", " ", txt).strip()
    BOUND = "⟐"
    boundary_re = re.compile(r'([\.!?])\s+(?=(?:["""\'\)\]]*\s*)?(?:\(|\[|[A-Z0-9]))')
    marked = boundary_re.sub(r"\1 " + BOUND + " ", txt)
    sents = [s.strip() for s in marked.split(BOUND) if s.strip()]

    def unprotect(s):
        for i, val in enumerate(protects): s = s.replace(f"§P{i}§", val)
        return s
    sents = [unprotect(s) for s in sents]

    final = []
    for s in sents:
        s = strip_leading_enumeration(s)
        if len(s) >= 3 and not re.fullmatch(r"[^\w]+", s): final.append(s)
    return final

def strip_leading_enumeration(s: str) -> str:
    s = re.sub(r"^\s*\(?\d+(?:\.\d+){0,2}\)?[)\.:\-]\s+", "", s)
    s = re.sub(r"^\s*[•\-–—]\s+", "", s)
    s = re.sub(r"^\s*\(?[ivxlcdm]{1,4}\)?[)\.:\-]\s+", "", s, flags=re.I)
    return s.strip()

def normalize_sentences(sentences: List[str]) -> List[str]:
    CITERE = re.compile(r"\[CITATION_\d+\]")
    cleaned: List[str] = []
    for s in sentences:
        s = strip_leading_enumeration(s)
        s_strip = s.strip()
        if len(s_strip) < 3 or re.fullmatch(r"[^\w]+", s_strip): continue
        cleaned.append(s_strip)
    merged: List[str] = []
    for s in cleaned:
        core = s.rstrip(".;,: ").strip()
        only_cite = False
        if not core: only_cite = True
        else:
            core_wo = CITERE.sub("", core).strip()
            if len(core_wo) == 0: only_cite = True
        if only_cite and merged: merged[-1] = (merged[-1].rstrip() + " " + s).strip()
        else: merged.append(s)
    final: List[str] = []
    i = 0
    while i < len(merged):
        s = merged[i]
        if len(s) < 25 and i + 1 < len(merged):
            final.append((s + " " + merged[i+1]).strip()); i += 2
        else:
            final.append(s); i += 1
    return final

# ---------------- Write chunk files ----------------
def write_chunk_files(sentences_marked: List[str],
                      bib_entries: Dict[str, Dict],
                      outdir: Path,
                      subset_bib: bool,
                      k_per_file: int) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    total = 0

    # STRICT candidate list: ONLY TEI keys, stable order (by xml:id sort)
    tei_keys_sorted = sorted(bib_entries.keys(), key=lambda k: (len(k), k))  # b0..b42 sort
    for i in range(0, len(sentences_marked), k_per_file):
        chunk_sents = sentences_marked[i:i + k_per_file]
        if not chunk_sents: continue
        chunk_text = " ".join(chunk_sents).strip()
        if not chunk_text: continue

        # For now, even in subset mode, we keep only TEI keys (no guessing/pseudo).
        if subset_bib:
            subset_keys = tei_keys_sorted[:]  # could add safe heuristics later
        else:
            subset_keys = tei_keys_sorted[:]

        subset_bibmap = {
            k: {"title": bib_entries[k].get("title") or "No title",
                "abstract": bib_entries[k].get("abstract")}
            for k in subset_keys
        }

        data = {"text": chunk_text,
                "citation_candidates": subset_keys,
                "bib_entries": subset_bibmap}
        fname = outdir / f"{(i // k_per_file) + 1}.in"
        fname.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        total += 1
    return total

# ---------------- Orchestrator / CLI ----------------
def main():
    ap = argparse.ArgumentParser(description="Unified academic pipeline (strict TEI bib)")
    ap.add_argument("--pdf", type=str, default="paper.pdf", help="PDF path")
    ap.add_argument("--grobid-url", type=str, default="http://localhost:8070", help="GROBID base URL")
    ap.add_argument("--tmp-tei", type=str, default="grobid_refs.xml", help="Temporary TEI output path")
    ap.add_argument("--sentences-per-file", type=int, default=5, help="Sentences per .in file")
    ap.add_argument("--subset-bib", action="store_true", help="Use TEI-only bib; restricted to TEI keys (default behavior)")
    ap.add_argument("--skip-grobid", action="store_true", help="Skip GROBID; run with existing TEI if exists")
    ap.add_argument("--disable-ner", action="store_true", help="Disable spaCy NER expansion for narrative patterns")
    ap.add_argument("--outdir", type=str, default="out", help="Output directory for .in files")
    ap.add_argument("--tei", type=str, help="Optional: directly provide a TEI XML path to parse (skips GROBID)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    outdir = Path(args.outdir)
    tei_path = Path(args.tmp_tei) if not args.tei else Path(args.tei)

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}"); sys.exit(1)

    ner_ok, nlp = try_load_ner(args.disable_ner)

    # Step 1: GROBID (only if no explicit TEI is given)
    have_tei = False
    if args.tei:
        have_tei = tei_path.exists()
        print(f"⏩ Using provided TEI: {tei_path} (exists={have_tei})")
    else:
        if not args.skip_grobid:
            print("🔄 Step 1: GROBID → TEI…")
            have_tei = grobid_process_references(pdf_path, tei_path, args.grobid_url)
        else:
            print("⏩ Skipping GROBID; will try existing TEI (if any)…")
            have_tei = tei_path.exists()

    # Step 2: Parse TEI (STRICT)
    bib_entries: Dict[str, Dict] = {}
    if have_tei and tei_path.exists():
        print("🔄 Step 2: Parse TEI (strict bib)…")
        bib_entries = parse_tei_build_entries(tei_path)
        print(f"   • bibliography entries (TEI ids): {len(bib_entries)}")
    else:
        print("⚠ No TEI available → continuing with EMPTY bib (no pseudo-keys will be created).")

    # Step 3: Enrich entries (Title → DOI)
    if bib_entries:
        print("🔄 Step 3: Enrich entries (Title → DOI)…")
        enrich_entries(bib_entries)

    # Step 4: Text extraction & processing
    print("🔄 Step 4A: Extract PDF text")
    raw = extract_text_from_pdf(pdf_path)
    print("🔄 Step 4B: Trim before References/Bibliography")
    trimmed = trim_before_references(raw)
    print("🔄 Step 4C: Pre-clean")
    pre = pre_clean_text(trimmed)
    
    # Initialize global citation marker generator
    marker_generator = CitationMarkerGenerator(start_counter=0)
    
    print("🔄 Step 4D: Replace citations (markers only; no bib mutation)")
    marked, count = replace_citations(pre, nlp if ner_ok else None, marker_generator)
    print(f"   • Markers emitted: {count}")

    print("🔄 Step 4E: Sentence split")
    sents = sentence_split(marked)
    print("🔄 Step 4F: Normalize sentences")
    sents_norm = normalize_sentences(sents)

    # Step 5: Write outputs (TEI-only bib/candidates)
    print("🔄 Step 5: Write *.in files")
    n_files = write_chunk_files(
        sents_norm, bib_entries, outdir,
        subset_bib=True,  # always keep TEI-only set; safe & strict
        k_per_file=args.sentences_per_file
    )
    print(f"💾 Wrote {n_files} files to: {outdir.resolve()}/ (1.in..{n_files}.in)")
    print("✅ Done.")

if __name__ == "__main__":
    main()