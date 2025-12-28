#!/usr/bin/env python3
"""
Crawl papers qua OpenAlex (ưu tiên PDF OA), lưu vào papers/ và manifest.jsonl.
- Dừng khi tổng số paper trong manifest đạt N_TARGET.
- Tránh trùng bằng id/hash.

Tùy chỉnh:
  - QUERIES: danh sách từ khóa theo chủ đề.
  - MAX_QUERIES: số query tối đa mỗi lượt.
  - MAX_PER_QUERY: số paper tối đa mỗi query.
"""

import hashlib
import json
import re
import time
from pathlib import Path

import requests

# --------- Cấu hình ---------
OUT_DIR = Path("papers")
MANIFEST = OUT_DIR / "manifest.jsonl"
MAX_QUERIES = None       # None = chạy hết tất cả queries
MAX_PER_QUERY = 50       # tối đa mỗi query
N_TARGET = 2000          # tổng số paper mong muốn trong manifest
SLEEP_BETWEEN_CALLS = 10  # giây giữa các call để giảm 429/403
# Đặt User-Agent rõ ràng để tránh bị block (thay email nếu muốn)
HEADERS = {"User-Agent": "openalex-crawler/0.1 (mailto:contact@example.com)"}

# Query theo các chủ đề đã liệt kê (focus: HOT 2024-2025 + practical + educational)
QUERIES = [
    # Core LLM & RAG (keeping high-performing queries)
    "retrieval augmented generation survey arxiv",
    "long context language model survey arxiv",
    "hallucination detection llm arxiv",
    "chain of thought reasoning llm arxiv",
    "self reflection llm arxiv",
    "lora qlora adapter finetuning arxiv",
    "safety alignment rlhf llm arxiv",

    # Academic/Research (core to citation-checking project)
    "scientific citation extraction arxiv",
    "academic document understanding arxiv",
    "scientific ner entity linking arxiv",
    "claim verification scientific text arxiv",
    "literature review automation survey arxiv",
    "research paper summarization extraction arxiv",
    "scientific writing assistant llm arxiv",
    "citation recommendation context arxiv",
    "academic search semantic scholar arxiv",

    # AI Agents - Hot & Practical (2024-2025 trends)
    "ai agent tool use function calling arxiv",
    "llm powered agent workflow arxiv",
    "react prompting reasoning acting arxiv",
    "autonomous agent benchmark evaluation arxiv",
    "agent memory long term planning arxiv",
    "multi agent collaboration framework arxiv",

    # Document AI - Very Practical
    "pdf parsing document understanding arxiv",
    "table extraction structured data arxiv",
    "document layout analysis detection arxiv",
    "information extraction json schema arxiv",
    "document question answering arxiv",
    "form understanding key value extraction arxiv",
    "receipt invoice parsing automation arxiv",

    # LLM Practical Skills
    "in context learning few shot arxiv",
    "prompt engineering optimization arxiv",
    "llm evaluation benchmark leaderboard arxiv",
    "fine tuning domain adaptation peft arxiv",

    # Code & Software (keeping best ones)
    "test case generation llm arxiv",
    "code summarization understanding arxiv",
    "log anomaly detection root cause arxiv",
    "automated testing ai program repair arxiv",
    "code generation language model arxiv",
    "program synthesis neural network arxiv",

    # Healthcare (keeping only best ones)
    "medical entity linking arxiv",
    "healthcare chatbot llm arxiv",
]

OPENALEX_URL = "https://api.openalex.org/works"


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_filename(title: str, fallback: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", title)[:120]
    return name or fallback


def load_manifest():
    seen = {}
    if MANIFEST.exists():
        for line in MANIFEST.read_text().splitlines():
            rec = json.loads(line)
            key = rec.get("key") or rec.get("id")
            if key:
                seen[key] = rec
            h = rec.get("hash")
            if h:
                seen[h] = rec
    return seen


def save_manifest(rec: dict):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def fetch_openalex(query: str, page: int, per_page: int = 10, retries: int = 3, backoff: int = 5):
    params = {
        "search": query,
        "filter": "open_access.is_oa:true,publication_year:2024-2025",
        "page": page,
        "per-page": per_page,
        "sort": "cited_by_count:desc",
    }
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(OPENALEX_URL, params=params, headers=HEADERS, timeout=30)
            if r.status_code in (403, 429):
                wait = backoff * (i + 1)
                print(f"  openalex {r.status_code}, sleeping {wait}s ...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            return data.get("results", [])
        except Exception as e:
            last_err = e
            wait = backoff * (i + 1)
            print(f"  fetch error page={page} attempt {i+1}/{retries}: {e}, sleeping {wait}s ...")
            time.sleep(wait)
    if last_err:
        raise last_err
    return []


def get_pdf_url(item: dict) -> str:
    # ưu tiên oa_url
    oa = item.get("open_access") or {}
    if oa.get("is_oa") and oa.get("oa_url"):
        return oa["oa_url"]
    loc = item.get("primary_location") or {}
    if loc.get("pdf_url"):
        return loc["pdf_url"]
    return ""


def main():
    existing_total = 0
    if MANIFEST.exists():
        existing_total = len(MANIFEST.read_text().splitlines())
    target_remaining = max(0, N_TARGET - existing_total)
    if target_remaining <= 0:
        print(f"Manifest already has {existing_total} entries, target reached.")
        return

    seen = load_manifest()
    saved = 0
    limit_queries = MAX_QUERIES or len(QUERIES)
    for qi, q in enumerate(QUERIES):
        if qi >= limit_queries or saved >= target_remaining:
            break
        print(f"== Query: {q}")
        page = 1
        per_page = 10
        per_query_saved = 0
        while per_query_saved < MAX_PER_QUERY and saved < target_remaining:
            try:
                results = fetch_openalex(q, page=page, per_page=per_page)
            except Exception as e:
                print(f"  fetch error page={page}: {e}")
                break
            if not results:
                print("  no results, break.")
                break
            for item in results:
                if per_query_saved >= MAX_PER_QUERY or saved >= target_remaining:
                    break
                key = item.get("id")
                title = (item.get("title") or "").strip()
                if not key or not title:
                    continue
                if key in seen:
                    continue
                pdf_url = get_pdf_url(item)
                if not pdf_url:
                    continue
                try:
                    resp = requests.get(pdf_url, timeout=30)
                    resp.raise_for_status()
                except Exception as dl_err:
                    print(f"  download failed: {pdf_url} ({dl_err})")
                    continue
                data = resp.content
                ctype = resp.headers.get("Content-Type", "").lower()
                if "pdf" not in ctype and not data.startswith(b"%PDF"):
                    if not pdf_url.lower().endswith(".pdf"):
                        print(f"  skip non-pdf {pdf_url}")
                        continue
                h = hash_bytes(data)
                if h in seen:
                    print("  skip duplicate hash")
                    continue
                fname = sanitize_filename(title, h[:16]) + ".pdf"
                path = OUT_DIR / fname
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                year = item.get("publication_year")
                rec = {
                    "key": key,
                    "title": title,
                    "hash": h,
                    "pdf_url": pdf_url,
                    "query": q,
                    "source": "openalex",
                    "year": year,
                }
                save_manifest(rec)
                seen[key] = rec
                seen[h] = rec
                saved += 1
                per_query_saved += 1
                print(f"  saved {path.name} [{saved}/{target_remaining}]")
            page += 1
            time.sleep(SLEEP_BETWEEN_CALLS)
    print(f"Done: added {saved} papers (manifest total: {existing_total + saved})")


if __name__ == "__main__":
    main()
