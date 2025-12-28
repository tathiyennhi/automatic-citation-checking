# APA_style_v2.py — TEI-aware Task 1a (NEW sentence splitting logic)
# Uses improved_sentence_split instead of raw NLTK

import os
import re
import json
import requests
from typing import List, Dict, Tuple, Any, Optional
from xml.etree import ElementTree as ET

# NEW: Import improved sentence splitter
from sentence_utils import improved_sentence_split

TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


# ---------- helpers (regex chỉ để dọn khoảng trắng/dấu câu) ----------
def clean_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def safe_sent_tokenize(text: str) -> List[str]:
    """NEW: Use improved sentence splitter"""
    text = clean_ws(text)
    if not text:
        return []
    return improved_sentence_split(text)

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
class PDFToPipelineProcessorAPA_V2:
    """
    Pipeline V2 with improved sentence splitting
    """
    def __init__(
        self,
        sentences_per_file: int = 5,
        grobid_url: str = "http://localhost:8070",
        mask_strategy: str = "keep"
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

    def build_paragraph_text_with_placeholders(self, runs: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        parts = []
        refs_meta = []
        for r in runs:
            if r["type"] == "text":
                parts.append(r["text"])
            else:
                idx = len(refs_meta)
                parts.append(f"§REF{idx}§")
                refs_meta.append({"idx": idx, "text": r.get("text", ""), "target": r.get("target", "")})
        return " ".join(parts), refs_meta

    def detect_citation_sentences(self, sentences_with_placeholders: List[Tuple[str, List[Dict[str, Any]]]]) -> List[str]:
        citation_sents = []
        for sent_with_refs, refs_meta in sentences_with_placeholders:
            if re.search(r'§REF\d+§', sent_with_refs):
                final_sent = replace_placeholders(sent_with_refs, refs_meta, self.mask_strategy)
                citation_sents.append(final_sent)
        return citation_sents

    def create_chunks(self, all_sentences: List[str], correct_citations: List[str]) -> List[Dict]:
        chunks = []
        buf = []
        for s in all_sentences:
            buf.append(s)
            if len(buf) >= self.sentences_per_file:
                chunk_cits = [x for x in buf if x in correct_citations]
                chunks.append({"texts": buf, "correct_citations": chunk_cits})
                buf = []
        if buf:
            chunk_cits = [x for x in buf if x in correct_citations]
            chunks.append({"texts": buf, "correct_citations": chunk_cits})
        return chunks

    @staticmethod
    def create_in_file(texts: List[str], idx: int, outdir: str):
        path = os.path.join(outdir, f"{idx:03d}.in")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"texts": texts}, f, ensure_ascii=False, indent=2)

    @staticmethod
    def create_label_file(texts: List[str], correct_citations: List[str], idx: int, outdir: str):
        path = os.path.join(outdir, f"{idx:03d}.label")
        style_value = "APA" if correct_citations else ""
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "style": style_value,
                "texts": texts,
                "correct_citations": correct_citations
            }, f, ensure_ascii=False, indent=2)

    # --- run ---
    def process_pdf(self, pdf_path: str, output_dir: str = "output"):
        print(f"[APA-TEI-V2] Processing PDF: {pdf_path}")
        os.makedirs(output_dir, exist_ok=True)

        print("[APA-TEI-V2] Calling Grobid...")
        tei_xml = self.process_pdf_with_grobid(pdf_path)
        root = ET.fromstring(tei_xml)

        print("[APA-TEI-V2] Detecting (by TEI <ref>) with IMPROVED sentence split...")
        all_paragraphs_runs = [self.paragraph_to_runs(p) for p in self.iter_body_paragraphs(root)]

        sentences_with_placeholders = []
        for runs in all_paragraphs_runs:
            para_text_with_ph, refs = self.build_paragraph_text_with_placeholders(runs)
            # NEW: Use improved sentence splitter
            sents = safe_sent_tokenize(para_text_with_ph)
            for s in sents:
                sentences_with_placeholders.append((s, refs))

        citation_sents = self.detect_citation_sentences(sentences_with_placeholders)

        all_sentences = []
        for sent_with_refs, refs_meta in sentences_with_placeholders:
            final_sent = replace_placeholders(sent_with_refs, refs_meta, self.mask_strategy)
            all_sentences.append(final_sent)

        print(f"[APA-TEI-V2] Sentences(raw): {len(all_sentences)} | Citation sentences(raw): {len(citation_sents)}")

        print(f"[APA-TEI-V2] Masking with mode = {self.mask_strategy}")
        print("[APA-TEI-V2] Creating chunks...")
        chunks = self.create_chunks(all_sentences, citation_sents)
        print(f"[APA-TEI-V2] Chunks: {len(chunks)}")

        print("[APA-TEI-V2] Writing files...")
        for i, chunk in enumerate(chunks):
            self.create_in_file(chunk["texts"], i, output_dir)
            self.create_label_file(chunk["texts"], chunk["correct_citations"], i, output_dir)

        total_sentences = sum(len(c["texts"]) for c in chunks)
        total_citations = len(citation_sents)
        print("\n" + "=" * 50)
        print("APA-TEI-V2 GENERATION SUMMARY (improved split)")
        print("=" * 50)
        print(f"Total files generated: {len(chunks)}")
        print(f"Total sentences processed: {total_sentences}")
        print(f"Total citation sentences: {total_citations}")
        if len(chunks) > 0:
            print(f"Average sentences/file: {total_sentences/len(chunks):.1f}")
            if total_sentences > 0:
                print(f"Citation percentage: {(total_citations/total_sentences)*100:.1f}%")
        print(f"Output dir: {output_dir}/")


def run(pdf_path: str, output_dir: str, sentences_per_file: int, grobid_url: str):
    processor = PDFToPipelineProcessorAPA_V2(
        sentences_per_file=sentences_per_file,
        grobid_url=grobid_url,
        mask_strategy="keep"
    )
    processor.process_pdf(pdf_path, output_dir)
