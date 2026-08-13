"""Splits a long text into overlapping chunks before extraction.

Chunking is an optional pipeline step: extractors are LLM-backed and degrade on
very long inputs, so the text is cut into pieces that each fit a token budget.
Sizes are expressed in tokens, counted with tiktoken when it is installed and
estimated from the text length otherwise, so the service never hard-fails on a
missing optional dependency.

The splitter is separator-driven: it cuts on paragraphs first, then lines, then
sentences, then words, and only ever falls back to a raw token cut for a single
unbreakable run of characters. Pieces are then packed greedily up to the chunk
size, and each chunk repeats the tail of the previous one so a fact split across
a boundary is still visible whole to the extractor.

Everything is carried as (start, end) spans into the *original* text rather than
as detached strings, so every chunk knows where it came from. Those offsets are
what lets a triple be traced back to the exact passage it was extracted from,
and — combined with the page offsets a parser reports — to a page number.
"""

import bisect
import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50
# Guard against a tiny chunk size turning one document into hundreds of LLM calls.
MAX_CHUNKS = 100

# Tried in order; each one loses only whitespace, so no content is dropped.
# Sentence splitting keeps its punctuation thanks to the lookbehind.
SEPARATOR_PATTERNS = (
    r"\n\s*\n",
    r"\n",
    r"(?<=[.!?…])\s+",
    r"\s+",
)

# Half-open (start, end) offsets into the text being chunked.
Span = tuple[int, int]

_encoder = None
_encoder_loaded = False


def _get_encoder():
    """Lazily loads the tiktoken encoder, or returns None when it is unavailable."""
    global _encoder, _encoder_loaded

    if _encoder_loaded:
        return _encoder

    _encoder_loaded = True

    try:
        import tiktoken

        _encoder = tiktoken.get_encoding("cl100k_base")
    except Exception:
        logger.info(
            "tiktoken unavailable, falling back to a length-based token estimate"
        )
        _encoder = None

    return _encoder


