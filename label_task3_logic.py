import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from task3_strict import validate_spans, resume_safe_has_valid_label


BASE_DIR = Path(__file__).parent / "data_outputs" / "task3"
VALID_SPLITS = ["train", "val", "test_gold_500", "test_silver_2500"]
SENTENCE_ENDINGS = ".!?"


def _sort_key(path: Path):
    try:
        return (0, int(path.stem))
    except ValueError:
        return (1, path.stem)


def _skip_ws_and_tags_right(text: str, pos: int) -> int:
    while pos < len(text):
        if text[pos] in " \t\n":
            pos += 1
            continue
        if text.startswith("[CITATION_", pos):
            end = text.find("]", pos)
            if end != -1:
                pos = end + 1
                continue
        break
    return pos


def _skip_ws_and_tags_left(text: str, pos: int) -> int:
    while pos >= 0:
        if text[pos] in " \t\n":
            pos -= 1
            continue
        if text[pos] == "]":
            start = text.rfind("[CITATION_", max(0, pos - 32), pos + 1)
            if start != -1 and text.find("]", start, pos + 1) == pos:
                pos = start - 1
                continue
        break
    return pos


def _is_between_sentences(text: str, tag_pos: int, tag_len: int) -> bool:
    left = _skip_ws_and_tags_left(text, tag_pos - 1)
    if left < 0 or text[left] not in SENTENCE_ENDINGS:
        return False
    right = _skip_ws_and_tags_right(text, tag_pos + tag_len)
    if right >= len(text):
        return False
    return text[right].isupper()


def _extract_sentence_before_tag(text: str, tag_pos: int, tag: str) -> str:
    end_pos = tag_pos + len(tag)
    while end_pos < len(text):
        tmp = end_pos
        while tmp < len(text) and text[tmp] in " \t\n":
            tmp += 1
        if text.startswith("[CITATION_", tmp):
            close = text.find("]", tmp)
            if close != -1:
                end_pos = close + 1
                continue
        break

    left = _skip_ws_and_tags_left(text, tag_pos - 1)
    search = left - 1
    while search >= 0:
        if _looks_like_sentence_boundary(text, search):
            start = _skip_ws_and_tags_right(text, search + 1)
            if start <= left and start < len(text):
                return text[start:end_pos]
        search -= 1
    return text[:end_pos]


def _sentence_start(text: str, pos: int) -> int:
    search = pos - 1
    while search >= 0:
        if _looks_like_sentence_boundary(text, search):
            return _skip_ws_and_tags_right(text, search + 1)
        search -= 1
    return 0


def _sentence_end(text: str, pos: int) -> int:
    search = pos
    while search < len(text):
        if _looks_like_sentence_boundary(text, search):
            return search + 1
        search += 1
    return len(text)


def _count_marker_occurrences(text: str, marker: str) -> int:
    count = 0
    start = 0
    while True:
        idx = text.find(marker, start)
        if idx == -1:
            return count
        count += 1
        start = idx + len(marker)


def _looks_like_sentence_boundary(text: str, pos: int) -> bool:
    if pos < 0 or pos >= len(text) or text[pos] not in SENTENCE_ENDINGS:
        return False
    if pos + 1 < len(text) and text[pos + 1].islower():
        return False

    next_pos = _skip_ws_and_tags_right(text, pos + 1)
    if next_pos >= len(text):
        return True
    if text[next_pos] in SENTENCE_ENDINGS:
        return False
    return text[next_pos].isupper()


def ensure_strict_span(text: str, marker: str, span: str) -> None:
    if _count_marker_occurrences(text, marker) != 1:
        raise ValueError(f"Ambiguous marker occurrence count for {marker}")
    if text.find(span) == -1:
        raise ValueError(f"Span is not exact substring for {marker}")
    if marker not in span:
        raise ValueError(f"Span missing marker for {marker}")

    span_start = text.find(span)
    span_end = span_start + len(span)

    if span_start > 0:
        prev = _skip_ws_and_tags_left(text, span_start - 1)
        if prev >= 0 and not _looks_like_sentence_boundary(text, prev):
            raise ValueError(f"Unclear sentence start for {marker}")

    next_pos = _skip_ws_and_tags_right(text, span_end)
    if span_end < len(text):
        terminal = _skip_ws_and_tags_left(text, span_end - 1)
        if terminal < 0 or not _looks_like_sentence_boundary(text, terminal):
            raise ValueError(f"Unclear sentence end for {marker}")
        if next_pos < len(text) and not text[next_pos].isupper():
            raise ValueError(f"Unclear next sentence boundary for {marker}")


