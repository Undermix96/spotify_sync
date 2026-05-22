import hashlib
from pathlib import Path
from typing import Optional


SUPPORTED_FORMATS = {".flac", ".alac", ".m4a", ".wav", ".aiff", ".aif"}


def is_lossless(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_FORMATS


def compute_checksum(path: Path, block_size: int = 65536) -> str:
    """Compute SHA256 of first 64KB of a file for quick deduplication."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        chunk = f.read(block_size)
        hasher.update(chunk)
    return hasher.hexdigest()


def extract_metadata_mutagen(path: Path) -> dict:
    """Extract audio metadata using mutagen."""
    try:
        import mutagen
        from mutagen.flac import FLAC
        from mutagen.aiff import AIFF
        from mutagen.wave import WAVE
        from mutagen.mp4 import MP4
    except ImportError:
        return {"artist": None, "album": None, "title": None, "track_number": None, "duration_ms": None}

    try:
        suffix = path.suffix.lower()
        if suffix == ".flac":
            audio = FLAC(path)
            duration = int(audio.info.length * 1000)
            artist = str(audio.get("artist", [""])[0]) if audio.get("artist") else None
            album = str(audio.get("album", [""])[0]) if audio.get("album") else None
            title = str(audio.get("title", [""])[0]) if audio.get("title") else path.stem
            tracknumber = audio.get("tracknumber", [None])
            track_number = None
            if tracknumber and tracknumber[0]:
                try:
                    track_number = int(str(tracknumber[0]).split("/")[0])
                except ValueError:
                    pass
            return {
                "artist": artist,
                "album": album,
                "title": title,
                "track_number": track_number,
                "duration_ms": duration,
                "format": "flac",
            }
        elif suffix == ".m4a" or suffix == ".alac":
            audio = MP4(path)
            duration = int(audio.info.length * 1000)
            artist = str(audio.get("\xa9ART", [""])[0]) or None
            album = str(audio.get("\xa9alb", [""])[0]) or None
            title = str(audio.get("\xa9nam", [""])[0]) or path.stem
            track_info = audio.get("trkn", [None])
            track_number = track_info[0][0] if track_info and track_info[0] else None
            return {
                "artist": artist,
                "album": album,
                "title": title,
                "track_number": track_number,
                "duration_ms": duration,
                "format": "alac",
            }
        elif suffix == ".wav":
            audio = WAVE(path)
            duration = int(audio.info.length * 1000)
            return {
                "artist": None,
                "album": None,
                "title": path.stem,
                "track_number": None,
                "duration_ms": duration,
                "format": "wav",
            }
        elif suffix in (".aiff", ".aif"):
            audio = AIFF(path)
            duration = int(audio.info.length * 1000)
            return {
                "artist": str(audio.get("artist", [""])[0]) if audio.get("artist") else None,
                "album": str(audio.get("album", [""])[0]) if audio.get("album") else None,
                "title": str(audio.get("title", [""])[0]) if audio.get("title") else path.stem,
                "track_number": None,
                "duration_ms": duration,
                "format": "aiff",
            }
        else:
            return {"artist": None, "album": None, "title": path.stem, "track_number": None, "duration_ms": None, "format": suffix.lstrip(".")}
    except Exception:
        return {"artist": None, "album": None, "title": path.stem, "track_number": None, "duration_ms": None, "format": path.suffix.lstrip(".")}


def sanitize_filename(name: str) -> str:
    """Remove characters that are problematic in filenames."""
    import re
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = name.strip().rstrip(". ")
    return name or "unknown"