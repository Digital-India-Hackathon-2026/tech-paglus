# AgriSarthi AI — project folder `agrisarthi_8`

AgriSarthi is a Next.js + FastAPI farmer-assistance website. This package preserves the existing registration, multilingual voice assistant, PDF/soil intake, location, weather, crop recommendation, mandi, irrigation, fertilizer, scheme, memory, and feedback features and adds a modular **AI Crop Pest and Disease Vision Analyzer** at:

```text
http://localhost:3000/pest-guard
```

## Existing architecture found in the uploaded project

```text
agrisarthi_8/
├── frontend/                  Next.js 15 App Router, React 18, Tailwind and Radix UI
│   ├── app/                   login, register, crop plan, main farmer agent and scanner routes
│   ├── components/            reusable UI, authentication, notifications and chatbot
│   └── lib/                   authentication, language, crop knowledge and helper modules
├── backend/                   FastAPI application
│   ├── main.py                existing routes plus the new vision router
│   ├── services/              weather, market, PDF, advisory, auth and vision services
│   ├── models/                Pydantic request/response schemas
│   ├── database.db            existing SQLite data used by the original app
│   └── migrations/            new vision database migration
├── ml_training/               separate training/evaluation/export workspace
└── start_*.sh / start_*.bat   existing launch helpers
```

Frontend requests use `/api/...`; `frontend/next.config.js` rewrites them to the FastAPI server at `http://127.0.0.1:8000` unless overridden.

## Vision analyzer implementation

The new backend is under `backend/services/vision/` and includes:

- real image-content validation through Pillow, not extension-only validation;
- JPEG, PNG and WEBP support, with optional HEIC/HEIF support through `pillow-heif`;
- EXIF orientation correction and metadata-stripping re-encoding;
- image size, brightness, overexposure, contrast and blur checks;
- configurable crop/part classifier, multi-label disease classifier, pest detector and damage segmenter adapters;
- one-time model loading during FastAPI lifespan startup;
- automatic CPU fallback, optional Apple Silicon MPS for YOLO, and ONNX Runtime CoreML use when available;
- low-confidence, top-alternative, apparently-healthy, unsupported-subject and unknown-condition handling;
- pest boxes, segmentation masks/polygons, damaged-region annotations and most-affected-region crops;
- severity only when segmentation evidence exists—classification confidence is never converted into fake severity;
- treatment filtering by crop, diagnosis, location, growth/harvest stage, preference, budget, weather, prior treatment and optional soil data;
- a verified-treatment gate: commercial advice is withheld unless a matching knowledge-base record is explicitly marked `verified`;
- temporary/consented retention policies, sanitized stored images and expiry cleanup;
- normalized SQLite tables for sessions, images, predictions, diseases, pests, regions, recommendations and feedback;
- feedback stored as `pending_expert_review` with separate candidate metadata; images are never copied into training automatically;
- rate limiting, upload limits, request timeouts, safe file paths and configurable CORS.

### Honest model status

No trained model weights were present in the uploaded ZIP, and none are fabricated in this package. The default registry therefore reports:

```text
development_mode
```

In development mode the service can validate and store images temporarily, but it returns **no disease, pest, crop or severity prediction**. It will become an inference service only after compatible, evaluated weights and labels are placed in `backend/model_artifacts/` and `backend/model_registry.json` is updated with real versions and metrics.

## Mac setup — backend

Open Terminal 1:

```bash
cd ~/Desktop/agrisarthi_8/backend

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/vision/health
```

For local ONNX/YOLO inference and HEIC support, stop the server and install the optional runtime:

```bash
source .venv/bin/activate
python -m pip install -r requirements-vision.txt
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --host 127.0.0.1 --port 8000
```

For ML packages, a separate Python 3.11 or 3.12 environment is often easier to troubleshoot than mixing them into an existing Python environment. The normal FastAPI backend does not require the optional ML runtime while no weights are installed.

## Mac setup — frontend

Open Terminal 2:

```bash
cd ~/Desktop/agrisarthi_8/frontend
cp .env.local.example .env.local
npm ci
npm run dev
```

