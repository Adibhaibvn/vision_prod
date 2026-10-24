"""Offline demo provider — no keys, no network, deterministic.

Lets the whole app run end to end (upload -> results -> translation ->
speech) before you plug in a real provider. It picks a canned catalogue
based on the image's average colour, so different uploads give different
plausible results.
"""
import hashlib
from io import BytesIO

from PIL import Image

from app.lens.base import shrink_image
from app.schemas import LensMatch, LensResult

CATALOGUE = [
    ("Running Shoes", [
        ("Nike Vaporfly 3 Men's Road Racing Shoes", "Nike", "₹19,995", 19995,
         "https://www.nike.com/in/t/vaporfly-3-mens-road-racing-shoes-8DD182"),
        ("ASICS Gel-Nimbus 26 Running Shoes", "Amazon.in", "₹15,499", 15499,
         "https://www.amazon.in/dp/B0CVQ1L9WX"),
    ]),
    ("Coffee Mug", [
        ("Ceramic Coffee Mug 350ml — Matte Finish", "Amazon.in", "₹399", 399,
         "https://www.amazon.in/dp/B08XXXXXXX"),
        ("Stainless Steel Travel Mug 400ml", "Blinkit", "₹649", 649,
         "https://blinkit.com/prn/travel-mug/prid/123456"),
    ]),
    ("Backpack", [
        ("Wildcraft 44L Laptop Backpack", "Amazon.in", "₹2,199", 2199,
         "https://www.amazon.in/dp/B07XXXXXXX"),
        ("American Tourister Casual Backpack", "Flipkart", "₹1,799", 1799,
         "https://www.flipkart.com/p/itmxxxx"),
    ]),
    ("Water Bottle", [
        ("Milton Thermosteel Flip Lid 1000ml", "Amazon.in", "₹1,099", 1099,
         "https://www.amazon.in/dp/B09XXXXXXX"),
        ("Borosil Hydra Trek Bottle 750ml", "Blinkit", "₹545", 545,
         "https://blinkit.com/prn/hydra-trek/prid/654321"),
    ]),
    ("Smartphone", [
        ("Redmi Note 13 5G (8GB/256GB)", "Amazon.in", "₹18,999", 18999,
         "https://www.amazon.in/dp/B0CQXXXXXX"),
        ("Realme Narzo 70 Pro 5G", "Flipkart", "₹19,999", 19999,
         "https://www.flipkart.com/p/itmxxxx"),
    ]),
]


class MockLens:
    name = "mock"
    note = "Demo provider — canned results. Add a real provider key in .env."

    async def identify(self, image_bytes: bytes, content_type: str) -> LensResult:
        small = shrink_image(image_bytes, max_bytes=200_000)
        digest = hashlib.sha1(small).hexdigest()

        # Average colour picks a bucket; the hash adds variety within it.
        image = Image.open(BytesIO(small))
        r, g, b = image.resize((1, 1)).getpixel((0, 0))
        bucket = (r + g + b) % len(CATALOGUE)
        label, items = CATALOGUE[bucket]

        matches = [
            LensMatch(
                title=title, source=source, price_text=price, price_inr=inr,
                link=url, in_stock=True, thumbnail=None,
                rating=round(3.9 + (int(digest[:2], 16) % 11) / 10, 1),
            )
            for (title, source, price, inr, url) in items
        ]

        return LensResult(
            provider=self.name, query=label,
            labels=[label, matches[0].source], matches=matches, note=self.note,
        )
