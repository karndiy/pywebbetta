from __future__ import annotations

from pathlib import Path
from typing import IO

from PIL import Image
from flask import current_app


def save_upload(file_storage, filename: str) -> str:
    upload_folder = Path(current_app.config.get("MEDIA_UPLOAD_FOLDER", "betta/static/uploads"))
    upload_folder.mkdir(parents=True, exist_ok=True)

    dest = upload_folder / filename
    file_storage.save(dest)
    return f"/static/uploads/{filename}"


def generate_thumbnail(image_path: Path, max_size: tuple[int, int] = (600, 600)) -> Path:
    thumb_folder = Path(current_app.config.get("MEDIA_UPLOAD_FOLDER", "betta/static/uploads")) / "thumbnails"
    thumb_folder.mkdir(parents=True, exist_ok=True)

    img = Image.open(image_path)
    img.thumbnail(max_size)
    thumb_path = thumb_folder / image_path.name
    img.save(thumb_path)
    return thumb_path
