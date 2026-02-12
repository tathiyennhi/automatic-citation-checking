import sys
import json
import time
import re
import shutil
import os
from pathlib import Path
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

from task3_strict import resume_safe_has_valid_label, validate_spans

# Load environment variables
load_dotenv()

# --- CONFIG ---
HF_API_KEY = os.getenv("HF_API_KEY")
# BASE_DIR = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3")
BASE_DIR = Path(__file__).parent / "data_outputs" / "task3"
MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"
VALID_SPLITS = ["train", "val", "test_gold_500", "test_silver_2500"]

client = InferenceClient(token=HF_API_KEY)

SYSTEM_PROMPT = "You are a citation span labeling bot. Output ONLY valid JSON. No explanation. No markdown. No code blocks."

USER_PROMPT = """TASK: Given JSON input, extract the text span that each citation supports.

RULES:
1. Extract the FULL SENTENCE containing [CITATION_X] from 'text'.
2. Cross-reference 'bib_entries' (title/abstract) to understand the citation content.
3. CRITICAL: span_text MUST be an EXACT substring of 'text'. Copy character by character.
   KEEP all [CITATION_X] tags exactly as they appear. Do NOT remove or modify them.
4. If multiple citations are in the same sentence, all of them get the same full sentence as span_text.
5. Do NOT add, remove, or change any characters. Exact copy from 'text'.
6. STRICT RULE: If [CITATION_X] appears between two sentences (after a period, before a new sentence
   starting with a capital letter, e.g. "Sentence A. [CITATION_X] Sentence B."), it supports
   Sentence A. Extract "Sentence A. [CITATION_X]" as the span. Do NOT include Sentence B.

OUTPUT: JSON only. No explanation. No markdown. No code blocks.
{"citation_spans": [{"citation_id": "[CITATION_1]", "span_text": "..."}]}

Input:
"""


def _skip_ws_and_tags_right(text, pos):
    while pos < len(text):
        if text[pos] in ' \t\n':
            pos += 1
        else:
            m = re.match(r'\[CITATION_\d+\]', text[pos:])
            if m:
                pos += m.end()
            else:
                break
    return pos


def _skip_ws_and_tags_left(text, pos):
    while pos >= 0:
        if text[pos] in ' \t\n':
            pos -= 1
        elif text[pos] == ']':
            m = re.search(r'\[CITATION_\d+\]$', text[max(0, pos - 20):pos + 1])
            if m:
                pos -= len(m.group(0))
            else:
                break
        else:
            break
    return pos


def _is_between_sentences(text, tag_pos, tag_len):
    left = _skip_ws_and_tags_left(text, tag_pos - 1)
    if left < 0 or text[left] != '.':
        return False
    right = _skip_ws_and_tags_right(text, tag_pos + tag_len)
    if right >= len(text):
        return False
    return text[right].isupper()


def _extract_sentence_before_tag(text, tag_pos, tag):
    end_pos = tag_pos + len(tag)
    while end_pos < len(text):
        tmp = end_pos
        while tmp < len(text) and text[tmp] in ' \t\n':
            tmp += 1
        m = re.match(r'\[CITATION_\d+\]', text[tmp:]) if tmp < len(text) else None
        if m:
            end_pos = tmp + m.end()
        else:
            break

    i = _skip_ws_and_tags_left(text, tag_pos - 1)

    search = i - 1
    while search >= 0:
        if text[search] == '.':
            j = _skip_ws_and_tags_right(text, search + 1)
            if j <= i and text[j].isupper():
                return text[j:end_pos]
        search -= 1
    return text[0:end_pos]


def fix_spans(text, citation_spans):
    fixed = []
    for span in citation_spans:
        cid = span["citation_id"]
        st = span["span_text"]
        tag_pos = text.find(cid)
        if tag_pos == -1:
            fixed.append(span)
            continue

        if _is_between_sentences(text, tag_pos, len(cid)):
            candidate = _extract_sentence_before_tag(text, tag_pos, cid)
            fixed.append({"citation_id": cid, "span_text": candidate})
            continue

        if text.find(st) != -1:
            fixed.append(span)
            continue

        cleaned = st.replace(cid + " ", "").replace(" " + cid, "").replace(cid, "").strip()
        if cleaned:
            clean_pos = text.find(cleaned)
            if clean_pos != -1:
                if text.find(cid + " " + cleaned) != -1:
                    fixed.append({"citation_id": cid, "span_text": cid + " " + cleaned})
                    continue
                if text.find(cleaned + " " + cid) != -1:
                    fixed.append({"citation_id": cid, "span_text": cleaned + " " + cid})
                    continue
        fixed.append(span)
    return fixed


