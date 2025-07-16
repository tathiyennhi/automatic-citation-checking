# quick_test.py - Standalone test script

import json
import re
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import fitz  # PyMuPDF

@dataclass
class PaperStructure:
    title: str = ""
    raw_text: str = ""
    clean_sentences: List[str] = None
    references_section: str = ""
    citation_candidates: List[str] = None
    reference_entries: Dict[str, str] = None

class SimpleProcessor:
    """Simplified processor for quick testing"""
    
    def __init__(self):
        self.skip_patterns = [
            # Publishers and journals
            r'^(Springer|Elsevier|IEEE|ACM|Nature|Science)$',
            r'^(Scientometrics|Journal of|Proceedings of).*',
            
            # Section headers
            r'^(Abstract|Introduction|Conclusion|References|Bibliography|Appendix)$',
            r'^(Keywords|Acknowledgment|Acknowledgement)s?$',
            r'^(Figure|Table|Fig\.|Tab\.)\s*\d+',
            
            # Page/document metadata
            r'^Page \d+',
            r'^\d+$',  # Just numbers
            r'^[a-z]$',  # Single letters
            
            # URLs and DOIs (when standalone)
            r'^https?://',
            r'^doi:',
            r'^10\.\d+/',
            
            # Short non-content lines
            r'^[A-Z][a-z]*$',  # Single words (like "Springer", "Scientometrics")
        ]
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                page_text = page.get_text("text", sort=True)
                text += page_text + "\n"
            doc.close()
            return text
        except Exception as e:
            print(f"❌ PDF extraction failed: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Basic cleaning
        patterns = {
            'doi_spaces': (r'https://d\s*oi\s*\.\s*o\s*rg/1\s*0\s*\.', 'https://doi.org/10.'),
            'multiple_spaces': (r'\s+', ' '),
            'hyphen_newline': (r'(\w+)-\s*\n\s*(\w+)', r'\1\2'),
        }
        
        cleaned = text
        for pattern_name, (pattern, replacement) in patterns.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned
    
    def extract_title(self, text: str) -> str:
        """Extract paper title"""
        lines = text.split('\n')
        
        for line in lines[:20]:
            line = line.strip()
            if (len(line) > 20 and 
                not line.isdigit() and 
                not re.match(r'^(Abstract|Introduction|Keywords)', line, re.I)):
                return line
        
        return "Title not found"
    
    def should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped"""
        for pattern in self.skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def extract_sentences(self, text: str) -> List[str]:
        """Extract valid sentences"""
        sentences = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip metadata lines
            if self.should_skip_line(line):
                continue
            
            # Basic sentence validation
            if (len(line) > 15 and 
                len(re.findall(r'\b[a-zA-Z]+\b', line)) > 3 and
                re.search(r'[a-z]', line)):  # Has lowercase letters
                
                if not line.endswith(('.', '!', '?')):
                    line += '.'
                sentences.append(line)
        
        return sentences
    
    def extract_references(self, text: str) -> Dict[str, str]:
        """Extract references section"""
        # Find references section
        ref_match = re.search(r'\n\s*(References|REFERENCES)\s*\n', text, re.IGNORECASE)
        if not ref_match:
            return {}
        
        ref_section = text[ref_match.end():]
        
        # Parse individual references
        references = {}
        ref_entries = re.split(r'\n(?=\w)', ref_section)
        
        for i, entry in enumerate(ref_entries[:10]):  # Limit to first 10
            entry = entry.strip()
            if len(entry) > 30:
                # Extract title (simple approach)
                title_match = re.search(r'\.\s*([^.]+?)\.\s*', entry)
                title = title_match.group(1) if title_match else entry[:50]
                
                references[str(i+1)] = {
                    "title": title,
                    "full_text": entry
                }
        
        return references
    
    def extract_citations(self, text: str) -> List[str]:
        """Extract citation markers"""
        citations = set()
        
        # Pattern: [1], [1,2], [1-3]
        for match in re.finditer(r'\[(\d+(?:[-,]\s*\d+)*)\]', text):
            citation_str = match.group(1)
            # Simple expansion
            parts = citation_str.replace(' ', '').split(',')
            for part in parts:
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        citations.update(str(i) for i in range(start, min(end+1, start+10)))
                    except:
                        citations.add(part)
                else:
                    citations.add(part)
        
        return sorted(citations, key=lambda x: int(x) if x.isdigit() else 0)
    
    def process_paper(self, pdf_path: str) -> Dict:
        """Process paper through pipeline"""
        
        print(f"📄 Processing: {pdf_path}")
        
        # Extract text
        print("1. Extracting text...")
        raw_text = self.extract_pdf_text(pdf_path)
        if not raw_text:
            return {}
        
        # Save raw text
        with open("debug_raw.txt", 'w', encoding='utf-8') as f:
            f.write(raw_text)
        print("💾 Raw text saved to: debug_raw.txt")
        
        # Clean text
        print("2. Cleaning text...")
        clean_text = self.clean_text(raw_text)
        with open("debug_clean.txt", 'w', encoding='utf-8') as f:
            f.write(clean_text)
        print("💾 Clean text saved to: debug_clean.txt")
        
        # Extract components
        print("3. Extracting components...")
        title = self.extract_title(clean_text)
        sentences = self.extract_sentences(clean_text)
        references = self.extract_references(clean_text)
        citations = self.extract_citations(clean_text)
        
        print(f"✅ Title: {title}")
        print(f"✅ Sentences: {len(sentences)}")
        print(f"✅ References: {len(references)}")
        print(f"✅ Citations: {len(citations)}")
        
        # Show what gets skipped
        print("\n🚫 Lines that will be SKIPPED:")
        lines = clean_text.split('\n')
        skipped_count = 0
        for line in lines[:20]:  # Show first 20 lines
            line = line.strip()
            if line and self.should_skip_line(line):
                print(f"   ❌ '{line}'")
                skipped_count += 1
        
        print(f"\n📊 Sample sentences kept:")
        for i, sent in enumerate(sentences[:3]):
            print(f"   ✅ {i+1}. {sent[:80]}...")
        
        # Build result
        result = {
            "title": title,
            "text": sentences,
            "citation_candidates": citations,
            "bib_entries": references
        }
        
        # Save result
        with open("result.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("💾 Result saved to: result.json")
        
        return result

def test_with_sample():
    """Test with sample text"""
    sample_text = """
Empirical Methods in Natural Language Processing (EMNLP) (pp. 6442–6454). Association for
Computational Linguistics.


Springer


Scientometrics

Yu, J., Bohnet, B., & Poesio, M. (2020). Named entity recognition as dependency parsing. 10.48550/
ARXIV.2005.07150.
Zhang, C., Mayr, P., Lu, W., & Zhang, Y. (2023). Guest editorial: Extraction and evaluation of knowledge
entities in the age of artificial intelligence. Aslib Journal of Information Management, 75, 433–437.
https://doi.org/10.1108/AJIM-05-2023-507

References

Smith, J. (2020). A comprehensive study of machine learning. Journal of AI Research, 15, 123-145.
Doe, A. & Brown, B. (2021). Natural language processing techniques. In Proceedings of ACL (pp. 1-10).
"""
    
    print("🧪 TESTING WITH SAMPLE TEXT")
    print("="*50)
    
    processor = SimpleProcessor()
    
    # Test cleaning and sentence extraction
    lines = sample_text.split('\n')
    print("Input lines:")
    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            status = "❌ SKIP" if processor.should_skip_line(line) else "✅ KEEP"
            print(f"  {status}: '{line}'")
    
    sentences = processor.extract_sentences(sample_text)
    print(f"\nExtracted {len(sentences)} sentences:")
    for i, sent in enumerate(sentences):
        print(f"  {i+1}. {sent}")

def main():
    """Main function"""
    import sys
    
    print("🔬 QUICK CITATION CHECKER TEST")
    print("="*50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        test_with_sample()
        return
    
    # Look for PDF file
    test_files = ["paper.pdf", "sample.pdf", "test.pdf", "example.pdf"]
    pdf_path = None
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        for test_file in test_files:
            if os.path.exists(test_file):
                pdf_path = test_file
                break
    
    if not pdf_path:
        print("❌ No PDF file found!")
        print("\n💡 Usage:")
        print(f"   python {sys.argv[0]} your_paper.pdf")
        print(f"   python {sys.argv[0]} sample  # Test with sample text")
        print("\n📁 Or place PDF file with name: paper.pdf, sample.pdf, test.pdf, example.pdf")
        return
    
    # Process PDF
    processor = SimpleProcessor()
    result = processor.process_paper(pdf_path)

if __name__ == "__main__":
    main()