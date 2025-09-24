from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body
from typing import Dict, Any
from services.storage_service import save_pdf_and_tei, get_tei_text
from services.citation_style_service import detect_citation_style_stub
from services.references_service import list_references_from_tei
from services.grobid_client import is_alive as grobid_is_alive
from services.citations_service import (
    count_intext_citations_from_tei,
    extract_intext_citations_task1b,
    make_rows_for_fe_task1b,
)

router = APIRouter()

# 0) Health GROBID (tiện debug)
@router.get("/health/grobid")
async def health_grobid() -> Dict[str, Any]:
    ok = await grobid_is_alive()
    return {"success": ok}

# 1) Upload PDF -> GROBID -> lưu TEI -> trả tei_id
@router.post("/papers/upload")
async def upload_paper(file: UploadFile = File(...)) -> Dict[str, Any]:
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF is accepted"
        )

    tei_id, meta = await save_pdf_and_tei(file)
    return {"success": True, "tei_id": tei_id, **meta}

# 2) Show type (detect citation style) từ TEI đã lưu
@router.post("/analyze/style")
async def analyze_style(tei_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    tei = get_tei_text(tei_id)
    style, conf, signals = await detect_citation_style_stub(
        tei.encode("utf-8"), filename=f"{tei_id}.tei.xml"
    )
    return {
        "success": True,
        "tei_id": tei_id,
        "style": style,
        "confidence": conf,
        "signals": signals
    }

# 3) Show list citation (References) từ TEI đã lưu
@router.post("/references/list")
async def references_list(tei_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    tei = get_tei_text(tei_id)
    result = list_references_from_tei(tei)
    result.update({"success": True, "tei_id": tei_id})
    return result

# 4) Đếm số citation in-text
@router.post("/citations/count")
async def citations_count(tei_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    tei = get_tei_text(tei_id)
    result = count_intext_citations_from_tei(tei)
    return {"success": True, "tei_id": tei_id, **result}

# 5) Trả về dữ liệu Task 1b (raw)
@router.post("/citations/task1b")
async def citations_task1b(tei_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    tei = get_tei_text(tei_id)
    result = extract_intext_citations_task1b(tei)
    return {"success": True, "tei_id": tei_id, **result}

# 6) Trả về dữ liệu rows cho FE
@router.post("/citations/rows")
async def citations_rows(tei_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    tei = get_tei_text(tei_id)
    result = make_rows_for_fe_task1b(tei)
    return {"success": True, "tei_id": tei_id, **result}
