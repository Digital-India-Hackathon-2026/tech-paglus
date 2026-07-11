# AgriSarthi AI — Smart Farmer Assistant (Next.js rebuild)

Voice-enabled AI agent for Indian farmers. Personalized crop, weather, mandi, irrigation & advisory that **varies by location, soil, water, season, budget**.

## Quick start (Mac / Linux)
```bash
yarn install
cp .env.example .env      # fill MONGO_URL; keep other keys blank for local rule-based mode
yarn dev                  # runs on http://localhost:3000
```

## What works WITHOUT API keys (default)
- Location: OpenStreetMap Nominatim (free) + browser GPS
- Weather + 7-day forecast + risk scoring: Open-Meteo (free)
- Crop recommendation engine (location/soil/water/season/budget scoring)
- Mandi price transparent estimator (varies by state/district/crop)
- Irrigation planner (drip/sprinkler/furrow) with 7-day schedule
- PDF soil report extractor (Soil Health Card, ROR, Pattadar)
- Multilingual voice agent (EN / TE / HI) via Web Speech API
- Feedback thumbs up/down → weighted preference learning (MongoDB)
- Government schemes card (PM-KISAN, PMFBY, PMKSY, Soil Health Card)

## Optional keys (in .env)
- `AI_ADVISORY_API_KEY` — Groq LLaMA-3.3 for LLM advisory
- `DATAGOV_API_KEY` — live AGMARKNET mandi prices
- `SENTINEL_HUB_CLIENT_ID/SECRET` — satellite hooks

## APIs used
| API | Purpose | Key needed |
|-----|---------|------------|
| Nominatim (OpenStreetMap) | Geocoding / reverse | No |
| Open-Meteo | Weather 7-day + current | No |
| Groq LLaMA-3.3 | LLM advisory (optional) | Yes |
| data.gov.in AGMARKNET | Mandi live | Yes |
| RainViewer / Sentinel Hub | Radar / satellite (optional) | No / Yes |

## Backend routes (all under /api)
- `POST /api/geocode` — {query} → lat/lon/state/district
- `POST /api/reverse-geocode` — {lat,lon} → address
- `POST /api/weather` — {lat,lon} → 7-day forecast + risk flags
- `POST /api/pdf-extract` — multipart PDF → extracted soil/land fields + confidence
- `POST /api/recommend` — full context → top 5 crops with score breakdown
- `POST /api/mandi` — {crop,state,district} → primary + nearby mandi prices
- `POST /api/irrigation` — full context → plan + 7-day schedule
- `POST /api/advisory` — multilingual rule-based advisory + voice summary
- `POST /api/feedback` — thumbs up/down → preference weights learned
- `GET/POST /api/profile` — session-scoped farmer memory

## Test scenarios (verified)
| Location | Soil / Water | Top-3 crops |
|----------|--------------|-------------|
| Warangal (Telangana) | red_loam / low | Red Gram, Green Gram, Ragi |
| Guntur (AP) | black / high | Red Gram, Jowar, Onion |
| Nizamabad (Telangana) | red / low, low budget | Red Gram, Green Gram, Ragi |
| Hyderabad/Rangareddy | any / borewell | region-fit crops with mandi variance |

Crops, mandi prices and advisory all vary per location.

## Voice controls
Start / Stop listening, Speak, Pause, Repeat, Change language — all built into hero.
Text chunked by punctuation for natural pauses; multilingual TTS via browser Speech Synthesis.

## Architecture
- `app/api/[[...path]]/route.js` — all API endpoints (Next.js catch-all)
- `app/page.js` — single-page AgentDashboard with all panels
- `lib/crop_kb.js` — crop knowledge base (states, soils, seasons, water, prices, demand)
- `lib/i18n.js` — English/Telugu/Hindi strings + voice tags

## Pest Guard Page

Open:

```text
http://localhost:3000/pest-guard
```

Added file:

```text
app/pest-guard/page.js
```

The page uses browser camera access through `navigator.mediaDevices.getUserMedia`, captures a frame to canvas, and sends it to the FastAPI backend endpoint `/api/pest-animal-detect`.

On a phone, camera access works best when using `localhost` during local testing or HTTPS when deployed.
