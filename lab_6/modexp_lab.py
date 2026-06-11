import argparse
import sys
from dataclasses import dataclass  # оставим для удобства, но можно было и класс с __init__


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def hamming_weight(x: int) -> int:
    """Вес Хэмминга – количество единичных битов."""
    if x < 0:
        raise ValueError("x должен быть >= 0")
    count = 0
    while x:
        count += x & 1
        x >>= 1
    return count


def bit_length(x: int) -> int:
    """Длина двоичного представления (для 0 возвращает 1)."""
    if x < 0:
        raise ValueError("x должен быть >= 0")
    if x == 0:
        return 1
    length = 0
    while x:
        length += 1
        x >>= 1
    return length


def explain_powers_of_two(x: int) -> str:
    """Разложение на сумму степеней двойки: 701 -> '512 + 128 + 32 + 16 + 8 + 4 + 1'."""
    if x == 0:
        return "0"
    parts = []
    for i in range(bit_length(x)):
        if (x >> i) & 1:
            parts.append(str(1 << i))
    parts.reverse()
    return " + ".join(parts)


def _check_args(a: int, x: int, p: int):
    """Общая валидация для возведения в степень."""
    if p < 1:
        raise ValueError(f"модуль p должен быть >= 1, получено {p}")
    if x < 0:
        raise ValueError(f"показатель x должен быть >= 0, получено {x}")
    if a < 0:
        raise ValueError(f"основание a должно быть >= 0, получено {a}")


# ---------------------------------------------------------------------------
# Алгоритмы возведения в степень
# ---------------------------------------------------------------------------

def naive_modexp(a: int, x: int, p: int) -> tuple[int, int]:
    """Медленное умножение: x умножений. Возвращает (результат, число умножений)."""
    _check_args(a, x, p)
    if p == 1:
        return 0, 0
    result = 1 % p
    base = a % p
    mults = 0
    for _ in range(x):
        result = (result * base) % p
        mults += 1
    return result, mults


@dataclass
class TraceStep:
    """Одна строка таблицы трассировки."""
    i: int
    power_of_two: int
    a_pow_raw: int
    a_pow_mod: int
    bit: int
    mul_raw: int | None
    mul_mod: int | None
    is_init: bool


def fast_modexp_traced(a: int, x: int, p: int) -> tuple[int, int, list[TraceStep]]:
    """
    Быстрое возведение с трассировкой: квадратирование и умножение.
    Биты показателя обрабатываются от младшего к старшему.
    """
    _check_args(a, x, p)
    if p == 1:
        return 0, 0, []
    if x == 0:
        return 1 % p, 0, []

    n_bits = bit_length(x)
    bits = [(x >> i) & 1 for i in range(n_bits)]

    mults = 0
    result = None
    a_pow_mod = a % p
    trace = []

    for i, bit in enumerate(bits):
        if i == 0:
            raw = a
        else:
            raw = a_pow_mod * a_pow_mod
            mults += 1
            a_pow_mod = raw % p

        mul_raw = None
        mul_mod = None
        is_init = False
        if bit == 1:
            if result is None:
                result = a_pow_mod
                is_init = True
            else:
                mul_raw = result * a_pow_mod
                mults += 1
                result = mul_raw % p
                mul_mod = result

        trace.append(
            TraceStep(
                i=i,
                power_of_two=1 << i,
                a_pow_raw=raw,
                a_pow_mod=a_pow_mod,
                bit=bit,
                mul_raw=mul_raw,
                mul_mod=mul_mod,
                is_init=is_init,
            )
        )

    assert result is not None
    return result, mults, trace


def fast_modexp(a: int, x: int, p: int) -> tuple[int, int]:
    """Быстрое возведение без трассировки."""
    res, mults, _ = fast_modexp_traced(a, x, p)
    return res, mults


