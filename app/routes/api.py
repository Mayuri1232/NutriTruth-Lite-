"""REST API endpoints."""
import pytesseract #type:ignore
from fastapi import APIRouter, File, Form, HTTPException, UploadFile #type:ignore

from app.config import MAX_UPLOAD_BYTES, find_tesseract, install_hint
from app.services import ocr, parser, scoring

router = APIRouter(prefix="/api", tags=["nutritruth"])


@router.get("/health")
def health():
    path = find_tesseract()
    return {"status": "ok", "tesseract": path, "tesseract_ready": bool(path)}


@router.post("/analyze")
def analyze_label(file: UploadFile = File(...), product_name: str = Form("")):
    """Synchronous on purpose: FastAPI runs it in its worker thread-pool so the
    CPU-heavy OpenCV / Tesseract work never blocks the event loop."""
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"Image is too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")

    try:
        raw_text, ocr_pass = ocr.extract_text(data)
    except ocr.ImageDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(status_code=500, detail=install_hint())
    except ocr.OCRTimeout as exc:
        raise HTTPException(status_code=504, detail=f"{exc} Try a smaller or clearer photo.")

    nutrients = parser.parse_nutrients(raw_text)
    if parser.count_found(nutrients) == 0:
        raise HTTPException(
            status_code=422,
            detail=("No nutrition rows were found in the image. Make sure the nutrition "
                    "table is in focus, well lit and fills most of the frame, then try again."),
        )

    return {
        "product_name": (product_name or "").strip() or "Unnamed product",
        "nutrients": nutrients,
        "traffic_lights": scoring.traffic_lights(nutrients),
        "nutri_score": scoring.nutri_score(nutrients),
        "additives": scoring.detect_additives(raw_text),
        "raw_text": raw_text.strip(),
        "ocr_pass": ocr_pass,
    }
