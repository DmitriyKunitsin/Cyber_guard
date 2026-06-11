import io
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path

import modexp_lab as mex


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
    """Запускает main() с заданными аргументами, возвращает (exit_code, stdout)."""
    with capture_stdout() as out, set_argv(*args):
        try:
            mex.main()
        except SystemExit as e:
            return e.code, out.getvalue()
    return 0, out.getvalue()


class TestHelpers(unittest.TestCase):
    def test_hamming_weight(self):
        self.assertEqual(mex.hamming_weight(0), 0)
        self.assertEqual(mex.hamming_weight(1), 1)
        self.assertEqual(mex.hamming_weight(0b1011), 3)
        self.assertEqual(mex.hamming_weight(701), 7)
        self.assertEqual(mex.hamming_weight((1 << 16) - 1), 16)

    def test_hamming_weight_negative_raises(self):
        with self.assertRaises(ValueError):
            mex.hamming_weight(-1)

    def test_bit_length(self):
        self.assertEqual(mex.bit_length(0), 1)
        self.assertEqual(mex.bit_length(1), 1)
        self.assertEqual(mex.bit_length(2), 2)
        self.assertEqual(mex.bit_length(701), 10)
        self.assertEqual(mex.bit_length((1 << 64) - 1), 64)

    def test_explain_powers_of_two(self):
        self.assertEqual(mex.explain_powers_of_two(0), "0")
        self.assertEqual(mex.explain_powers_of_two(1), "1")
        self.assertEqual(
            mex.explain_powers_of_two(701),
            "512 + 128 + 32 + 16 + 8 + 4 + 1",
        )


class TestNaiveModexp(unittest.TestCase):
    def test_zero_exponent(self):
        self.assertEqual(mex.naive_modexp(7, 0, 13), (1, 0))

    def test_modulus_one(self):
        self.assertEqual(mex.naive_modexp(7, 50, 1), (0, 0))

    def test_known_values(self):
        self.assertEqual(mex.naive_modexp(2, 10, 1000)[0], 24)
        self.assertEqual(mex.naive_modexp(5, 701, 11)[0], pow(5, 701, 11))

    def test_mult_count_equals_exponent(self):
        for x in (0, 1, 2, 5, 17, 100):
            _, mults = mex.naive_modexp(3, x, 17)
            self.assertEqual(mults, x)


class TestFastModexp(unittest.TestCase):
    def test_lecture_example_5_701_11(self):
        res, mults = mex.fast_modexp(5, 701, 11)
        self.assertEqual(res, 5)
        self.assertEqual(res, pow(5, 701, 11))
        self.assertEqual(mults, 15)

    def test_lecture_example_3_800_13(self):
        res, mults = mex.fast_modexp(3, 800, 13)
        self.assertEqual(res, 9)
        self.assertEqual(res, pow(3, 800, 13))
        self.assertEqual(mults, 11)

    def test_zero_exponent(self):
        self.assertEqual(mex.fast_modexp(7, 0, 13), (1, 0))

    def test_modulus_one(self):
        self.assertEqual(mex.fast_modexp(7, 50, 1), (0, 0))

    def test_matches_builtin_random_small(self):
        cases = [
            (2, 1, 7),
            (3, 4, 7),
            (10, 0, 13),
            (12345, 678, 100003),
            (5, (1 << 16) - 1, 1_000_003),
            (7, 2**32 + 1, 1_000_000_007),
        ]
        for a, x, p in cases:
            with self.subTest(a=a, x=x, p=p):
                res, _ = mex.fast_modexp(a, x, p)
                self.assertEqual(res, pow(a, x, p))

    def test_fast_equals_naive_for_small_x(self):
        for x in (0, 1, 2, 7, 17, 100, 200, 1024, 10000):
            with self.subTest(x=x):
                fr, _ = mex.fast_modexp(5, x, 97)
                nr, _ = mex.naive_modexp(5, x, 97)
                self.assertEqual(fr, nr)


