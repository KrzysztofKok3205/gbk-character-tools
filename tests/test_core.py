import unittest

from gbk_character_tools import (
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


class TestRoundTrip(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(decode(b"hello"), "hello")
        self.assertEqual(encode("hello"), b"hello")

    def test_chinese(self):
        text = "\u4e2d\u6587"  # 中文
        raw = encode(text)
        self.assertEqual(raw, b"\xd6\xd0\xce\xc4")
        self.assertEqual(decode(raw), text)

    def test_mixed(self):
        text = "abc\u4e2d\u6587def"
        self.assertEqual(decode(encode(text)), text)

    def test_empty(self):
        self.assertEqual(decode(b""), "")
        self.assertEqual(encode(""), b"")

    def test_full_width_punctuation(self):
        text = "\uff0c\u3002\uff01"  # ，。！
        self.assertEqual(decode(encode(text)), text)


class TestErrors(unittest.TestCase):
    def test_decode_invalid_raises(self):
        with self.assertRaises(GBKDecodeError) as ctx:
            decode_bytes(b"\xff\xff")
        self.assertEqual(ctx.exception.offset, 0)
        self.assertEqual(ctx.exception.data, b"\xff\xff")

    def test_decode_truncated_raises(self):
        # A lone lead byte with no trail byte.
        with self.assertRaises(GBKDecodeError) as ctx:
            decode_bytes(b"\xd6")
        self.assertEqual(ctx.exception.offset, 0)

    def test_encode_unrepresentable_raises(self):
        with self.assertRaises(GBKEncodeError) as ctx:
            encode_text("\U0001f600")  # emoji, not in GBK
        self.assertEqual(ctx.exception.index, 0)
        self.assertEqual(ctx.exception.text, "\U0001f600")

    def test_error_is_value_error(self):
        self.assertTrue(issubclass(GBKDecodeError, ValueError))
        self.assertTrue(issubclass(GBKEncodeError, ValueError))
        self.assertTrue(issubclass(GBKError, ValueError))

    def test_error_attributes_present(self):
        err = GBKDecodeError(b"\xff", 0, "bad")
        self.assertEqual(err.data, b"\xff")
        self.assertEqual(err.offset, 0)
        self.assertEqual(err.reason, "bad")


class TestErrorModes(unittest.TestCase):
    def test_decode_replace(self):
        result = decode(b"\xff\xff", errors="replace")
        self.assertEqual(result, "\ufffd\ufffd")

    def test_decode_ignore(self):
        result = decode(b"\xff\xff", errors="ignore")
        self.assertEqual(result, "")

    def test_encode_replace(self):
        result = encode("\U0001f600", errors="replace")
        self.assertEqual(result, b"?")

    def test_encode_ignore(self):
        result = encode("\U0001f600", errors="ignore")
        self.assertEqual(result, b"")


class TestIsEncodable(unittest.TestCase):
    def test_true_for_chinese(self):
        self.assertTrue(is_gbk_encodable("\u4e2d\u6587"))

    def test_true_for_empty(self):
        self.assertTrue(is_gbk_encodable(""))

    def test_false_for_emoji(self):
        self.assertFalse(is_gbk_encodable("\U0001f600"))


class TestIterDecode(unittest.TestCase):
    def test_small_chunks_do_not_split_pairs(self):
        text = "\u4e2d\u6587\u6d4b\u8bd5"  # 中文测试
        raw = encode(text)
        # chunk_size=1 forces the generator to handle split pairs.
        chunks = list(iter_decode(raw, chunk_size=1))
        self.assertEqual("".join(chunks), text)

    def test_default_chunk_size(self):
        text = "\u4e2d\u6587" * 100
        raw = encode(text)
        self.assertEqual("".join(iter_decode(raw)), text)

    def test_empty_input(self):
        self.assertEqual(list(iter_decode(b"")), [])

    def test_invalid_chunk_size(self):
        with self.assertRaises(ValueError):
            list(iter_decode(b"abc", chunk_size=0))

    def test_invalid_input_raises(self):
        with self.assertRaises(GBKDecodeError):
            list(iter_decode(b"\xff\xff"))

    def test_ascii_only(self):
        self.assertEqual("".join(iter_decode(b"hello", chunk_size=2)), "hello")


class TestCodecName(unittest.TestCase):
    def test_codec_name(self):
        self.assertEqual(GBK_CODEC, "gbk")


if __name__ == "__main__":
    unittest.main()
