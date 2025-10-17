import json
import re
import os
from typing import List, Dict, Any, Tuple, Optional

class CitationExtractionPipeline:
    """
    Task 1b: Extract citations in APA (author–year) and IEEE (numeric).
    ALWAYS split one grouped citation into multiple mentions (mention-level),
    and output the exact schema:
    {
      "style": "APA" | "IEEE",
      "text": ...,
      "text_norm": ...,
      "mask": ...,
      "citation_references": [
        {"reference_text": "...", "citation_marker": "[CITATION_i]"},
        ...
      ]
    }
    """

    # ===== Regex =====
    # APA: multi-item parenthetical groups, e.g., (Luan et al., 2017; Groth et al., 2018; ...)
    APA_GROUP = re.compile(
        r'\('
        r'[A-Z][A-Za-z\-\.\s&]+?,?\s*\d{4}(?:\s*[a-z])?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?'
        r'(?:;\s*[A-Z][A-Za-z\-\.\s&]+?,?\s*\d{4}(?:\s*[a-z])?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?)*'
        r'\)'
    )
    # APA inline: "Author et al. (2020)", "Author & Author (2020)", "Author (2020)", "(Author, 2020)"
    APA_INLINE = [
        re.compile(r'\b[A-Z][A-Za-z\-\']+\s+et\s+al\.\s*\(\d{4}[a-z]?\)'),
        re.compile(r'\b[A-Z][A-Za-z\-\']+\s+(?:and|&)\s+[A-Z][A-Za-z\-\']+\s*\(\d{4}[a-z]?\)'),
        re.compile(r'\b[A-Z][A-Za-z\-\']+\s*\(\d{4}[a-z]?\)'),
        re.compile(r'\([A-Z][A-Za-z\-\']+,?\s*\d{4}[a-z]?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?\)')
    ]

    # IEEE numeric: [1], [1, 3], [1-3], [1–3], (2), (2,4–6)
    IEEE_GROUPS = [
        re.compile(r'\[\s*\d+(?:\s*(?:,|-|–)\s*\d+)*\s*\]'),
        re.compile(r'\(\s*\d+(?:\s*(?:,|-|–)\s*\d+)*\s*\)')
    ]

    # ========= Public API =========
    def process_directory(self, input_dir: str, output_dir: str = "task1b_output"):
        """
        Read all .label files (Task 1a output) containing "correct_citations": [sentences],
        and (optionally) "style": "APA" | "IEEE".
        Produce .in / .label pairs for Task 1b with the minimal required structure.
        """
        print(f"Processing directory: {input_dir}")
        os.makedirs(output_dir, exist_ok=True)

        total_sent = 0
        total_mentions = 0

        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith(".label"):
                continue
            path = os.path.join(input_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[Skip] {filename}: {e}")
                continue

            sentences = data.get("correct_citations", [])
            if not sentences:
                continue

            forced_style = data.get("style")  # "APA" | "IEEE" if the batch is style-forced
            s_count, m_count = self._process_file(sentences, forced_style, output_dir, total_sent)
            total_sent += s_count
            total_mentions += m_count

        print("\n✅ Task 1b done")
        print(f"- Sentences processed: {total_sent}")
        print(f"- Mentions extracted: {total_mentions}")
        print(f"- Output dir: {output_dir}/")

    # ========= Core per-file =========
    def _process_file(
        self,
        sentences: List[str],
        forced_style: Optional[str],
        out_dir: str,
        start_idx: int
    ) -> Tuple[int, int]:
        processed = 0
        mentions = 0

        for sent in sentences:
            obj = self.extract(sent, forced_style=forced_style)
            if obj["citation_references"]:
                idx = start_idx + processed
                self._write_in(sent, idx, out_dir)
                self._write_label(obj, idx, out_dir)
                processed += 1
                mentions += len(obj["citation_references"])

        return processed, mentions

    # ========= Extraction =========
    def extract(self, text: str, forced_style: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract with a forced style (if provided), otherwise auto-detect.
        Always split a grouped citation into multiple mentions.
        Return exactly 5 fields.
        """
        style = forced_style or self._auto_detect_style(text)
        if style == "IEEE":
            return self._extract_ieee(text)
        # default APA
        return self._extract_apa(text)

    def _auto_detect_style(self, text: str) -> str:
        # Prefer IEEE if numeric markers are detected
        for pat in self.IEEE_GROUPS:
            if pat.search(text):
                return "IEEE"
        # If APA patterns are present, choose APA
        if self.APA_GROUP.search(text):
            return "APA"
        for pat in self.APA_INLINE:
            if pat.search(text):
                return "APA"
        # Default to APA (safer for academic prose)
        return "APA"

    # ----- APA -----
    def _extract_apa(self, text: str) -> Dict[str, Any]:
        matches, occupied = [], []

        # Prioritize parenthetical groups
        for m in self.APA_GROUP.finditer(text):
            s, e = m.span()
            if self._overlap(s, e, occupied):
                continue
            matches.append(("paren", s, e, m.group(0)))
            occupied.append((s, e))

        # Then inline patterns
        for pat in self.APA_INLINE:
            for m in pat.finditer(text):
                s, e = m.span()
                if self._overlap(s, e, occupied):
                    continue
                matches.append(("inline", s, e, m.group(0)))
                occupied.append((s, e))

        matches.sort(key=lambda x: x[1])

        all_items: List[str] = []
        refs: List[Dict[str, str]] = []
        parts: List[str] = []
        last = 0
        counter = 0

        for kind, s, e, raw in matches:
            parts.append(text[last:s])
            items = self._split_apa_items(raw, kind)
            all_items.extend(items)

            markers = []
            for it in items:
                counter += 1
                mk = f"[CITATION_{counter}]"
                markers.append(mk)
                refs.append({"reference_text": it.strip(), "citation_marker": mk})

            parts.append(", ".join(markers))
            last = e

        parts.append(text[last:])
        text_norm = "".join(parts)

        # === APA mask formatting ===
        # Nếu có ít nhất 1 match là "paren" → dùng ngoặc tròn; nếu chỉ inline → không ngoặc.
        had_paren = any(k == "paren" for k, _, _, _ in matches)
        if all_items:
            mask = f"({'; '.join(all_items)})" if had_paren else "; ".join(all_items)
        else:
            mask = ""

        return {
            "style": "APA",
            "text": text,
            "text_norm": text_norm,
            "mask": mask,
            "citation_references": refs
        }

    def _split_apa_items(self, raw: str, kind: str) -> List[str]:
        if kind == "paren":
            inner = self._strip_outer(raw)
            parts = [p.strip() for p in inner.split(";") if p.strip()]
            out = []
            for p in parts:
                # keep only items that contain a year token
                if re.search(r'\b\d{4}(?:\s*[a-z])?\b', p):
                    out.append(p)
            return out if out else [inner]
        # inline: normalize "Author … (YYYY)" → "Author …, YYYY"
        m = re.search(r'^(?P<auth>.+?)\s*\(\s*(?P<year>\d{4}\s*[a-z]?)\s*\)\s*$', raw.strip())
        if m:
            auth = re.sub(r'\s+', ' ', m.group("auth").strip())
            year = re.sub(r'\s+', ' ', m.group("year").strip())
            return [f"{auth}, {year}"]
        return [raw.strip()]

    # ----- IEEE -----
    def _extract_ieee(self, text: str) -> Dict[str, Any]:
        matches, occupied = [], []
        for pat in self.IEEE_GROUPS:
            for m in pat.finditer(text):
                s, e = m.span()
                if self._overlap(s, e, occupied):
                    continue
                matches.append((s, e, m.group(0)))
                occupied.append((s, e))
        matches.sort(key=lambda x: x[0])

        all_items: List[str] = []
        refs: List[Dict[str, str]] = []
        parts: List[str] = []
        last = 0
        counter = 0

        for s, e, raw in matches:
            parts.append(text[last:s])
            nums = self._split_ieee_numbers(raw)
            all_items.extend(nums)

            markers = []
            for n in nums:
                counter += 1
                mk = f"[CITATION_{counter}]"
                markers.append(mk)
                refs.append({"reference_text": n, "citation_marker": mk})

            parts.append(", ".join(markers))
            last = e

        parts.append(text[last:])
        text_norm = "".join(parts)

        # === IEEE mask formatting ===
        mask = f"[{', '.join(all_items)}]" if all_items else "[]"

        return {
            "style": "IEEE",
            "text": text,
            "text_norm": text_norm,
            "mask": mask,
            "citation_references": refs
        }

    def _split_ieee_numbers(self, raw: str) -> List[str]:
        inner = self._strip_outer(raw)
        # Example: "1, 3, 5–7" → split by commas
        tokens = [t.strip() for t in inner.split(",") if t.strip()]
        out: List[str] = []
        for tok in tokens:
            t = tok.replace(" ", "")
            # range: 5-7 or 5–7
            m = re.match(r'^(\d+)[\-–](\d+)$', t)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                if a <= b:
                    out.extend([str(i) for i in range(a, b + 1)])
                else:
                    out.extend([str(i) for i in range(b, a + 1)])
            elif re.match(r'^\d+$', t):
                out.append(t)
            else:
                # Fallback: if token contains unexpected characters, keep it as-is
                out.append(tok)
        return out if out else [inner]

    # ===== Helpers =====
    @staticmethod
    def _overlap(s: int, e: int, taken: List[Tuple[int, int]]) -> bool:
        return any(not (e <= s2 or s >= e2) for s2, e2 in taken)

    @staticmethod
    def _strip_outer(s: str) -> str:
        s = s.strip()
        if (s.startswith("(") and s.endswith(")")) or (s.startswith("[") and s.endswith("]")):
            return s[1:-1].strip()
        return s

    # ===== I/O =====
    @staticmethod
    def _write_in(text: str, idx: int, out_dir: str):
        path = os.path.join(out_dir, f"citation_{idx:03d}.in")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"text": text}, f, ensure_ascii=False, indent=2)
    @staticmethod
    def _write_label(obj: Dict[str, Any], idx: int, out_dir: str):
        path = os.path.join(out_dir, f"citation_{idx:03d}.label")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)



def main():
    input_dir = "output"          # .label directory from Task 1a
    output_dir = "task1b_output"  # output directory for Task 1b

    if not os.path.exists(input_dir):
        print(f"Input directory '{input_dir}' not found! Run Task 1a first.")
        return

    CitationExtractionPipeline().process_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()
