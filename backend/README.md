# AgriSarthi FastAPI backend

Run from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --host 127.0.0.1 --port 8000
```

Optional vision runtime:

```bash
python -m pip install -r requirements-vision.txt
```

API documentation: `http://127.0.0.1:8000/docs`.

The new vision implementation is in `services/vision/`. It uses `model_registry.json`, `model_artifacts/`, `knowledge_base/treatments.json`, and migration `migrations/001_create_vision_tables.sql`. No trained weights or verified chemical records are bundled; the API reports development mode until those are supplied.

Run tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

See the root `README.md` for all routes, API samples, training commands and troubleshooting.
