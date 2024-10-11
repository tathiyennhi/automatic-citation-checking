# import re
# import json
# import logging
# from typing import List, Dict
# import spacy

# # Thiết lập logging để theo dõi quá trình trích xuất
# logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

# # Tải mô hình ngôn ngữ SpaCy
# try:
#     nlp = spacy.load("en_core_web_sm")
# except OSError:
#     logging.info("Mô hình SpaCy 'en_core_web_sm' chưa được tải. Đang tải mô hình...")
#     from spacy.cli import download
#     download("en_core_web_sm")
#     nlp = spacy.load("en_core_web_sm")

# def clean_author(author: str) -> str:
#     """Làm sạch chuỗi tác giả bằng cách loại bỏ các phần không cần thiết."""
#     # Loại bỏ các cụm từ không liên quan
#     author = re.sub(r'^(?:additional previous work in this area includes|'
#                     r'the work of|the special issue by|cited in|as cited in)\s+',
#                     '', author, flags=re.IGNORECASE)
#     # Loại bỏ các ký tự không cần thiết
#     author = re.sub(r'\s+', ' ', author)
#     author = author.strip()
#     return author

# def determine_citation_validity(content: str) -> bool:
#     """Xác định xem nội dung có phải là trích dẫn hợp lệ hay không."""
#     has_year = re.search(r'\b\d{4}\b', content)
#     has_author = re.search(r'\b[A-Z][a-zA-Z]+', content)
#     is_too_short = len(content.strip()) < 3
#     is_single_char = re.match(r'^[a-zA-Z0-9]$', content.strip())

#     if has_year and has_author and not is_single_char and not is_too_short:
#         return True  # Là trích dẫn hợp lệ
#     else:
#         return False  # Không phải trích dẫn hợp lệ

# def extract_citations_from_sentence(sentence: str) -> List[Dict]:
#     """Trích xuất tất cả các trích dẫn từ một câu."""
#     citations = []

#     # Mẫu regex cho trích dẫn narrative (ví dụ: "Jiang et al. (2022)")
#     narrative_citation_regex = r'\b(?P<author>[A-Z][a-zA-Z\'’\-]+(?:\s+(?:et\s+al\.?|and|&)\s*(?:[A-Z][a-zA-Z\'’\-]+)?)*)\s*\((?P<year>\d{4})\)'

#     # Mẫu regex cho trích dẫn parenthetical (ví dụ: "(Smith, 2020)" hoặc "(Conditional Random Field)")
#     parenthetical_citation_regex = r'\(([^()]+)\)'

#     # Mẫu regex cho trích dẫn trực tiếp với dấu ngoặc kép chuẩn (ví dụ: "“...“ (Author, Year))")
#     direct_quote_regex = r'"(.*?)"\s*\(([^()]+)\)'  # Sử dụng dấu ngoặc kép chuẩn

#     # Tìm trích dẫn trực tiếp trong câu
#     for match in re.finditer(direct_quote_regex, sentence):
#         quote = match.group(1).strip()
#         citation_content = quote
#         citation_text = match.group(0)
#         citation_info = match.group(2).strip()
#         start = match.start()
#         end = match.end()

#         logging.info(f"Found direct_quote: {citation_text}")

#         # Xử lý thông tin trích dẫn
#         refs = re.split(r';\s*', citation_info)
#         ref_citations = []
#         for ref in refs:
#             ref = ref.strip()
#             # Tách tác giả và năm
#             parts = re.split(r',\s*', ref)
#             if len(parts) >= 2:
#                 author = ', '.join(parts[:-1]).strip()
#                 year = parts[-1].strip()
#             else:
#                 author = ref
#                 year = ''
#             ref_citations.append({
#                 'author': clean_author(author),
#                 'year_published': year
#             })
#         citations.append({
#             'type': 'direct_quote',
#             'citation_content': citation_content,
#             'ref_citations': ref_citations,
#             'original_citation_text': citation_text,
#             'start': start,
#             'end': end
#         })

#     # Loại bỏ các trích dẫn trực tiếp khỏi câu để tránh trùng lặp khi xử lý các trích dẫn khác
#     sentence_without_direct_quotes = re.sub(direct_quote_regex, '', sentence)

