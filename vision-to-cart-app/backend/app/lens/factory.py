"""Pick a vision provider from settings."""
from app.config import settings
from app.lens.base import LensProvider
from app.lens.gcp_vision import GcpVisionLens
from app.lens.google_lens import GoogleLensUnofficial
from app.lens.mock import MockLens
from app.lens.serpapi_lens import SerpApiLens


def build_lens_provider() -> LensProvider:
    choice = settings.lens_provider.lower().strip()

    if choice == "serpapi" and settings.serpapi_key:
        return SerpApiLens(settings.serpapi_key)
    if choice == "gcp_vision" and settings.gcp_vision_api_key:
        return GcpVisionLens(settings.gcp_vision_api_key)
    if choice == "google_lens":
        return GoogleLensUnofficial()
    if choice == "mock":
        return MockLens()

    # auto: prefer the most reliable configured provider, else demo mode.
    if settings.serpapi_key:
        return SerpApiLens(settings.serpapi_key)
    if settings.gcp_vision_api_key:
        return GcpVisionLens(settings.gcp_vision_api_key)
    return MockLens()
