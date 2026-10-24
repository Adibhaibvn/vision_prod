"""Blinkit search via a headless browser.

Blinkit publishes no public product API, so this drives Playwright against
the web search page. Two honest caveats:

  1. The selectors below are illustrative and need maintenance — Blinkit
     ships markup changes often.
  2. Automated scraping may breach Blinkit's Terms of Service.

Keep this adapter behind `ProductSource` so it can be swapped for a
licensed data partner without touching anything else.
"""
import re

from playwright.async_api import async_playwright

from app.schemas import Product

SEARCH_URL = "https://blinkit.com/s/?q={query}"


class BlinkitSource:
    name = "blinkit"

    async def search(self, query: str, *, limit: int = 5) -> list[Product]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(
                locale="en-IN",
                extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            )
            try:
                await page.goto(
                    SEARCH_URL.format(query=query.replace(" ", "%20")),
                    wait_until="domcontentloaded",
                )
                await page.wait_for_selector(
                    '[data-testid="plp-product"]', timeout=15000
                )
                cards = await page.query_selector_all('[data-testid="plp-product"]')

                products: list[Product] = []
                for card in cards[:limit]:
                    products.append(await self._read_card(card))
                return products
            finally:
                await browser.close()

    @staticmethod
    async def _read_card(card) -> Product:
        name = await card.query_selector('[class*="ProductName"]')
        price = await card.query_selector('[class*="Price"]')
        link = await card.query_selector("a")
        price_text = (await price.inner_text()).strip() if price else None

        return Product(
            source="Blinkit",
            origin="blinkit",
            title=(await name.inner_text()).strip() if name else "Unknown",
            price_text=price_text,
            price_inr=_parse_inr(price_text),
            in_stock=True,                      # Blinkit lists buyable SKUs only
            url=(await link.get_attribute("href")) if link else None,
        )


def _parse_inr(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d[\d,]*)", text)
    if not match:
        return None
    return round(float(match.group(1).replace(",", "")), 2)