#     # Tìm trích dẫn narrative trong câu đã loại bỏ trích dẫn trực tiếp
#     for match in re.finditer(narrative_citation_regex, sentence_without_direct_quotes, re.IGNORECASE):
#         author = match.group('author').strip()
#         year = match.group('year').strip()
#         citation_text = match.group(0)
#         start = match.start()
#         end = match.end()

#         logging.info(f"Found narrative citation: {citation_text}")

#         citations.append({
#             'type': 'narrative',
#             'author': author,
#             'year_published': year,
#             'citation_text': citation_text,
#             'start': start,
#             'end': end
#         })

#     # Tìm trích dẫn parenthetical trong câu đã loại bỏ trích dẫn trực tiếp
#     for match in re.finditer(parenthetical_citation_regex, sentence_without_direct_quotes):
#         content = match.group(1).strip()
#         start = match.start()
#         end = match.end()
#         if not determine_citation_validity(content):
#             logging.info(f"Ignoring invalid parenthetical citation: {match.group(0)}")
#             continue

#         # Tách các trích dẫn bên trong dấu ngoặc đơn
#         refs = re.split(r';\s*', content)
#         ref_citations = []
#         for ref in refs:
#             ref = ref.strip()
#             # Tách tác giả và năm
#             parts = re.split(r',\s*', ref)
#             if len(parts) >= 2:
#                 author = ', '.join(parts[:-1]).strip()
#                 year = parts[-1].strip()
#             else:
#                 author = ref
#                 year = ''
#             ref_citations.append({
#                 'author': clean_author(author),
#                 'year_published': year
#             })
#         citations.append({
#             'type': 'parenthetical',
#             'ref_citations': ref_citations,
#             'original_citation_text': match.group(0),
#             'start': start,
#             'end': end
#         })

#     # Sắp xếp các trích dẫn theo vị trí trong câu
#     citations.sort(key=lambda x: x['start'])

#     return citations

# def extract_sentences(text: str) -> List[str]:
#     """Tách văn bản thành các câu riêng lẻ, xử lý ngoại lệ như 'et al.' và 'Sr.'."""
    
#     # Sử dụng SpaCy để tách câu, đây là cách hiệu quả hơn để xử lý các từ viết tắt
#     doc = nlp(text)
#     sentences = [sent.text.strip() for sent in doc.sents]
#     logging.debug(f"Extracted sentences: {sentences}")
#     return sentences

# def extract_citations_with_context(text: str) -> List[Dict]:
#     """Trích xuất trích dẫn từ mỗi câu."""
#     sentences = extract_sentences(text)
#     results = []

#     for sentence in sentences:
#         citations_in_sentence = extract_citations_from_sentence(sentence)
#         if not citations_in_sentence:
#             continue

#         citation_entries = []
#         citation_count = len(citations_in_sentence)

#         for citation in citations_in_sentence:
#             citation_type = citation['type']
#             needs_manual_check = False

#             if citation_type == 'narrative':
#                 # Trích xuất nội dung sau trích dẫn narrative
#                 citation_content = sentence[citation['end']:].strip() if citation['end'] < len(sentence) else ""
#                 if len(citation_content.split()) < 2:
#                     needs_manual_check = True

#                 citation_entry = {
#                     'citation_content': citation_content,
#                     'author': citation['author'],
#                     'year_published': citation['year_published'],
#                     'original_citation_text': citation['citation_text'],
#                     'citation_type': citation_type,
#                     'needs_manual_check': needs_manual_check
#                 }

#             elif citation_type == 'direct_quote':
#                 citation_entry = {
#                     'citation_content': citation.get('citation_content', ''),
#                     'ref_citations': citation.get('ref_citations', []),
#                     'original_citation_text': citation['original_citation_text'],
#                     'citation_type': citation_type,
#                     'needs_manual_check': needs_manual_check
#                 }