Open:

```text
http://127.0.0.1:3000
http://127.0.0.1:3000/pest-guard
```

## Vision endpoints

```text
POST /api/vision/analyze
POST /api/vision/analyze-session
GET  /api/vision/result/{analysis_id}
GET  /api/vision/history?owner_id=...
POST /api/vision/feedback
GET  /api/vision/model-info
GET  /api/vision/health
```

The former `POST /api/pest-animal-detect` route is retained for compatibility with older clients.

### Single-image request

```bash
curl -X POST http://127.0.0.1:8000/api/vision/analyze \
  -F "file=@/absolute/path/to/leaf.jpg" \
  -F "owner_id=my-browser-session" \
  -F "crop=auto" \
  -F "plant_part=auto" \
  -F "growth_stage=auto" \
  -F "harvest_stage=auto" \
  -F "location=Warangal, Telangana" \
  -F "latitude=17.9689" \
  -F "longitude=79.5941" \
  -F "treatment_preference=integrated" \
  -F "budget=low" \
  -F "previous_treatment=" \
  -F "consent=false"
```

### Multiple-image session

```bash
curl -X POST http://127.0.0.1:8000/api/vision/analyze-session \
  -F "files=@/absolute/path/to/full-plant.jpg" \
  -F "files=@/absolute/path/to/leaf-front.jpg" \
  -F "files=@/absolute/path/to/leaf-back.jpg" \
  -F "files=@/absolute/path/to/pest-closeup.jpg" \
  -F "owner_id=my-browser-session" \
  -F "crop=tomato" \
  -F "treatment_preference=cheapest" \
  -F "budget=low" \
  -F "consent=false"
```

### Feedback request

```bash
curl -X POST http://127.0.0.1:8000/api/vision/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "replace-with-analysis-id",
    "owner_id": "my-browser-session",
    "verdict": "partially_correct",
    "crop_correct": true,
    "disease_correct": false,
    "corrected_label": "expert-reviewed label",
    "notes": "Uploaded front and back leaf views"
  }'
```

## Model placement and registry

Default files expected by `backend/model_registry.json`:

```text
backend/model_artifacts/crop_part_classifier.onnx
backend/model_artifacts/disease_classifier.onnx
backend/model_artifacts/disease_labels.json
backend/model_artifacts/pest_detector.onnx
backend/model_artifacts/damage_segmenter.onnx
```

After exporting real models:

1. Copy/export them into `backend/model_artifacts/`.
2. Put the exact disease label order in `disease_labels.json`.
3. Update `model_registry.json` with the real version, training date, supported crops, thresholds and validation metrics.
4. Restart FastAPI so models load once at startup.
5. Confirm `/api/vision/health` shows the expected models as `ready`.
6. Test with held-out field images before enabling farmer-facing claims.

Model files are intentionally excluded from the ZIP and `.gitignore` because no evaluated weights were supplied.

## Verified treatment knowledge base

`backend/knowledge_base/treatments.json` is empty by design. Only entries with all of the following can produce commercial recommendations:

```json
{
  "verification_status": "verified",
  "regulatory_status": "registered_unrestricted",
  "crop_compatible": true,
  "active": true
}
```

This prevents draft, banned, restricted, inactive, or crop-incompatible records from reaching farmers. Use `treatments.schema.example.json` as the schema, then validate each crop, diagnosis, region, pre/post-harvest use, active ingredient, safety warning, re-entry interval and pre-harvest interval against an official regulator, registered product label or agricultural authority.

Never add invented dosage. Leave unavailable fields null and direct the farmer to the label or local agriculture officer.

## Training workspace

```bash
cd ~/Desktop/agrisarthi_8/ml_training
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-training.txt
```

Prepare a leakage-safe classification manifest:

```bash
python scripts/prepare_dataset.py
```

Train:

```bash
python train_classifier.py
python train_detector.py --data configs/pest_detection.yaml
python train_segmenter.py --data configs/damage_segmentation.yaml
```

Evaluate:

```bash
python evaluate_models.py \
  --detector models/pest_detector/weights/best.pt \
  --segmenter models/damage_segmenter/weights/best.pt
```

Export into the backend model directory:

```bash
python export_models.py \
  --classifier-checkpoint models/disease_classifier/best.pt \
  --detector models/pest_detector/weights/best.pt \
  --segmenter models/damage_segmenter/weights/best.pt
```

Read `ml_training/README.md` before adding datasets. Class names are configuration-driven; the sample directories are empty and do not indicate accuracy.

## Tests

The included backend suite currently contains 15 passing tests covering clear, dark, blurry, unsupported, oversized, healthy, non-plant/unclear, low-confidence, multi-disease, multi-pest, model-unavailable, database-unavailable, feedback/history and existing-route preservation scenarios.

Backend:

```bash
cd ~/Desktop/agrisarthi_8/backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Frontend syntax/build:

```bash
cd ~/Desktop/agrisarthi_8/frontend
npm ci
npm run build
```

A full Next.js build requires package-registry access. In the packaging environment, dependency installation could not complete because the npm registry was unreachable, so source-level JSX parsing was run instead. Run the two commands above on the deployment Mac before making a production claim.

Optional browser tests:

```bash
cd ~/Desktop/agrisarthi_8/frontend
npm install --save-dev @playwright/test
npx playwright install chromium
npm run test:e2e
```

The browser tests mock the backend to cover upload, uncertainty-safe result rendering and mobile-width overflow. Real-model tests require separately supplied held-out images and trained weights. The scanner downloads a farmer-friendly HTML report that can be opened or printed to PDF; Advanced view also exports the full technical JSON.

## Troubleshooting

### `zsh: command not found: uvicorn`

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --port 8000
```

### `No such file or directory: requirements.txt`

You are in the wrong folder:

```bash
cd ~/Desktop/agrisarthi_8/backend
pwd
ls
```

### Scanner says development mode

This is correct until evaluated weights exist. Check:

```bash
curl http://127.0.0.1:8000/api/vision/model-info
```

Then verify the model files and label order in `backend/model_registry.json`.

### HEIC image rejected

```bash
cd ~/Desktop/agrisarthi_8/backend
source .venv/bin/activate
python -m pip install pillow-heif
```

Restart the backend, or convert the image to JPEG on the phone/Mac.

### Upload receives `413`

Reduce the image size or change `VISION_MAX_UPLOAD_MB` in `backend/.env`, then restart FastAPI. Do not set an unlimited value on a public server.

### Browser reports API or CORS failure

Confirm both terminals are running. Ensure `BACKEND_URL` in `frontend/.env.local` points to the backend and the frontend origin is listed in `CORS_ALLOWED_ORIGINS`.

### No chemical recommendation appears

This is a safety feature. Add only verified, region-compatible records to the knowledge base. The system will not invent dosage or treat fertilizer as a cure for infection.

### Database unavailable

Ensure the backend directory is writable and `VISION_DATABASE_PATH` points to a writable SQLite file. Delete only `vision.db` if you intentionally want to recreate the new vision history; do not delete the original `database.db` unless you accept losing existing app data.

## Security and privacy notes

- The final package contains no local `.env`, `.env.local`, virtual environment, `node_modules`, Next build cache, model weight, or runtime vision database.
- Rotate any real API key that was previously stored in the uploaded ZIP because removing it from the returned package does not invalidate an already exposed key.
- Images without consent expire according to `VISION_TEMP_RETENTION_HOURS`; consented images expire according to `VISION_CONSENT_RETENTION_DAYS`.
- Feedback metadata is written under `backend/storage/dataset_candidates/pending/`; it remains ineligible for training until expert approval.
- `VISION_MAX_PIXELS` blocks decompression-bomb-style oversized image dimensions, while `VISION_MAX_UPLOAD_MB` limits transfer size.
- Stored copies are re-encoded to strip EXIF metadata.
- The image analysis is advisory and not a replacement for laboratory testing, an agriculture expert or a registered product label.
