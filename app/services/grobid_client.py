import os
import httpx

GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")

async def process_fulltext_document(pdf_bytes: bytes) -> str:
    """
    Gọi GROBID /api/processFulltextDocument và trả về TEI XML (string).
    """
    url = f"{GROBID_URL}/api/processFulltextDocument"
    async with httpx.AsyncClient(timeout=120) as client:
        files = {"input": ("paper.pdf", pdf_bytes, "application/pdf")}
        data = {"consolidateHeader": 1, "consolidateCitations": 1}
        r = await client.post(url, files=files, data=data)
        r.raise_for_status()
        return r.text

async def is_alive() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{GROBID_URL}/api/isalive")
            return r.status_code == 200
    except Exception:
        return False
