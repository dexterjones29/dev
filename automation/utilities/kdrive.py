"""
K: Drive Utilities Package
--------------------------
- get_folder()
- get_files()
- get_latest_file()
- read_file()
"""

from collections.abc import Iterable
from pathlib import Path

def get_folder(folder_path: str | Path) -> Path:
    """Return a validated K: drive folder."""
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f'K: drive folder not found: {folder}')

    if not folder.is_dir():
        raise NotADirectoryError(f'K: drive path is not a folder: {folder}')

    return folder

def get_files(folder_path: str | Path, patterns: str | Iterable[str] = '*', recursive: bool = False) -> list[Path]:
    """Return matching files from a K: drive folder."""
    folder = get_folder(folder_path)

    if isinstance(patterns, str):
        patterns = [patterns]

    files = []

    for pattern in patterns:
        matches = folder.rglob(pattern) if recursive else folder.glob(pattern)
        files.extend(file for file in matches if file.is_file())

    return sorted(set(files), key=lambda file: file.name.lower())

def get_latest_file(folder_path: str | Path, patterns: str | Iterable[str] = '*', recursive: bool = False) -> Path:
    """Return the most recently modified matching file."""
    files = get_files(folder_path=folder_path, patterns=patterns, recursive=recursive)

    if not files:
        raise FileNotFoundError(f'No matching files found in {Path(folder_path)} for pattern(s): {patterns}')

    return max(files, key=lambda file: file.stat().st_mtime)

def read_file(file_path: str | Path) -> bytes:
    """Read an return a K: drive file as bytes."""
    file = Path(file_path)

    if not file.exists():
        raise FileNotFoundError(f'K: drive file not found: {file}')

    if not file.is_file():
        raise IsADirectoryError(f'K: drive path is not a file: {file}')

    return file.read_bytes()