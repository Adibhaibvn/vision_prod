"""Amazon.in search via the Product Advertising API (PA-API 5.0).

Requires an approved Amazon Associates account. Requests are signed with
AWS SigV4 and rate-limited; the `amazon-paapi` SDK handles signing.

This adapter is optional — if the keys are absent, the app still works
using Lens matches alone (see app/services/orchestrator.py).
"""
import asyncio

from app.config import settings
from app.schemas import Product

try:
    from amazon_paapi import AmazonApi
except ImportError:  # the SDK is optional at runtime
    AmazonApi = None  # type: ignore[assignment]


class AmazonSource:
    name = "amazon"

    def __init__(self) -> None:
        if AmazonApi is None:
            raise RuntimeError("amazon-paapi is not installed")
        self._api = AmazonApi(
            key=settings.amazon_access_key,
            secret=settings.amazon_secret_key,
            tag=settings.amazon_partner_tag,
            country="IN",
        )

    async def search(self, query: str, *, limit: int = 5) -> list[Product]:
        items = await asyncio.to_thread(
            self._api.search_items, keywords=query, item_count=limit
        )
        return [self._to_product(i) for i in (getattr(items, "items", None) or [])]

    @staticmethod
    def _to_product(item) -> Product:
        info = item.item_info
        listing = item.offers.listings[0] if item.offers.listings else None
        amount = getattr(getattr(listing, "price", None), "amount", None)
        return Product(
            source="Amazon.in",
            origin="amazon",
            title=info.title.display_value,
            price_inr=_parse_inr(amount),
            in_stock=bool(listing and listing.availability.type == "Now"),
            url=item.detail_page_url,
            image_url=None,
        )


def _parse_inr(value) -> float | None:
    if value is None:
        return None
    try:
        return round(float(str(value).replace(",", "").replace("₹", "").strip()), 2)
    except ValueError:
        return None