class TestMultiplicationCount(unittest.TestCase):
    def test_power_of_two_exponent(self):
        for k in range(1, 16):
            with self.subTest(k=k):
                _, mults = mex.fast_modexp(3, 1 << k, 97)
                self.assertEqual(mults, k)

    def test_all_ones_exponent(self):
        for k in range(1, 12):
            x = (1 << k) - 1
            with self.subTest(k=k, x=x):
                _, mults = mex.fast_modexp(7, x, 1_000_003)
                self.assertEqual(mults, max(0, 2 * k - 2))

    def test_formula_holds_random(self):
        for x in (1, 2, 3, 5, 8, 17, 31, 100, 701, 800, 12345, (1 << 20) | 1):
            with self.subTest(x=x):
                _, mults = mex.fast_modexp(11, x, 1_000_003)
                expected = (mex.bit_length(x) - 1) + (mex.hamming_weight(x) - 1)
                self.assertEqual(mults, expected)

    def test_higher_hamming_weight_means_more_mults(self):
        m_low = mex.fast_modexp(5, 1 << 15, 1_000_003)[1]
        m_mid = mex.fast_modexp(5, (1 << 15) | 0xFF, 1_000_003)[1]
        m_high = mex.fast_modexp(5, (1 << 16) - 1, 1_000_003)[1]
        self.assertLess(m_low, m_mid)
        self.assertLess(m_mid, m_high)


class TestTrace(unittest.TestCase):
    def test_trace_lecture_first_row(self):
        _, _, trace = mex.fast_modexp_traced(5, 701, 11)
        self.assertEqual(len(trace), 10)
        self.assertEqual(
            [s.a_pow_raw for s in trace],
            [5, 25, 9, 81, 16, 25, 9, 81, 16, 25],
        )

    def test_trace_lecture_mod_row(self):
        _, _, trace = mex.fast_modexp_traced(5, 701, 11)
        self.assertEqual(
            [s.a_pow_mod for s in trace],
            [5, 3, 9, 4, 5, 3, 9, 4, 5, 3],
        )

    def test_trace_lecture_bit_row(self):
        _, _, trace = mex.fast_modexp_traced(5, 701, 11)
        self.assertEqual(
            [s.bit for s in trace],
            [1, 0, 1, 1, 1, 1, 0, 1, 0, 1],
        )

    def test_trace_init_only_at_first_set_bit(self):
        for x in (1, 2, 3, 800, 701, 1024):
            with self.subTest(x=x):
                _, _, trace = mex.fast_modexp_traced(7, x, 97)
                inits = [s for s in trace if s.is_init]
                self.assertEqual(len(inits), 1)
                first_set = next(i for i in range(64) if (x >> i) & 1)
                self.assertEqual(inits[0].i, first_set)

    def test_format_table_contains_key_pieces(self):
        _, _, trace = mex.fast_modexp_traced(5, 701, 11)
        text = mex.format_trace_table(5, 701, 11, trace)
        self.assertIn("2^i", text)
        self.assertIn("бит x_i", text)
        self.assertIn("init", text)


class TestErrors(unittest.TestCase):
    def test_negative_modulus(self):
        with self.assertRaises(ValueError):
            mex.fast_modexp(2, 3, 0)

    def test_negative_exponent(self):
        with self.assertRaises(ValueError):
            mex.fast_modexp(2, -1, 5)

    def test_negative_base(self):
        with self.assertRaises(ValueError):
            mex.fast_modexp(-1, 3, 5)


class TestCLI(unittest.TestCase):
    def test_compute_cli(self):
        exit_code, out = run_cli("compute", "5", "701", "11")
        self.assertEqual(exit_code, 0)
        self.assertIn("5^701 mod 11 = 5", out)
        self.assertIn("умножений: 15", out)

    def test_trace_cli(self):
        exit_code, out = run_cli("trace", "5", "701", "11")
        self.assertEqual(exit_code, 0)
        self.assertIn("Y = 5^701 mod 11", out)
        self.assertIn("512 + 128 + 32 + 16 + 8 + 4 + 1", out)
        self.assertIn("init", out)
        self.assertIn("Результат: Y = 5", out)

    def test_compare_cli_small(self):
        exit_code, out = run_cli("compare", "7", "200", "1000")
        self.assertEqual(exit_code, 0)
        self.assertIn("Быстрый:", out)
        self.assertIn("Медленный:", out)
        self.assertIn("Совпадают: True", out)

    def test_hamming_demo_cli(self):
        exit_code, out = run_cli("hamming-demo", "--bits", "16")
        self.assertEqual(exit_code, 0)
        self.assertIn("HW", out)
        self.assertIn("умножений", out)

    def test_demo_cli(self):
        exit_code, out = run_cli("demo")
        self.assertEqual(exit_code, 0)
        self.assertIn("5^701 mod 11", out)
        self.assertIn("3^800 mod 13", out)

    def test_compute_cli_zero_exponent(self):
        exit_code, out = run_cli("compute", "9", "0", "17")
        self.assertEqual(exit_code, 0)
        self.assertIn("= 1", out)


if __name__ == "__main__":
    unittest.main()