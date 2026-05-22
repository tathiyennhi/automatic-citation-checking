"""
LLM Inference — Gemma 4 E4B (Few-shot)
Citation prediction on 250-file subset via Ollama local.

Usage:
  python llm_inference_gemma.py
"""

import json
import re
from pathlib import Path

import ollama


# ── Config ───────────────────────────────────────────────────
SUBSET_DIR  = Path("./data_outputs/task2/test_subset_250")
OUTPUT_DIR  = Path("./data_outputs/task2/cocitation_results/predictions/gemma_4_e4b")
MODEL_ID    = "gemma4:e4b"
MAX_RETRIES = 2

TEMPERATURE = 0.0
NUM_PREDICT = 50
NUM_CTX     = 32768

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Prompt ───────────────────────────────────────────────────
def create_prompt(in_data, citation_marker):
    text = in_data["text"].replace(citation_marker, "[MASK]")

    candidate_list = ""
    for ref_id in in_data["bib_entries"].keys():
        entry    = in_data["bib_entries"].get(ref_id, {})
        title    = entry.get("title", "")
        abstract = entry.get("abstract", "")
        candidate_list += f"- {ref_id}: \"{title}\" - {abstract}\n"

    return f"""### Instruction ###

I will provide you with some examples of citation prediction. Your task is to predict which paper is cited at the masked position [MASK] in a scientific paragraph. You MUST return ONLY the numeric ID exactly as it appears in the candidates list. Do not add any prefix or explanation.

### Context ###

A citation prediction task has 3 components:
- The paragraph text: which contains the citation context
- The masked position: where [MASK] appears in the text
- Candidate papers: a list of papers with ref_id, title, and abstract

Each candidate paper is a bibliography entry from the same scientific paper. Your goal is to identify which candidate paper best matches or supports the citation context at [MASK].

Use only the provided paragraph and candidate papers. Do not invent new reference IDs. If multiple citations appear in the paragraph, predict only the paper cited at the current [MASK] position.

### Example 1 ###

Input:

Paragraph: "Recent work [MASK] showed that transformer models outperform recurrent neural networks on various NLP tasks."

Candidates:
- 17512345: "Attention is All You Need" - We propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output...
- 29834761: "Long Short-Term Memory Networks" - We introduce LSTM networks, a type of recurrent neural network capable of learning long-term dependencies in sequence data...

Output:

17512345

### Example 2 ###

Input:

Paragraph: "Sentiment analysis approaches [MASK] have achieved state-of-the-art results on standard benchmark datasets."

Candidates:
- 38291047: "Convolutional Neural Networks for Sentence Classification" - We report on a series of experiments with convolutional neural networks trained on top of pre-trained word vectors for sentence-level classification tasks...
- 51023894: "Deep Learning for Computer Vision" - This paper presents a comprehensive survey of deep learning techniques for image recognition and object detection...

Output:

38291047

### Now predict ###

Input:

Paragraph: "{text}"

Candidates:
{candidate_list}
Output:
"""


# ── Parse ────────────────────────────────────────────────────
def parse_ref_id(response_text, valid_ids):
    response_text = response_text.strip()
    for ref_id in valid_ids:
        ref_id  = str(ref_id)
        pattern = rf"(?<!\d){re.escape(ref_id)}(?!\d)"
        if re.search(pattern, response_text):
            return ref_id
    return None


# ── Main ─────────────────────────────────────────────────────
def main():
    label_files = sorted(SUBSET_DIR.glob("*.label"), key=lambda f: int(f.stem))
    print(f"✅ Found {len(label_files)} files | Model: {MODEL_ID}")
    print(f"   Output: {OUTPUT_DIR}\n")

    total_citations = 0
    parse_failures  = 0

    for i, lf in enumerate(label_files):
        in_file  = lf.with_suffix(".in")
        file_id  = lf.stem
        out_json = OUTPUT_DIR / f"{file_id}.json"

        if out_json.exists():
            print(f"[{i+1}/{len(label_files)}] {file_id} — skip (already done)")
            continue

        try:
            in_data    = json.loads(in_file.read_text())
            label_data = json.loads(lf.read_text())
        except Exception as e:
            print(f"[{i+1}/{len(label_files)}] {file_id} — load error: {e}")
            continue

        correct_map = label_data.get("correct_citation", {})
        predictions = {}

        print(f"[{i+1}/{len(label_files)}] {file_id} ({len(correct_map)} citations)")

        for citation_marker, gold in correct_map.items():
            predicted_ref = None

            for attempt in range(MAX_RETRIES):
                try:
                    prompt = create_prompt(in_data, citation_marker)

                    response = ollama.chat(
                        model=MODEL_ID,
                        messages=[{"role": "user", "content": prompt}],
                        options={
                            "temperature": TEMPERATURE,
                            "num_predict": NUM_PREDICT,
                            "num_ctx":     NUM_CTX,
                        },
                        think=False,
                    )

                    response_text = response["message"]["content"]
                    valid_ids     = list(in_data["bib_entries"].keys())
                    predicted_ref = parse_ref_id(response_text, valid_ids)

                    if predicted_ref is None:
                        print(f"  ⚠️  {citation_marker} parse fail (attempt {attempt+1}): {response_text[:80]!r}")
                        if attempt < MAX_RETRIES - 1:
                            continue
                        parse_failures += 1
                        predicted_ref = "000000"
                    else:
                        correct = "✓" if predicted_ref == gold else "✗"
                        print(f"  {correct} {citation_marker} → {predicted_ref}  (gold: {gold})")
                    break

                except Exception as e:
                    print(f"  ❌ {citation_marker} Ollama error (attempt {attempt+1}): {e}")
                    if attempt == MAX_RETRIES - 1:
                        predicted_ref = "000000"

            predictions[citation_marker] = [predicted_ref]
            total_citations += 1

        # Save predictions in inference format
        out_json.write_text(json.dumps(predictions, ensure_ascii=False, indent=2))

        # Save in standard Task 2-like format
        task2_output = {
            "text": in_data.get("text", ""),
            "correct_citation": {
                marker: ranked[0]
                for marker, ranked in predictions.items()
                if ranked and ranked[0] != "000000"
            },
            "bib_entries": in_data.get("bib_entries", {}),
        }
        (OUTPUT_DIR / f"{file_id}.pred.label").write_text(
            json.dumps(task2_output, ensure_ascii=False, indent=2)
        )

        if (i + 1) % 10 == 0:
            print(f"\n{'='*50}")
            print(f"  Checkpoint: {i+1}/{len(label_files)} files done")
            print(f"  Citations processed: {total_citations} | Parse failures: {parse_failures}")
            print(f"{'='*50}\n")

    print(f"\n{'='*50}")
    print(f"✅ Done! {len(label_files)} files processed")
    print(f"   Total citations : {total_citations}")
    print(f"   Parse failures  : {parse_failures} ({parse_failures/max(total_citations,1)*100:.1f}%)")
    print(f"   Output          : {OUTPUT_DIR}")
    print(f"{'='*50}")
    print("\nNext step:")
    print("  python error_analysis.py --model gemma_4_e4b")


if __name__ == "__main__":
    main()
