"""Async client for the Sarvam AI APIs used by the multilingual layer.

All four endpoints share one auth header: `api-subscription-key`.
"""
import base64

import httpx

BASE_URL = "https://api.sarvam.ai"


class SarvamClient:
    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._headers = {"api-subscription-key": api_key}
        self._http = httpx.AsyncClient(base_url=BASE_URL, timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ---- translation ----------------------------------------------------
    async def translate(
        self,
        text: str,
        target_language_code: str,
        source_language_code: str = "auto",       # 'auto' = detect (mayura:v1)
        *,
        mode: str = "modern-colloquial",          # natural product copy
        model: str = "mayura:v1",
        numerals_format: str = "international",
    ) -> str:
        resp = await self._http.post(
            "/translate",
            headers=self._headers,
            json={
                "input": text,
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
                "mode": mode,
                "model": model,
                "numerals_format": numerals_format,
            },
        )
        resp.raise_for_status()
        return resp.json()["translated_text"]

    # ---- text to speech -------------------------------------------------
    async def text_to_speech(
        self,
        text: str,
        language_code: str,
        *,
        speaker: str = "shubh",
        model: str = "bulbul:v3",
    ) -> bytes:
        """Return decoded WAV bytes (the API hands back base64)."""
        resp = await self._http.post(
            "/text-to-speech",
            headers=self._headers,
            json={
                "text": text,
                "language_code": language_code,
                "speaker": speaker,
                "model": model,
            },
        )
        resp.raise_for_status()
        return base64.b64decode("".join(resp.json()["audios"]))

    # ---- speech to text -------------------------------------------------
    async def speech_to_text(
        self,
        audio: bytes,
        filename: str = "clip.wav",
        *,
        model: str = "saaras:v4",
        mode: str = "transcribe",
        language_code: str = "unknown",
    ) -> dict:
        resp = await self._http.post(
            "/speech-to-text",
            headers=self._headers,
            files={"file": (filename, audio, "audio/wav")},
            data={"model": model, "mode": mode, "language_code": language_code},
        )
        resp.raise_for_status()
        return resp.json()

    # ---- language identification ---------------------------------------
    async def identify_language(self, text: str) -> str:
        resp = await self._http.post(
            "/text-lid", headers=self._headers, json={"input": text}
        )
        resp.raise_for_status()
        return resp.json().get("language_code", "unknown")
