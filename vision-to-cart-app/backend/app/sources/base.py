"""Marketplace adapters — one interface, two realities."""
from typing import Protocol

from app.schemas import Product


class ProductSource(Protocol):
    name: str

    async def search(self, query: str, *, limit: int = 5) -> list[Product]:
        """Return normalized products. Never raise on a single bad result."""
        ...