#             elif citation_type == 'parenthetical':
#                 # Trích xuất nội dung sau trích dẫn parenthetical
#                 citation_content = sentence[citation['end']:].strip() if citation['end'] < len(sentence) else ""
#                 citation_entry = {
#                     'citation_content': citation_content,
#                     'ref_citations': citation.get('ref_citations', []),
#                     'original_citation_text': citation['original_citation_text'],
#                     'citation_type': citation_type,
#                     'needs_manual_check': needs_manual_check
#                 }

#             citation_entries.append(citation_entry)

#         results.append({
#             'original_sentence': sentence,
#             'citation_count': citation_count,
#             'citations': citation_entries
#         })

#     return results

# if __name__ == "__main__":
#     # Ví dụ 1
#     text1 = """
#     Jiang et al. (2022) proposed a strategy for the identification of software in scientific bioinformatics publications using the combination of SVM and CRF (Conditional Random Field).
#     """

#     # Ví dụ 2
#     text2 = """
#     Cronin and Weaver (1995) ascribe an acknowledgment alongside authorship and citedness to measures of a researcher’s scholarly performance: a feature that reflects the researcher’s productivity and impact.
#     """

#     # Trích xuất trích dẫn với ngữ cảnh
#     citations1 = extract_citations_with_context(text1)
#     citations2 = extract_citations_with_context(text2)

#     # Gộp kết quả
#     citations = citations1 + citations2

#     # Xuất kết quả ra tệp JSON
#     with open('output.json', 'w', encoding='utf-8') as f:
#         json.dump(citations, f, ensure_ascii=False, indent=4)

#     # In kết quả ra màn hình
#     print(json.dumps(citations, ensure_ascii=False, indent=4))


# #TEST FOR NOUN CHUNKS CASES
# import spacy
# import re

# nlp = spacy.load("en_core_web_sm")

# sentences = [
#     "The training was initiated with a small learning rate using the Adam Optimisation Algorithm (Kingma & Ba, 2014).",
#     "We implemented the BERT model (Devlin et al., 2018) for our text classification task.",
#     "The Transformer architecture (Vaswani et al., 2017) has revolutionized natural language processing.",
#     "For image recognition, we utilized the ResNet (He et al., 2016) architecture.",
#     "The study employed Principal Component Analysis (PCA) (Pearson, 1901) for dimensionality reduction.",
#     "We used the popular k-means clustering algorithm (MacQueen, 1967) in our data analysis.",
#     "The experiment was conducted using Support Vector Machines (Cortes & Vapnik, 1995) for classification.",
#     "Our model is based on the Long Short-Term Memory (LSTM) architecture (Hochreiter & Schmidhuber, 1997).",
#     "We applied the PageRank algorithm (Page et al., 1999) to analyze the network structure.",
#     "The data was processed using the MapReduce framework (Dean & Ghemawat, 2008) for distributed computing."
# ]

# def extract_cited_content(doc):
#     # Tìm kiếm cụm danh từ gần nhất trước dấu ngoặc đơn
#     for token in reversed(list(doc)):
#         if token.text == "(":
#             for chunk in doc.noun_chunks:
#                 if chunk.end == token.i:
#                     content = chunk.text
#                     # Xử lý trường hợp đặc biệt cho viết tắt trong ngoặc
#                     if "(" in content and ")" in content:
#                         content = content.split("(")[0].strip()
#                     return content

#     # Nếu không tìm thấy, sử dụng regex
#     match = re.search(r'(\w+(?:[-\s]\w+)*(?:\s*\([^)]*\))?)\s*\(', doc.text)
#     if match:
#         content = match.group(1)
#         # Xử lý trường hợp đặc biệt cho viết tắt trong ngoặc
#         if "(" in content and ")" in content:
#             content = content.split("(")[0].strip()
#         return content

#     return None

# # Xử lý và trích xuất nội dung từ mỗi câu
# for sentence in sentences:
#     doc = nlp(sentence)
#     content = extract_cited_content(doc)
#     print(f"Sentence: {sentence}")
#     print(f"Extracted content: {content}\n")


# import spacy
# import re

# # Load SpaCy English model
# try:
#     nlp = spacy.load("en_core_web_sm")
# except OSError:
#     import subprocess
#     import sys
#     subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
#     nlp = spacy.load("en_core_web_sm")