def extract_json(text):
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Cannot extract JSON: {text[:300]}")


def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    user_input = json.dumps(data, ensure_ascii=False)
    markers = list((data.get("correct_citation", {}) or {}).keys())
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT + user_input}
    ]

    for attempt in range(3):
        try:
            response = client.chat_completion(
                messages=messages,
                model=MODEL_NAME,
                max_tokens=2048,
                temperature=0.1
            )
            raw_text = response.choices[0].message.content
            result = extract_json(raw_text)

            spans = fix_spans(data["text"], result.get("citation_spans", []))
            errors = validate_spans(data["text"], markers, spans)
            if errors:
                raise ValueError(f"Invalid spans: {errors}")

            output = {
                "doc_id": data.get("doc_id", file_path.stem),
                "text": data["text"],
                "correct_citation": data.get("correct_citation", {}),
                "citation_spans": spans,
                "bib_entries": data.get("bib_entries", {}),
                "generator": MODEL_NAME
            }
            return output

        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif attempt == 2:
                raise e
            else:
                time.sleep(5)
    raise Exception("All retries exhausted")


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "train"
    if split not in VALID_SPLITS:
        print(f"Invalid split '{split}'. Valid: {VALID_SPLITS}")
        sys.exit(1)

    pending_dir = BASE_DIR / split / "pending"
    done_dir = BASE_DIR / split / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    # Recovery: move back .in files in done/ that have missing or invalid .label
    recovered = 0
    for in_file in done_dir.glob("*.in"):
        label_file = done_dir / in_file.name.replace(".in", ".label")
        valid = False
        if label_file.exists() and label_file.stat().st_size > 0:
            try:
                with open(label_file) as f:
                    data = json.load(f)
                if data is not None:
                    valid = True
            except (json.JSONDecodeError, Exception):
                pass
        if not valid:
            shutil.move(str(in_file), str(pending_dir / in_file.name))
            if label_file.exists():
                label_file.unlink()
            recovered += 1
    if recovered:
        print(f"Recovered {recovered} incomplete files back to pending/")

    def sort_key(path: Path):
        try:
            return (0, int(path.stem))
        except ValueError:
            return (1, path.stem)

    files = sorted(pending_dir.glob("*.in"), key=sort_key)
    total = len(files)
    print(f"Split: {split} | Pending: {total} | Done: {len(list(done_dir.glob('*.in')))} | Model: {MODEL_NAME}")

    success, failed = 0, 0
    failed_files = []

    for i, file_path in enumerate(files):
        try:
            # If a valid label already exists in done/ (e.g., previous run wrote label but crashed
            # before moving .in), just move the .in over and continue without re-calling HF.
            existing_label = done_dir / file_path.name.replace(".in", ".label")
            if resume_safe_has_valid_label(existing_label):
                shutil.move(str(file_path), str(done_dir / file_path.name))
                success += 1
                if success % 100 == 0:
                    remaining = total - success - failed
                    print(f"  [{success}/{total}] done={success} failed={failed} remaining={remaining}")
                continue

            output = process_file(file_path)

            # Save .label to done/
            label_path = done_dir / file_path.name.replace(".in", ".label")
            with open(label_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            # Move .in to done/
            shutil.move(str(file_path), str(done_dir / file_path.name))

            success += 1

            if success % 100 == 0:
                remaining = total - success - failed
                print(f"  [{success}/{total}] done={success} failed={failed} remaining={remaining}")

            time.sleep(1)

        except Exception as e:
            failed += 1
            failed_files.append(file_path.name)
            print(f"❌ {file_path.name}: {e}")

    print(f"\n{'='*60}")
    print(f"DONE [{split}]: success={success} | failed={failed}")
    if failed_files:
        print(f"Failed: {failed_files[:20]}")


if __name__ == "__main__":
    main()
