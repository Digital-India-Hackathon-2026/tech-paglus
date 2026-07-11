# AgriSarthi Neural Pest & Animal Guard

This version replaces the earlier visual-heuristic pest scanner with a neural-network-ready pipeline.

## What changed

### Backend

New files:

```text
backend/services/nn_pest_classifier.py
backend/ml_models/pest_labels.json
backend/requirements-ml.txt
backend/scripts/train_pest_classifier.py
```

Updated files:

```text
backend/services/pest_animal_detector.py
backend/main.py
```

Backend endpoint:

```text
POST /api/pest-animal-detect
```

It accepts:

```text
file: crop/pest image
crop: crop name, e.g. cotton, paddy, chilli
camera_mode: rgb | near_ir_like | thermal_external
```

### Frontend

Updated page:

```text
frontend/app/pest-guard/page.js
```

Open:

```text
http://localhost:3000/pest-guard
```

## How the neural network is connected

The backend uses this priority order:

1. **Roboflow hosted neural network**, if these are set in `backend/.env`:

```env
ROBOFLOW_API_KEY=your_key_here
ROBOFLOW_MODEL_ID=your-workspace-model/version
ROBOFLOW_CONFIDENCE=35
```

2. **Local ONNX neural-network classifier**, if this file exists:

```text
backend/ml_models/pest_classifier.onnx
```

3. If no model is connected, the app still accepts images but clearly reports that a trained model is missing.

## Local ONNX setup

Install normal backend requirements first. Then install optional ML requirements:

```bash
cd ~/Desktop/agrisarthi_6_pest_nn_fullstack/backend
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-ml.txt
```

Place your trained model here:

```text
backend/ml_models/pest_classifier.onnx
```

Place class labels here:

```text
backend/ml_models/pest_labels.json
```

The labels already include examples:

```text
healthy_crop, aphids, whitefly, fall_armyworm, bollworm, stem_borer,
leaf_miner, thrips, mites, locust_grasshopper, rodent_animal_damage,
wild_boar_cattle_damage
```

## Phone camera from OnePlus to laptop

Best practical method:

1. Run backend on laptop.
2. Run frontend on laptop.
3. Expose frontend with HTTPS tunnel, for example ngrok.
4. Open the HTTPS frontend URL on your OnePlus.
5. Go to `/pest-guard` and allow camera permission.
6. The phone sends frames to the laptop backend through the Next.js frontend.

Backend:

```bash
cd ~/Desktop/agrisarthi_6_pest_nn_fullstack/backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd ~/Desktop/agrisarthi_6_pest_nn_fullstack/frontend
npm install
npm run dev -- --hostname 0.0.0.0
```

Tunnel frontend:

```bash
ngrok http 3000
```

Open the HTTPS ngrok URL on your phone:

```text
https://your-ngrok-url.ngrok-free.app/pest-guard
```

## Thermal / IR note

A phone RGB camera or IR face/security camera is not a calibrated thermal camera. It cannot measure crop or animal heat maps like a FLIR/Seek thermal camera. The app supports a `thermal_external` mode so that if you later connect a real thermal camera and capture frames, the backend can classify those images too, but the neural network must be trained on similar thermal images.

## Important agriculture note

Pests are usually controlled using integrated pest management: scouting, traps, biocontrol, neem-based sprays, and only then label-approved pesticides. Fertilisers improve crop health but do not directly kill pests. This app therefore suggests natural crop-care inputs such as compost, FYM, neem cake, balanced NPK and potash correction based on the detected pest class.
