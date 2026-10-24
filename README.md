# Vision-to-Cart

Point a camera at an object. Get a shoppable, spoken product listing back in
your own language. Vision identifies the object (Google Lens), the backend
finds where to buy it, and **Sarvam AI** carries the whole thing across the
language gap — text translation, speech synthesis and voice input.

```
photo ─▶ Google Lens ─▶ object + visual matches ─▶ rank ─▶ Sarvam ─▶ localized results
                                                    │
                                                    └─ (optional) Amazon / Blinkit enrichment
```

## What's in the box

| Piece | File(s) | Notes |
|---|---|---|
| Vision providers | `backend/app/lens/` | SerpApi · Cloud Vision · unofficial Lens · demo |
| Marketplace adapters | `backend/app/sources/` | Amazon PA-API · Blinkit (Playwright) |
| Orchestration | `backend/app/services/orchestrator.py` | fan-out, dedupe, rank |
| Multilingual layer | `backend/app/sarvam/client.py`, `services/localization.py` | translate · TTS · STT · LID |
| API + static hosting | `backend/app/main.py` | FastAPI, serves the frontend too |
| Frontend | `frontend/` | plain HTML/CSS/JS — no build step |

## Run it

```bash
./run.sh            # creates a venv, installs deps, starts on :8000
```

Then open <http://localhost:8000>. **It works with zero API keys** — the app
falls back to a demo vision provider so you can walk the whole flow
(upload → identify → translate → listen) immediately.

Manual equivalent:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Choosing a vision provider

There is **no first-party "Google Lens API."** `LENS_PROVIDER` selects how the
app asks "what is this object?":

| Value | What it is | Cost | Reliability |
|---|---|---|---|
| `serpapi` | **Recommended.** SerpApi's Google Lens API — real Lens visual matches with titles, prices, sources. | Paid | High |
| `gcp_vision` | Official Google Cloud Vision, `WEB_DETECTION`. Returns web entities + pages containing the image. | Paid | High |
| `google_lens` | Google's own **undocumented** upload endpoint (`lens.google.com/v3/upload`). | Free | Low — against ToS, returns HTML, will break |
| `mock` | Canned catalogue, chosen by image colour. | Free | N/A (demo) |

`LENS_PROVIDER=auto` picks the best configured one, else `mock`.

> **Honest note on `google_lens`:** it is not an API. It posts to the same
> endpoint the Lens web UI uses, returns a JS-rendered HTML page, and the
> parser here is deliberately loose. It exists so the app works with no paid
> keys; use `serpapi` for anything real.

## Multilingual layer (Sarvam AI)

Set `SARVAM_API_KEY` and every user-facing string is translated, with an
optional spoken summary. Endpoints used:

| Endpoint | Purpose |
|---|---|
| `POST /translate` | product titles + summaries (`mayura:v1`, `mode=modern-colloquial`) |
| `POST /text-to-speech` | spoken summary (`bulbul:v3`) |
| `POST /speech-to-text` | voice search (`saaras:v4`) |
| `POST /text-lid` | language identification |

Without the key, the app returns English and marks `translated: false`.

## API

| Method | Path | Body |
|---|---|---|
| `POST` | `/api/v1/scan` | multipart: `image`, `lang`, `speak` |
| `POST` | `/api/v1/scan/voice` | multipart: `audio`, `lang`, `speak` |
| `GET` | `/api/v1/languages` | — |
| `GET` | `/api/v1/health` | — |

```bash
curl -F image=@sneaker.jpg -F lang=hi -F speak=true \
  http://localhost:8000/api/v1/scan | jq '.products[0]'
```

## Amazon & Blinkit (optional)

- **Amazon** uses PA-API 5.0 and needs an approved Associates account. If the
  keys are absent the adapter is simply skipped — Lens matches stand alone.
- **Blinkit** has no public API, so the adapter drives a headless browser
  (`pip install playwright && playwright install chromium`). The selectors are
  illustrative, will need maintenance, and scraping may breach Blinkit's Terms
  of Service. Swap it for a licensed data partner behind the same interface.

## Adding a language

Append to `LANGUAGE_CODES` in `backend/app/services/localization.py` and add a
display name in `frontend/app.js` (`NAMES`). Nothing else changes.

## Notes & limits

- Sarvam `/translate` caps input at 1,000 chars (`mayura:v1`); TTS at 2,500;
  REST speech-to-text at 30 s of audio.
- SerpApi image uploads are capped at 500 KB — `app/lens/base.py` resizes
  automatically.
- No secrets are committed; everything is read from `backend/.env`.
