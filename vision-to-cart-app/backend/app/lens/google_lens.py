"""Google Lens via its own (undocumented) upload endpoint — best effort.

This talks to the same endpoint the Lens web UI uses:

    POST https://lens.google.com/v3/upload?ep=ccm&st=<ms>
    multipart/form-data:  encoded_image=<file>   processed_image_dimensions=W,H

It is *not* an official API. It is undocumented, against Google's Terms
of Service, returns HTML rather than JSON, and will break whenever Google
changes its markup. It is included so the app works with zero paid keys,
but treat the output as a rough hint — prefer `serpapi` for production.

Because the results page is JS-rendered, this parses whatever title/link
pairs it can find in the returned HTML. Expect noisy, partial results.
"""
import html
import re
import time

import httpx

from app.config import settings
from app.lens.base import shrink_image
from app.schemas import LensMatch, LensResult

UPLOAD_URL = "https://lens.google.com/v3/upload"

_TITLE_RE = re.compile(r'aria-label="([^"]{8,120})"')
_LINK_RE = re.compile(r'href="(https?://(?!lens\.google|www\.google|accounts\.google)[^"]+)"')


class GoogleLensUnofficial:
    name = "google_lens"
    note = (
        "Unofficial Lens endpoint — undocumented, may return partial results, "
        "and can break without notice. Use SerpApi for production."
    )

    async def identify(self, image_bytes: bytes, content_type: str) -> LensResult:
        small = shrink_image(image_bytes, max_bytes=1_500_000)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": f"{settings.lens_hl},en;q=0.9",
        }

        async with httpx.AsyncClient(
            timeout=settings.request_timeout, follow_redirects=True, headers=headers
        ) as client:
            resp = await client.post(
                UPLOAD_URL,
                params={"ep": "ccm", "st": str(int(time.time() * 1000))},
                files={"encoded_image": ("image.jpg", small, "image/jpeg")},
                data={"processed_image_dimensions": "1000,1000"},
            )
            resp.raise_for_status()
            body = resp.text

        matches = _parse(body)
        query = matches[0].title if matches else "unknown object"

        return LensResult(
            provider=self.name,
            query=query,
            labels=[m.source for m in matches if m.source][:6],
            matches=matches,
            note=self.note,
        )


def _parse(body: str) -> list[LensMatch]:
    """Extract title/link pairs from the results HTML — deliberately loose."""
    titles = [html.unescape(t).strip() for t in _TITLE_RE.findall(body)]
    links = _LINK_RE.findall(body)

    out: list[LensMatch] = []
    seen: set[str] = set()
    for i, title in enumerate(titles):
        if title in seen:
            continue
        seen.add(title)
        link = links[i] if i < len(links) else None
        out.append(
            LensMatch(
                title=title,
                link=link,
                source=_host(link),
            )
        )
        if len(out) >= 12:
            break
    return out


def _host(url: str | None) -> str | None:
    if not url:
        return None
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1).replace("www.", "") if m else None
