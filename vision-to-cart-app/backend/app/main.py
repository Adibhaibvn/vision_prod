"""Vision-to-Cart — FastAPI app.

Endpoints
    POST /api/v1/scan          upload an image -> identified object + products
    POST /api/v1/scan/voice    speak a product name -> same pipeline
    GET  /api/v1/languages     languages the UI can offer
    GET  /api/v1/health        liveness + which providers are configured
The frontend is served from / (see the mount at the bottom).
"""
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.lens.factory import build_lens_provider
from app.sarvam.client import SarvamClient
from app.schemas import LensResult, ScanResponse
from app.services.localization import LANGUAGE_CODES, LocalizationService
from app.services.orchestrator import ProductOrchestrator

app = FastAPI(title="Vision-to-Cart API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- wire up providers --------------------------------------------------
lens_provider = build_lens_provider()
sarvam = SarvamClient(settings.sarvam_api_key) if settings.sarvam_api_key else None
localizer = LocalizationService(sarvam)

_marketplace_sources: list = []
if settings.enable_marketplace_search and settings.amazon_access_key:
    try:
        from app.sources.amazon import AmazonSource
        _marketplace_sources.append(AmazonSource())
    except Exception:
        pass  # Amazon enrichment is optional

orchestrator = ProductOrchestrator(_marketplace_sources)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/bmp"}


@app.post("/api/v1/scan", response_model=ScanResponse)
async def scan(
    image: UploadFile = File(...),
    lang: str = Form("en"),
    speak: bool = Form(True),
):
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported image type: {image.content_type}")

    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Empty upload")
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image exceeds {settings.max_upload_mb:g} MB")

    try:
        lens: LensResult = await lens_provider.identify(raw, image.content_type)
    except Exception as exc:
        raise HTTPException(502, f"Vision provider failed: {exc}") from exc

    products = await orchestrator.build(lens, limit=settings.max_results)
    localized, translated = await localizer.localize(products, lang, speak=speak)

    return ScanResponse(
        provider=lens.provider,
        query=lens.query,
        labels=lens.labels,
        note=lens.note,
        count=len(localized),
        products=localized,
        target_language=lang,
        translated=translated,
    )


@app.post("/api/v1/scan/voice", response_model=ScanResponse)
async def scan_voice(audio: UploadFile = File(...), lang: str = "auto", speak: bool = True):
    """Voice search: transcribe with Sarvam, then run the text pipeline."""
    if sarvam is None:
        raise HTTPException(503, "Voice search needs SARVAM_API_KEY")

    result = await sarvam.speech_to_text(await audio.read(), mode="transcribe")
    transcript = result.get("transcript", "").strip()
    if not transcript:
        raise HTTPException(422, "Could not transcribe the audio")

    detected = (result.get("language_code") or "en-IN").split("-")[0]
    english_query = transcript
    if detected != "en":
        english_query = await sarvam.translate(
            transcript, target_language_code="en-IN", source_language_code="auto"
        )

    lens = LensResult(
        provider="voice", query=english_query, labels=[transcript],
        matches=[], note="Voice search — matched by text query.",
    )
    products = await orchestrator.build(lens, limit=settings.max_results)
    localized, translated = await localizer.localize(products, lang, speak=speak)

    return ScanResponse(
        provider="voice", query=english_query, labels=[transcript], note=lens.note,
        count=len(localized), products=localized,
        target_language=lang, translated=translated,
    )


@app.get("/api/v1/languages")
async def languages():
    return {
        "languages": [
            {"code": code, "bcp47": bcp47} for code, bcp47 in LANGUAGE_CODES.items()
        ]
    }


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "lens_provider": lens_provider.name,
        "sarvam": sarvam is not None,
        "marketplaces": [s.name for s in _marketplace_sources],
    }


# --- serve the frontend -------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
