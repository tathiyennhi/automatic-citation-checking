# app/services/citation_style_service.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import re
from lxml import etree

NS = {"tei": "http://www.tei-c.org/ns/1.0"}

# ===================== Citation Pattern Regexes =====================

# IEEE: [1], [2, 3], [4-6], [7–9]
IEEE_RE = re.compile(r"^\[\s*\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*\s*\]$")

# APA in-text: (Smith, 2020), (Lee & Kim, 2019; Park, 2021)
APA_PAREN_RE = re.compile(
    r"""
    \(
        \s*
        [A-Z][A-Za-z\-]+
        (?:\s+(?:&|and)\s+[A-Z][A-Za-z\-]+)?     # & Coauthor (opt)
        (?:\s+et\ al\.)?                         # et al. (opt)
        \s*,\s*
        \d{4}[a-z]?                              # Year (+a/b)
        (?:\s*[;,]\s*
            [A-Z][A-Za-z\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z\-]+)?(?:\s+et\ al\.)?\s*,\s*\d{4}[a-z]?
        )*                                       # ; other cites
        (?:\s*,\s*(?:p{1,2}\.)\s*\d+(?:\s*[–-]\s*\d+)?)?  # p./pp. (opt)
        \s*
    \)
    """,
    re.VERBOSE,
)

# APA narrative: Smith (2020), Johnson et al. (2018b)
APA_NARRATIVE_RE = re.compile(
    r"""
    \b
    [A-Z][A-Za-z\-]+(?:\s+et\ al\.)?
    \s*\(\s*\d{4}[a-z]?\s*\)
    """,
    re.VERBOSE,
)

# Chicago notes: 7) or 7.
CHICAGO_RE = re.compile(r"^(?:\^\d+|\d+\s*[.)])$")

# Numeric values (NOT citations): (4,432), (2024), (123)
NUMERIC_VALUE_RE = re.compile(r"^\(\d+(?:,\d+)*\)$")

# ===================== Core Detection Functions =====================

def detect_citation_style(text: str) -> str:
    """
    Detect citation style for a single citation text.
    Returns: 'numeric' | 'author_year' | 'note' | 'unknown'
    """
    t = text.strip()
    
    if NUMERIC_VALUE_RE.match(t):
        return "unknown"
    
    if IEEE_RE.match(t):
        return "numeric"
    if APA_PAREN_RE.match(t) or APA_NARRATIVE_RE.match(t):
        return "author_year"
    if CHICAGO_RE.match(t):
        return "note"
    
    return "unknown"

async def detect_citation_style_stub(pdf_or_tei_bytes: bytes, filename: Optional[str] = None) -> Tuple[str, float, Dict[str, List[str]]]:
    """Detect overall document citation style from TEI/PDF content"""
    try:
        text = pdf_or_tei_bytes.decode("utf-8", errors="ignore")
    except:
        text = pdf_or_tei_bytes.decode("latin-1", errors="ignore")

    # Extract citation candidates
    candidates = _extract_citation_candidates(text)
    
    # Count each style
    ieee_count = sum(1 for c in candidates if IEEE_RE.search(c))
    apa_count = sum(1 for c in candidates if APA_PAREN_RE.search(c) or APA_NARRATIVE_RE.search(c))
    note_count = sum(1 for c in candidates if CHICAGO_RE.search(c))
    
    total = max(1, ieee_count + apa_count + note_count)
    
    # Determine dominant style
    if ieee_count >= max(apa_count, note_count) and ieee_count >= 3:
        return "IEEE", min(1.0, 0.5 + ieee_count/total), {"counts": [f"ieee={ieee_count}"]}
    if apa_count >= max(ieee_count, note_count) and apa_count >= 3:
        return "APA", min(1.0, 0.5 + apa_count/total), {"counts": [f"apa={apa_count}"]}
    if note_count >= 3:
        return "Chicago-Notes", min(1.0, 0.5 + note_count/total), {"counts": [f"notes={note_count}"]}
    
    # Fallback for small counts
    if ieee_count > 0 and ieee_count >= max(apa_count, note_count):
        return "IEEE", 0.6, {"counts": [f"ieee={ieee_count}"]}
    if apa_count > 0:
        return "APA", 0.6, {"counts": [f"apa={apa_count}"]}
    if note_count > 0:
        return "Chicago-Notes", 0.55, {"counts": [f"notes={note_count}"]}
    
    return "Unknown", 0.3, {"counts": ["none"]}

def _extract_citation_candidates(text: str) -> List[str]:
    """Extract potential citation patterns from text"""
    candidates = []
    
    # Try TEI parsing first
    try:
        root = etree.fromstring(text.encode("utf-8"))
        refs = root.findall(".//tei:ref[@type='bibr']", namespaces=NS)
        candidates = ["".join(r.itertext()).strip() for r in refs if r.text]
    except:
        pass
    
    # Fallback: regex search on full text
    if not candidates:
        candidates.extend(re.findall(r"\[[^\]]{1,50}\]", text))
        candidates.extend([m.group(0) for m in APA_PAREN_RE.finditer(text)])
        candidates.extend([m.group(0) for m in APA_NARRATIVE_RE.finditer(text)])
        candidates.extend([m.group(0) for m in CHICAGO_RE.finditer(text)])
    
    return list(dict.fromkeys([c.strip() for c in candidates if c.strip()]))

# ===================== Backward Compatibility Functions =====================

def is_ieee(text: str) -> bool:
    """Check if text is IEEE format"""
    return bool(IEEE_RE.match(text.strip()))

def is_apa_in_paren(text: str) -> bool:
    """Check if text is APA in-paren format"""
    return bool(APA_PAREN_RE.match(text.strip()))

def is_apa_narrative(text: str) -> bool:
    """Check if text is APA narrative format"""
    return bool(APA_NARRATIVE_RE.match(text.strip()))

def is_chicago_note(text: str) -> bool:
    """Check if text is Chicago note format"""
    return bool(CHICAGO_RE.match(text.strip()))

def is_numeric_value_in_parens(text: str) -> bool:
    """Check if text is numeric value in parens"""
    return bool(NUMERIC_VALUE_RE.match(text.strip()))