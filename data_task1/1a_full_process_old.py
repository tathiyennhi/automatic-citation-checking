import os
import re
import json
from typing import List, Dict, Tuple

# --- Optional imports with graceful fallback ---
# Order of preference: PyMuPDF (fitz) -> pdfplumber -> PyPDF2
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except Exception:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except Exception:
    HAS_PYPDF2 = False

import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class PDFToPipelineProcessor:
    def __init__(self, sentences_per_file: int = 5):
        """
        Initialize the processor

        Args:
            sentences_per_file: Number of sentences per output file
        """
        self.sentences_per_file = sentences_per_file

    # -------------------------------
    # 1) PDF TEXT EXTRACTION (improved)
    # -------------------------------
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text content from PDF file with best-effort spacing.

        Tries PyMuPDF -> pdfplumber -> PyPDF2 (fallback).
        """
        # 1. Try PyMuPDF (fitz)
        if HAS_FITZ:
            try:
                text = self._extract_with_fitz(pdf_path)
                if text and text.strip():
                    return text
            except Exception as e:
                print(f"[fitz] Warning: {e}")

        # 2. Try pdfplumber
        if HAS_PDFPLUMBER:
            try:
                text = self._extract_with_pdfplumber(pdf_path)
                if text and text.strip():
                    return text
            except Exception as e:
                print(f"[pdfplumber] Warning: {e}")

        # 3. Fallback: PyPDF2 (original approach)
        if HAS_PYPDF2:
            try:
                text = self._extract_with_pypdf2(pdf_path)
                if text and text.strip():
                    return text
            except Exception as e:
                print(f"[PyPDF2] Warning: {e}")

        print("Error: No PDF backend worked (fitz/pdfplumber/PyPDF2).")
        return ""

    def _extract_with_fitz(self, pdf_path: str) -> str:
        """
        Use PyMuPDF to extract text with blocks to better preserve spaces.
        """
        text_parts: List[str] = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                # 'text' yields reasonable spacing; 'blocks' can be used if needed
                txt = page.get_text("text")
                text_parts.append(txt)
        return "\n".join(text_parts)

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Use pdfplumber with a sensible layout to preserve spaces.
        """
        text_parts: List[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # extract_text() of pdfplumber generally preserves spacing well
                txt = page.extract_text() or ""
                text_parts.append(txt)
        return "\n".join(text_parts)

    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """
        Fallback: PyPDF2 extraction (may lose spaces on some PDFs).
        """
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                txt = page.extract_text() or ""
                text += txt + "\n"
        return text

    # -------------------------------
    # 2) CLEANING / NORMALIZING
    # -------------------------------
    def normalize_spacing(self, text: str) -> str:
        """
        Heuristic fixes for missing spaces caused by bad PDF text layers.
        - Insert space between lower→Upper (e.g., acknowledgementsEconStor -> acknowledgements EconStor)
        - Insert space between letter↔digit (e.g., method1->method 1, 24Kentities->24K entities)
        - Insert space after .,;:!? when followed by a letter/number without spaces
        - Fix variants like "et al ." -> "et al."
        - Collapse multiple spaces, trim
        """
        s = text

        # Space after punctuation if missing
        s = re.sub(r'([.,;:!?])([A-Za-z0-9])', r'\1 \2', s)

        # Space between lower->Upper (camel bump)
        s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)

        # Space between letter<->digit and digit<->letter
        s = re.sub(r'([A-Za-z])([0-9])', r'\1 \2', s)
        s = re.sub(r'([0-9])([A-Za-z])', r'\1 \2', s)

        # Fix "et al ." -> "et al."
        s = re.sub(r'\bet\s+al\s+\.', 'et al.', s)

        # Occasionally PDFs drop a space before parentheses: "task(see" -> "task (see"
        s = re.sub(r'([A-Za-z0-9])\(', r'\1 (', s)
        # And after closing parentheses: ")text" -> ") text"
        s = re.sub(r'\)([A-Za-z0-9])', r') \1', s)

        # Reduce multiple spaces
        s = re.sub(r'\s+', ' ', s)
        return s.strip()

    def clean_text(self, text: str) -> str:
        """
        Clean and preprocess the extracted text
        """
        # Normalize spacing first (critical for this PDF)
        text = self.normalize_spacing(text)

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F]{2}))+', '', text)

        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '', text)

        # Remove trailing page numbers per-line (defensive)
        text = re.sub(r'\n?\s*\d+\s*$', '', text, flags=re.MULTILINE)

        # Final collapse
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # -------------------------------
    # 3) SENTENCE SPLITTING
    # -------------------------------
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using NLTK
        """
        sentences = sent_tokenize(text)

        # Filter out very short sentences (likely noise)
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and not sentence.isdigit():
                filtered_sentences.append(sentence)
        return filtered_sentences

    # -------------------------------
    # 4) APA DETECTION (unchanged logic)
    # -------------------------------
    def detect_apa_citations(self, sentences: List[str]) -> Tuple[List[str], List[str]]:
        """
        Detect APA citations in sentences
        """
        correct_citations = []

        apa_patterns = [
            r'\b[A-Z][a-z]+,\s*\d{4}\b',
            r'\b[A-Z][a-z]+\s+\(\d{4}\)',
            r'\([A-Z][a-z]+,\s*\d{4}\)',
            r'\([A-Z][a-z]+\s+\(\d{4}\)\)',

            r'\b[A-Z][a-z]+\s+&\s+[A-Z][a-z]+,\s*\d{4}\b',
            r'\([A-Z][a-z]+\s+&\s+[A-Z][a-z]+,\s*\d{4}\)',
            r'\b[A-Z][a-z]+\s+&\s+[A-Z][a-z]+\s+\(\d{4}\)',

            r'\b[A-Z][a-z]+\s+and\s+[A-Z][a-z]+,\s*\d{4}\b',
            r'\([A-Z][a-z]+\s+and\s+[A-Z][a-z]+,\s*\d{4}\)',
            r'\b[A-Z][a-z]+\s+and\s+[A-Z][a-z]+\s+\(\d{4}\)',

            r'\b[A-Z][a-z]+\s+et\s+al\.,\s*\d{4}\b',
            r'\b[A-Z][a-z]+\s+et\s+al\.\s+\(\d{4}\)',
            r'\([A-Z][a-z]+\s+et\s+al\.,\s*\d{4}\)',
            r'\b[A-Z][a-z]+\s+et\s+al\.\.\s+\(\d{4}\)',
            r'\([A-Z][a-z]+\s+et\s+al\.\.\s+\(\d{4}\)\)',

            r'\([A-Z][a-z]+,\s*\d{4},\s*p\.\s*\d+\)',
            r'\([A-Z][a-z]+,\s*\d{4},\s*pp\.\s*\d+-\d+\)',
            r'\([A-Z][a-z]+\s+et\s+al\.,\s*\d{4},\s*p\.\s*\d+\)',

            r'\b[A-Z][a-z]+,\s*\d{4}[a-z]\b',
            r'\([A-Z][a-z]+,\s*\d{4}[a-z]\)',
            r'\b[A-Z][a-z]+\s+\(\d{4}[a-z]\)',
            r'\b[A-Z][a-z]+\s+et\s+al\.,\s*\d{4}[a-z]\b',

            r'\([A-Z][a-z]+,\s*\d{4};\s*[A-Z][a-z]+,\s*\d{4}\)',
            r'\([A-Z][a-z]+\s+et\s+al\.,\s*\d{4};\s*[A-Z][a-z]+,\s*\d{4}\)',

            r'\b[A-Z][a-z]+.*?\(\d{4}\)',

            r'\b[A-Z][a-z]+\s*,\s*\d{4}\b',
            r'\b[A-Z][a-z]+\s+et\s+al\s*\.\s*,\s*\d{4}\b',
            r'\b[A-Z][a-z]+\s+et\s+al\s*\.\s*\(\d{4}\)',
        ]

        for sentence in sentences:
            if any(re.search(p, sentence) for p in apa_patterns):
                correct_citations.append(sentence)

        return sentences, correct_citations

    # -------------------------------
    # 5) CHUNKING & FILE I/O
    # -------------------------------
    def create_file_chunks(self, sentences: List[str], correct_citations: List[str]) -> List[Dict]:
        chunks = []
        current_texts = []

        for sentence in sentences:
            current_texts.append(sentence)
            if len(current_texts) >= self.sentences_per_file:
                chunk_citations = [s for s in current_texts if s in correct_citations]
                chunks.append({"texts": current_texts.copy(), "correct_citations": chunk_citations})
                current_texts = []

        if current_texts:
            chunk_citations = [s for s in current_texts if s in correct_citations]
            chunks.append({"texts": current_texts, "correct_citations": chunk_citations})

        return chunks

    def create_in_file(self, texts: List[str], file_index: int, output_dir: str):
        file_path = os.path.join(output_dir, f"data_{file_index:03d}.in")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"texts": texts}, f, ensure_ascii=False, indent=2)

    def create_label_file(self, texts: List[str], correct_citations: List[str], file_index: int, output_dir: str):
        file_path = os.path.join(output_dir, f"data_{file_index:03d}.label")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"texts": texts, "correct_citations": correct_citations}, f, ensure_ascii=False, indent=2)

    # -------------------------------
    # 6) MAIN PROCESS
    # -------------------------------
    def process_pdf(self, pdf_path: str, output_dir: str = "output"):
        print(f"Processing PDF: {pdf_path}")
        os.makedirs(output_dir, exist_ok=True)

        print("Extracting text from PDF...")
        raw_text = self.extract_text_from_pdf(pdf_path)
        if not raw_text:
            print("No text extracted from PDF!")
            return

        print("Cleaning text...")
        cleaned_text = self.clean_text(raw_text)

        print("Splitting into sentences...")
        sentences = self.split_into_sentences(cleaned_text)
        print(f"Found {len(sentences)} sentences")

        print("Detecting APA citations...")
        all_sentences, correct_citations = self.detect_apa_citations(sentences)
        print(f"Found {len(correct_citations)} APA citations")

        print("Creating file chunks...")
        chunks = self.create_file_chunks(all_sentences, correct_citations)
        print(f"Created {len(chunks)} file chunks")

        print("Generating output files...")
        for i, chunk in enumerate(chunks):
            self.create_in_file(chunk["texts"], i, output_dir)
            self.create_label_file(chunk["texts"], chunk["correct_citations"], i, output_dir)

        print(f"Processing complete! Generated {len(chunks)} pairs of files in '{output_dir}' directory")
        self.print_summary(chunks, output_dir, len(correct_citations))

    def print_summary(self, chunks: List[Dict], output_dir: str, total_citations: int):
        print("\n" + "="*50)
        print("GENERATION SUMMARY")
        print("="*50)

        total_sentences = sum(len(chunk["texts"]) for chunk in chunks)
        print(f"Total files generated: {len(chunks)} pairs")
        print(f"Total sentences processed: {total_sentences}")
        print(f"Total APA citations found: {total_citations}")
        if len(chunks) > 0:
            print(f"Average sentences per file: {total_sentences/len(chunks):.1f}")
            print(f"Citation percentage: {(total_citations/total_sentences)*100:.1f}%")

        print(f"\nFiles saved in: {output_dir}/")
        for i, chunk in enumerate(chunks):
            print(f"  - data_{i:03d}.in (texts: {len(chunk['texts'])})")
            print(f"  - data_{i:03d}.label (citations: {len(chunk['correct_citations'])})")


def main():
    processor = PDFToPipelineProcessor(sentences_per_file=5)
    pdf_file = "sci-ner.pdf"   
    output_directory = "output"

    if os.path.exists(pdf_file):
        processor.process_pdf(pdf_file, output_directory)
    else:
        print(f"PDF file '{pdf_file}' not found!")
        print("Please make sure the PDF file exists in the current directory.")


if __name__ == "__main__":
    main()
