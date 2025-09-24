# app/services/storage_service.py
import os
import uuid
from fastapi import UploadFile, HTTPException
from .grobid_client import process_fulltext_document

PDF_DIR = os.getenv("PDF_DIR", "/tmp/papers")
TEI_DIR = os.getenv("TEI_DIR", "/tmp/papers_tei")
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEI_DIR, exist_ok=True)

def _normalize_tei_id(tei_id: str) -> str:
    # chỉ lấy basename, bỏ mọi path user gửi lên
    base = os.path.basename(tei_id.strip())
    # nếu lỡ gửi kèm đuôi .tei.xml thì cắt đi
    if base.endswith(".tei.xml"):
        base = base[: -len(".tei.xml")]
    return base

async def save_pdf_and_tei(file: UploadFile):
    data = await file.read()
    tei_id = str(uuid.uuid4())
    pdf_path = os.path.join(PDF_DIR, f"{tei_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(data)

    try:
        tei_xml = await process_fulltext_document(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GROBID error: {type(e).__name__}: {e}")

    tei_path = os.path.join(TEI_DIR, f"{tei_id}.tei.xml")
    with open(tei_path, "w", encoding="utf-8") as f:
        f.write(tei_xml)

    return tei_id, {
        "filename": file.filename,
        "size_bytes": len(data),
        "pdf_path": pdf_path,
        "tei_path": tei_path,
    }

def get_tei_text(tei_id: str) -> str:
    tei_id = _normalize_tei_id(tei_id)  # <<< NEW
    tei_path = os.path.join(TEI_DIR, f"{tei_id}.tei.xml")
    if not os.path.exists(tei_path):
        # báo 404 rõ ràng để FE hiển thị thông điệp
        raise HTTPException(status_code=404, detail=f"TEI not found for tei_id={tei_id}")
    with open(tei_path, "r", encoding="utf-8") as f:
        return f.read()
