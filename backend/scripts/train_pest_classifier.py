"""Train a pest image classifier and export ONNX.

Dataset format:
backend/datasets/pest_dataset/
  train/
    aphids/*.jpg
    whitefly/*.jpg
    healthy_crop/*.jpg
  val/
    aphids/*.jpg
    whitefly/*.jpg
    healthy_crop/*.jpg

This is a template. For real accuracy, collect local crop/pest images from your
region and label them carefully. Export output to:
    backend/ml_models/pest_classifier.onnx
"""

print("Training template added. Use PyTorch/TensorFlow/Roboflow to train on your labelled pest dataset, then export ONNX to backend/ml_models/pest_classifier.onnx")
