import os
import json
import spacy

# Load spaCy model (English)
nlp = spacy.load("en_core_web_sm")

def extract_claim_span(text, marker):
    """
    Extract claim span chính xác cho từng citation marker với debug
    """
    if marker not in text:
        return ""
    
    # DEBUG: In ra để kiểm tra
    print(f"\n=== DEBUG {marker} ===")
    marker_pos = text.find(marker)
    print(f"Marker position: {marker_pos}")
    print(f"Text around marker: '{text[max(0, marker_pos-50):marker_pos+50]}'")
    
    # Tách text thành sentences bằng regex đơn giản trước
    import re
    # Split by sentence endings, nhưng giữ lại delimiters
    sentences = re.split(r'(\. )', text)
    
    # Rebuild sentences with proper boundaries
    rebuilt_sentences = []
    current = ""
    for i, part in enumerate(sentences):
        current += part
        if part == ". " or i == len(sentences) - 1:  # End of sentence
            if current.strip():
                rebuilt_sentences.append(current.strip())
            current = ""
    
    print(f"Sentences found: {len(rebuilt_sentences)}")
    for i, sent in enumerate(rebuilt_sentences):
        print(f"  {i}: '{sent[:60]}...'")
    
    # Tìm sentence chứa marker
    target_sentence = None
    sentence_start_pos = 0
    
    for sent in rebuilt_sentences:
        sentence_end_pos = sentence_start_pos + len(sent)
        
        # Check xem marker có nằm trong sentence này không
        if sentence_start_pos <= marker_pos <= sentence_end_pos:
            target_sentence = sent
            print(f"Found target sentence: '{sent}'")
            break
        
        # Move to next sentence (account for spacing)
        sentence_start_pos = sentence_end_pos + 1  # +1 for space
    
    if not target_sentence:
        print("ERROR: No target sentence found!")
        return ""
    
    # Tìm vị trí marker trong sentence
    marker_in_sentence = target_sentence.find(marker)
    if marker_in_sentence == -1:
        print("ERROR: Marker not found in target sentence!")
        return ""
    
    print(f"Marker position in sentence: {marker_in_sentence}")
    
    # Extract before và after
    before = target_sentence[:marker_in_sentence].strip()
    after = target_sentence[marker_in_sentence + len(marker):].strip()
    
    print(f"Before: '{before}'")
    print(f"After: '{after}'")
    
    # Quyết định lấy phần nào
    if before and len(before.split()) >= 3:
        claim_text = before.rstrip('.,;:')
    elif after and len(after.split()) >= 3:
        claim_text = after.lstrip('.,;:')
    else:
        # Combine cả 2
        parts = []
        if before:
            parts.append(before.rstrip('.,;:'))
        if after:
            parts.append(after.lstrip('.,;:'))
        claim_text = " ".join(parts)
    
    # Clean up citation markers khác
    claim_text = re.sub(r'\[CITATION_\d+\]', '', claim_text)
    claim_text = re.sub(r'\[Citation_\d+\]', '', claim_text)
    claim_text = " ".join(claim_text.split()).strip()
    
    print(f"Final claim: '{claim_text}'")
    print("=== END DEBUG ===\n")
    
    return claim_text

def process_label_file(label_path):
    with open(label_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    results = []
    
    # BUG 1: Sửa từ "texts" thành "text" (theo JSON structure)
    text_content = data.get("text", "")
    
    # BUG 2: Sửa từ "correct_citations" thành "correct_citation" 
    correct_citations = data.get("correct_citation", {})
    
    # BUG 3: Duyệt qua từng citation marker trong text
    for marker, ref_id in correct_citations.items():
        if marker in text_content:
            claim_span = extract_claim_span(text_content, marker)
            if claim_span:  # Chỉ add nếu có claim_span
                results.append({
                    "marker": marker,
                    "claim_span": claim_span,
                    "reference_id": ref_id
                })
    
    # Xuất ra file .task3
    out_path = label_path.replace(".label", ".task3")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✔ Generated {out_path} with {len(results)} samples")

def main():
    cwd = os.getcwd()
    for file in os.listdir(cwd):
        if file.endswith(".label"):
            process_label_file(os.path.join(cwd, file))

if __name__ == "__main__":
    main()