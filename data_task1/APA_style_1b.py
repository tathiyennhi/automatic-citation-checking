# APA_style_1b.py — TEI-aware Task 1b (no regex for DETECT)
# Goal (each sentence -> 1 .in/.label pair):
# - text: original sentence (restore verbatim <ref>...)
# - text_norm: replace EACH <ref> with [CITATION_i] (numbered by order of appearance in SENTENCE)
# - mask: LIST of adjacent <ref> groups (verbatim, keep brackets, semicolons, spaces between refs)
# - citation_references: each <ref> = 1 mention:
#       {"reference_text": "...", "citation_marker": "[CITATION_i]"}
#   reference_text: inner text of <ref> with brackets/semicolon/comma cleaned from start/end IF ref belongs to multi-item group

import os
import re
import json
import requests
from typing import List, Dict, Any, Tuple, Optional
from xml.etree import ElementTree as ET

TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}
# Delimiter characters between refs in 1 group: only spaces, semicolons or commas
DELIMS = set(" \t\r\n;,")  # DO NOT remove brackets here -> so mask preserves brackets

# ---------------- Helpers ----------------
def clean_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def strip_paren_semicolon(s: str) -> str:
    """
    Normalize 1 citation item (inner text of <ref>):
    - Remove all opening/closing brackets at START or END: ( ) [ ]
    - Remove ; , and extra spaces at START/END
    Examples:
      "(Araoz, 2020"           -> "Araoz, 2020"
      "OpenAI, 2023;"          -> "OpenAI, 2023"
      "Xiao et al., 2023)"     -> "Xiao et al., 2023"
      "[Smith, 2021, pp. 3-5]" -> "Smith, 2021, pp. 3-5"
    """
    t = (s or "").strip()
    t = re.sub(r'^[\s\(\)\[\];,]+', '', t)   # start of string
    t = re.sub(r'[\s\(\)\[\];,]+$', '', t)   # end of string
    return t

def only_delims(s: str) -> bool:
    return all(ch in DELIMS for ch in s)

# Restore placeholders §REFi§ -> inner_text
def restore_placeholders(text_with_placeholders: str, idx2text: Dict[int, str]) -> str:
    def repl(m):
        i = int(m.group(1))
        return idx2text.get(i, '')
    return re.sub(r'§REF(\d+)§', repl, text_with_placeholders)

# Replace placeholders §REFi§ -> markers [CITATION_k] (k = order in SENTENCE)
def replace_placeholders_with_markers(text_with_placeholders: str) -> Tuple[str, List[Tuple[int, int, str]]]:
    """
    Returns:
      - text_norm: string after replacing each §REFi§ with [CITATION_k]
      - spans: list of (start, end, original_placeholder) MEASURED ON ORIGINAL SENTENCE STRING (before replacement),
               to accurately group/mask by old positions.
    """
    spans = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r'§REF(\d+)§', text_with_placeholders)]
    out_parts = []
    cursor = 0
    local_idx = 0
    for start, end, _ in spans:
        out_parts.append(text_with_placeholders[cursor:start])
        local_idx += 1
        out_parts.append(f"[CITATION_{local_idx}]")
        cursor = end
    out_parts.append(text_with_placeholders[cursor:])
    return "".join(out_parts), spans