def format_trace_table(a: int, x: int, p: int, trace: list[TraceStep]) -> str:
    """Формирует строку с таблицей трассировки."""
    if not trace:
        return "(пустая трассировка)"

    # заголовки колонок
    columns = {
        "i": [str(s.i) for s in trace],
        "2^i": [str(s.power_of_two) for s in trace],
        f"a^(2^i)  (a={a})": [str(s.a_pow_raw) for s in trace],
        f"a^(2^i) mod {p}": [str(s.a_pow_mod) for s in trace],
        "бит x_i": [str(s.bit) for s in trace],
        "r * a^(2^i)": [
            "init" if s.is_init else ("-" if s.mul_raw is None else str(s.mul_raw))
            for s in trace
        ],
        f"r mod {p}": [
            "-" if s.bit == 0 else str(s.a_pow_mod if s.is_init else s.mul_mod)
            for s in trace
        ],
    }

    label_w = max(len(l) for l in columns)
    col_w = max(max(len(v) for v in vals) for vals in columns.values())
    col_w = max(col_w, 3)

    sep = "+" + "-" * (label_w + 2) + ("+" + "-" * (col_w + 2)) * len(trace) + "+"
    lines = [sep]
    for label, values in columns.items():
        row = f"| {label:<{label_w}} |" + "".join(f" {v:>{col_w}} |" for v in values)
        lines.append(row)
        lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Обработчики команд CLI
# ---------------------------------------------------------------------------

def cmd_compute(args):
    a, x, p = args.a, args.x, args.p
    res, mults = fast_modexp(a, x, p)
    print(f"{a}^{x} mod {p} = {res}")
    print(f"Фактически выполнено умножений: {mults}")
    print(f"Длина показателя в битах: {bit_length(x)}, вес Хэмминга: {hamming_weight(x)}")


def cmd_trace(args):
    a, x, p = args.a, args.x, args.p
    res, mults, trace = fast_modexp_traced(a, x, p)
    print(f"Y = {a}^{x} mod {p}")
    print(f"{x} = {explain_powers_of_two(x)}")
    print(f"Длина показателя: {bit_length(x)} бит, вес Хэмминга: {hamming_weight(x)}")
    print()
    print(format_trace_table(a, x, p, trace))
    print()
    print(f"Результат: Y = {res}")
    print(f"Фактически выполнено умножений: {mults}")
    n = bit_length(x)
    h = hamming_weight(x)
    print(f"Теоретическая оценка для этого x: (n-1) + (HW-1) = ({n}-1) + ({h}-1) = {(n-1)+(h-1)}")


def cmd_compare(args):
    a, x, p = args.a, args.x, args.p
    fast_res, fast_mults = fast_modexp(a, x, p)
    print(f"Быстрый:   {a}^{x} mod {p} = {fast_res}, умножений = {fast_mults}")
    if x <= 200_000:
        naive_res, naive_mults = naive_modexp(a, x, p)
        print(f"Медленный: {a}^{x} mod {p} = {naive_res}, умножений = {naive_mults}")
        print(f"Совпадают: {fast_res == naive_res}")
    else:
        print("Медленный пропущен (x слишком большой).")
    builtin = pow(a, x, p)
    print(f"Проверка через builtin pow: {builtin}  ->  совпадает: {fast_res == builtin}")


