import io
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import caesar as caesar  


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


class TestCaesarCipher(unittest.TestCase):
    def setUp(self):
        self.c = caesar.CaesarCipher()

    def test_encrypt_decrypt_roundtrip(self):
        s = "Hello, World! 123 xyz"
        for k in range(26):
            encrypted = self.c.encrypt(s, k)
            self.assertEqual(self.c.decrypt(encrypted, k), s)

    def test_encrypt_known(self):
        self.assertEqual(self.c.encrypt("abc", 1), "bcd")
        self.assertEqual(self.c.encrypt("XYZ", 3), "ABC")
        self.assertEqual(self.c.encrypt("z", 1), "a")

    def test_key_wrap(self):
        self.assertEqual(self.c.encrypt("a", 26), "a")
        self.assertEqual(self.c.encrypt("a", 52), "a")

    def test_non_letters_unchanged(self):
        self.assertEqual(self.c.encrypt(" !?9\n", 5), " !?9\n")

    def test_known_plaintext_key(self):
        self.assertEqual(self.c.known_plaintext_key("abc", "def"), 3)
        self.assertEqual(self.c.known_plaintext_key("Hello", "Khoor"), 3)
        self.assertIsNone(self.c.known_plaintext_key("123", "456"))

    def test_known_plaintext_majority_vote(self):
        # большее количество пар даёт ключ 1
        self.assertEqual(self.c.known_plaintext_key("aaaax", "bbbbx"), 1)

    def test_brute_force_count(self):
        out = self.c.brute_force("a")
        self.assertEqual(len(out), 26)
        self.assertTrue(any(k == 0 and p == "a" for k, p in out))


class TestWordDictionary(unittest.TestCase):
    def test_score(self):
        d = caesar.WordDictionary({"hello", "world"})
        self.assertEqual(d.score("Hello world!"), (2, 2))
        self.assertEqual(d.score("zzz"), (0, 1))

    def test_best_key(self):
        c = caesar.CaesarCipher()
        d = caesar.WordDictionary({"hello", "world"})
        cipher = c.encrypt("Hello world", 7)
        k, plain, ratio = d.best_key(cipher, c)
        self.assertEqual(k, 7)
        self.assertEqual(plain.lower(), "hello world")
        self.assertEqual(ratio, 1.0)

    def test_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "words.txt"
            p.write_text("alpha\nbeta\n", encoding="utf-8")
            d = caesar.WordDictionary.from_file(p)
            self.assertEqual(d.words, {"alpha", "beta"})

    def test_from_file_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.txt"
            p.write_text("", encoding="utf-8")
            d = caesar.WordDictionary.from_file(p)
            # должен использоваться встроенный набор
            self.assertIn("hello", d.words)


class TestCLI(unittest.TestCase):
    def test_encrypt(self):
        with capture_stdout() as out, set_argv("encrypt", "abc", "-k", "1"):
            caesar.main()
        self.assertEqual(out.getvalue().strip(), "bcd")

    def test_decrypt(self):
        with capture_stdout() as out, set_argv("decrypt", "bcd", "-k", "1"):
            caesar.main()
        self.assertEqual(out.getvalue().strip(), "abc")

    def test_kpa(self):
        with capture_stdout() as out, set_argv("kpa", "--plain", "Hello", "--cipher", "Khoor"):
            caesar.main()
        self.assertEqual(out.getvalue().strip(), "3")

    def test_brute_force(self):
        with capture_stdout() as out, set_argv("brute", "a"):
            caesar.main()
        output = out.getvalue()
        # должно быть 26 строк вида "k= 0 a"
        self.assertEqual(len(output.strip().splitlines()), 26)

    def test_dict_attack(self):
        with tempfile.TemporaryDirectory() as tmp:
            words_file = Path(tmp) / "words.txt"
            words_file.write_text("hello\nworld\n", encoding="utf-8")
            c = caesar.CaesarCipher()
            cipher = c.encrypt("hello world", 7)
            # --words должен идти до подкоманды!
            with capture_stdout() as out, set_argv("--words", str(words_file), "dict-attack", cipher):
                caesar.main()
            output = out.getvalue()
            self.assertIn("key=7", output)

    def test_demo(self):
        with capture_stdout() as out, set_argv("demo"):
            caesar.main()
        output = out.getvalue()
        self.assertIn("1. Шифрование", output)
        self.assertIn("2. Атака по известному", output)


if __name__ == "__main__":
    unittest.main()