import sys
import json
import time
import re
import shutil
from pathlib import Path

# --- CONFIG ---
# BASE_DIR = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3")
BASE_DIR = Path(__file__).parent / "data_outputs" / "task3"
VALID_SPLITS = ["train", "val", "test_gold_500", "test_silver_2500"]
GENERATOR_NAME = "rules_sentence_extractor_v1"


_CITATION_RE = re.compile(r"\[CITATION_(\d+)\]")
_SENT_START_RE = re.compile(r"[.!?]\s+(?=[A-Z0-9(\\[\"'•])")
_SENT_END_RE = re.compile(r"[.!?](?:\s+[A-Z0-9(\\[\"'•]|\s*$)")


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


def _sentence_start(text, pos):
    start = 0
    for m in _SENT_START_RE.finditer(text[:pos]):
        start = m.end()
    return start


def _sentence_end(text, pos_after_tag):
    after_text = text[pos_after_tag:]
    m = _SENT_END_RE.search(after_text)
    if not m:
        return len(text)
    return pos_after_tag + m.start() + 1


def _sort_marker_key(marker):
    m = _CITATION_RE.match(marker)
    if not m:
        return (1, marker)
    return (0, int(m.group(1)))


def extract_spans(text, markers):
    spans = []
    for cid in sorted(markers, key=_sort_marker_key):
        tag_pos = text.find(cid)
        if tag_pos == -1:
            # Unexpected: marker missing in text. Use full text as "best effort" substring.
            spans.append({"citation_id": cid, "span_text": text})
            continue

        if _is_between_sentences(text, tag_pos, len(cid)):
            span_text = _extract_sentence_before_tag(text, tag_pos, cid)
            spans.append({"citation_id": cid, "span_text": span_text})
            continue

        start = _sentence_start(text, tag_pos)
        end = _sentence_end(text, tag_pos + len(cid))
        span_text = text[start:end]
        spans.append({"citation_id": cid, "span_text": span_text})
    return spans


def process_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("text", "")
    correct_citation = data.get("correct_citation", {}) or {}
    markers = list(correct_citation.keys())

    output = {
        "doc_id": data.get("doc_id", file_path.stem),
        "text": text,
        "correct_citation": correct_citation,
        "citation_spans": extract_spans(text, markers),
        "bib_entries": data.get("bib_entries", {}) or {},
        "generator": GENERATOR_NAME,
    }
    return output


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
                    label_data = json.load(f)
                if label_data is not None:
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
        f"Split: {split} | Pending: {total} | Done: {len(list(done_dir.glob('*.in')))} | Generator: {GENERATOR_NAME}"
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
            if success % 1000 == 0:
                remaining = total - success - failed
                print(f"  [{success}/{total}] done={success} failed={failed} remaining={remaining}")

        except Exception as e:
            failed += 1
            failed_files.append(file_path.name)
            print(f"❌ {file_path.name}: {e}")
            time.sleep(0.2)

    print(f"\n{'='*60}")
    print(f"DONE [{split}]: success={success} | failed={failed}")
    if failed_files:
        print(f"Failed: {failed_files[:20]}")


if __name__ == "__main__":
    main()
