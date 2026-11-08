"""Core GBK encode/decode primitives.

Why this module exists
----------------------
Python's built-in ``str.encode('gbk')`` and ``bytes.decode('gbk')`` already do
the heavy lifting, but they raise bare ``UnicodeDecodeError`` / ``UnicodeEncodeError``
instances whose messages do not say which byte offset or which character caused
the failure in a form that is convenient to log or to surface to a user.  This
module wraps the standard codec and re-raises a single, library-specific
exception family that always carries the offending byte offset (for decoding)
or the offending character index (for encoding).

The trade-off: we deliberately do *not* implement our own GBK table.  Python's
codec is the authoritative implementation and reimplementing it would be a
large, error-prone surface.  We only add error context.
"""

from __future__ import annotations

from typing import Iterator, Optional

# The name Python uses for the GBK codec.  Exposed so callers can hand it to
# ``codecs`` helpers without hard-coding the string.
GBK_CODEC = "gbk"


class GBKError(ValueError):
    """Base class for every error raised by this library.

    Subclasses ``ValueError`` so that callers who do not care about the
distinction can catch ``ValueError`` and still be correct.
    """


class GBKDecodeError(GBKError):
    """Raised when a byte sequence is not valid GBK.

    Attributes
    ----------
    data:
        The full byte string that was being decoded.
    offset:
        Zero-based index into ``data`` where decoding stopped.
    reason:
        Human-readable explanation from the underlying codec.
    """

    def __init__(self, data: bytes, offset: int, reason: str) -> None:
        self.data = data
        self.offset = offset
        self.reason = reason
        super().__init__(
            f"invalid GBK byte at offset {offset}: {reason}"
        )


class GBKEncodeError(GBKError):
    """Raised when a string contains characters GBK cannot represent.

    Attributes
    ----------
    text:
        The full string that was being encoded.
    index:
        Zero-based character index into ``text`` where encoding stopped.
    reason:
        Human-readable explanation from the underlying codec.
    """

    def __init__(self, text: str, index: int, reason: str) -> None:
        self.text = text
        self.index = index
        self.reason = reason
        super().__init__(
            f"character at index {index} cannot be encoded as GBK: {reason}"
        )


def decode_bytes(data: bytes) -> str:
    """Decode ``data`` as GBK, raising :class:`GBKDecodeError` on failure.

    This is the strict counterpart to :func:`decode`.  It never replaces or
    ignores bytes; every byte must belong to a valid GBK sequence.
    """
    try:
        return data.decode(GBK_CODEC)
    except UnicodeDecodeError as exc:  # pragma: no cover - exercised by tests
        raise GBKDecodeError(data, exc.start, exc.reason) from exc


def encode_text(text: str) -> bytes:
    """Encode ``text`` as GBK, raising :class:`GBKEncodeError` on failure.

    This is the strict counterpart to :func:`encode`.  It never substitutes
    ``?`` or drops characters; every character must be representable.
    """
    try:
        return text.encode(GBK_CODEC)
    except UnicodeEncodeError as exc:  # pragma: no cover - exercised by tests
        raise GBKEncodeError(text, exc.start, exc.reason) from exc


def decode(data: bytes, errors: str = "strict") -> str:
    """Decode ``data`` as GBK.

    Parameters
    ----------
    data:
        Bytes to decode.
    errors:
        Error handling mode passed through to the standard codec.  The
        default ``"strict"`` raises :class:`GBKDecodeError`; other values
        (``"replace"``, ``"ignore"``) are forwarded verbatim.

    Returns
    -------
    str
        The decoded text.
    """
    if errors == "strict":
        return decode_bytes(data)
    try:
        return data.decode(GBK_CODEC, errors=errors)
    except UnicodeDecodeError as exc:  # pragma: no cover - defensive
        raise GBKDecodeError(data, exc.start, exc.reason) from exc


def encode(text: str, errors: str = "strict") -> bytes:
    """Encode ``text`` as GBK.

    Parameters
    ----------
    text:
        Text to encode.
    errors:
        Error handling mode passed through to the standard codec.  The
        default ``"strict"`` raises :class:`GBKEncodeError`; other values
        (``"replace"``, ``"ignore"``) are forwarded verbatim.

    Returns
    -------
    bytes
        The encoded bytes.
    """
    if errors == "strict":
        return encode_text(text)
    try:
        return text.encode(GBK_CODEC, errors=errors)
    except UnicodeEncodeError as exc:  # pragma: no cover - defensive
        raise GBKEncodeError(text, exc.start, exc.reason) from exc


def is_gbk_encodable(text: str) -> bool:
    """Return ``True`` if every character in ``text`` has a GBK encoding.

    Empty strings are encodable by definition.  This is a convenience over
    ``try: encode_text(text) except GBKEncodeError: return False`` and is
    provided because callers frequently want to filter user input without
    paying the cost of constructing an exception on the common path.
    """
    try:
        text.encode(GBK_CODEC)
    except UnicodeEncodeError:
        return False
    return True


def iter_decode(data: bytes, chunk_size: int = 4096) -> Iterator[str]:
    """Yield decoded chunks of ``data``.

    GBK is a variable-width encoding (one or two bytes per character), so a
    naive split on ``chunk_size`` can cut a two-byte sequence in half.  This
    generator keeps a trailing partial sequence for the next iteration.

    Parameters
    ----------
    data:
        Bytes to decode.
    chunk_size:
        Maximum number of bytes to consume per iteration.  Must be positive.

    Yields
    ------
    str
        Successive decoded fragments; concatenating them yields the full text.

    Raises
    ------
    ValueError
        If ``chunk_size`` is not positive.
    GBKDecodeError
        If ``data`` is not valid GBK.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    pending = b""
    position = 0
    length = len(data)

    while position < length:
        end = min(position + chunk_size, length)
        pending += data[position:end]
        position = end

        # Decode as much as possible.  If the final bytes form a truncated
        # two-byte sequence, hold them back for the next chunk.
        try:
            decoded = pending.decode(GBK_CODEC)
            pending = b""
        except UnicodeDecodeError as exc:
            # A truncated trailing sequence is recoverable: the codec reports
            # the error at the start of the incomplete sequence, and there are
            # still bytes left to read.  Anything else is a real error.
            if exc.start >= len(pending) - 1 and position < length:
                decoded = pending[: exc.start].decode(GBK_CODEC)
                pending = pending[exc.start :]
            else:
                raise GBKDecodeError(pending, exc.start, exc.reason) from exc

        if decoded:
            yield decoded

    if pending:
        # No more input, so any remaining bytes must decode on their own.
        try:
            yield pending.decode(GBK_CODEC)
        except UnicodeDecodeError as exc:
            raise GBKDecodeError(pending, exc.start, exc.reason) from exc
