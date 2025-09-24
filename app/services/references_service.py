from typing import Dict, Any, List
from lxml import etree  # pip install lxml

NS = {"tei": "http://www.tei-c.org/ns/1.0"}

def list_references_from_tei(tei_xml: str) -> Dict[str, Any]:
    """
    Parse TEI và trả ra danh sách references (biblStruct trong listBibl).
    Trích các field cơ bản + chuỗi display gọn.
    """
    root = etree.fromstring(tei_xml.encode("utf-8"))
    bibl_elems = root.findall(".//tei:listBibl/tei:biblStruct", namespaces=NS)

    refs: List[Dict[str, Any]] = []
    for i, b in enumerate(bibl_elems, start=1):
        # title ưu tiên analytic trước, nếu không có thì lấy từ monogr
        title = b.find(".//tei:analytic/tei:title", namespaces=NS)
        if title is None:
            title = b.find(".//tei:monogr/tei:title", namespaces=NS)

        surname = b.find(".//tei:author/tei:persName/tei:surname", namespaces=NS)
        forename = b.find(".//tei:author/tei:persName/tei:forename", namespaces=NS)
        date = b.find(".//tei:date", namespaces=NS)
        venue = b.find(".//tei:monogr/tei:title", namespaces=NS)

        author = None
        if surname is not None:
            author = surname.text
            if forename is not None and forename.text:
                author = f"{surname.text} {forename.text[0]}."

        year = date.get("when") if date is not None else None
        title_txt = title.text if title is not None else None
        venue_txt = venue.text if venue is not None else None

        display = " • ".join([x for x in [f"[{i}]", author, year, title_txt, venue_txt] if x])

        refs.append({
            "index": i,
            "author": author,
            "year": year,
            "title": title_txt,
            "venue": venue_txt,
            "display": display
        })

    return {"count": len(refs), "references": refs}
