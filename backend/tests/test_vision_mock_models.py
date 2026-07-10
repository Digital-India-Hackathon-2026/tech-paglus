from io import BytesIO

from PIL import Image, ImageDraw

from services.vision.runtime import InputImage, VisionRuntime


class FakeAdapter:
    ready = True

    def __init__(self, payload):
        self.payload = payload

    def predict(self, image):
        return self.payload


def source() -> InputImage:
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    for index in range(0, 800, 20):
        draw.ellipse((index, 100, index + 80, 350), fill=(30, 130, 40), outline=(0, 80, 0), width=4)
    out = BytesIO(); image.save(out, "JPEG", quality=92)
    return InputImage("crop.jpg", out.getvalue())


def runtime_with_models(disease_predictions, pest_detections, segment_regions=None, crop_predictions=None):
    runtime = VisionRuntime()
    runtime.initialized = True
    runtime.adapters = {
        "crop_part_classifier": FakeAdapter({"predictions": crop_predictions if crop_predictions is not None else [{"label": "tomato__leaf__fruiting__pre_harvest__close_up", "confidence": 0.97}]}),
        "disease_classifier": FakeAdapter({"predictions": disease_predictions}),
        "pest_detector": FakeAdapter({"detections": pest_detections}),
        "damage_segmenter": FakeAdapter({"regions": segment_regions if segment_regions is not None else [{"label": "lesion", "confidence": 0.9, "bbox": [0.2, 0.2, 0.3, 0.3], "area_fraction": 0.12}]}),
    }
    runtime.statuses = {key: {"key": key, "name": key, "version": "test", "task": key, "adapter": "fake", "threshold": 0.5, "ready": True, "message": "test"} for key in runtime.adapters}
    return runtime


def test_multiple_diseases_and_pests_are_preserved():
    runtime = runtime_with_models(
        [
            {"label": "fungal__early_blight", "confidence": 0.91},
            {"label": "nutrient__nitrogen_deficiency", "confidence": 0.72},
            {"label": "bacterial__spot", "confidence": 0.41},
        ],
        [
            {"label": "aphid__adult", "confidence": 0.86, "bbox": [0.1, 0.1, 0.1, 0.1]},
            {"label": "whitefly__nymph", "confidence": 0.76, "bbox": [0.5, 0.4, 0.1, 0.1]},
        ],
    )
    result = runtime.analyze_session([source()], owner_id="mock_owner_1234", crop="auto")
    assert result["status"] == "completed"
    assert result["detected_crop"] == "Tomato"
    assert len(result["diseases"]) == 2
    assert len(result["pests"]) == 2
    assert result["severity"]["level"] == "low"
    assert result["images"][0]["urls"]["annotated"]
    assert result["images"][0]["urls"]["zoom"]


def test_low_confidence_is_uncertain_not_forced():
    runtime = runtime_with_models(
        [{"label": "fungal__early_blight", "confidence": 0.31}],
        [],
    )
    result = runtime.analyze_session([source()], owner_id="mock_low_conf_1234", crop="auto")
    assert result["status"] == "uncertain"
    assert result["diseases"] == []
    assert result["possible_alternatives"]


def test_reliable_healthy_class_does_not_create_disease_or_chemical_advice():
    runtime = runtime_with_models(
        [{"label": "healthy", "confidence": 0.94}],
        [],
        segment_regions=[],
    )
    result = runtime.analyze_session([source()], owner_id="mock_healthy_1234", crop="auto")
    assert result["status"] == "completed"
    assert result["health_assessment"]["label"] == "Apparently healthy"
    assert result["diseases"] == []
    assert result["pests"] == []
    assert result["recommendations"]["commercial"] == []
    assert "No pesticide" in result["recommendations"]["commercial_warning"]


def test_non_plant_or_unclear_subject_is_rejected_before_disease_classification():
    runtime = runtime_with_models(
        [{"label": "fungal__early_blight", "confidence": 0.99}],
        [],
        segment_regions=[],
        crop_predictions=[],
    )
    result = runtime.analyze_session([source()], owner_id="mock_nonplant_1234", crop="auto")
    assert result["status"] == "needs_better_images"
    assert result["diseases"] == []
    assert "unsupported_or_unclear_subject" in result["images"][0]["quality"]["issues"]