# # Sample sentences containing various types of citations
# sentences = [
#     "The training was initiated with a small learning rate using the Adam Optimisation Algorithm (Kingma & Ba, 2014).",
#     "We implemented the BERT model (Devlin et al., 2018) for our text classification task.",
#     "The Transformer architecture (Vaswani et al., 2017) has revolutionized natural language processing.",
#     "For image recognition, we utilized the ResNet (He et al., 2016) architecture.",
#     "The study employed Principal Component Analysis (PCA) (Pearson, 1901) for dimensionality reduction.",
#     "We used the popular k-means clustering algorithm (MacQueen, 1967) in our data analysis.",
#     "The experiment was conducted using Support Vector Machines (Cortes & Vapnik, 1995) for classification.",
#     "Our model is based on the Long Short-Term Memory (LSTM) architecture (Hochreiter & Schmidhuber, 1997).",
#     "We applied the PageRank algorithm (Page et al., 1999) to analyze the network structure.",
#     "The data was processed using the MapReduce framework (Dean & Ghemawat, 2008) for distributed computing.",
#     "Kayal et al. (2017) introduced a method for extraction of funding organizations and grants from acknowledgment texts using a combination of sequential learning models: conditional random fields (CRF), hidden markov models (HMM), and maximum entropy models (MaxEnt)."
# ]

# def clean_author(author):
#     """Clean the author's name by removing periods and trimming whitespace."""
#     return author.replace(".", "").strip()

# def determine_citation_validity(content):
#     """Determine the validity of the citation based on the presence of a 4-digit year."""
#     year_match = re.search(r'\b\d{4}\b', content)
#     return bool(year_match)

# def extract_noun_chunk_before_parentheses(doc, parentheses_char_pos):
#     """
#     Extract the noun chunk immediately before the parenthesis '('.

#     Args:
#         doc (spacy.tokens.Doc): The SpaCy Doc object.
#         parentheses_char_pos (int): The character position of '(' in the sentence.

#     Returns:
#         str: The extracted noun chunk without determiners and trailing punctuations.
#     """
#     # Find all noun_chunks with their start and end character positions
#     noun_chunks = list(doc.noun_chunks)

#     # Find the noun_chunk that ends before parentheses_char_pos and is not within another parenthetical
#     preceding_chunks = []
#     for chunk in noun_chunks:
#         if chunk.end_char <= parentheses_char_pos:
#             # Check if the noun_chunk is within any parenthetical except the current one
#             is_within_other_parenthetical = False
#             for match in re.finditer(r'\([^()]+\)', doc.text):
#                 if match.start() < parentheses_char_pos and match.start() <= chunk.start_char < match.end():
#                     is_within_other_parenthetical = True
#                     break
#             if not is_within_other_parenthetical:
#                 preceding_chunks.append(chunk)

#     if not preceding_chunks:
#         return ''

#     # Get the last noun_chunk that ends before the parenthesis
#     last_noun_chunk = preceding_chunks[-1]

#     # Remove determiners from the noun_chunk
#     tokens = [token.text for token in last_noun_chunk if token.dep_ != "det"]

#     # Join tokens and remove any trailing punctuations
#     noun_phrase = ' '.join(tokens).rstrip(".,;:'\"!?()")
#     return noun_phrase

# def is_proper_noun_chunk(noun_chunk):
#     """Check if the noun chunk contains any proper nouns."""
#     if not noun_chunk:
#         return False
#     doc = nlp(noun_chunk)
#     for token in doc:
#         if token.pos_ == "PROPN":
#             return True
#     return False

# def extract_citations_from_sentence(sentence):
#     """
#     Extract all citations from a sentence.

#     Args:
#         sentence (str): The sentence to process.

#     Returns:
#         list: A list of dictionaries containing citation details.
#     """
#     citations = []
#     doc = nlp(sentence)

#     # Regex patterns for different citation types
#     narrative_citation_regex = r'\b(?P<author>[A-Z][a-zA-Z\'’\-]+(?:\s+(?:et\s+al\.?|and|&)\s*(?:[A-Z][a-zA-Z\'’\-]+)?)*)\s*\((?P<year>\d{4})\)'
#     parenthetical_citation_regex = r'\(([^()]+)\)'
#     direct_quote_regex = r'“(.*?)”\s*\(([^()]+)\)'

