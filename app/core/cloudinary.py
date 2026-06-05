import re

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _extract_public_id(image_url: str) -> str | None:
    match = re.search(r"/v\d+/(.+)\.\w+$", image_url)
    return match.group(1) if match else None


def _configure_cloudinary():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


async def upload_event_image(file: UploadFile) -> str:
    _configure_cloudinary()

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"field": "image", "message": "Invalid image format. Allowed: jpeg, png, webp, gif"}],
        )

    contents = await file.read()

    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"field": "image", "message": "Image size must not exceed 5 MB"}],
        )

    try:
        result = cloudinary.uploader.upload(
            contents,
            folder="events/",
            resource_type="image",
        )
        return result["secure_url"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"field": "image", "message": f"Failed to upload image: {str(e)}"}],
        )


def delete_event_image(image_url: str) -> None:
    public_id = _extract_public_id(image_url)
    if not public_id:
        return

    _configure_cloudinary()

    try:
        cloudinary.uploader.destroy(public_id, resource_type="image")
    except Exception:
        pass
