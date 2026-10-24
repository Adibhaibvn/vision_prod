"""Shared data models."""
from pydantic import BaseModel, Field


class LensMatch(BaseModel):
    """One visual match returned by the Lens provider."""
    title: str
    link: str | None = None
    source: str | None = None            # e.g. "Amazon.in", "Nike", "Reddit"
    price_text: str | None = None        # as shown by the source, any currency
    price_inr: float | None = None       # only when the source quotes INR
    in_stock: bool | None = None
    thumbnail: str | None = None
    rating: float | None = None


class LensResult(BaseModel):
    """What the vision stage hands to the search stage."""
    provider: str
    query: str                                    # best-guess product query
    labels: list[str] = Field(default_factory=list)   # detected entities / classes
    matches: list[LensMatch] = Field(default_factory=list)
    note: str | None = None                       # provider caveats, shown in UI


class Product(BaseModel):
    """A normalized, purchasable result (from Lens matches or a marketplace)."""
    source: str
    title: str
    price_text: str | None = None
    price_inr: float | None = None
    in_stock: bool = True
    url: str | None = None
    image_url: str | None = None
    rating: float | None = None
    origin: str = "lens"                  # "lens" | "amazon" | "blinkit"


class LocalizedProduct(Product):
    summary: str = ""
    audio_b64: str | None = None          # base64 WAV from Sarvam TTS


class ScanResponse(BaseModel):
    provider: str
    query: str
    labels: list[str]
    note: str | None = None
    count: int
    products: list[LocalizedProduct]
    target_language: str
    translated: bool = False