#     # 1. Extract Direct Quote Citations
#     for match in re.finditer(direct_quote_regex, sentence):
#         quote = match.group(1).strip()
#         citation_info = match.group(2).strip()
#         start = match.start()
#         end = match.end()

#         # Split multiple citations separated by ';'
#         refs = re.split(r';\s*', citation_info)
#         ref_citations = []
#         for ref in refs:
#             ref = ref.strip()
#             parts = re.split(r',\s*', ref)
#             if len(parts) >= 2:
#                 author = ', '.join(parts[:-1]).strip()
#                 year = parts[-1].strip()
#             else:
#                 author = ref
#                 year = ''
#             ref_citations.append({
#                 'author': clean_author(author),
#                 'year_published': year
#             })
#         citations.append({
#             'type': 'direct_quote',
#             'citation_content': quote,
#             'ref_citations': ref_citations,
#             'original_citation_text': match.group(0),
#             'start': start,
#             'end': end
#         })

#     # Remove direct quotes to prevent duplicate processing
#     sentence_without_direct_quotes = re.sub(direct_quote_regex, '', sentence)
#     doc_without_quotes = nlp(sentence_without_direct_quotes)

#     # 2. Extract Narrative Citations
#     for match in re.finditer(narrative_citation_regex, sentence_without_direct_quotes):
#         author = match.group('author').strip()
#         year = match.group('year').strip()
#         citation_text = match.group(0)
#         start = match.start()
#         end = match.end()
#         citations.append({
#             'type': 'narrative',
#             'author': author,
#             'year': year,
#             'citation_text': citation_text,
#             'start': start,
#             'end': end
#         })

#     # 3. Extract Parenthetical Citations
#     for match in re.finditer(parenthetical_citation_regex, sentence_without_direct_quotes):
#         content = match.group(1).strip()
#         start_char = match.start()
#         end_char = match.end()

#         # Validate citation based on the presence of a year
#         if not determine_citation_validity(content):
#             continue

#         # Split multiple citations separated by ';'
#         refs = re.split(r';\s*', content)
#         ref_citations = []
#         for ref in refs:
#             ref = ref.strip()
#             parts = re.split(r',\s*', ref)
#             if len(parts) >= 2:
#                 author = ', '.join(parts[:-1]).strip()
#                 year = parts[-1].strip()
#             else:
#                 author = ref
#                 year = ''
#             ref_citations.append({
#                 'author': clean_author(author),
#                 'year_published': year
#             })

#         # Extract noun chunk before the parenthesis using noun_chunks
#         noun_chunk = extract_noun_chunk_before_parentheses(doc_without_quotes, start_char)

#         # Check if the noun chunk contains proper nouns
#         is_proper = is_proper_noun_chunk(noun_chunk)

#         # Flag for manual check based on proper noun presence
#         flag_manual_check = is_proper

#         citations.append({
#             'type': 'parenthetical',
#             'noun_chunk': noun_chunk,  # Extracted noun chunk
#             'ref_citations': ref_citations,
#             'original_citation_text': match.group(0),
#             'start': start_char,
#             'end': end_char,
#             'flag_manual_check': flag_manual_check  # Flag for manual verification
#         })

#     # Sort citations based on their position in the sentence
#     citations.sort(key=lambda x: x['start'])

#     return citations

# # Additional helper functions used in extract_citations_with_context
# def clean_text(text):
#     """Clean the input text by removing unnecessary characters or formatting."""
#     # Placeholder for actual text cleaning logic
#     return text

# def extract_sentences(text):
#     """Split text into sentences using SpaCy's sentence segmentation."""
#     doc = nlp(text)
#     return [sent.text for sent in doc.sents]

# def is_insignificant_text(text):
#     """Determine if the preceding text is insignificant for citation context."""
#     # Define insignificant phrases
#     insignificant_phrases = ["", "and", "or", "but", "so", "yet"]
#     return text.lower() in insignificant_phrases

