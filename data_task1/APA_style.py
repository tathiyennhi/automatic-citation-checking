# APA_style.py — TEI-aware Task 1a (detect by TEI <ref>, keep original citation text)
# Không dùng regex để DETECT; chỉ dùng cho cleanup khoảng trắng/dấu câu sau khi thay thế placeholder.

import os
import re
import json
import requests
from typing import List, Dict, Tuple, Any, Optional
from xml.etree import ElementTree as ET

import nltk
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


# ---------- helpers (regex chỉ để dọn khoảng trắng/dấu câu) ----------
def clean_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def safe_sent_tokenize(text: str) -> List[str]:
    text = clean_ws(text)
    if not text:
        return []
    return [s.strip() for s in sent_tokenize(text) if len(s.strip()) > 0]

def replace_placeholders(
    sent_with_refs: str,
    refs_meta: List[Dict[str, Any]],
    mode: str = "keep"  # "keep" | "marker" | "remove"
) -> str:
    """
    Thay §REFi§ bằng:
      - keep   : inner text của <ref> (giữ nguyên dạng GROBID đưa ra, thường đã có ngoặc)
      - marker : chuỗi "[CITATION]"
      - remove : xóa hẳn
    """
    out = sent_with_refs
    idx2text = {ref["idx"]: clean_ws(ref.get("text", "")) for ref in refs_meta}

    def repl(m):
        i = int(m.group(1))
        if mode == "keep":
            return idx2text.get(i, "")
        elif mode == "marker":
            return "[CITATION]"
        else:
            return ""

    out = re.sub(r'§REF(\d+)§', repl, out)

    # cleanup spacing/punct
    out = re.sub(r'\s+([,.;:!?])', r'\1', out)
    out = re.sub(r'\(\s*\)', '', out)
    out = re.sub(r'\s+\)', ')', out)
    out = re.sub(r'\(\s+', '(', out)
    out = re.sub(r'\s{2,}', ' ', out).strip()
    return out


