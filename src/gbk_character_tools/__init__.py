"""GBK character encoding and decoding helpers.

This package exposes a small, dependency-free API for working with the GBK
character encoding, which is a superset of GB2312 and the de-facto standard
for Simplified Chinese on legacy Windows systems.
"""

from .core import (
    GBKError,
    GBKDecodeError,
    GBKEncodeError,
    decode,
    encode,
    decode_bytes,
    encode_text,
    is_gbk_encodable,
    iter_decode,
    GBK_CODEC,
)

__all__ = [
    "GBKError",
    "GBKDecodeError",
    "GBKEncodeError",
    "decode",
    "encode",
    "decode_bytes",
    "encode_text",
    "is_gbk_encodable",
    "iter_decode",
    "GBK_CODEC",
]
