import re
from typing import List, Optional
from dataclasses import dataclass
from reference_parser import Reference

@dataclass
class Citation:
    text: str
    start: int
    end: int
    style: str
    quoted_text: Optional[str] = None
    quoted_start: Optional[int] = None
    quoted_end: Optional[int] = None
    reference_id: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[str] = None

class CitationDetector:
    def __init__(self):
        self.citation_patterns = {
            "apa": [
                r"\(([A-Za-z][A-Za-z\s,&-]+),\s*(\d{4}[a-z]?)(,\s*p\.?\s*\d+)?\)",
                r"\(([A-Za-z][A-Za-z\s,&-]+),\s*(\d{4}[a-z]?)(,\s*p\.?\s*\d+)?(;\s*[A-Za-z][A-Za-z\s,&-]+,\s*\d{4}[a-z]?)+\)"
            ],
            "ieee": [
                r"\[(\d+)\]",
                r"\[(\d+(,\s*\d+)+)\]",
                r"\[(\d+\s*-\s*\d+)\]"
            ],
            "chicago": [
                r"([A-Za-z]+)\s*\((\d{4})(,\s*p\.?\s*\d+)?\)",
                r"([A-Za-z]+)\s*\((\d{4}):\s*\d+\)"
            ],
            "harvard": [
                r"\(([A-Za-z][A-Za-z\s,&-]+)\s+(\d{4})(,\s*p\.?\s*\d+)?\)"
            ]
        }

    def extract_authors_year(self, citation_text: str, style: str) -> tuple[Optional[str], Optional[str]]:
        """Trích xuất tác giả và năm từ citation text."""
        if style == "ieee":
            return None, None  # IEEE style không chứa thông tin tác giả và năm trong citation

        # Loại bỏ dấu ngoặc và khoảng trắng thừa
        text = citation_text.strip("()[]")
        
        if style in ["apa", "harvard"]:
            # Pattern cho APA và Harvard: Author, Year hoặc Author Year
            match = re.match(r"([A-Za-z][A-Za-z\s,&-]+)[,]\s*(\d{4})", text)
            if match:
                return match.group(1).strip(), match.group(2)
        
        elif style == "chicago":
            # Pattern cho Chicago: Author Year
            match = re.match(r"([A-Za-z]+)\s*(\d{4})", text)
            if match:
                return match.group(1).strip(), match.group(2)
        
        return None, None

    def find_matching_reference(self, citation: Citation, references: List[Reference]) -> Optional[Reference]:
        """Tìm reference phù hợp với citation dựa trên tác giả và năm."""
        if not citation.authors or not citation.year:
            return None

        # Chuẩn hóa tên tác giả để so sánh
        citation_authors = re.sub(r"[^a-zA-Z\s]", "", citation.authors.lower())
        
        for ref in references:
            if not ref.authors or not ref.year:
                continue
                
            # Chuẩn hóa tên tác giả của reference
            ref_authors = re.sub(r"[^a-zA-Z\s]", "", ref.authors.lower())
            
            # So sánh năm và tên tác giả
            if ref.year == citation.year and citation_authors in ref_authors:
                return ref
                
        return None

    def detect_citations(self, text: str, style: str, references: List[Reference] = None) -> List[Citation]:
        if style not in self.citation_patterns:
            return []
            
        patterns = self.citation_patterns[style]
        citations = []
        
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                citation = Citation(
                    text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    style=style
                )
                
                # Trích xuất tác giả và năm
                authors, year = self.extract_authors_year(citation.text, style)
                citation.authors = authors
                citation.year = year
                
                # Tìm reference phù hợp nếu có danh sách references
                if references:
                    matching_ref = self.find_matching_reference(citation, references)
                    if matching_ref:
                        citation.reference_id = matching_ref.id
                
                citations.append(citation)
                
        citations.sort(key=lambda c: c.start)
        return citations

    def detect_quoted_text(self, text: str, citations: List[Citation], window: int = 50, mode: str = "fixed") -> List[Citation]:
        """Phát hiện đoạn văn được trích dẫn cho mỗi citation."""
        for citation in citations:
            if mode == "fixed":
                # Lấy window ký tự trước và sau citation
                start = max(0, citation.start - window)
                end = min(len(text), citation.end + window)
                citation.quoted_text = text[start:end]
                citation.quoted_start = start
                citation.quoted_end = end
            else:
                # Lấy toàn bộ câu chứa citation
                sentence_start = text.rfind(".", 0, citation.start) + 1
                sentence_end = text.find(".", citation.end) + 1
                if sentence_start == 0:
                    sentence_start = 0
                if sentence_end == 0:
                    sentence_end = len(text)
                citation.quoted_text = text[sentence_start:sentence_end]
                citation.quoted_start = sentence_start
                citation.quoted_end = sentence_end
        return citations
