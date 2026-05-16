"""
MAGI Meta Layer — Outputs Router.

File listing, download, preview, and delete for magi_outputs directory.
"""

import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from magi.meta.services import settings_store

router = APIRouter()


def _get_output_dir() -> Path:
    """Get the configured output directory, defaulting to magi_outputs."""
    # Best-effort sync access — settings are cached in memory
    base = Path(__file__).parent.parent.parent.parent
    return base / "magi_outputs"


class FileEntry(BaseModel):
    name: str
    path: str
    size_bytes: int
    modified_at: float
    type: str   # "json" | "csv" | "png" | "txt" | "other"


class OutputListResponse(BaseModel):
    files: List[FileEntry]
    meta: dict


@router.get("/", response_model=OutputListResponse)
async def list_output_files(subdir: Optional[str] = None):
    """List files in the outputs directory."""
    base = _get_output_dir()
    target = base / subdir if subdir else base
    if not target.exists():
        return {
            "files": [],
            "meta": {
                "outputs_root": str(base.resolve()),
                "target": str(target.resolve()),
                "subdir": subdir,
                "exists": False,
                "count": 0,
            },
        }

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
    return {
        "files": entries,
        "meta": {
            "outputs_root": str(base.resolve()),
            "target": str(target.resolve()),
            "subdir": subdir,
            "exists": True,
            "count": len(entries),
        },
    }


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download a specific output file."""
    base = _get_output_dir()
    full_path = (base / file_path).resolve()
    # Security: ensure file is within outputs dir
    if not str(full_path).startswith(str(base.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path), filename=full_path.name)


@router.delete("/{file_path:path}")
async def delete_file(file_path: str):
    """Delete a specific output file."""
    base = _get_output_dir()
    full_path = (base / file_path).resolve()
    if not str(full_path).startswith(str(base.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    full_path.unlink()
    return {"status": "success", "message": f"Deleted {file_path}"}


@router.get("/preview/{file_path:path}")
async def preview_file(file_path: str, max_chars: int = 5000):
    """Return text content of a file for in-browser preview."""
    base = _get_output_dir()
    full_path = (base / file_path).resolve()
    if not str(full_path).startswith(str(base.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        return {"name": full_path.name, "content": content, "truncated": len(content) >= max_chars}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot preview file: {e}")
