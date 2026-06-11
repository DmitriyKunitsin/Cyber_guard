import io
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import block_cipher as bc


@contextmanager
def capture_stdout():
    old = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


@contextmanager
def set_argv(*args):
    old = sys.argv
    sys.argv = [sys.argv[0]] + list(args)
    try:
        yield
    finally:
        sys.argv = old


def run_cli(*args):
    """Запускает main() с заданными аргументами и возвращает (exit_code, stdout)."""
    with capture_stdout() as out, set_argv(*args):
        try:
            bc.main()
        except SystemExit as e:
            return e.code, out.getvalue()
    return 0, out.getvalue()


class TestXTEA(unittest.TestCase):
    def test_encrypt_decrypt_block_roundtrip(self):
        key = bytes(range(16))
        for rounds in (1, 8, 32, 64):
            cipher = bc.XTEA(key, rounds=rounds)
            for plain in (b"\x00" * 8, b"abcdefgh", bytes(range(8))):
                self.assertEqual(cipher.decrypt_block(cipher.encrypt_block(plain)), plain)

    def test_wrong_key_length(self):
        with self.assertRaises(ValueError):
            bc.XTEA(b"short")

    def test_wrong_block_length(self):
        cipher = bc.XTEA(bytes(16))
        with self.assertRaises(ValueError):
            cipher.encrypt_block(b"1234567")
        with self.assertRaises(ValueError):
            cipher.decrypt_block(b"1234567")


class TestCBC(unittest.TestCase):
    def setUp(self):
        self.key = bytes(i * 17 % 256 for i in range(16))
        self.cbc = bc.CBC(bc.XTEA(self.key))

    def test_roundtrip_bytes(self):
        for plain in (b"", b"a", b"hello world", b"x" * 1000):
            iv = bytes(8)
            blob = self.cbc.encrypt(plain, iv=iv)
            self.assertEqual(self.cbc.decrypt(blob), plain)

    def test_random_iv_changes_blob(self):
        p = b"same"
        b1 = self.cbc.encrypt(p)
        b2 = self.cbc.encrypt(p)
        self.assertNotEqual(b1, b2)
        self.assertEqual(self.cbc.decrypt(b1), p)
        self.assertEqual(self.cbc.decrypt(b2), p)

    def test_decrypt_short_file(self):
        with self.assertRaises(ValueError):
            self.cbc.decrypt(b"1234567")

    def test_pkcs7_unpad_invalid(self):
        with self.assertRaises(ValueError):
            self.cbc.decrypt(bytes(16) + b"\x00" * 8)


class TestLoadKey(unittest.TestCase):
    def test_key_hex(self):
        h = "0" * 32
        k = bc.load_key(None, h)
        self.assertEqual(k, bytes(16))

    def test_key_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "k.bin"
            p.write_bytes(bytes(range(16)))
            k = bc.load_key(p, None)
            self.assertEqual(k, bytes(range(16)))


class TestCLI(unittest.TestCase):
    def test_encrypt_decrypt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plain_file = base / "plain.txt"
            key_file = base / "key.bin"
            cipher_file = base / "out.bin"
            recovered_file = base / "back.txt"

            plain_file.write_text("secret data", encoding="utf-8")
            key_file.write_bytes(bytes(range(16)))

            exit_code, out = run_cli("encrypt", str(plain_file), str(cipher_file), "--key-file", str(key_file))
            self.assertEqual(exit_code, 0)
            self.assertTrue(cipher_file.is_file())

            exit_code, out = run_cli("decrypt", str(cipher_file), str(recovered_file), "--key-file", str(key_file))
            self.assertEqual(exit_code, 0)
            self.assertEqual(recovered_file.read_text(encoding="utf-8"), "secret data")

    def test_prepare_samples_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            samples_dir = Path(tmp) / "samples"
            exit_code, out = run_cli("prepare-samples", "--dir", str(samples_dir))
            self.assertEqual(exit_code, 0)
            plain_file = samples_dir / "plain.txt"
            key_file = samples_dir / "key.bin"
            self.assertTrue(plain_file.is_file())
            self.assertTrue(key_file.is_file())
            self.assertEqual(key_file.stat().st_size, 16)


if __name__ == "__main__":
    unittest.main()