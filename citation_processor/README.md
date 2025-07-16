# Citation Processor

A tool for processing academic papers to extract and analyze citations and references.

## Features

- Extract text from PDF files
- Detect citations in various formats (APA, IEEE, Chicago)
- Parse references
- Generate BIO tags for citation detection
- Map citations to references
- Detect quoted text

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd citation_processor
```

2. Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

## Usage

1. Place your PDF files in the `data/input` directory.

2. Run the processor:

```bash
chmod +x run.sh
./run.sh
```

3. Find the processed results in `data/output` directory.

## Output Format

The tool generates JSON files with the following structure:

```json
{
  "text": "Original text without citation markers",
  "citations": [
    {
      "id": "citation_1",
      "text": "Citation text",
      "start": 123,
      "end": 145,
      "style": "APA",
      "reference_id": "ref_1",
      "quoted_text": "Text being cited",
      "quoted_start": 156,
      "quoted_end": 178,
      "bio_tags": ["B-CITATION", "I-CITATION", "O", ...]
    }
  ],
  "references": [
    {
      "id": "ref_1",
      "text": "Full reference text",
      "style": "APA",
      "parsed_info": {
        "authors": ["Author1", "Author2"],
        "year": "2020",
        "title": "Paper title",
        "journal": "Journal name",
        "volume": "15",
        "issue": "2",
        "pages": "123-145"
      },
      "source_text": "Original paper text",
      "quoted_sections": [
        {
          "text": "Quoted text from source",
          "start": 45,
          "end": 67
        }
      ]
    }
  ]
}
```

## Requirements

- Python 3.8+
- pdfplumber
- nltk
- spacy
- python-dotenv
- pytest
