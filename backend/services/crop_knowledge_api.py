import os

from models.schemas import ApiStatus
from services.http_client import ApiError, get_json


def get_crop_knowledge(crop: str) -> ApiStatus:
    api_url = os.getenv("CROP_KNOWLEDGE_API_URL")
    if not api_url:
        return ApiStatus(
            source="External Crop Knowledge API",
            configured=False,
            message="CROP_KNOWLEDGE_API_URL is not configured",
            data={},
        )

    try:
        data = get_json(api_url, {"crop": crop})
        return ApiStatus(source="External Crop Knowledge API", data=data)
    except ApiError as exc:
        return ApiStatus(
            source="External Crop Knowledge API",
            configured=True,
            message=f"crop knowledge api failed: {exc}",
            data={},
        )
