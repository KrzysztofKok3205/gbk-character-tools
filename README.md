# gbk-character-tools

Strict GBK encoding and decoding for Python, with byte offsets and character
indices attached to errors.

## Usage

```python
from gbk_character_tools import decode, encode, GBKDecodeError

raw = encode("\u4e2d\u6587")          # b'\xd6\xd0\xce\xc4'
text = decode(raw)                    # '\u4e2d\u6587'

try:
    decode(b"\xff\xff")
except GBKDecodeError as exc:
    print(exc.offset, exc.reason)
```

The exported names are:

- `decode(data, errors="strict")`
- `encode(text, errors="strict")`
- `decode_bytes(data)`
- `encode_text(text)`
- `is_gbk_encodable(text)`
- `iter_decode(data, chunk_size=4096)`
- `GBK_CODEC`
- `GBKError`, `GBKDecodeError`, `GBKEncodeError`

## Why this exists

Python's standard library already ships a GBK codec, and this library does not
replace it. The problem it solves is error reporting: `bytes.decode("gbk")`
raises `UnicodeDecodeError`, whose `start` attribute is easy to miss when the
exception is logged or re-raised across a boundary. This library re-raises a
single `GBKError` subclass that always carries the offending byte offset (for
decoding) or character index (for encoding), so callers can report *where* the
input went wrong without inspecting the original exception.

The trade-off is deliberate: no hand-written GBK table. The standard library's
codec is the authoritative mapping, and duplicating it would be a large,
error-prone surface with no benefit.

## The awkward edge

GBK is variable-width: ASCII is one byte, Chinese characters are two. Any
chunked decoder has to avoid splitting a two-byte sequence across a chunk
boundary. `iter_decode` handles this by holding back a trailing incomplete
sequence until the next chunk arrives; a `chunk_size` of 1 is a valid (if
slow) way to exercise that path. The generator raises `GBKDecodeError` if the
final pending bytes are themselves invalid, so a truncated stream is not
silently swallowed.
