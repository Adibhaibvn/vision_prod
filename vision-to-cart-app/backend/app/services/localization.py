"""The single choke point for every user-facing string.

If no Sarvam key is configured the service degrades gracefully: it
returns the English payload untranslated rather than failing the scan.
"""
import base64

from app.sarvam.client import SarvamClient
from app.schemas import LocalizedProduct, Product

# UI keys -> Sarvam BCP-47 codes (the languages mayura:v1 covers).
LANGUAGE_CODES = {
    "en": "en-IN", "hi": "hi-IN", "bn": "bn-IN", "gu": "gu-IN",
    "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN", "od": "od-IN",
    "pa": "pa-IN", "ta": "ta-IN", "te": "te-IN",
}


class LocalizationService:
    def __init__(self, sarvam: SarvamClient | None) -> None:
        self._sarvam = sarvam

    async def localize(
        self,
        products: list[Product],
        lang: str,
        *,
        speak: bool = True,
        top_n: int = 4,
    ) -> tuple[list[LocalizedProduct], bool]:
        """Returns (products, translated?)."""
        code = LANGUAGE_CODES.get(lang, "en-IN")
        top = products[:top_n]

        if self._sarvam is None or code == "en-IN":
            return [LocalizedProduct(**p.model_dump(), summary=_english(p)) for p in top], False

        out: list[LocalizedProduct] = []
        for p in top:
            try:
                title = await self._sarvam.translate(p.title, code)
                summary = await self._sarvam.translate(_english(p), code)
                audio_b64 = None
                if speak:
                    wav = await self._sarvam.text_to_speech(summary, code)
                    audio_b64 = base64.b64encode(wav).decode()
            except Exception:
                # A translation hiccup should not lose the product.
                out.append(LocalizedProduct(**p.model_dump(), summary=_english(p)))
                continue

            out.append(
                LocalizedProduct(
                    **p.model_dump(), title=title, summary=summary, audio_b64=audio_b64
                )
            )
        return out, True


def _english(p: Product) -> str:
    price = p.price_text or (f"₹{p.price_inr:,.0f}" if p.price_inr is not None else "price not available")
    stock = "in stock" if p.in_stock else "out of stock"
    where = p.source or "the web"
    return f"{p.title}. {price}, {stock}. Found on {where}."
