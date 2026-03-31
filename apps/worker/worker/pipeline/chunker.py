"""Split text into overlapping chunks."""

import re
from dataclasses import dataclass

CHUNK_SIZE = 1000  # chars (MVP uses chars, upgrade to tokens later)
CHUNK_OVERLAP = 200  # chars


@dataclass
class ChunkResult:
    chunk_index: int
    content: str


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[ChunkResult]:
    """Split text into overlapping chunks.

    1. Normalize whitespace
    2. Split into chunks of `chunk_size` chars with `overlap` overlap
    3. Return list of ChunkResult
    """
    # Normalize
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    chunks: list[ChunkResult] = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + chunk_size
        chunk_content = text[start:end].strip()

        if chunk_content:
            chunks.append(ChunkResult(chunk_index=idx, content=chunk_content))
            idx += 1

        # Move start forward by (chunk_size - overlap)
        start += chunk_size - overlap

        # Avoid infinite loop on very small texts
        if start <= (end - chunk_size):
            break

    return chunks