def extract_span_for_marker(text: str, marker: str) -> str:
    tag_pos = text.find(marker)
    if tag_pos == -1:
        raise ValueError(f"Marker not found in text: {marker}")

    if _is_between_sentences(text, tag_pos, len(marker)):
        span = _extract_sentence_before_tag(text, tag_pos, marker)
        ensure_strict_span(text, marker, span)
        return span

    start = _sentence_start(text, tag_pos)
    end = _sentence_end(text, tag_pos + len(marker))
    span = text[start:end]
    if marker not in span:
        raise ValueError(f"Extracted span missing marker: {marker}")
    ensure_strict_span(text, marker, span)
    return span


def process_file(file_path: Path) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = data["text"]
    markers = list((data.get("correct_citation") or {}).keys())
    citation_spans = [{"citation_id": marker, "span_text": extract_span_for_marker(text, marker)} for marker in markers]

    errors = validate_spans(text, markers, citation_spans)
    if errors:
        raise ValueError(f"Invalid spans: {errors}")

    return {
        "doc_id": data.get("doc_id", file_path.stem),
        "text": text,
        "correct_citation": data.get("correct_citation", {}),
        "citation_spans": citation_spans,
        "bib_entries": data.get("bib_entries", {}),
        "generator": "logic:full-sentence-heuristic-v1-strict",
    }


def run_test(split: str, limit: int) -> None:
    pending_dir = BASE_DIR / split / "pending"
    files = sorted(pending_dir.glob("*.in"), key=_sort_key)[:limit]
    if not files:
        print(f"No .in files found in {pending_dir}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = Path(__file__).parent / "test_results" / f"logic_test_{split}_{timestamp}"
    test_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== LOGIC TEST MODE ===")
    print(f"Split: {split} | Files: {len(files)}")
    print(f"Output: {test_dir}")

    success = 0
    failed = 0
    for i, file_path in enumerate(files, 1):
        try:
            output = process_file(file_path)
            label_path = test_dir / file_path.name.replace(".in", ".label")
            with open(label_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            success += 1
            print(f"  [{i}/{len(files)}] {file_path.name} -> OK")
        except Exception as e:
            failed += 1
            print(f"  [{i}/{len(files)}] {file_path.name} -> FAILED: {e}")

    print(f"\nRESULTS: {success}/{len(files)} OK, failed={failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Heuristic citation span labeler")
    parser.add_argument("split", nargs="?", default="train", choices=VALID_SPLITS)
    parser.add_argument("--test", type=int, nargs="?", const=5, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.test is not None:
        run_test(args.split, args.test)
        return

    split = args.split
    pending_dir = BASE_DIR / split / "pending"
    done_dir = BASE_DIR / split / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    recovered = 0
    for in_file in done_dir.glob("*.in"):
        label_file = done_dir / in_file.name.replace(".in", ".label")
        if resume_safe_has_valid_label(label_file):
            continue
        shutil.move(str(in_file), str(pending_dir / in_file.name))
        if label_file.exists():
            label_file.unlink()
        recovered += 1
    if recovered:
        print(f"Recovered {recovered} incomplete files back to pending/")

    files = sorted(pending_dir.glob("*.in"), key=_sort_key)
    if args.limit is not None:
        files = files[:args.limit]
    total = len(files)
    print(f"Split: {split} | Pending: {total} | Done: {len(list(done_dir.glob('*.in')))} | Model: logic")

    success = 0
    failed = 0
    failed_files = []

    for i, file_path in enumerate(files, 1):
        try:
            existing_label = done_dir / file_path.name.replace(".in", ".label")
            if resume_safe_has_valid_label(existing_label):
                shutil.move(str(file_path), str(done_dir / file_path.name))
                success += 1
                continue

            output = process_file(file_path)

            with open(existing_label, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            shutil.move(str(file_path), str(done_dir / file_path.name))
            success += 1

            if i % 100 == 0:
                remaining = total - success - failed
                print(f"  [{i}/{total}] done={success} failed={failed} remaining={remaining}")
        except Exception as e:
            failed += 1
            failed_files.append(file_path.name)
            print(f"  [{i}/{total}] {file_path.name} -> FAILED: {e}")

    print(f"\nDONE [{split}]: success={success} | failed={failed}")
    if failed_files:
        print(f"Failed: {failed_files[:20]}")


if __name__ == "__main__":
    main()