# ---------------- Core (TEI-first) ----------------
class APA1B:
    def __init__(self, grobid_url: str = "http://localhost:8070", output_dir: str = "task1b_output"):
        self.grobid_url = grobid_url
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ====== GROBID ======
    def process_pdf_with_grobid(self, pdf_path: str) -> str:
        url = f"{self.grobid_url}/api/processFulltextDocument"
        with open(pdf_path, 'rb') as f:
            r = requests.post(url, files={'input': f}, timeout=180)
        if r.status_code != 200:
            raise RuntimeError(f"Grobid error: {r.status_code} - {r.text[:500]}")
        return r.text

    # ====== TEI parsing ======
    def iter_body_units(self, tei_root: ET.Element):
        """
        Prefer sentence <s> nodes if available. If no <s>, fallback to <p>.
        Returns iterator of TEI elements (each element = 1 "sentence" to build .label).
        """
        # Try to get sentence <s>
        s_nodes = tei_root.findall('.//tei:text/tei:body//tei:p//tei:s', TEI_NS)
        if s_nodes:
            for s in s_nodes:
                yield s
            return
        # No <s> -> use <p>
        for p in tei_root.findall('.//tei:text/tei:body//tei:p', TEI_NS):
            yield p

    @staticmethod
    def _is_bibl_ref(el: ET.Element) -> bool:
        if el is None:
            return False
        if el.tag.endswith('ref'):
            if el.get('type') == 'bibr':
                return True
            tgt = el.get('target') or ""
            return tgt.startswith('#b')
        return False

    def node_to_runs(self, node: ET.Element) -> List[Dict[str, Any]]:
        """
        Convert 1 node (can be <s> or <p>) into sequential runs [text/ref].
        DO NOT split sentences again — rely on TEI structure.
        """
        runs: List[Dict[str, Any]] = []

        def push_text(txt: Optional[str]):
            t = clean_ws(txt or "")
            if t:
                runs.append({"type": "text", "text": t})

        def walk(n: ET.Element):
            if n.text:
                push_text(n.text)
            for child in list(n):
                tag = child.tag.split('}', 1)[1] if '}' in child.tag else child.tag
                if tag == 'ref' and self._is_bibl_ref(child):
                    inner_text = clean_ws(''.join(child.itertext()))
                    runs.append({
                        "type": "ref",
                        "target": child.get('target'),
                        "text": inner_text
                    })
                else:
                    walk(child)
                if child.tail:
                    push_text(child.tail)

        walk(node)
        return runs

    def runs_to_string_with_placeholders(
        self, runs: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[int, Dict[str, Any]]]:
        """
        Returns:
          - text_with_ph: string with §REFi§ replacing each <ref> IN ORDER within the node
          - idx2meta: map i -> {"text": inner_text, "target": target}
        """
        parts: List[str] = []
        idx2meta: Dict[int, Dict[str, Any]] = {}
        ref_count = 0
        for r in runs:
            if r["type"] == "text":
                parts.append(r["text"])
            else:
                ref_count += 1
                parts.append(f"§REF{ref_count}§")
                idx2meta[ref_count] = {
                    "text": r.get("text", ""),
                    "target": r.get("target")
                }
        return clean_ws(' '.join(parts)), idx2meta

    # ====== Build 1b objects per "sentence-like" unit ======
    def build_1b_from_sentence(self, sent_with_ph: str, idx2meta: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        # 1) text_norm + placeholder spans on ORIGINAL STRING
        text_norm, spans = replace_placeholders_with_markers(sent_with_ph)

        # 2) restore original text (replace §REFi§ -> inner_text)
        text = restore_placeholders(sent_with_ph, {i: idx2meta[i]["text"] for i in idx2meta}).strip()

        # 3) group adjacent §REF§ by DELIMS (to determine which ref belongs to group or single)
        groups: List[List[int]] = []
        group_masks: List[str] = []
        if spans:
            cur = [0]
            for i in range(1, len(spans)):
                prev_end = spans[i-1][1]
                next_start = spans[i][0]
                middle = sent_with_ph[prev_end:next_start]
                if only_delims(middle):
                    cur.append(i)
                else:
                    groups.append(cur)
                    cur = [i]
            groups.append(cur)

            # verbatim mask for each group (restore inner_text to preserve brackets/separators)
            for g in groups:
                s0 = spans[g[0]][0]
                eN = spans[g[-1]][1]
                slice_with_ph = sent_with_ph[s0:eN]
                def repl_local(m):
                    gi = int(m.group(1))
                    return idx2meta.get(gi, {}).get("text", "")
                mask_str = re.sub(r'§REF(\d+)§', repl_local, slice_with_ph).strip()
                if mask_str:
                    group_masks.append(mask_str)

        # set of indices (zero-based) of refs belonging to groups > 1
        in_multi_group = set()
        for g in groups:
            if len(g) > 1:
                in_multi_group.update(g)

        # 4) build citation_references in order of appearance WITHIN "SENTENCE"
        citation_refs: List[Dict[str, str]] = []
        for local_idx, (_, _, ph) in enumerate(spans, start=1):
            m = re.match(r'§REF(\d+)§', ph)
            if not m:
                continue
            gi = int(m.group(1))
            inner = idx2meta.get(gi, {}).get("text", "").strip()

            # 🔑 ONLY strip brackets/separators when ref BELONGS TO multi-item group
            if (local_idx - 1) in in_multi_group:
                ref_text = strip_paren_semicolon(inner)
            else:
                ref_text = inner  # single -> keep as-is

            citation_refs.append({
                "reference_text": ref_text,
                "citation_marker": f"[CITATION_{local_idx}]"
            })

        # sanity check
        marker_count = len(re.findall(r'\[CITATION_\d+\]', text_norm))
        if marker_count != len(citation_refs):
            raise RuntimeError(
                f"[1b-APA] marker/mentions mismatch: markers={marker_count}, "
                f"mentions={len(citation_refs)}\nSENT: {sent_with_ph}\nNORM: {text_norm}"
            )

        return {
            "style": "APA",
            "text": text,
            "text_norm": text_norm.strip(),
            "mask": group_masks,
            "citation_references": citation_refs
        }

    # ====== Main run ======
    def run_pdf(self, pdf_path: str):
        print(f"[1b-APA] Processing: {pdf_path}")
        tei_xml = self.process_pdf_with_grobid(pdf_path)
        tei_root = ET.fromstring(tei_xml)

        out_idx = 0
        total_mentions = 0

        for node in self.iter_body_units(tei_root):
            runs = self.node_to_runs(node)
            if not runs:
                continue
            sent_with_ph, idx2meta = self.runs_to_string_with_placeholders(runs)
            if not sent_with_ph:
                continue

            # Each node (<s> or <p>) = 1 "sentence" to build .label
            obj = self.build_1b_from_sentence(sent_with_ph, idx2meta)
            self._write_pair(obj, out_idx)
            out_idx += 1
            total_mentions += len(obj["citation_references"])

        print(f"\n✅ Done 1b-APA. Sentences: {out_idx} | Mentions: {total_mentions}")
        print(f"Output dir: {self.output_dir}/")

    # ====== I/O ======
    def _write_pair(self, obj: Dict[str, Any], idx: int):
        in_path = os.path.join(self.output_dir, f"citation_{idx:03d}.in")
        lb_path = os.path.join(self.output_dir, f"citation_{idx:03d}.label")
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump({"text": obj["text"]}, f, ensure_ascii=False, indent=2)
        with open(lb_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

# convenience
def run(pdf_path: str, output_dir: str = "task1b_output", grobid_url: str = "http://localhost:8070"):
    APA1B(grobid_url=grobid_url, output_dir=output_dir).run_pdf(pdf_path)