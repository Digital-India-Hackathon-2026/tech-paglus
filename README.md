# AgriSarthi Full-Stack Working Application

This folder combines:

- `backend/` — FastAPI backend from **agri_website 4**
- `frontend/` — editable Next.js frontend from **agrisarthi_5 / agri_website 5**
- Next.js API rewrites so frontend calls go to FastAPI at `http://127.0.0.1:8000`

Note: the uploaded `agrisarthi_nextjs` ZIP contained only `.next` build/cache files and no editable Next.js source. The editable working frontend has therefore been taken from the uploaded `agrisarthi_5` project and connected to the `agri_website 4` backend.

## Folder Structure

```text
agrisarthi_fullstack_working/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── models/
│   ├── services/
│   └── sample_docs/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── next.config.js
├── start_backend.bat
├── start_frontend.bat
└── start_all.bat
```

## Run Backend

Open Terminal 1:

```bat
cd %USERPROFILE%\Desktop\agrisarthi_fullstack_working\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --host 127.0.0.1 --port 8000
```

Check backend:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Run Frontend

Open Terminal 2:

```bat
cd %USERPROFILE%\Desktop\agrisarthi_fullstack_working\frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## One-command run

From the project root:

```bat
cd %USERPROFILE%\Desktop\agrisarthi_fullstack_working
start_all.bat
```

The one-command script starts FastAPI in the background and then starts the Next.js frontend.

## Important API Connection

The frontend uses normal calls like:

```js
fetch('/api/recommend')
fetch('/api/geocode')
fetch('/api/pdf-extract')
```

`frontend/next.config.js` rewrites these calls to:

```text
http://127.0.0.1:8000/api/...
```

The backend includes compatibility routes for the Next.js UI:

```text
POST /api/geocode
POST /api/reverse-geocode
POST /api/pdf-extract
POST /api/recommend
POST /api/mandi
POST /api/irrigation
POST /api/advisory-ui
POST /api/feedback-ui
POST /api/profile
```

The original backend routes are also preserved:

```text
POST /api/advisory
POST /api/recommendations
POST /api/soil-report
POST /api/document-intake
POST /api/location/verify
GET  /api/memory
POST /api/memory/consent
POST /api/feedback
```

## Environment Keys

The ZIP intentionally includes only safe `.env.example` files. Add your real keys locally in `backend/.env` if needed:

```env
DATAGOV_API_KEY=
AI_ADVISORY_API_KEY=
```

The app still works with local fallback logic if these keys are blank.

## If port 8000 is already busy

```bat
for /f "tokens=5" %p in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %p
```

Then restart the backend.

## New Feature: Live Pest & Animal Guard

This ZIP also includes a phone-camera scouting feature for pest, animal and crop-damage risk.

Open after starting both backend and frontend:

```text
http://localhost:3000/pest-guard
```

Files added/changed:

```text
frontend/app/pest-guard/page.js              # phone camera UI + photo upload + live scanning
frontend/app/page.js                         # added button linking to Pest Guard
backend/services/pest_animal_detector.py     # lightweight image analysis logic
backend/main.py                              # added /api/pest-animal-detect endpoint
backend/requirements.txt                     # added Pillow dependency
```

Backend endpoint:

```text
POST /api/pest-animal-detect
```

It accepts a JPG/PNG/WEBP image under multipart field name `file` and returns possible pest, animal, and crop-damage risk signs.

Important: normal phone cameras cannot perform true thermal imaging. The UI includes a thermal-style visual filter for scouting, but true thermal/night heat detection requires an external FLIR/Seek/USB-C thermal camera, thermal drone camera, or similar sensor. The current module is designed so you can later replace `backend/services/pest_animal_detector.py` with a trained YOLO/TFLite/Roboflow model.

## Neural Pest & Animal Guard upgrade

Open `/pest-guard` for phone-camera pest/animal detection. The updated backend is neural-network-ready:

- hosted Roboflow detector via `ROBOFLOW_API_KEY` and `ROBOFLOW_MODEL_ID`, or
- local ONNX classifier at `backend/ml_models/pest_classifier.onnx`.

Read `PEST_NEURAL_NETWORK_GUIDE.md` for exact setup and phone-camera workflow.
