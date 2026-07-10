# Legacy pest detector compatibility note

The uploaded project already contained a basic `/api/pest-animal-detect` route with optional Roboflow and local ONNX support. That route remains available so older clients do not break.

The new farmer-facing feature is the modular **AI Crop Pest and Disease Vision Analyzer** documented in the root `README.md` and served at:

```text
http://localhost:3000/pest-guard
```

Use these files for the new pipeline:

```text
backend/model_registry.json
backend/model_artifacts/
backend/knowledge_base/treatments.json
backend/services/vision/
ml_training/
```

No API key or trained model is bundled. Put secrets only in `backend/.env`, which is excluded from the final package. Put evaluated local weights in `backend/model_artifacts/`, update the registry with real versions and metrics, and verify `/api/vision/health` before enabling farmer-facing claims.

The legacy Roboflow environment variables, when intentionally used by the old endpoint, are:

```env
ROBOFLOW_API_KEY=your_key_here
ROBOFLOW_MODEL_ID=your-workspace-model/version
ROBOFLOW_CONFIDENCE=35
```

Do not store a real key in source control or in the frontend.
