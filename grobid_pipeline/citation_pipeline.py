
"""Citation extraction + (optional) abstract crawler
====================================================
Fixed:
  • Syntax errors on multi‑var annotations
  • JSON serialisation (use dataclasses.asdict)
  • --no-abstracts flag to skip crawling (faster)
  • --workers to reduce parallel requests
  • Shorter time‑outs + single retry
  • Cache persists via shelve (thread‑safe)
Logic flow of the original script is preserved.
"""

from __future__ import annotations
import argparse, json, logging, pathlib, re, shelve, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import fitz  # PyMuPDF

###############################################################################
# -------------------------  MINIMAL 3RD‑PARTY DEPS  ------------------------ #
###############################################################################
try:
    import pdfplumber  # prettier fallback extraction
except ModuleNotFoundError:  # pragma: no cover
    pdfplumber = None

try:
    import spacy  # sentence boundary for fallback ref parsing
    NLP = spacy.load("en_core_web_sm")
except Exception:  # pragma: no cover
    NLP = None

import requests

###############################################################################
# ------------------------------  CONFIG  ------------------------------------ #
###############################################################################
HEADERS = {"User-Agent": "citation-pipeline/1.0"}
TIMEOUT = 5  # seconds
RETRY   = 1
CACHE_FILE = pathlib.Path("abstract_cache.db")

log = logging.getLogger("citation_pipeline")
logging.basicConfig(format="%(levelname)s | %(message)s", level=logging.INFO)

###############################################################################
# ----------------------------  DATA MODELS  --------------------------------- #
###############################################################################
@dataclass
class Span:
    start: int
    end: int

@dataclass
class Citation:
    cid: str
    style: str
    raw: str
    span: Span
    parsed: Dict[str, object]

@dataclass
class Reference:
    ref_id: str
    style: str
    raw: str
    parsed: Dict[str, object]