# ---------- TEI-aware Task 1a ----------
class PDFToPipelineProcessorAPA:
    """
    Pipeline:
      1) GROBID -> TEI
      2) Duyệt <p>, giữ <ref> bibl
      3) Thay <ref> bằng §REFi§ để tách câu an toàn
      4) Detect: câu nào có §REF => citation sentence
      5) Mask (mặc định 'keep') rồi ghi .in/.label
    """
    def __init__(
        self,
        sentences_per_file: int = 5,
        grobid_url: str = "http://localhost:8070",
        mask_strategy: str = "keep"  # GIỮ NGUYÊN citation
    ):
        self.sentences_per_file = sentences_per_file
        self.grobid_url = grobid_url
        assert mask_strategy in ("remove", "marker", "keep")
        self.mask_strategy = mask_strategy

    # --- GROBID ---
    def process_pdf_with_grobid(self, pdf_path: str) -> str:
        url = f"{self.grobid_url}/api/processFulltextDocument"
        with open(pdf_path, 'rb') as f:
            files = {'input': f}
            r = requests.post(url, files=files, timeout=120)
        if r.status_code != 200:
            raise Exception(f"Grobid error: {r.status_code} - {r.text[:500]}")
        return r.text

    # --- TEI parsing ---
    def iter_body_paragraphs(self, tei_root: ET.Element):
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

    def paragraph_to_runs(self, p: ET.Element) -> List[Dict[str, Any]]:
        runs: List[Dict[str, Any]] = []

        def push_text(txt: Optional[str]):
            t = clean_ws(txt or "")
            if t:
                runs.append({"type": "text", "text": t})

        def walk(node: ET.Element):
            if node.text:
                push_text(node.text)
            for child in list(node):
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

        walk(p)
        return runs

    def runs_to_string_with_placeholders(
        self, runs: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        parts: List[str] = []
        refs_meta: List[Dict[str, Any]] = []
        ref_count = 0
        for r in runs:
            if r["type"] == "text":
                parts.append(r["text"])
            else:
                ref_count += 1
                parts.append(f"§REF{ref_count}§")
                refs_meta.append({
                    "idx": ref_count,
                    "target": r.get("target"),
                    "text": r.get("text", "")
                })
        return clean_ws(' '.join(parts)), refs_meta

    def split_paragraph_into_sentences_with_refs(self, para_text: str) -> List[str]:
        return safe_sent_tokenize(para_text)

    @staticmethod
    def sentence_has_ref_placeholder(sent: str) -> bool:
        return '§REF' in sent

    def build_sentences_and_citations_raw(
        self, tei_root: ET.Element
    ) -> Tuple[List[str], List[str], List[List[Dict[str, Any]]]]:
        all_sents_raw: List[str] = []
        citation_sents_raw: List[str] = []
        refs_meta_per_sent: List[List[Dict[str, Any]]] = []

        for p in self.iter_body_paragraphs(tei_root):
            runs = self.paragraph_to_runs(p)
            if not runs:
                continue
            para_text, refs_meta = self.runs_to_string_with_placeholders(runs)
            if not para_text:
                continue

            sents = self.split_paragraph_into_sentences_with_refs(para_text)
            if not sents:
                continue

            for s in sents:
                all_sents_raw.append(s)
                refs_meta_per_sent.append(refs_meta)
                if self.sentence_has_ref_placeholder(s):
                    citation_sents_raw.append(s)

        return all_sents_raw, citation_sents_raw, refs_meta_per_sent

    def mask_sentences(
        self,
        sents_raw: List[str],
        refs_meta_per_sent: List[List[Dict[str, Any]]]
    ) -> List[str]:
        return [
            replace_placeholders(s, meta, mode=self.mask_strategy)
            for s, meta in zip(sents_raw, refs_meta_per_sent)
        ]

    def mask_subset(
        self,
        subset_raw: List[str],
        all_sents_raw: List[str],
        refs_meta_per_sent: List[List[Dict[str, Any]]]
    ) -> List[str]:
        out = []
        used = set()
        for s in subset_raw:
            idx = None
            for i, cand in enumerate(all_sents_raw):
                if i in used:
                    continue
                if cand is s or cand == s:
                    idx = i
                    break
            if idx is None:
                idx = all_sents_raw.index(s)
            used.add(idx)
            out.append(replace_placeholders(s, refs_meta_per_sent[idx], mode=self.mask_strategy))
        return out

    # --- chunk & I/O ---
    def create_file_chunks(self, sentences: List[str], correct_citations: List[str]) -> List[Dict]:
        chunks, buf = [], []
        for s in sentences:
            buf.append(s)
            if len(buf) >= self.sentences_per_file:
                chunk_cits = [x for x in buf if x in correct_citations]
                chunks.append({"texts": buf.copy(), "correct_citations": chunk_cits})
                buf = []
        if buf:
            chunk_cits = [x for x in buf if x in correct_citations]
            chunks.append({"texts": buf, "correct_citations": chunk_cits})
        return chunks

    @staticmethod
    def create_in_file(texts: List[str], idx: int, outdir: str):
        path = os.path.join(outdir, f"data_{idx:03d}.in")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"texts": texts}, f, ensure_ascii=False, indent=2)

    @staticmethod
    def create_label_file(texts: List[str], correct_citations: List[str], idx: int, outdir: str):
        path = os.path.join(outdir, f"data_{idx:03d}.label")
        style_value = "APA" if correct_citations else ""
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "style": style_value,
                "texts": texts,
                "correct_citations": correct_citations
            }, f, ensure_ascii=False, indent=2)

    # --- run ---
    def process_pdf(self, pdf_path: str, output_dir: str = "output"):
        print(f"[APA-TEI] Processing PDF: {pdf_path}")
        os.makedirs(output_dir, exist_ok=True)

        print("[APA-TEI] Calling Grobid...")
        try:
            tei_xml = self.process_pdf_with_grobid(pdf_path)
        except Exception as e:
            print(f"❌ Grobid failed: {e}")
            return

        try:
            tei_root = ET.fromstring(tei_xml)
        except ET.ParseError as e:
            print(f"❌ TEI parse error: {e}")
            return

        print("[APA-TEI] Detecting (by TEI <ref>) BEFORE masking...")
        all_raw, cits_raw, refs_meta_per_sent = self.build_sentences_and_citations_raw(tei_root)
        print(f"[APA-TEI] Sentences(raw): {len(all_raw)} | Citation sentences(raw): {len(cits_raw)}")

        print("[APA-TEI] Masking with mode =", self.mask_strategy)
        all_masked = self.mask_sentences(all_raw, refs_meta_per_sent)
        cits_masked = self.mask_subset(cits_raw, all_raw, refs_meta_per_sent)

        print("[APA-TEI] Creating chunks...")
        chunks = self.create_file_chunks(all_masked, cits_masked)
        print(f"[APA-TEI] Chunks: {len(chunks)}")

        print("[APA-TEI] Writing files...")
        for i, ch in enumerate(chunks):
            self.create_in_file(ch["texts"], i, output_dir)
            self.create_label_file(ch["texts"], ch["correct_citations"], i, output_dir)

        self.print_summary(chunks, output_dir, len(cits_masked))

    @staticmethod
    def print_summary(chunks: List[Dict], output_dir: str, total_citations: int):
        print("\n" + "="*50)
        print("APA-TEI GENERATION SUMMARY (keep citations)")
        print("="*50)
        total_sentences = sum(len(ch["texts"]) for ch in chunks)
        print(f"Total files generated: {len(chunks)}")
        print(f"Total sentences processed: {total_sentences}")
        print(f"Total citation sentences: {total_citations}")
        if len(chunks) > 0 and total_sentences > 0:
            print(f"Average sentences/file: {total_sentences/len(chunks):.1f}")
            print(f"Citation percentage: {(total_citations/total_sentences)*100:.1f}%")
        print(f"Output dir: {output_dir}/")


def run(
    pdf_path: str,
    output_dir: str = "output",
    sentences_per_file: int = 5,
    grobid_url: str = "http://localhost:8070",
    mask_strategy: str = "keep"   # GIỮ NGUYÊN citation
):
    proc = PDFToPipelineProcessorAPA(
        sentences_per_file=sentences_per_file,
        grobid_url=grobid_url,
        mask_strategy=mask_strategy
    )
    proc.process_pdf(pdf_path, output_dir)
