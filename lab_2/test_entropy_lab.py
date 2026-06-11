import io
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import entropy_lab as ent

@contextmanager
def capture_stdout():
    """Перехватывает stdout, возвращает StringIO."""
    old = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


@contextmanager
def set_argv(*args):
    """Временно подменяет sys.argv."""
    old = sys.argv
    sys.argv = [sys.argv[0]] + list(args)
    try:
        yield
    finally:
        sys.argv = old


class TestFrequencies(unittest.TestCase):
    def test_byte_frequencies(self):
        c = ent.byte_frequencies(b"aba")
        self.assertEqual(c[ord("a")], 2)
        self.assertEqual(c[ord("b")], 1)
        self.assertEqual(sum(c.values()), 3)

    def test_empty(self):
        self.assertEqual(dict(ent.byte_frequencies(b"")), {})


class TestEntropy(unittest.TestCase):
    def test_single_symbol_zero(self):
        c = ent.byte_frequencies(b"ZZZZ")
        self.assertAlmostEqual(ent.entropy_from_frequencies(c), 0.0)

    def test_empty_zero(self):
        self.assertEqual(ent.entropy_from_frequencies(ent.Counter()), 0.0)

    def test_fair_coin_one_bit(self):
        c = ent.byte_frequencies(b"01" * 5000)
        h = ent.entropy_from_frequencies(c)
        self.assertAlmostEqual(h, 1.0)

    def test_uniform_four_symbols(self):
        c = ent.Counter({0: 1, 1: 1, 2: 1, 3: 1})
        self.assertAlmostEqual(ent.entropy_from_frequencies(c), 2.0)

    def test_theoretical_max(self):
        self.assertAlmostEqual(ent.max_entropy(256), 8.0)
        self.assertAlmostEqual(ent.max_entropy(2), 1.0)


class TestFileRoundtrip(unittest.TestCase):
    def test_from_file_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.bin"
            p.write_bytes(b"aabb")
            c = ent.byte_frequencies(p.read_bytes())
            self.assertEqual(c[ord("a")], 2)
            self.assertEqual(c[ord("b")], 2)


class TestCLI(unittest.TestCase):
    def test_freq_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.bin"
            p.write_bytes(b"aaa")
            with capture_stdout() as out, set_argv("freq", str(p), "--top", "5"):
                ent.main()
            self.assertIn("Всего символов", out.getvalue())

    def test_entropy_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.bin"
            p.write_bytes(b"01" * 100)
            with capture_stdout() as out, set_argv("entropy", str(p)):
                ent.main()
            self.assertIn("H =", out.getvalue())

    def test_demo_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Сохраняем текущую рабочую директорию и переходим в tmp
            old_cwd = Path.cwd()
            try:
                import os
                os.chdir(tmp)
                with capture_stdout() as out, set_argv("demo", "-n", "5000", "--seed", "1"):
                    ent.main()
                # Проверяем, что файлы созданы в tmp/samples
                samples = Path(tmp) / "samples"
                self.assertTrue((samples / "const.bin").is_file())
                self.assertTrue((samples / "uniform.bin").is_file())
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()