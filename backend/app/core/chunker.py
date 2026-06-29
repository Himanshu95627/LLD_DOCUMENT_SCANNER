"""
Recursive character-based text splitter.

Strategy:
  1. Try to split on paragraph breaks (\n\n) first — preserves semantic units
  2. Fall back to sentence breaks (\n, ". ")
  3. Last resort: split on spaces

This is better than fixed-size splitting because it avoids cutting
mid-sentence, which degrades retrieval quality.
"""

import re
from dataclasses import dataclass
import tiktoken

from app.core.config import settings

@dataclass
class TextChunk:
    content: str
    chunk_index: int
    char_offset: int
    token_count: int

_TOKENIZER = tiktoken.get_encoding("cl100k_base")

_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]


def _count_tokens(text: str) -> int:
    return len(_TOKENIZER.encode(text))

def _split_text(text: str, separators: list[str]) -> list[str]:
    """Recursively split text using the first separator that works."""

    if not separators:
        return text
    
    sep = separators[0]
    remaining = separators[1:]

    if sep == "":
        return list(text)

    
    parts = text.split(sep)

    if len(parts) ==1:
        return _split_text(text,remaining)
    
    return [p + sep for p in parts[:-1]] + [parts[-1]]


def chunk_text(
        text: str,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks of ~chunk_size tokens.

    Returns a list of TextChunk objects with content, position and token count
    """

    text = re.sub(r"\n{3,}","\n\n",text).strip()

    if not text:
        return []
    
    pieces = _split_text(text=text, separators= _SEPARATORS)

    chunks: list[TextChunk] = []
    current_pieces: list[str] = []
    current_tokens = 0
    current_char_offset = 0
    chunk_index = 0

    for piece in pieces:
        piece_tokens = _count_tokens(piece)


        if current_tokens + piece_tokens > chunk_size and current_pieces:
            chunk_text_content = "".join(current_pieces).strip()

            if chunk_text_content:
                chunks.append(
                    TextChunk(
                        content=chunk_text_content,
                        chunk_index=chunk_index,
                        char_offset=current_char_offset,
                        token_count=current_tokens,
                    )
                )

                chunk_index +=1

            overlap_pieces: list[str] =[]
            overlap_tokens= 0

            for p in reversed(current_pieces):
                p_tok = _count_tokens(p)

                if overlap_tokens + p_tok <= chunk_overlap:
                    overlap_pieces.insert(0,p)
                    overlap_tokens += p_tok
                else:
                    break

            consumed = "".join(current_pieces)
            overlap_text = "".join(overlap_pieces)
            current_char_offset += len(consumed)-len(overlap_text)

            current_pieces = overlap_pieces
            current_tokens = overlap_tokens

        current_pieces.append(piece)
        current_tokens += piece_tokens
    
    if current_pieces:
        chunk_text_content = "".join(current_pieces).strip()

        if chunk_text_content:
            chunks.append(
                TextChunk(
                    content=chunk_text_content,
                    chunk_index=chunk_index,
                    char_offset=current_char_offset,
                    token_count=current_tokens,
                )
            )
    
    return chunks