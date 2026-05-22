"""File organizer — moves downloaded files to /music/{Artist}/{Album}/ structure."""
import logging
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.utils.audio import sanitize_filename, extract_metadata_mutagen, compute_checksum

logger = logging.getLogger(__name__)


async def import_file(source_path: Path, db: AsyncSession) -> dict:
    """Move a downloaded file to the organized music library.
    Returns dict with success, dest_path, and metadata.
    """
    if not source_path.exists():
        return {"success": False, "error": "Source file not found"}

    metadata = extract_metadata_mutagen(source_path)
    artist = sanitize_filename(metadata.get("artist") or "Unknown Artist")
    album = sanitize_filename(metadata.get("album") or "Unknown Album")
    title = sanitize_filename(metadata.get("title") or source_path.stem)
    track_number = metadata.get("track_number")
    extension = source_path.suffix.lower()

    # Build destination path
    if track_number is not None:
        dest_filename = f"{track_number:02d} - {title}{extension}"
    else:
        dest_filename = f"{title}{extension}"

    dest_dir = Path(config.music_path) / artist / album
    dest_path = dest_dir / dest_filename

    # Handle duplicates
    if dest_path.exists():
        existing_checksum = compute_checksum(dest_path)
        new_checksum = compute_checksum(source_path)
        if existing_checksum == new_checksum:
            logger.info("Duplicate file (same checksum), removing source: %s", source_path)
            source_path.unlink(missing_ok=True)
            return {
                "success": True,
                "dest_path": str(dest_path),
                "metadata": metadata,
                "duplicate": True,
            }
        else:
            # Different content, add suffix
            stem = dest_path.stem
            counter = 2
            while dest_path.exists():
                dest_filename = f"{stem} ({counter}){extension}"
                dest_path = dest_dir / dest_filename
                counter += 1

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Move file
    try:
        shutil.move(str(source_path), str(dest_path))
        logger.info("Moved %s → %s", source_path, dest_path)
    except Exception as e:
        logger.error("Failed to move %s: %s", source_path, e)
        return {"success": False, "error": str(e)}

    return {
        "success": True,
        "dest_path": str(dest_path),
        "metadata": metadata,
        "duplicate": False,
    }