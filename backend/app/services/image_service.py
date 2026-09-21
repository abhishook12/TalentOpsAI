"""
image_service.py — Avatar and profile image optimization and formatting service.
Supports native PC image upload, base64 data URIs, EXIF auto-rotation, 1:1 center-cropping,
and Lanczos antialiased resampling to compact WebP format.
"""
import io
import base64
import logging
from typing import Optional, Union
from PIL import Image, ImageOps

logger = logging.getLogger("talentops.image_service")

MAX_INPUT_BYTES = 10 * 1024 * 1024  # 10MB limit
AVATAR_TARGET_SIZE = 256  # 256x256 high-DPI thumbnail
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}


def process_avatar_bytes(image_bytes: bytes) -> str:
    """
    Validates, center-crops to 1:1, resizes to AVATAR_TARGET_SIZE,
    and converts the image to a compact WebP data URI string.
    """
    if not image_bytes:
        raise ValueError("Image data is empty.")

    if len(image_bytes) > MAX_INPUT_BYTES:
        raise ValueError("Image file exceeds maximum allowable size (10MB).")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)  # Correct orientation from camera/phone EXIF
    except Exception as err:
        raise ValueError(f"Invalid image format or corrupted file: {err}")

    # Center crop to 1:1 square
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))

    # Resize with high quality antialiasing
    img = img.resize((AVATAR_TARGET_SIZE, AVATAR_TARGET_SIZE), Image.Resampling.LANCZOS)

    # Convert to WebP (superior compression and wide modern browser support)
    out_buf = io.BytesIO()
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img.save(out_buf, format="WEBP", quality=85, method=4)
    else:
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out_buf, format="WEBP", quality=85, method=4)

    encoded = base64.b64encode(out_buf.getvalue()).decode("utf-8")
    return f"data:image/webp;base64,{encoded}"


def process_avatar_data_uri_or_bytes(raw_input: Union[bytes, str]) -> str:
    """
    Handles either raw bytes from a file upload, or a base64 Data URI string.
    """
    if isinstance(raw_input, str):
        if raw_input.startswith("data:image/"):
            parts = raw_input.split(",", 1)
            if len(parts) == 2:
                raw_bytes = base64.b64decode(parts[1])
                return process_avatar_bytes(raw_bytes)
        elif raw_input.startswith("http://") or raw_input.startswith("https://"):
            return raw_input
        else:
            raw_bytes = base64.b64decode(raw_input)
            return process_avatar_bytes(raw_bytes)
    return process_avatar_bytes(raw_input)