# def get_following_content(sentence, end_pos):
#     """Get the content following the citation."""
#     return sentence[end_pos:].strip()

# def get_preceding_noun_phrase(sentence, start_pos):
#     """Get the noun phrase preceding the citation."""
#     doc = nlp(sentence[:start_pos])
#     noun_chunks = list(doc.noun_chunks)
#     if not noun_chunks:
#         return ''
#     last_noun_chunk = noun_chunks[-1]
#     # Remove determiners
#     tokens = [token.text for token in last_noun_chunk if token.dep_ != "det"]
#     return ' '.join(tokens)

# def extract_citations_with_context(text):
#     """Extract citations from each sentence with contextual information."""
#     text = clean_text(text)
#     sentences = extract_sentences(text)
#     results = []

#     for sentence in sentences:
#         citations_in_sentence = extract_citations_from_sentence(sentence)
#         if not citations_in_sentence:
#             continue

#         citation_entries = []
#         citation_count = len(citations_in_sentence)

#         for idx, citation in enumerate(citations_in_sentence):
#             citation_type = citation.get('type', None)
#             if citation_type is None:
#                 # Skip citations without a type to prevent KeyError
#                 continue

#             start = citation.get('start', None)
#             end = citation.get('end', None)
#             needs_manual_check = False

#             if citation_type == 'narrative':
#                 if idx == 0:
#                     preceding_text = sentence[:start].strip()
#                     if preceding_text == '' or is_insignificant_text(preceding_text):
#                         citation_content = get_following_content(sentence, end)
#                     else:
#                         citation_content = preceding_text
#                 else:
#                     prev_end = citations_in_sentence[idx - 1].get('end', 0)
#                     citation_content = sentence[prev_end:start].strip()

#                 if len(citation_content.strip().split()) < 2:
#                     needs_manual_check = True

#                 author = citation.get('author', '')
#                 author = clean_author(author)
#                 year = citation.get('year', '')
#                 citation_text = citation.get('citation_text', '')
#                 citation_entry = {
#                     'citation_content': citation_content,
#                     'author': author,
#                     'year_published': year,
#                     'original_citation_text': citation_text,
#                     'citation_type': citation_type,
#                     'needs_manual_check': needs_manual_check
#                 }

#             elif citation_type == 'direct_quote':
#                 citation_content = citation.get('citation_content', '')
#                 ref_citations = citation.get('ref_citations', [])
#                 citation_text = citation.get('original_citation_text', '')
#                 citation_entry = {
#                     'citation_content': citation_content,
#                     'ref_citations': ref_citations,
#                     'original_citation_text': citation_text,
#                     'citation_type': citation_type,
#                     'needs_manual_check': needs_manual_check
#                 }

#             else:  # parenthetical
#                 # Handle parenthetical citations according to your specific logic
#                 noun_phrase = citation.get('noun_chunk', '')
#                 if noun_phrase:
#                     citation_content = noun_phrase
#                     needs_manual_check = True
#                 else:
#                     # Fallback to preceding text if noun_phrase is empty
#                     if idx == 0:
#                         preceding_text = sentence[:start].strip()
#                     else:
#                         prev_end = citations_in_sentence[idx - 1].get('end', 0)
#                         preceding_text = sentence[prev_end:start].strip()
#                     citation_content = preceding_text

#                 if len(citation_content.strip().split()) < 2 and not needs_manual_check:
#                     needs_manual_check = True

#                 ref_citations = citation.get('ref_citations', [])
#                 citation_text = citation.get('original_citation_text', '')
#                 citation_entry = {
#                     'citation_content': citation_content,
#                     'ref_citations': ref_citations,
#                     'original_citation_text': citation_text,
#                     'citation_type': citation_type,
#                     'needs_manual_check': needs_manual_check
#                 }

#             citation_entries.append(citation_entry)

#         results.append({
#             'original_sentence': sentence,
#             'citation_count': citation_count,
#             'citations': citation_entries
#         })

#     return results

