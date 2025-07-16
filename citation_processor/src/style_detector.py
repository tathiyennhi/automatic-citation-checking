import re

class StyleDetector:
    def __init__(self):
        pass

    def detect_style(self, text: str) -> str:
        """
        Phát hiện style của bài báo dựa trên một số regex heuristics.
        Ưu tiên kiểm tra kiểu APA với pattern linh hoạt (cho cả nhiều citation trong 1 dấu ngoặc đơn).
        """
        # APA: ví dụ: (Kassirer & Angell, 1991, p. 1511) hoặc (Giles & Councill, 2004; Paul-Hus et al., 2017)
        apa_pattern = r"\([A-Za-z][A-Za-z\s,&-]+,\s*\d{4}[a-z]?(,\s*p\.?\s*\d+)?(;\s*[A-Za-z][A-Za-z\s,&-]+,\s*\d{4}[a-z]?)*\)"
        if re.search(apa_pattern, text):
            return "apa"

        # IEEE: có dạng [1], [1, 2] hoặc [1-4]
        if re.search(r"\[\d+(,\s*\d+)*(\s*-\s*\d+)?\]", text):
            return "ieee"

        # Chicago: dạng "Smith (2020)" hoặc "Smith (2020, p. 12)"
        if re.search(r"[A-Z][a-z]+\s*\(\d{4}(,\s*p\.?\s*\d+)?\)", text):
            return "chicago"

        # Harvard: dạng "(Smith 2020)"
        if re.search(r"\([A-Za-z][A-Za-z\s,&-]+\s+\d{4}(,\s*p\.?\s*\d+)?\)", text):
            return "harvard"

        return "unknown"
