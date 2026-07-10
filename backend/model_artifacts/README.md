# Vision model artifacts

Place exported inference files here. The default registry expects:

- `crop_part_classifier.onnx`
- `disease_classifier.onnx`
- `disease_labels.json`
- `pest_detector.onnx`
- `damage_segmenter.onnx`

The repository intentionally contains no trained weights. Until compatible files are added and the registry is updated with real validation metrics, `/api/vision/health` reports `development_mode` and the analyzer will not invent a diagnosis.