def count_tokens(text: str) -> int:
    """Counts the tokens in a text, estimating them when no tokenizer is available."""
    if not text:
        return 0

    encoder = _get_encoder()

    if encoder is not None:
        return len(encoder.encode(text))

    # Roughly four characters per token on latin scripts, never below the word
    # count so short words are not undercounted.
    return max(len(text) // 4, len(text.split()))


def _trim(text: str, start: int, end: int) -> Span:
    """Narrows a span to drop the whitespace at both ends, the way str.strip does."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1

    return start, end


def _hard_split(text: str, start: int, end: int, chunk_size: int) -> list[Span]:
    """Last-resort cut of an unbreakable run of characters, on token boundaries."""
    encoder = _get_encoder()

    if encoder is None:
        step = max(chunk_size * 4, 1)
        return [
            (offset, min(offset + step, end))
            for offset in range(start, end, step)
        ]

    tokens = encoder.encode(text[start:end])
    spans: list[Span] = []
    cursor = start

    for index in range(0, len(tokens), chunk_size):
        piece = encoder.decode(tokens[index:index + chunk_size])
        # decode(encode(x)) round-trips, but clamp anyway so a lossy edge case
        # can never hand back an offset past the span we were given.
        next_cursor = min(cursor + len(piece), end)
        if next_cursor > cursor:
            spans.append((cursor, next_cursor))
        cursor = next_cursor

    return spans


def _split_units(
    text: str,
    start: int,
    end: int,
    chunk_size: int,
    separators: tuple[str, ...] = SEPARATOR_PATTERNS,
) -> list[Span]:
    """Breaks a span down into pieces that each fit within chunk_size tokens."""
    start, end = _trim(text, start, end)

    if start >= end:
        return []

    if count_tokens(text[start:end]) <= chunk_size:
        return [(start, end)]

    if not separators:
        return _hard_split(text, start, end, chunk_size)

    separator, *remaining = separators
    remaining = tuple(remaining)
    # Matching against the substring keeps this identical to a re.split on the
    # piece itself — it matters for the sentence pattern, whose lookbehind must
    # not see the characters preceding the span.
    fragment = text[start:end]
    units: list[Span] = []
    cursor = 0

    for match in re.finditer(separator, fragment):
        units.extend(
            _split_units(text, start + cursor, start + match.start(), chunk_size, remaining)
        )
        cursor = match.end()

    units.extend(_split_units(text, start + cursor, end, chunk_size, remaining))

    return units


def _carry_overlap(text: str, units: list[Span], overlap: int) -> tuple[list[Span], int]:
    """Returns the trailing units to repeat at the start of the next chunk."""
    if overlap <= 0:
        return [], 0

    carried: list[Span] = []
    total = 0

    for span in reversed(units):
        unit_tokens = count_tokens(text[span[0]:span[1]])

        if total + unit_tokens > overlap:
            break

        carried.insert(0, span)
        total += unit_tokens

    return carried, total


def _pack(
    text: str, units: list[Span], chunk_size: int, overlap: int
) -> list[list[Span]]:
    """Fills chunks up to chunk_size, repeating the tail of the previous one."""
    chunks: list[list[Span]] = []
    current: list[Span] = []
    current_tokens = 0

    for span in units:
        unit_tokens = count_tokens(text[span[0]:span[1]])

        if current and current_tokens + unit_tokens > chunk_size:
            chunks.append(current)
            current, current_tokens = _carry_overlap(text, current, overlap)

        current.append(span)
        current_tokens += unit_tokens

    if current:
        chunks.append(current)

    return chunks


def _build_chunk(text: str, spans: list[Span], index: int) -> dict:
    """
    Turns the units packed into one chunk into its public shape: the text handed
    to the extractor, plus where that text sits in the document.

    The units are re-joined with a newline, so the chunk text is not always the
    verbatim slice text[start:end] — only the whitespace between units differs.
    start and end stay the true document offsets, which is what provenance needs.
    """
    return {
        "chunk_id": f"c{index + 1}",
        "text": "\n".join(text[span[0]:span[1]] for span in spans),
        "start": spans[0][0],
        "end": spans[-1][1],
    }


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Splits a text into overlapping chunks of at most chunk_size tokens.

    Each chunk is a dict with a ``chunk_id``, its ``text``, and the ``start`` /
    ``end`` offsets of that text in the document it came from. Returns a
    single-item list when the text already fits, so callers can treat the chunked
    and unchunked paths the same way.
    """
    text = text or ""
    start, end = _trim(text, 0, len(text))

    if start >= end:
        return []

    chunk_size = max(int(chunk_size), 1)
    # An overlap as large as the chunk would repeat everything and never advance.
    chunk_overlap = min(max(int(chunk_overlap), 0), chunk_size - 1)

    if count_tokens(text[start:end]) <= chunk_size:
        return [_build_chunk(text, [(start, end)], 0)]

    packed = _pack(text, _split_units(text, start, end, chunk_size), chunk_size, chunk_overlap)

    if len(packed) > MAX_CHUNKS:
        raise ValueError(
            f"Chunk size is too small for this document: it would produce "
            f"{len(packed)} chunks (maximum {MAX_CHUNKS}). Increase 'chunk_size'."
        )

    return [_build_chunk(text, spans, index) for index, spans in enumerate(packed)]


def whole_text_chunk(text: str) -> dict | None:
    """
    Returns the single chunk standing for an unchunked text, so a triple extracted
    without the chunking step still carries a span pointing at its document.
    """
    text = text or ""
    start, end = _trim(text, 0, len(text))

    if start >= end:
        return None

    return {"chunk_id": "c1", "text": text[start:end], "start": start, "end": end}


def resolve_page(start: int, page_offsets: list[int] | None) -> int | None:
    """
    Maps an offset onto a 1-based page number, given the offsets at which each
    page starts. Returns None when the parser reported no pagination (plain text,
    Office documents), since a page number would then be made up.
    """
    if not page_offsets:
        return None

    return max(1, bisect.bisect_right(page_offsets, start))
