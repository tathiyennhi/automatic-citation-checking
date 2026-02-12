import os
import sys
import json
import time
import re
import shutil
from pathlib import Path
from urllib import request, error

# --- CONFIG ---
# BASE_DIR = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3")
BASE_DIR = Path(__file__).parent / "data_outputs" / "task3"
VALID_SPLITS = ["train", "val", "test_gold_500", "test_silver_2500"]

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0"))
NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))
SEED = os.getenv("OLLAMA_SEED")

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

_CITATION_RE = re.compile(r"\[CITATION_(\d+)\]")


def _skip_ws_and_tags_right(text, pos):
    while pos < len(text):
        if text[pos] in " \t\n":
            pos += 1
        else:
            m = re.match(r"\[CITATION_\d+\]", text[pos:])
            if m:
                pos += m.end()
            else:
                break
    return pos


def _skip_ws_and_tags_left(text, pos):
    while pos >= 0:
        if text[pos] in " \t\n":
            pos -= 1
        elif text[pos] == "]":
            m = re.search(r"\[CITATION_\d+\]$", text[max(0, pos - 20) : pos + 1])
            if m:
                pos -= len(m.group(0))
            else:
                break
        else:
            break
    return pos


def _is_between_sentences(text, tag_pos, tag_len):
    left = _skip_ws_and_tags_left(text, tag_pos - 1)
    if left < 0 or text[left] != ".":
        return False
    right = _skip_ws_and_tags_right(text, tag_pos + tag_len)
    if right >= len(text):
        return False
    return text[right].isupper()


def _extract_sentence_before_tag(text, tag_pos, tag):
    end_pos = tag_pos + len(tag)
    while end_pos < len(text):
        tmp = end_pos
        while tmp < len(text) and text[tmp] in " \t\n":
            tmp += 1
        m = re.match(r"\[CITATION_\d+\]", text[tmp:]) if tmp < len(text) else None
        if m:
            end_pos = tmp + m.end()
        else:
            break

    i = _skip_ws_and_tags_left(text, tag_pos - 1)

    search = i - 1
    while search >= 0:
        if text[search] == ".":
            j = _skip_ws_and_tags_right(text, search + 1)
            if j <= i and text[j].isupper():
                return text[j:end_pos]
        search -= 1
    return text[0:end_pos]


def _sort_marker_key(marker):
    m = _CITATION_RE.match(marker)
    if not m:
        return (1, marker)
    return (0, int(m.group(1)))


def _normalize_spans_from_model(model_spans):
    if not isinstance(model_spans, list):
        return []
    norm = []
    for s in model_spans:
        if not isinstance(s, dict):
            continue
        cid = s.get("citation_id")
        st = s.get("span_text")
        if not isinstance(cid, str) or not isinstance(st, str):
            continue
        norm.append({"citation_id": cid, "span_text": st})
    return norm


def validate_spans(text, markers, model_spans):
    """
    Enforce hard constraints:
    - span_text must be an exact substring of text
    - span_text must contain its citation_id tag
    - every marker must have an entry
    """
    markers_sorted = sorted(markers, key=_sort_marker_key)
    normalized = _normalize_spans_from_model(model_spans)

    by_id = {s["citation_id"]: s["span_text"] for s in normalized if s["citation_id"] not in (None, "")}

    errors = []
    missing = [cid for cid in markers_sorted if cid not in by_id]
    if missing:
        errors.append(f"Missing citation_ids: {missing}")

    for cid in markers_sorted:
        if cid not in by_id:
            continue
        st = by_id[cid]
        if not isinstance(st, str):
            errors.append(f"{cid}: span_text is not a string")
            continue
        if cid not in st:
            errors.append(f"{cid}: span_text does not include the citation tag")
        if text.find(st) == -1:
            errors.append(f"{cid}: span_text is not an exact substring of text")

    extras = sorted([cid for cid in by_id.keys() if cid not in set(markers_sorted)], key=_sort_marker_key)
    if extras:
        errors.append(f"Unknown extra citation_ids: {extras}")

    return errors


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

    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Cannot extract JSON: {text[:300]}")


def _post_chat(payload, timeout=180):
    url = f"{OLLAMA_HOST.rstrip('/')}/api/chat"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def chat_ollama(messages, model=MODEL_NAME, temperature=TEMPERATURE, num_predict=NUM_PREDICT):
    """
    Calls Ollama's /api/chat. Tries `format: json` first for stricter output;
    falls back to no format if the server doesn't support it.
    """
    base_payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "top_p": 1.0, "num_predict": num_predict},
    }
    if SEED is not None and SEED != "":
        try:
            base_payload["options"]["seed"] = int(SEED)
        except ValueError:
            pass

    # Attempt 1: request JSON format (supported in modern Ollama)
    payload = dict(base_payload)
    payload["format"] = "json"
    status, text = _post_chat(payload)
    if status == 200:
        data = json.loads(text)
        return data["message"]["content"]

    # If `format` not supported, retry without it.
    if status in (400, 404):
        payload = dict(base_payload)
        status2, text2 = _post_chat(payload)
        if status2 == 200:
            data = json.loads(text2)
            return data["message"]["content"]
        raise RuntimeError(f"Ollama error {status2}: {text2[:300]}")

    raise RuntimeError(f"Ollama error {status}: {text[:300]}")


def process_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_input = json.dumps(data, ensure_ascii=False)
    markers = list((data.get("correct_citation", {}) or {}).keys())
    base_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT + user_input},
    ]

    for attempt in range(3):
        try:
            messages = list(base_messages)
            if attempt > 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous output was invalid.\n"
                            "Fix it and output ONLY valid JSON.\n"
                            "Hard constraints:\n"
                            "- For each citation_id in correct_citation, span_text MUST contain that exact [CITATION_X] tag.\n"
                            "- span_text MUST be an exact substring of the provided text.\n"
                            "- Return one entry per citation_id.\n"
                        ),
                    }
                )

            raw_text = chat_ollama(messages=messages)
            result = extract_json(raw_text)
            spans = fix_spans(data["text"], result.get("citation_spans", []))
            errors = validate_spans(data["text"], markers, spans)
            if errors:
                raise ValueError("Invalid spans: " + "; ".join(errors) + f" | raw={raw_text[:300]!r}")

            output = {
                "doc_id": data.get("doc_id", file_path.stem),
                "text": data["text"],
                "correct_citation": data.get("correct_citation", {}),
                "citation_spans": spans,
                "bib_entries": data.get("bib_entries", {}),
                "generator": f"ollama:{MODEL_NAME}",
            }
            return output

        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(3 * (attempt + 1))

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
                    _ = json.load(f)
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
    print(
        f"Split: {split} | Pending: {total} | Done: {len(list(done_dir.glob('*.in')))} | Model: ollama:{MODEL_NAME}"
    )

    success, failed = 0, 0
    failed_files = []

    for file_path in files:
        try:
            output = process_file(file_path)

            label_path = done_dir / file_path.name.replace(".in", ".label")
            with open(label_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            shutil.move(str(file_path), str(done_dir / file_path.name))

            success += 1
            if success % 50 == 0:
                remaining = total - success - failed
                print(f"  [{success}/{total}] done={success} failed={failed} remaining={remaining}")

            time.sleep(0.1)

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