def cmd_hamming_demo(args):
    a = args.a
    p = args.p
    bits = args.bits
    if bits < 1 or bits > 64:
        sys.exit("--bits должно быть от 1 до 64")

    cases = [
        ("min HW (одна 1)", 1 << (bits - 1)),
        ("две 1", (1 << (bits - 1)) | 1),
        ("половина HW", int("10" * (bits // 2) + ("1" if bits % 2 else ""), 2)),
        ("max HW (все 1)", (1 << bits) - 1),
    ]
    print(f"a = {a}, p = {p}, длина показателя = {bits} бит\n")
    header = f"{'случай':<22} | {'x':>20} | {'HW':>4} | {'умножений':>10} | {'результат':>14}"
    print(header)
    print("-" * len(header))
    for label, x in cases:
        res, mults = fast_modexp(a, x, p)
        ok = "ok" if res == pow(a, x, p) else "FAIL"
        print(f"{label:<22} | {x:>20} | {hamming_weight(x):>4} | {mults:>10} | {res:>14}  [{ok}]")
    print("\nВывод: при одинаковой длине показателя число умножений = (n-1) + (HW-1).")


def cmd_demo(args):
    """Полный демонстрационный сценарий."""
    sep = "=" * 70

    print(f"\n{sep}\n1. Пример из лекции: Y = 5^701 mod 11\n{sep}")
    a, x, p = 5, 701, 11
    res, mults, trace = fast_modexp_traced(a, x, p)
    print(f"{x} = {explain_powers_of_two(x)}")
    print(f"Длина показателя: {bit_length(x)} бит, вес Хэмминга: {hamming_weight(x)}")
    print()
    print(format_trace_table(a, x, p, trace))
    print()
    print(f"Результат: Y = {res}")
    print(f"Умножений: {mults}")
    print(f"Проверка pow: {pow(a, x, p)} (совпадает: {res == pow(a, x, p)})")
    print("В лекции тоже 15 умножений: 9 квадратирований + 6 «доумножений».")

    print(f"\n{sep}\n2. Второй пример: Y = 3^800 mod 13\n{sep}")
    a, x, p = 3, 800, 13
    res, mults, trace = fast_modexp_traced(a, x, p)
    print(f"{x} = {explain_powers_of_two(x)}")
    print(f"Длина: {bit_length(x)} бит, HW = {hamming_weight(x)}")
    print()
    print(format_trace_table(a, x, p, trace))
    print()
    print(f"Результат: Y = {res} (проверка: {pow(a, x, p)})")
    print(f"Умножений: {mults}")

    print(f"\n{sep}\n3. Сравнение быстрого и медленного (x=200)\n{sep}")
    a, x, p = 7, 200, 1000
    fr, fm = fast_modexp(a, x, p)
    nr, nm = naive_modexp(a, x, p)
    print(f"  быстрый:   {fr}  за {fm} умножений")
    print(f"  медленный: {nr}  за {nm} умножений")
    print(f"  совпадают: {fr == nr}; ускорение в {nm / max(fm, 1):.1f} раз")

    print(f"\n{sep}\n4. Влияние веса Хэмминга (32 бита)\n{sep}")
    a, p, bits = 5, 1_000_003, 32
    cases = [
        ("min HW = 1   ", 1 << (bits - 1)),
        ("HW = 2       ", (1 << (bits - 1)) | 1),
        ("HW ~ 16      ", int("10" * (bits // 2), 2)),
        ("max HW = 32  ", (1 << bits) - 1),
    ]
    print(f"a={a}, p={p}, длина показателя = {bits} бит")
    print(f"{'случай':<14} | {'x':>11} | {'HW':>3} | {'умножений':>10}")
    print("-" * 50)
    for label, x in cases:
        res, mults = fast_modexp(a, x, p)
        assert res == pow(a, x, p)
        print(f"{label:<14} | {x:>11} | {hamming_weight(x):>3} | {mults:>10}")
    print("\nПодтверждение формулы: умножений = (n-1) + (HW-1).")

    print(f"\n{sep}\n5. Большое число (2^512-1 mod 2^521-1)\n{sep}")
    a, x, p = 7, (1 << 512) - 1, (1 << 521) - 1
    res, mults = fast_modexp(a, x, p)
    print(f"a = {a}")
    print(f"x = 2^512 - 1 (512 бит, HW = 512)")
    print(f"p = 2^521 - 1 (простое Мерсенна M_521)")
    print(f"Результат получен за {mults} умножений (медленный метод: ~2^512).")
    print(f"Проверка pow: {res == pow(a, x, p)}")


# ---------------------------------------------------------------------------
# CLI на argparse
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description="Быстрое возведение в степень по модулю")
    sub = parser.add_subparsers(dest="command", required=True)

    # compute
    p_comp = sub.add_parser("compute", help="a^x mod p")
    p_comp.add_argument("a", type=int)
    p_comp.add_argument("x", type=int)
    p_comp.add_argument("p", type=int)
    p_comp.set_defaults(func=cmd_compute)

    # trace
    p_trace = sub.add_parser("trace", help="Трассировка вычисления")
    p_trace.add_argument("a", type=int)
    p_trace.add_argument("x", type=int)
    p_trace.add_argument("p", type=int)
    p_trace.set_defaults(func=cmd_trace)

    # compare
    p_cmp = sub.add_parser("compare", help="Сравнение быстрого и медленного алгоритмов")
    p_cmp.add_argument("a", type=int)
    p_cmp.add_argument("x", type=int)
    p_cmp.add_argument("p", type=int)
    p_cmp.set_defaults(func=cmd_compare)

    # hamming-demo
    p_hw = sub.add_parser("hamming-demo", help="Демонстрация влияния веса Хэмминга")
    p_hw.add_argument("--a", type=int, default=5)
    p_hw.add_argument("--p", type=int, default=1_000_003)
    p_hw.add_argument("--bits", type=int, default=32)
    p_hw.set_defaults(func=cmd_hamming_demo)

    # demo
    p_demo = sub.add_parser("demo", help="Полный демонстрационный сценарий")
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nПрервано пользователем", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()