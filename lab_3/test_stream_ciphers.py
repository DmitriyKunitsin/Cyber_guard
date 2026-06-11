import io
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


import stream_ciphers as sc


@contextmanager
def capture_stdio():
    """Перехватывает stdout и stderr, возвращает кортеж (out, err)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@contextmanager
def set_argv(*args):
    """Временно подменяет sys.argv."""
    old = sys.argv
    sys.argv = [sys.argv[0]] + list(args)
    try:
        yield
    finally:
        sys.argv = old


def run_cli(*args):
    """Запускает main() с заданными аргументами и возвращает (exit_code, stdout, stderr)."""
    with capture_stdio() as (out, err), set_argv(*args):
        try:
            sc.main()
        except SystemExit as e:
            return e.code, out.getvalue(), err.getvalue()
    return 0, out.getvalue(), err.getvalue()


class TestLCG(unittest.TestCase):
    def test_lcg_deterministic(self):
        a = sc.LCG(12345)
        b = sc.LCG(12345)
        for _ in range(100):
            self.assertEqual(a.next_byte(), b.next_byte())

    def test_key_file_lcg_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "k.bin"
            sc.generate_key_file(p, 500, method="lcg", seed=1)
            self.assertEqual(p.stat().st_size, 500)


class TestVernam(unittest.TestCase):
    def test_roundtrip(self):
        plain = b"secret message"
        key = b"k" * len(plain)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pf, kf, cf, rf = t / "p.bin", t / "k.bin", t / "c.bin", t / "r.bin"
            pf.write_bytes(plain)
            kf.write_bytes(key)
            sc.vernam_encrypt(pf, kf, cf)
            sc.vernam_decrypt(cf, kf, rf)
            self.assertEqual(rf.read_bytes(), plain)

    def test_xor_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pf = t / "p.bin"
            kf = t / "k.bin"
            of = t / "o.bin"
            pf.write_bytes(bytes([0x00, 0xFF, 0x55]))
            kf.write_bytes(bytes([0xAA, 0x55, 0xFF]))
            sc.vernam_xor(pf, kf, of)
            self.assertEqual(of.read_bytes(), bytes([0xAA, 0xAA, 0xAA]))

    def test_key_too_short(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pf, kf, of = t / "p.bin", t / "k.bin", t / "o.bin"
            pf.write_bytes(b"abcd")
            kf.write_bytes(b"ab")
            with self.assertRaises(ValueError):
                sc.vernam_xor(pf, kf, of)


class TestChaCha20(unittest.TestCase):
    def test_key_derivation_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "key.bin"
            key_file.write_bytes(b"any-length-password")
            k = sc.chacha_key_from_file(key_file)
            self.assertEqual(len(k), 32)

    def test_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            inp, outp, back, kf = t / "i.bin", t / "o.bin", t / "b.bin", t / "key.bin"
            inp.write_bytes(b"file stream data")
            kf.write_bytes(b"material from key file")
            sc.chacha_encrypt_file(inp, kf, outp)
            sc.chacha_decrypt_file(outp, kf, back)
            self.assertEqual(back.read_bytes(), b"file stream data")
            self.assertGreaterEqual(outp.stat().st_size, 16 + len(b"file stream data"))

    def test_decrypt_short_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            bad = t / "bad.bin"
            out = t / "o.bin"
            kf = t / "key.bin"
            bad.write_bytes(b"short")
            kf.write_bytes(b"x")
            with self.assertRaises(ValueError):
                sc.chacha_decrypt_file(bad, kf, out)

class TestCLI(unittest.TestCase):
    def test_gen_key_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "k.bin"
            exit_code, stdout, stderr = run_cli("gen-key", str(out_file), "-n", "32", "--method", "secrets")
            self.assertEqual(exit_code, 0)
            self.assertEqual(out_file.stat().st_size, 32)

    def test_gen_key_lcg_requires_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "k.bin"
            exit_code, stdout, stderr = run_cli("gen-key", str(out_file), "-n", "10", "--method", "lcg")
            self.assertNotEqual(exit_code, 0)

    def test_prepare_samples_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            samples_dir = Path(tmp) / "samples"
            exit_code, stdout, stderr = run_cli("prepare-samples", "--dir", str(samples_dir), "--method", "secrets")
            self.assertEqual(exit_code, 0)
            plain = samples_dir / "plain.txt"
            key = samples_dir / "key.bin"
            self.assertTrue(plain.is_file())
            self.assertTrue(key.is_file())
            self.assertEqual(plain.stat().st_size, key.stat().st_size)

    def test_vernam_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pf, kf, cf, rf = t / "p.txt", t / "k.bin", t / "c.bin", t / "r.txt"
            pf.write_bytes(b"hi")
            kf.write_bytes(b"\x01\x02")
            exit_code, _, _ = run_cli("vernam-encrypt", str(pf), str(kf), str(cf))
            self.assertEqual(exit_code, 0)
            exit_code, _, _ = run_cli("vernam-decrypt", str(cf), str(kf), str(rf))
            self.assertEqual(exit_code, 0)
            self.assertEqual(rf.read_bytes(), b"hi")

    def test_chacha_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            pf, kf, cf, rf = t / "p.bin", t / "k.bin", t / "c.bin", t / "r.bin"
            pf.write_bytes(b"secret data")
            kf.write_bytes(b"my-key-material")
            exit_code, _, _ = run_cli("chacha-encrypt", str(pf), str(kf), str(cf))
            self.assertEqual(exit_code, 0)
            exit_code, _, _ = run_cli("chacha-decrypt", str(cf), str(kf), str(rf))
            self.assertEqual(exit_code, 0)
            self.assertEqual(rf.read_bytes(), b"secret data")


if __name__ == "__main__":
    unittest.main()