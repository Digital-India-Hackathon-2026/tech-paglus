# AgriSarthi AI Web

This is a modular FastAPI + React website based on the AgriSarthi AI hackathon PDF. It recommends profitable crops using PDF-first farmer input, voice assistance, farm profile, location, soil, season, irrigation, historical weather risk, satellite/agroclimate data, mandi prices, seed options, fertilizer needs, soil report analysis and regional demand planning.

Recommended farmer documents:

- First file: Soil Health Card or soil test report PDF.
- Optional second file: land passbook, pattadar passbook, ROR-1B, crop booking receipt, e-Crop receipt, or any land/farm detail PDF.

## Backend

```bash
cd ~/Desktop/"agri_website 3"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --reload-exclude ".venv/*" --host 127.0.0.1 --port 8000
```

If `uvicorn` is not found, run it through Python:

```bash
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --port 8000
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

Main endpoints:

```text
POST /api/advisory
POST /api/recommendations
POST /api/soil-report
POST /api/document-intake
```

Example request:

```json
{
  "farmer_name": "Gnaneshwar",
  "location": "Village: Hasanparthy, Mandal: Hasanparthy, District: Warangal, State: Telangana",
  "crop": "cotton",
  "soil_type": "black",
  "season": "kharif",
  "land_type": "normal",
  "irrigation_available": true,
  "farm_area_acres": 2,
  "budget_per_acre": 40000,
  "preferred_language": "English"
}
```

## Frontend

```bash
cd ~/Desktop/"agri_website 3/frontend"
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

If Vite shows a different local URL, open the URL printed in the terminal.

## Environment Setup

The app works without OpenAI. For the advisory LLM, use Groq because it is OpenAI-compatible with the existing backend.

```env
DATAGOV_API_KEY=your_data_gov_in_key_here
AI_ADVISORY_API_URL=https://api.groq.com/openai/v1/chat/completions
AI_ADVISORY_API_KEY=your_groq_key_here
AI_ADVISORY_MODEL=llama-3.3-70b-versatile
CROP_KNOWLEDGE_API_URL=
RADAR_TILE_PROVIDER=rainviewer
```

If `AI_ADVISORY_API_KEY` is blank, the app still returns local Telugu, Hindi and English farmer advice from the risk engine. RainViewer radar does not need an API key.

## Features Covered

- Advanced Mode v3.1 UI with sticky navigation and separate sections for advisory, PDF input, voice agent, recommendations, mandi, weather risk, inputs, Admin/FPO and advanced features.
- Farmer registration and farm profile form with empty first-load inputs, placeholders, validation and optional sample data.
- PDF-first intake for 1 or 2 farmer documents, auto-filling farmer name, location, crop, soil type, season, land type, irrigation, area, budget and language where readable.
- Soil report PDF/text upload with pH, NPK, organic carbon, EC, inferred soil type, confidence, detected issues and recommendations.
- Browser voice agent for spoken input and farmer-friendly Telugu, Hindi and English spoken advisory output with slower delivery and pauses.
- Full-address and coordinate-aware location detection from farmer documents, including village/mandal/district/state labels and latitude/longitude text where present.
- Location, soil, season, irrigation, area, budget and regional crop-cluster based crop recommendation.
- Top 3 crop recommendations with total score, soil score, weather score, mandi score, demand score, profit score and risk score.
- Profit estimate, fertilizer plan and seed suggestions.
- Nearby mandi price comparison with data.gov.in support when `DATAGOV_API_KEY` is configured, plus transparent locality-based estimates when live data is unavailable.
- Weather forecast, one-year historical weather archive, soil moisture, elevation, satellite/agroclimate and field-centered RainViewer radar integration.
- Local ML weather danger model that compares forecast stress against historical climate baselines for the selected field location.
- AI-style farmer explanation and risk advice.
- Admin/FPO dashboard for regional demand, oversupply warnings and planning actions.
- Working advanced advisory modules for offline cache, WhatsApp/SMS alert text, leaf-image triage hook, pest/disease warnings, scheme matching, marketplace suggestions and local feedback storage.

## API Modules

- `services/location_api.py`: converts full location text or latitude/longitude into field coordinates with district/state fallbacks.
- `services/weather_api.py`: gets rainfall, wind, temperature, soil moisture and evapotranspiration forecast.
- `services/historical_weather_api.py`: gets one-year daily historical rainfall, temperature, wind and evapotranspiration for the field location.
- `services/radar_api.py`: gets public radar tile metadata plus a field-centered radar preview URL.
- `services/satellite_api.py`: gets NASA POWER agroclimatology data.
- `services/soil_topography_api.py`: gets elevation and soil moisture summary.
- `services/soil_report_api.py`: reads PDF/text soil reports and extracts useful soil health values.
- `services/document_intake_api.py`: reads 1-2 farmer documents and produces an auto-filled farm profile with confidence, evidence and missing questions.
- `services/ml_weather_risk_api.py`: local trained lightweight weather danger scorer using forecast, history and satellite/agroclimate features.
- `services/market_api.py`: gets mandi price data when `DATAGOV_API_KEY` is configured and otherwise returns locality-based estimated records.
- `services/recommendation_engine.py`: ranks crops using soil, weather, profit, mandi and locality crop-priority scoring.
- `services/production_features_api.py`: produces alert messages, pest/disease warnings, scheme matches and marketplace suggestions.
- `services/crop_knowledge_api.py`: connects to an external crop knowledge API if configured.
- `services/advisory_api.py`: connects to Groq/OpenAI-compatible chat completions if configured, with local multilingual fallback advice.
- `services/risk_engine.py`: combines API data into crop risk scores.

## Pest & Animal Detection Endpoint

Added file:

```text
services/pest_animal_detector.py
```

Added endpoint:

```text
POST /api/pest-animal-detect
```

Example with curl:

```bash
curl -X POST http://127.0.0.1:8000/api/pest-animal-detect \
  -F "file=@sample_crop_photo.jpg"
```

The current implementation is a lightweight explainable RGB image scout. For production ML, replace `analyze_crop_frame()` with a trained YOLO/TFLite model and keep the same response JSON shape so the frontend continues to work.