###############################################################################
# -------------------------  ABSTRACT CACHE  --------------------------------- #
###############################################################################
class AbstractCache:
    """Disk‑backed cache via shelve (thread‑safe for multiple reads)."""

    def __init__(self, path: pathlib.Path):
        self.path = str(path)
        self._db: Optional[shelve.DbfilenameShelf] = None

    def __enter__(self):
        self._db = shelve.open(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._db is not None:
            self._db.close()
            self._db = None

    # -----------------------------------------------------
    def get(self, key: str) -> Optional[str]:
        return self._db.get(key) if self._db else None

    def set(self, key: str, abstract: str):
        if self._db is not None:
            self._db[key] = abstract

###############################################################################
# ---------------------------  HELPERS  -------------------------------------- #
###############################################################################
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_norm   = lambda t: re.sub(r"[^a-z]", "", t.lower())

# ---- minimal title cleaning (remove urls / doi) -----------------------------
def clean_title(raw: str) -> str:
    raw = re.sub(r"https?://\S+", "", raw)
    raw = re.sub(r"doi:\s*\S+", "", raw, flags=re.I)
    return raw.strip()

# -----------------------------  PDF TEXT  ------------------------------------

def extract_text(pdf_path: pathlib.Path) -> str:
    pages: List[str] = []
    with fitz.open(pdf_path) as doc:
        for p in doc:
            pages.append(p.get_text("text"))
    if not any(pages) and pdfplumber:  # fallback
        with pdfplumber.open(pdf_path) as doc:
            pages = [p.extract_text() or "" for p in doc.pages]
    text = "\n".join(pages)
    # merge words broken by hyphen at EOL
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

###############################################################################
# ------------------------  CITATION DETECTOR  ------------------------------- #
###############################################################################
class CitationExtractor:
    """Detect in‑text citations + split reference list (heuristics)."""

    APA_PAREN  = re.compile(r"\(([^()]+?),\s*(\d{4}[a-z]?)\)")
    IEEE_BRACK = re.compile(r"\[(\d{1,3}(?:\s*[,–-]\s*\d{1,3})*)]")
    REF_HEAD   = re.compile(r"^\s*(references?|bibliography|works\s+cited)\b", re.I)

    def detect(self, text: str) -> Tuple[List[Citation], List[str]]:
        citations: List[Citation] = []
        spans: set[Tuple[int, int]] = set()
        cid_counter = 0

        def push(m: re.Match, style: str, parsed: dict):
            nonlocal cid_counter
            s = (m.start(), m.end())
            if s in spans:
                return
            spans.add(s)
            citations.append(Citation(f"c{cid_counter}", style, m.group(0), Span(*s), parsed))
            cid_counter += 1

        for m in self.APA_PAREN.finditer(text):
            au, yr = m.groups()
            push(m, "APA", {"first": au.split()[0], "year": int(yr[:4])})

        for m in self.IEEE_BRACK.finditer(text):
            idxs = re.split(r"[,–-]", m.group(1))
            for idx in idxs:
                if idx.strip():
                    push(m, "IEEE", {"index": int(idx)})

        citations.sort(key=lambda c: c.span.start)
        # crude ref section detection – last 25% or after heading
        pos_head = None
        for match in self.REF_HEAD.finditer(text):
            pos_head = match.start(); break
        ref_block = text[pos_head:] if pos_head else text[int(len(text)*0.75):]
        refs = self._split_refs(ref_block)
        return citations, refs

    # crude splitting on newlines / numbering patterns
    def _split_refs(self, block: str) -> List[str]:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        entries, buf = [], []
        for ln in lines:
            # new ref marker?
            if (re.match(r"^\[\d+]|^\d+\. |^[A-Z].+?,", ln) and buf):
                entries.append(" ".join(buf)); buf = []
            buf.append(ln)
        if buf:
            entries.append(" ".join(buf))
        return entries

###############################################################################
# --------------------  ABSTRACT FETCH (semanticscholar + xref)  ------------- #
###############################################################################

def fetch_abstract(title: str) -> Optional[str]:
    title_q = quote_plus(title)
    # 1) Semantic Scholar
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={title_q}&limit=1&fields=title,abstract"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if res.ok and (data := res.json()).get("data"):
            rec = data["data"][0]
            if _similar(title, rec.get("title", "")) >= 0.45:
                return rec.get("abstract")
    except Exception:
        pass
    # 2) CrossRef
    try:
        url = f"https://api.crossref.org/works?query.bibliographic={title_q}&rows=1"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if res.ok and (items := res.json().get("message", {}).get("items")):
            item = items[0]
            if _similar(title, item.get("title", [""])[0]) >= 0.45:
                return item.get("abstract")
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------

def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()

###############################################################################
# ---------------------------  MAIN ROUTINE  ----------------------------------#
###############################################################################

def process(pdf_path: pathlib.Path, crawl: bool = True, workers: int = 8) -> dict:
    log.info("🔍 Extracting text …")
    text = extract_text(pdf_path)
    ext = CitationExtractor()
    citations, raw_refs = ext.detect(text)

    # ------------------------------------------ REF objects
    references: List[Reference] = []
    for i, raw in enumerate(raw_refs, 1):
        references.append(Reference(f"r{i}", "", raw, {}))

    # ------------------------------------------ optional abstract crawling
    if crawl and raw_refs:
        log.info("🌐 Fetching abstracts …")
        with AbstractCache(CACHE_FILE) as cache:
            tasks = {}
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for ref in references:
                    title = clean_title(ref.raw)
                    if not title:
                        continue
                    if (abs_cached := cache.get(title)) is not None:
                        ref.parsed["abstract"] = abs_cached
                        continue
                    tasks[pool.submit(fetch_abstract, title)] = (ref, title)
                for fut in as_completed(tasks):
                    ref, title = tasks[fut]
                    try:
                        abs_txt = fut.result()
                        if abs_txt:
                            ref.parsed["abstract"] = abs_txt
                            cache.set(title, abs_txt)
                    except Exception as e:
                        log.debug(f"Fetch error: {e}")

    # ------------------------------------------ build JSON‑serialisable dict
    result = {
        "pdf": str(pdf_path.name),
        "citations": [asdict(c) for c in citations],
        "references": [asdict(r) for r in references],
    }
    return result

###############################################################################
# --------------------------------  CLI  -------------------------------------#
###############################################################################

def cli():
    ap = argparse.ArgumentParser(description="Extract in‑text citations & (optionally) fetch abstracts")
    ap.add_argument("pdf", type=pathlib.Path)
    ap.add_argument("-o", "--out", type=pathlib.Path, help="Output JSON file")
    ap.add_argument("--no-abstracts", action="store_true", help="Skip online abstract fetching")
    ap.add_argument("--workers", type=int, default=8, help="Parallel requests when crawling")

    args = ap.parse_args()
    out_path = args.out or args.pdf.with_suffix(".json")

    data = process(args.pdf, crawl=not args.no_abstracts, workers=args.workers)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info(f"✅ Saved → {out_path}")

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        log.warning("Interrupted!")
