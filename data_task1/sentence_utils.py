# sentence_utils.py - Improved sentence splitting logic

import re
from typing import List
from nltk.tokenize import sent_tokenize


def post_process_merge_sentences(sentences: List[str]) -> List[str]:
    """
    Post-process NLTK sentences to merge wrongly split ones

    Common issues to fix:
    1. Citation split: "(Anon." + "2018)."
    2. Very short fragments (< 20 chars) that should merge with previous
    3. Fragments starting with year/lowercase
    4. "Fig./Table/Eq./Sect." + number
    5. Short abbreviation + lowercase
    """
    if not sentences:
        return []

    result = []
    i = 0

    while i < len(sentences):
        current = sentences[i].strip()

        # Look ahead to see if we should merge
        should_merge = False
        if i + 1 < len(sentences):
            next_sent = sentences[i + 1].strip()

            # Case 1: Current ends with "(Author." and next is short
            # Example: "(Anon." + "2018)."
            if re.search(r'\([A-Z][a-z]+\.$', current) and len(next_sent) < 30:
                should_merge = True

            # Case 2: Current ends with "et al." and next starts with year in parentheses
            # Example: "Hui et al." + "(2021) proposed..." or "( 2021 ) proposed..."
            elif (re.search(r'\bet al\.$', current) and
                  re.match(r'^\(\s*\d{4}[a-z]?\s*\)', next_sent)):
                should_merge = True

            # Case 2b: Current ends with "et al." and next starts with year) (nested citation)
            # Example: "PointNet++ (Qi et al." + "2017) for place recognition..."
            # Also handles: "2021), PPT-Net..." (comma after paren)
            elif (re.search(r'\bet al\.$', current) and
                  re.match(r'^\d{4}[a-z]?\)', next_sent)):
                should_merge = True

            # Case 2c: Current ends with "et al." and next starts with [number] (IEEE citation)
            # Example: "Mukhopadhyay et al." + "[116] proposed..."
            elif (re.search(r'\bet al\.$', current) and
                  re.match(r'^\[\d+\]', next_sent)):
                should_merge = True

            # Case 2d: Current ends with "et al." and next starts with 's (possessive)
            # Example: "Pennycook et al." + "'s participants..."
            elif (re.search(r'\bet al\.$', current) and
                  next_sent.startswith("'s ")):
                should_merge = True

            # Case 2e: Current ends with "et al." and next is lowercase continuation (short)
            # Example: "Du et al." + "in their previous study"
            elif (re.search(r'\bet al\.$', current) and
                  len(next_sent) < 50 and
                  re.match(r'^[a-z]', next_sent)):
                should_merge = True

            # Case 3: Next sentence is very short and starts with year/number/lowercase
            # Example: "area (Anon." + "2018b)."
            elif (len(next_sent) < 20 and
                  (re.match(r'^\d{4}', next_sent) or
                   re.match(r'^[a-z0-9]', next_sent) or
                   next_sent.startswith(')'))):
                should_merge = True

            # Case 3: Next sentence is just a parenthesis closer
            # Example: "text" + ")."
            elif re.match(r'^\)\.?$', next_sent):
                should_merge = True

            # Case 4: Current ends with "Fig./Table/Eq./Sect." + next starts with number
            # Example: "As shown in Fig." + "9, the result..."
            elif (re.search(r'\b(Fig|Table|Eq|Sect|Section)\.$', current, re.IGNORECASE) and
                  re.match(r'^\d', next_sent)):
                should_merge = True

            # Case 5: Current ends with short abbreviation (2-4 chars) + next starts lowercase
            # Example: "...B.D." + "covering a distance..."
            # BUT skip common ones that NLTK handles well: Dr., Mr., Mrs., Ms.
            elif (re.search(r'\b[A-Z]{1,2}\.[A-Z]{1,2}\.$', current) and  # U.S., B.D., R.A.
                  re.match(r'^[a-z]', next_sent) and
                  not re.search(r'\b(Dr|Mr|Mrs|Ms)\.$', current)):
                should_merge = True

        if should_merge:
            current = current + " " + sentences[i + 1].strip()
            i += 2  # Skip next sentence
        else:
            i += 1

        if current:
            result.append(current)

    return result


def remove_heading_prefix(sentence: str) -> str:
    """
    Remove heading text that got concatenated to sentence start

    Example: "INTRODUCTIONDeep learning..." → "Deep learning..."
    """
    # Pattern: consecutive uppercase letters/spaces followed by uppercase + lowercase
    # Example: "INTRODUCTION" before "Deep"
    pattern = r'^([A-Z\s]{3,}?)(?=[A-Z][a-z])'
    return re.sub(pattern, '', sentence).strip()


def improved_sentence_split(text: str) -> List[str]:
    """
    Improved sentence splitting:
    1. Use NLTK as base (handles most cases well)
    2. Post-process to merge wrongly split sentences
    3. Remove heading prefixes
    """
    # Step 1: NLTK split (baseline)
    sentences = sent_tokenize(text)

    # Step 2: Merge wrongly split sentences
    sentences = post_process_merge_sentences(sentences)

    # Step 3: Clean up each sentence
    result = []
    for sent in sentences:
        # Remove heading prefix
        sent = remove_heading_prefix(sent)

        # Skip if too short or empty
        if len(sent.strip()) > 10:
            result.append(sent.strip())

    return result
