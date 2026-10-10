"""
File I/O utilities for news-agg.
Provides crash-safe atomic JSON writes using temporary files and os.replace.
"""

import os
import json
import tempfile
from typing import Any


def atomic_write_json(file_path: str, data: Any, indent: int = 2) -> None:
    """
    Atomically writes data as JSON to file_path using a temporary file in the same directory.
    Guarantees that an unexpected error, crash, or interruption never leaves a truncated
    or corrupted file.
    """
    target_dir = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(target_dir, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=".tmp_", suffix=".json")
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def atomic_write_text(file_path: str, content: str, encoding: str = "utf-8") -> None:
    """
    Atomically writes text content to file_path using a temporary file in the same directory.
    Guarantees that an unexpected error, crash, or interruption never leaves a truncated
    or corrupted file.
    """
    target_dir = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(target_dir, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=".tmp_", suffix=".tmp")
    try:
        with open(tmp_fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
