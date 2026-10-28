"""
File Upload & Validation Utility
--------------------------------
Handles secure MIME-type inspection using magic bytes, size limits, 
and randomized file storage.
"""

import uuid
from pathlib import Path
import aiofiles
import magic  # Requires 'python-magic' package
from fastapi import UploadFile, HTTPException, status

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB max file size limit


async def save_upload_file_securely(image: UploadFile, upload_dir: Path) -> str:
    """
    Validates file integrity using magic bytes (MIME sniffing), enforces size caps,
    and saves the file with a randomized UUID name to prevent path traversal or overwrites.
    """
    if not image or not image.filename:
        return None

    # Read header chunk for magic bytes inspection (MIME type verification)
    header_chunk = await image.read(2048)
    await image.seek(0)  # Reset file pointer back to start
    
    mime = magic.from_buffer(header_chunk, mime=True)
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{mime}'. Only JPEG, PNG, and WebP images are allowed.",
        )

    # Enforce file size limit
    file_bytes = await image.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5MB maximum limit.",
        )

    # Generate a secure, randomized filename (discarding user-supplied name)
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    file_ext = ext_map.get(mime, "jpg")
    unique_filename = f"{uuid.uuid4().hex}.{file_ext}"

    # Save file asynchronously to disk
    destination = upload_dir / unique_filename
    async with aiofiles.open(destination, "wb") as buffer:
        await buffer.write(file_bytes)

    return f"/static/uploads/{unique_filename}"
