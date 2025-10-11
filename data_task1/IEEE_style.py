# IEEE_style.py (Grobid version)
import os
import re
import json
import requests
from typing import List, Dict, Tuple
from xml.etree import ElementTree as ET

import nltk
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class PDFToPipelineProcessorIEEE:
    def __init__(self, sentences_per_file: int = 5, grobid_url: str = "http://localhost:8070"):
        self.sentences_per_file = sentences_per_file
        self.grobid_url = grobid_url

    def process_pdf_with_grobid(self, pdf_path: str) -> str:
        """Send PDF to Grobid and get TEI XML back"""
        url = f"{self.grobid_url}/api/processFulltextDocument"
        
        with open(pdf_path, 'rb') as f:
            files = {'input': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Grobid error: {response.status_code} - {response.text}")

    def extract_text_from_grobid_xml(self, xml_content: str) -> str:
        """Extract body text from Grobid TEI XML with proper spacing"""
        root = ET.fromstring(xml_content)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        
        body = root.find('.//tei:text/tei:body', ns)
        if body is None:
            return ""
        
        # Convert to string và fix spacing
        xml_str = ET.tostring(body, encoding='unicode')
        
        # Thêm space giữa các closing/opening tags
        xml_str = re.sub(r'</ref><ref', r'</ref> <ref', xml_str)
        xml_str = re.sub(r'</head><p', r'</head> <p', xml_str)
        xml_str = re.sub(r'</p><p', r'</p> <p', xml_str)
        
        # Parse lại và extract
        body_fixed = ET.fromstring(xml_str)
        text = ''.join(body_fixed.itertext())
        
        # Fix spacing issues
        text = re.sub(r'\s+([.,;:!?)\]])', r'\1', text)
        text = re.sub(r';([A-Z])', r'; \1', text)
        text = re.sub(r'(\d{4})([A-Z])', r'\1 \2', text)
        
        # Fix double punctuation (Grobid errors)
        text = re.sub(r';;+', ';', text)
        text = re.sub(r',,+', ',', text)
        text = re.sub(r',\s*,', ',', text)
        
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()


    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK"""
        text = re.sub(r'\s+', ' ', text).strip()
        sents = sent_tokenize(text)
        return [s.strip() for s in sents if len(s.strip()) > 10 and not s.strip().isdigit()]

    def detect_numeric_citations(self, sentences: List[str]) -> Tuple[List[str], List[str]]:
        """Detect IEEE/Numeric citations: [1], [2,3], [4-6], etc."""
        correct_citations = []
        rx = re.compile(r'\[\s*\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*\s*\]')
        
        for s in sentences:
            if rx.search(s):
                correct_citations.append(s)
        
        return sentences, correct_citations

    def create_file_chunks(self, sentences: List[str], correct_citations: List[str]) -> List[Dict]:
        chunks = []
        buf = []
        
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

    def create_in_file(self, texts: List[str], idx: int, outdir: str):
        path = os.path.join(outdir, f"data_{idx:03d}.in")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"texts": texts}, f, ensure_ascii=False, indent=2)

    def create_label_file(self, texts: List[str], correct_citations: List[str], idx: int, outdir: str):
        path = os.path.join(outdir, f"data_{idx:03d}.label")
        with open(path, "w", encoding="utf-8") as f:
            style_value = "IEEE" if correct_citations else ""
            json.dump({
                "style": style_value,
                "texts": texts, 
                "correct_citations": correct_citations
            }, f, ensure_ascii=False, indent=2)

    def process_pdf(self, pdf_path: str, output_dir: str = "output"):
        print(f"[IEEE-Grobid] Processing PDF: {pdf_path}")
        os.makedirs(output_dir, exist_ok=True)

        print("[IEEE-Grobid] Sending to Grobid server...")
        try:
            xml_content = self.process_pdf_with_grobid(pdf_path)
        except Exception as e:
            print(f"Grobid processing failed: {e}")
            return

        print("[IEEE-Grobid] Extracting text from XML...")
        text = self.extract_text_from_grobid_xml(xml_content)
        if not text:
            print("No text extracted from Grobid XML!")
            return

        print("[IEEE-Grobid] Splitting into sentences...")
        sentences = self.split_into_sentences(text)
        print(f"[IEEE-Grobid] Found {len(sentences)} sentences")

        print("[IEEE-Grobid] Detecting numeric citations...")
        all_sents, correct_cits = self.detect_numeric_citations(sentences)
        print(f"[IEEE-Grobid] Found {len(correct_cits)} numeric citations")

        print("[IEEE-Grobid] Creating file chunks...")
        chunks = self.create_file_chunks(all_sents, correct_cits)
        print(f"[IEEE-Grobid] Created {len(chunks)} file chunks")

        print("[IEEE-Grobid] Generating output files...")
        for i, ch in enumerate(chunks):
            self.create_in_file(ch["texts"], i, output_dir)
            self.create_label_file(ch["texts"], ch["correct_citations"], i, output_dir)

        print(f"[IEEE-Grobid] Done. Files in '{output_dir}'")
        self.print_summary(chunks, output_dir, len(correct_cits))

    def print_summary(self, chunks: List[Dict], output_dir: str, total_citations: int):
        print("\n" + "="*50)
        print("IEEE-GROBID GENERATION SUMMARY")
        print("="*50)

        total_sentences = sum(len(chunk["texts"]) for chunk in chunks)
        print(f"Total files generated: {len(chunks)} pairs")
        print(f"Total sentences processed: {total_sentences}")
        print(f"Total numeric citations found: {total_citations}")
        if len(chunks) > 0:
            print(f"Average sentences per file: {total_sentences/len(chunks):.1f}")
            print(f"Citation percentage: {(total_citations/total_sentences)*100:.1f}%")

        print(f"\nFiles saved in: {output_dir}/")


def run(pdf_path: str, output_dir: str = "output", sentences_per_file: int = 5, grobid_url: str = "http://localhost:8070"):
    proc = PDFToPipelineProcessorIEEE(sentences_per_file=sentences_per_file, grobid_url=grobid_url)
    proc.process_pdf(pdf_path, output_dir)