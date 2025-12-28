import json
import re
import os
from typing import List, Dict, Any, Tuple

class CitationExtractionPipeline:
    def __init__(self):
        """
        Initialize pipeline for extracting citations from sentences (Task 1b)
        """
        pass

    def process_directory(self, input_dir: str, output_dir: str = "task1b_output"):
        """
        Process all .label files from main.py output directory

        Args:
            input_dir: Directory containing .label files from main.py
            output_dir: Output directory for task 1b files
        """
        print(f"Processing directory: {input_dir}")

        os.makedirs(output_dir, exist_ok=True)

        total_processed = 0
        total_citations_found = 0

        # Duyệt từng file .label
        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith('.label'):
                continue

            file_path = os.path.join(input_dir, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"Debug: Successfully loaded JSON for {filename}")

                # STRICT: Chỉ xử lý file có style VÀ correct_citations
                sentences = data.get("correct_citations", [])
                style = data.get("style", "")

                if not style or not sentences:
                    # Edge case: có citations nhưng không có style → warning
                    if sentences and not style:
                        print(f"⚠️  Warning: {filename} has citations but no style! Skipping.")
                    else:
                        print(f"Debug: No correct_citations found in {filename}")
                    continue

                print(f"Debug: About to call process_label_file for {filename}")
                processed, citations_count = self.process_label_file(
                    data, filename, output_dir, total_processed
                )
                total_processed += processed
                total_citations_found += citations_count

            except json.JSONDecodeError as e:
                print(f"JSON error in {filename}: {e}")
                print(f"Skipping corrupt file: {filename}")
                continue  # Bỏ qua file lỗi JSON
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                import traceback
                traceback.print_exc()
                break  # Dừng để xem stack trace chi tiết

        print(f"\nTask 1b processing complete!")
        print(f"Processed {total_processed} citation sentences")
        print(f"Extracted {total_citations_found} individual citations")
        print(f"Files saved in: {output_dir}/")

    def process_label_file(
        self,
        data: Dict,
        filename: str,
        output_dir: str,
        start_index: int
    ) -> Tuple[int, int]:
        """
        Process a single .label file

        Args:
            data: JSON data from .label file
            filename: Original filename
            output_dir: Output directory
            start_index: Starting index for file numbering

        Returns:
            Tuple of (processed_sentences, total_citations)
        """
        correct_citations = data.get("correct_citations", [])
        processed_count = 0
        total_citations = 0

        print(f"Processing {filename}: {len(correct_citations)} citation sentences")
        print(f"Debug: Keys in data = {list(data.keys())}")

        for sentence in correct_citations:
            # Extract citations and create mask
            citations_data = self.extract_citations_with_mask(sentence)

            # Chỉ tạo file nếu tìm thấy citation
            if citations_data["citation_references"]:
                file_index = start_index + processed_count

                # Tạo .in
                self.create_in_file(sentence, file_index, output_dir)

                # Tạo .label
                self.create_label_file(citations_data, file_index, output_dir)

                processed_count += 1
                # Đếm theo số lượng citation_references
                total_citations += len(citations_data["citation_references"])

        return processed_count, total_citations

    def split_grouped_citations(self, citation_text: str) -> List[str]:
        """
        Split grouped citations into individual citations

        Args:
            citation_text: Citation text that may contain multiple references

        Returns:
            List of individual citations
        """
        # Bỏ ngoặc ngoài nếu có
        text = citation_text.strip()
        if text.startswith('(') and text.endswith(')'):
            text = text[1:-1]

        # Tách theo dấu ';' là chính
        individual_citations = []
        parts = text.split(';')

        for part in parts:
            part = part.strip()
            if part and re.search(r'\d{4}', part):  # cần có năm
                individual_citations.append(part)

        # Nếu không tách được thì coi như 1 citation
        if len(individual_citations) <= 1 and citation_text.strip():
            return [citation_text.strip()]

        return individual_citations

    def extract_citations_with_mask(self, text: str) -> Dict[str, Any]:
        """
        Extract citations and create mask with markers

        Args:
            text: Input text with citations

        Returns:
            Dictionary với:
              - text
              - mask: join toàn bộ citation đơn lẻ bằng "; "
              - citation_references: list[{reference_text, citation_marker}]
        """
        # Thứ tự pattern quan trọng: cụ thể trước, tổng quát sau
        citation_patterns = [
            # Nhiều citation trong ngoặc: (Shen et al., 2022; Beltagy et al.., 2019)
            r'\([A-Z][a-z]+[^)]*\d{4}[^)]*(?:;\s*[A-Z][a-z]+[^)]*\d{4}[^)]*)*\)',

            # Author et al. (Year): Smith et al. (2020), Beltagy et al.. (2019)
            r'\b[A-Z][a-z]+\s+et\s+al\.\.?\s+\(\d{4}[a-z]?\)',

            # Hai tác giả (Year): Smith and Jones (2020) / Smith & Jones (2020)
            r'\b[A-Z][a-z]+\s+(?:and|&)\s+[A-Z][a-z]+\s+\(\d{4}[a-z]?\)',

            # Một tác giả (Year): Cronin (2020), Smith (2019)
            r'\b[A-Z][a-z]+\s+\(\d{4}[a-z]?\)',

            # Parenthetical et al.: (Smith et al., 2020)
            r'\([A-Z][a-z]+\s+et\s+al\.\.?,?\s*\d{4}[a-z]?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?\)',

            # Parenthetical 2 tác giả: (Smith & Jones, 2020)
            r'\([A-Z][a-z]+\s+(?:&|and)\s+[A-Z][a-z]+,?\s*\d{4}[a-z]?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?\)',

            # Parenthetical 1 tác giả: (Smith, 2020)
            r'\([A-Z][a-z]+,?\s*\d{4}[a-z]?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?\)',
        ]

        citations_raw = []
        citation_positions = []

        # Tìm non-overlap
        for pattern in citation_patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                citation_text = match.group(0).strip()

                overlaps = any(not (end <= es or start >= ee) for es, ee in citation_positions)
                if not overlaps:
                    citations_raw.append(citation_text)
                    citation_positions.append((start, end))

        # Sort theo vị trí
        combined = list(zip(citations_raw, citation_positions))
        combined.sort(key=lambda x: x[1][0])

        # Tách citation nhóm thành đơn lẻ
        all_individual_citations: List[str] = []
        citation_references: List[Dict[str, str]] = []

        for citation, (_start, _end) in combined:
            individual_cites = self.split_grouped_citations(citation)
            for individual_cite in individual_cites:
                cleaned = individual_cite.strip()
                all_individual_citations.append(cleaned)
                citation_references.append({
                    "reference_text": cleaned,
                    "citation_marker": f"[CITATION_{len(all_individual_citations)}]"
                })

        # Mask = join của toàn bộ citation đơn lẻ
        mask = "; ".join(all_individual_citations) if all_individual_citations else ""

        return {
            "text": text,
            "mask": mask,
            "citation_references": citation_references
        }

    def create_in_file(self, text: str, file_index: int, output_dir: str):
        """
        Create .in file for task 1b

        Args:
            text: Original text with citations
            file_index: File index
            output_dir: Output directory
        """
        file_path = os.path.join(output_dir, f"citation_{file_index:03d}.in")
        content = {"text": text}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    def create_label_file(self, citations_data: Dict[str, Any], file_index: int, output_dir: str):
        """
        Create .label file for task 1b

        Args:
            citations_data: Dictionary with text, mask, and citations
            file_index: File index
            output_dir: Output directory
        """
        file_path = os.path.join(output_dir, f"citation_{file_index:03d}.label")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(citations_data, f, ensure_ascii=False, indent=2)

    def print_example_output(self, output_dir: str):
        """
        Print example of generated output

        Args:
            output_dir: Output directory
        """
        # Tìm 1 file .label để in ví dụ
        for filename in sorted(os.listdir(output_dir)):
            if not filename.endswith('.label'):
                continue

            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                example = json.load(f)

            print("\n" + "="*50)
            print("EXAMPLE OUTPUT")
            print("="*50)
            print(f"File: {filename}")
            print(f"Original text: {example.get('text','')[:100]}...")
            print(f"Mask: {example.get('mask','')}")
            refs = example.get('citation_references', [])
            print(f"Citations found: {len(refs)}")
            if refs:
                print("Citations mapping:")
                for item in refs:
                    print(f"  {item['citation_marker']}: {item['reference_text']}")
            break


def main():
    """
    Main function for task 1b pipeline
    """
    processor = CitationExtractionPipeline()

    # Input directory từ main.py
    input_directory = "../data_outputs/task1a"
    output_directory = "../data_outputs/task1b"

    if os.path.exists(input_directory):
        processor.process_directory(input_directory, output_directory)

        # Show example output
        if os.path.exists(output_directory):
            processor.print_example_output(output_directory)
    else:
        print(f"Input directory '{input_directory}' not found!")
        print("Please run main.py first to generate citation data.")


if __name__ == "__main__":
    main()
