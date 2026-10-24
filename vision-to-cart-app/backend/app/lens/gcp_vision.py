"""Google Lens-style identification via Cloud Vision API (official).

Uses the WEB_DETECTION feature: it returns inferred web entities, a
"best guess label", and pages that contain the same image. It is not
Lens shopping per se, but it is a first-party, ToS-clean way to answer
"what is this object?" and it returns product pages you can shop from.

Endpoint: POST https://vision.googleapis.com/v1/images:annotate?key=API_KEY
"""
import base64
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.lens.base import shrink_image
from app.schemas import LensMatch, LensResult

ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"


class GcpVisionLens:
    name = "gcp_vision"
    note = "Cloud Vision WEB_DETECTION — official, but not shopping-ranked."

    def __init__(self, api_key: str) -> None:
        self._key = api_key

    async def identify(self, image_bytes: bytes, content_type: str) -> LensResult:
        small = shrink_image(image_bytes, max_bytes=1_500_000)
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(small).decode()},
                    "features": [{"type": "WEB_DETECTION", "maxResults": 15}],
                }
            ]
        }

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.post(
                ANNOTATE_URL, params={"key": self._key}, json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Vision API: {data['error'].get('message', 'error')}")

        web = data["responses"][0].get("webDetection", {})
        labels = _labels(web)
        matches = _matches(web)
        query = labels[0] if labels else (matches[0].title if matches else "unknown object")

        return LensResult(
            provider=self.name, query=query, labels=labels, matches=matches,
            note=self.note,
        )


def _labels(web: dict) -> list[str]:
    out: list[str] = []
    for label in web.get("bestGuessLabels", []):
        if label.get("label"):
            out.append(str(label["label"]))
    for entity in sorted(
        web.get("webEntities", []), key=lambda e: e.get("score", 0), reverse=True
    ):
        desc = entity.get("description")
        if desc and desc not in out:
            out.append(str(desc))
    return out[:6]


def _matches(web: dict) -> list[LensMatch]:
    out: list[LensMatch] = []
    for page in web.get("pagesWithMatchingImages", [])[:12]:
        images = page.get("fullMatchingImages") or page.get("partialMatchingImages") or []
        out.append(
            LensMatch(
                title=_clean_title(page.get("pageTitle")) or _host(page.get("url")),
                link=page.get("url"),
                source=_host(page.get("url")),
                thumbnail=(images[0].get("url") if images else None),
            )
        )
    return out


def _clean_title(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.replace("<b>", "").replace("</b>", "").strip()


def _host(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).netloc.replace("www.", "") or None
