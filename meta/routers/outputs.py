"""
MAGI Meta Layer — Outputs Router.

File listing, download, preview, and delete for configured output directory.
"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from magi.meta.services import settings_store

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = "magi_outputs"


def _is_subpath(candidate: Path, base: Path) -> bool:
    """Return True when candidate is inside base (or equals base)."""
    try:
        candidate.relative_to(base)
        return True
    except ValueError:
        return False


async def _get_output_dir() -> Path:
    """Resolve and normalize configured output directory under project root."""
    configured = str(await settings_store.get("general.output_dir", DEFAULT_OUTPUT_DIR) or DEFAULT_OUTPUT_DIR).strip()
    configured_path = Path(configured)

    if configured_path.is_absolute():
        resolved = configured_path.resolve()
        # Absolute paths are only allowed when they stay under project root policy.
        if _is_subpath(resolved, PROJECT_ROOT):
            return resolved
        return (PROJECT_ROOT / DEFAULT_OUTPUT_DIR).resolve()

    return (PROJECT_ROOT / configured_path).resolve()


class FileEntry(BaseModel):
    name: str
    path: str
    size_bytes: int
    modified_at: float
    type: str   # "json" | "csv" | "png" | "txt" | "other"


class OutputListMetadata(BaseModel):
    output_dir: str
    subdir: Optional[str] = None


class OutputListResponse(BaseModel):
    files: List[FileEntry]
    metadata: OutputListMetadata


@router.get("/", response_model=OutputListResponse)
async def list_output_files(subdir: Optional[str] = None):
    """List files in the outputs directory."""
    base = await _get_output_dir()
    target = (base / subdir).resolve() if subdir else base.resolve()
    if not _is_subpath(target, base.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target.exists():
        return OutputListResponse(files=[], metadata=OutputListMetadata(output_dir=str(base), subdir=subdir))

    entries = []
    for p in sorted(target.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            suffix = p.suffix.lstrip(".").lower() or "other"
            if suffix not in ("json", "csv", "png", "jpg", "txt", "md"):
                suffix = "other"
            entries.append(FileEntry(
                name=p.name,
                path=str(p.relative_to(base)),
                size_bytes=p.stat().st_size,
                modified_at=p.stat().st_mtime,
                type=suffix,
            ))
    return OutputListResponse(files=entries, metadata=OutputListMetadata(output_dir=str(base), subdir=subdir))


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download a specific output file."""
    base = await _get_output_dir()
    full_path = (base / file_path).resolve()
    # Security: ensure file is within outputs dir
    if not _is_subpath(full_path, base.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path), filename=full_path.name)


@router.delete("/{file_path:path}")
async def delete_file(file_path: str):
    """Delete a specific output file."""
    base = await _get_output_dir()
    full_path = (base / file_path).resolve()
    if not _is_subpath(full_path, base.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    full_path.unlink()
    return {"status": "success", "message": f"Deleted {file_path}"}


@router.get("/preview/{file_path:path}")
async def preview_file(file_path: str, max_chars: int = 5000):
    """Return text content of a file for in-browser preview."""
    base = await _get_output_dir()
    full_path = (base / file_path).resolve()
    if not _is_subpath(full_path, base.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        return {"name": full_path.name, "content": content, "truncated": len(content) >= max_chars}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot preview file: {e}")
