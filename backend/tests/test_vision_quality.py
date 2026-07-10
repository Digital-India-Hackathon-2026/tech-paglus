from PIL import Image, ImageDraw, ImageFilter

from services.vision.quality import evaluate_image_quality


def textured_image() -> Image.Image:
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    for index in range(0, 800, 18):
        draw.line((index, 0, 800 - index, 600), fill=(20 + index % 180, 120, 45), width=5)
    return image


def test_clear_high_resolution_image_is_accepted():
    report = evaluate_image_quality(textured_image())
    assert report.suitable is True
    assert not report.issues


def test_blurry_image_is_rejected():
    image = textured_image().filter(ImageFilter.GaussianBlur(radius=20))
    report = evaluate_image_quality(image)
    assert report.suitable is False
    assert "blurry" in report.issues


def test_dark_image_is_rejected():
    report = evaluate_image_quality(Image.new("RGB", (800, 600), (5, 5, 5)))
    assert report.suitable is False
    assert "too_dark" in report.issues
