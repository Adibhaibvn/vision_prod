"""Google Lens via SerpApi — the reliable, documented route.

Flow (two calls):
  1. POST https://serpapi.com/image          multipart `image` (<= 500 KB) -> image_id
  2. GET  https://serpapi.com/search         engine=google_lens & image_id=... & type=visual_matches

The `image_id` expires after ~10 minutes, which is fine for a single scan.
"""
import httpx

from app.config import settings
from app.lens.base import shrink_image
from app.schemas import LensMatch, LensResult

SEARCH_URL = "https://serpapi.com/search"
IMAGE_URL = "https://serpapi.com/image"

INR_SYMBOLS = {"₹", "inr", "rs", "rs."}


class SerpApiLens:
    name = "serpapi"
    note = None

    def __init__(self, api_key: str) -> None:
        self._key = api_key

    async def identify(self, image_bytes: bytes, content_type: str) -> LensResult:
        small = shrink_image(image_bytes, max_bytes=500_000)

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            upload = await client.post(
                IMAGE_URL,
                data={"api_key": self._key},
                files={"image": ("image.jpg", small, "image/jpeg")},
            )
            upload.raise_for_status()
            image_id = upload.json()["image_id"]

            search = await client.get(
                SEARCH_URL,
                params={
                    "engine": "google_lens",
                    "api_key": self._key,
                    "image_id": image_id,
                    "type": "visual_matches",
                    "hl": settings.lens_hl,
                    "country": settings.lens_country,
                },
            )
            search.raise_for_status()
            data = search.json()

        if "error" in data:
            raise RuntimeError(f"SerpApi: {data['error']}")

        matches = [_to_match(m) for m in data.get("visual_matches", [])]
        labels = _labels(data, matches)

        return LensResult(
            provider=self.name,
            query=_query(data, matches),
            labels=labels,
            matches=matches,
        )


def _query(data: dict, matches: list[LensMatch]) -> str:
    """Best guess at what the object is, used as the marketplace query."""
    related = data.get("related_content") or []
    for item in related:
        if item.get("query"):
            return str(item["query"])
    if matches:
        # The top visual match is ranked by visual similarity — a decent query.
        return matches[0].title[:80]
    return "unknown object"


def _labels(data: dict, matches: list[LensMatch]) -> list[str]:
    labels: list[str] = []
    for item in (data.get("related_content") or [])[:4]:
        if item.get("query"):
            labels.append(str(item["query"]))
    for match in matches[:4]:
        if match.source and match.source not in labels:
            labels.append(match.source)
    return labels[:6]


def _to_match(raw: dict) -> LensMatch:
    price = raw.get("price") or {}
    currency = str(price.get("currency", "")).strip()
    value = price.get("extracted_value")
    is_inr = currency.lower() in INR_SYMBOLS

    return LensMatch(
        title=(raw.get("title") or "Untitled").strip(),
        link=raw.get("link"),
        source=raw.get("source"),
        price_text=price.get("value"),
        price_inr=float(value) if (is_inr and value is not None) else None,
        in_stock=raw.get("in_stock"),
        thumbnail=raw.get("thumbnail") or raw.get("image"),
        rating=raw.get("rating"),
    )
