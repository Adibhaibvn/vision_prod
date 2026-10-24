"""Vision-provider interface + shared image helpers."""
from io import BytesIO
from typing import Protocol

from PIL import Image

from app.schemas import LensResult


class LensProvider(Protocol):
    """A Google-Lens-style visual identification backend."""
    name: str
    note: str | None

    async def identify(self, image_bytes: bytes, content_type: str) -> LensResult:
        ...


def shrink_image(image_bytes: bytes, max_bytes: int = 500_000) -> bytes:
    """Re-encode to JPEG, shrinking until it fits `max_bytes`.

    SerpAPI's Image API rejects uploads over 500 KB, and most providers
    are happier with smaller payloads, so we normalise here.
    """
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    # Cap the long edge first so we rarely need many quality passes.
    if max(image.size) > 1600:
        ratio = 1600 / max(image.size)
        image = image.resize(
            (int(image.width * ratio), int(image.height * ratio)), Image.LANCZOS
        )

    for quality in (85, 75, 65, 55, 45, 35):
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
    return buf.getvalue()
