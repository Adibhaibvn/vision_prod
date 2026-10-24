"""Orchestrator: Lens matches -> products -> optional marketplace enrichment.

Lens already returns shoppable visual matches, so those are the primary
source. Amazon/Blinkit are an optional enrichment pass keyed on the query
Lens derived, and their failure must never sink the scan.
"""
import asyncio

from app.schemas import LensResult, Product


class ProductOrchestrator:
    def __init__(self, sources: list) -> None:
        self._sources = sources

    async def build(self, lens: LensResult, limit: int = 6) -> list[Product]:
        products = [_from_match(m) for m in lens.matches]

        if self._sources:
            results = await asyncio.gather(
                *(s.search(lens.query, limit=limit) for s in self._sources),
                return_exceptions=True,          # one marketplace down != failed scan
            )
            for result in results:
                if not isinstance(result, Exception):
                    products.extend(result)

        return _rank(_dedupe(products), limit)


def _from_match(match) -> Product:
    return Product(
        source=match.source or "Google Lens",
        origin="lens",
        title=match.title,
        price_text=match.price_text,
        price_inr=match.price_inr,
        in_stock=match.in_stock if match.in_stock is not None else True,
        url=match.link,
        image_url=match.thumbnail,
        rating=match.rating,
    )


def _dedupe(products: list[Product]) -> list[Product]:
    seen: set[str] = set()
    out: list[Product] = []
    for p in products:
        key = p.title.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _rank(products: list[Product], limit: int) -> list[Product]:
    def score(p: Product) -> float:
        s = 0.0
        s += 2.0 if p.in_stock else 0.0
        s += 1.5 if p.price_inr is not None else 0.0
        s += 1.0 if p.image_url else 0.0
        s += 0.5 if p.url else 0.0
        s += (p.rating or 0) / 5.0
        # Nudge Amazon/Blinkit (a known Indian marketplace) above raw web hits.
        s += 0.8 if p.origin in {"amazon", "blinkit"} else 0.0
        return s

    return sorted(products, key=score, reverse=True)[:limit]