# # Process each sentence and extract citations
# for sentence in sentences:
#     citations = extract_citations_from_sentence(sentence)
#     print(f"Sentence: {sentence}")
#     for citation in citations:
#         if citation['type'] == 'parenthetical':
#             print(f"  [Parenthetical Citation]")
#             print(f"    Noun Chunk: {citation.get('noun_chunk')}")
#             print(f"    References: {citation.get('ref_citations')}")
#             print(f"    Flag Manual Check: {citation.get('flag_manual_check')}")
#         elif citation['type'] == 'narrative':
#             print(f"  [Narrative Citation]")
#             print(f"    Author: {citation.get('author')}")
#             print(f"    Year: {citation.get('year')}")
#         elif citation['type'] == 'direct_quote':
#             print(f"  [Direct Quote Citation]")
#             print(f"    Quote: {citation.get('citation_content')}")
#             print(f"    References: {citation.get('ref_citations')}")
#     print("\n")

# # Example usage of extract_citations_with_context
# print("=== Extract Citations with Context ===\n")
# for sentence in sentences:
#     context_citations = extract_citations_with_context(sentence)
#     for context in context_citations:
#         print(f"Original Sentence: {context['original_sentence']}")
#         print(f"Citation Count: {context['citation_count']}")
#         for citation in context['citations']:
#             print(f"  Citation Type: {citation['citation_type']}")
#             print(f"    Citation Content: {citation['citation_content']}")
#             if citation['citation_type'] == 'narrative':
#                 print(f"    Author: {citation['author']}")
#                 print(f"    Year Published: {citation['year_published']}")
#             elif citation['citation_type'] == 'direct_quote':
#                 print(f"    Quote: {citation['citation_content']}")
#                 print(f"    References: {citation['ref_citations']}")
#             elif citation['citation_type'] == 'parenthetical':
#                 print(f"    References: {citation['ref_citations']}")
#             print(f"    Needs Manual Check: {citation['needs_manual_check']}")
#         print("\n")


import spacy
# Tải mô hình tiếng Anh
nlp = spacy.load("en_core_web_lg")

def get_noun_phrases_with_entities(sentence):
    """
    Hàm này nhận vào một câu và trả về danh sách các cụm danh từ cùng với thông tin
    về việc chúng có thuộc các Special Entity không.
    """
    doc = nlp(sentence)
    noun_phrases_info = []

    # Trích xuất các cụm danh từ
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text
        # Kiểm tra xem có thực thể đặc biệt (Special Entity) nào nằm trong cụm danh từ không
        special_entities = [ent.label_ for ent in doc.ents if ent.start >= chunk.start and ent.end <= chunk.end]

        if special_entities:
            noun_phrases_info.append((chunk_text, special_entities))
        else:
            noun_phrases_info.append((chunk_text, None))

    return noun_phrases_info

# Câu mẫu
sentence = "Flair has three default training algorithms for NER which were used for the first experiment in the present research: a) NER Model with Flair Embeddings (later on Flair Embeddings) (Akbik et al., 2018), b) NER Model with Transformers (later on Transformers) (Schweter & Akbik, 2020), and c) Zeroshot NER with TARS (later on TARS) (Halder et al., 2020) 8."

# Trích xuất cụm danh từ và kiểm tra thực thể đặc biệt
noun_phrases_with_entities = get_noun_phrases_with_entities(sentence)

# Hiển thị kết quả
print("Câu:", sentence)
print("Các cụm danh từ được nhận diện và thực thể đặc biệt (nếu có):")
for np, entities in noun_phrases_with_entities:
    if entities:
        print(f"- {np} (Special Entity: {', '.join(entities)})")
    else:
        print(f"- {np} (Không có Special Entity)")



# from transformers import AutoTokenizer, AutoModelForTokenClassification
# from transformers import pipeline

# # Tải mô hình SciBERT đã được tinh chỉnh cho NER
# tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
# model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")

# # Sử dụng pipeline cho NER
# ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer)

# # Câu cần phân tích
# sentence = "The training was initiated with a small learning rate using the Adam Optimisation Algorithm (Kingma & Ba, 2014)."

# # Áp dụng NER
# entities = ner_pipeline(sentence)

# # Hiển thị kết quả các thực thể đặc biệt
# for entity in entities:
#     print(f"Entity: {entity['word']}, Label: {entity['entity']}")



