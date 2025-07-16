import re
import uuid
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Reference:
    id: str
    text: str
    authors: Optional[str] = None
    year: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class ReferenceParser:
    def __init__(self):
        # Pattern cho các định dạng references phổ biến
        self.patterns = {
            # APA style: Author, A. A., & Author, B. B. (Year). Title. Journal, Volume(Issue), Pages.
            'apa': re.compile(
                r"^(?P<authors>.+?)\.\s*\((?P<year>\d{4})\)\.\s*(?P<title>.+?)\.\s*(?P<journal>.+?),\s*(?P<volume>\d+)(?:\((?P<issue>[^)]+)\))?,\s*(?P<pages>\d+-\d+)\.\s*(?P<doi>https?://doi\.org/\S+)?",
                re.DOTALL
            ),
            # IEEE style: A. Author, B. Author, "Title," Journal, vol. X, no. Y, pp. Z-Z, Year.
            'ieee': re.compile(
                r"^(?P<authors>.+?),\s*\"(?P<title>.+?)\",\s*(?P<journal>.+?),\s*vol\.\s*(?P<volume>\d+),\s*no\.\s*(?P<issue>[^,]+),\s*pp\.\s*(?P<pages>\d+-\d+),\s*(?P<year>\d{4})",
                re.DOTALL
            ),
            # Chicago style: Author, A. A., and B. B. Author. Year. "Title." Journal Volume(Issue): Pages.
            'chicago': re.compile(
                r"^(?P<authors>.+?)\.\s*(?P<year>\d{4})\.\s*\"(?P<title>.+?)\"\.\s*(?P<journal>.+?)\s*(?P<volume>\d+)(?:\((?P<issue>[^)]+)\))?:\s*(?P<pages>\d+-\d+)",
                re.DOTALL
            )
        }
        # Pattern cho DOI và URL
        self.doi_pattern = re.compile(r"(https?://doi\.org/\S+|doi:\s*\S+)", re.IGNORECASE)
        self.url_pattern = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)")
        # Pattern cho publisher và location
        self.publisher_pattern = re.compile(r"(?:Published by|Publisher:|)(?P<publisher>[^,]+)(?:,|\.)")
        self.location_pattern = re.compile(r"(?P<city>[^,]+),\s*(?P<country>[^,]+)(?:,|\.)")

    def parse_reference_line(self, line: str) -> Reference:
        ref = Reference(id="ref_" + uuid.uuid4().hex[:8], text=line)
        
        # Thử parse với từng pattern
        for style, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                # Parse các trường cơ bản
                ref.authors = match.group("authors").strip()
                ref.year = match.group("year").strip()
                ref.title = match.group("title").strip()
                ref.journal = match.group("journal").strip()
                ref.volume = match.group("volume").strip()
                if "issue" in match.groupdict():
                    ref.issue = match.group("issue").strip()
                if "pages" in match.groupdict():
                    ref.pages = match.group("pages").strip()
                break

        # Parse DOI
        doi_match = self.doi_pattern.search(line)
        if doi_match:
            ref.doi = doi_match.group(0).strip().replace(" ", "")

        # Parse URL
        url_match = self.url_pattern.search(line)
        if url_match:
            ref.url = url_match.group(0).strip()

        # Parse publisher và location
        publisher_match = self.publisher_pattern.search(line)
        if publisher_match:
            ref.publisher = publisher_match.group("publisher").strip()

        location_match = self.location_pattern.search(line)
        if location_match:
            ref.city = location_match.group("city").strip()
            ref.country = location_match.group("country").strip()

        return ref

    def parse_references(self, text: str) -> List[Reference]:
        # Tìm phần References
        ref_section = ""
        m = re.search(r"(References|REFERENCES|Bibliography|BIBLIOGRAPHY)(.*)", text, re.DOTALL)
        if m:
            ref_section = m.group(2)
        else:
            return []

        # Tách thành các dòng và lọc
        lines = ref_section.split("\n")
        ref_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
        
        # Parse từng reference
        references = []
        for line in ref_lines:
            ref = self.parse_reference_line(line)
            references.append(ref)
        return references
