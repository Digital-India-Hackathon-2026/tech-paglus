# Reviewed-feedback candidate area

Feedback is written to `pending/` as metadata with status `pending_expert_review`.

- Farmer images are never copied here automatically.
- Original image paths are listed only when the farmer consented to image use.
- A qualified reviewer must verify crop, disease/pest label, region, image quality and consent before changing status or moving any image into a training dataset.
- The production API never trains directly from this directory.
- Pending runtime JSON files are excluded from the final ZIP and source control.
