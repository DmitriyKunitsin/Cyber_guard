"""
Частоты символов и энтропия файла (байтовая модель).
Переписанная версия: argparse вместо click, print вместо logging.
"""
import argparse
import math
import random
import sys
from collections import Counter
from pathlib import Path


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def byte_frequencies(data: bytes) -> Counter[int]:
    """Подсчёт частот байтов."""
    return Counter(data)


def entropy_from_frequencies(counts: Counter[int]) -> float:
    """Энтропия Шеннона в битах на символ."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def max_entropy(alphabet_size: int) -> float:
    """Теоретический максимум энтропии для алфавита данного размера."""
    if alphabet_size <= 1:
        return 0.0
    return math.log2(alphabet_size)


# ---------------------------------------------------------------------------
# Генерация тестовых данных (без класса SampleGenerator)
# ---------------------------------------------------------------------------

def generate_constant(size: int, byte_val: int = 65) -> bytes:
    return bytes([byte_val]) * size


def generate_coin(size: int, rng: random.Random) -> bytes:
    return bytes(rng.choice((48, 49)) for _ in range(size))  # '0' или '1'


def generate_uniform(size: int, rng: random.Random) -> bytes:
    return bytes(rng.randint(0, 255) for _ in range(size))


def generate_two_symbols_equal(size: int, rng: random.Random) -> bytes:
    a, b = ord("x"), ord("y")
    half = size // 2
    seq = bytearray([a] * half + [b] * (size - half))
    rng.shuffle(seq)
    return bytes(seq)


def write_samples(out_dir: Path, size: int, seed: int) -> list[tuple[str, Path]]:
    """Создаёт образцы файлов и возвращает список (метка, путь)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    samples = []

    def add(label: str, filename: str, data: bytes):
        p = out_dir / filename
        p.write_bytes(data)
        samples.append((label, p))

    add("Один повторяющийся символ", "const.bin", generate_constant(size))
    add("Случайные '0'/'1'", "coin.txt", generate_coin(size, rng))
    add("Случайные байты 0…255", "uniform.bin", generate_uniform(size, rng))
    add("Два символа 50/50", "two_equal.bin", generate_two_symbols_equal(size, rng))

    text = ("Hello entropy " * (max(1, size // 15)))[:size].encode("utf-8", errors="ignore")
    if len(text) < size:
        text += b" " * (size - len(text))
    add("Повторяющийся текст", "text.txt", text[:size])

    return samples


# ---------------------------------------------------------------------------
# Вывод отчётов
# ---------------------------------------------------------------------------

def print_freq_report(counts: Counter[int], limit: int = 32):
    total = sum(counts.values())
    print(f"Всего символов (байтов): {total}")
    if total == 0:
        print("(пустой файл)")
        return
    items = counts.most_common(limit)
    print(f"Топ-{len(items)} по частоте (байт как число / символ если printable):")
    for b, n in items:
        ch = chr(b) if 32 <= b < 127 else "."
        print(f"  {b:3d} 0x{b:02x} '{ch}'  ->  {n}  ({100.0 * n / total:.4f}%)")


def print_entropy_info(counts: Counter[int], label: str = ""):
    h = entropy_from_frequencies(counts)
    m = len(counts)
    h_max = max_entropy(m)
    if label:
        print(f"\n{label}")
    print(f"  Размер алфавита: {m}")
    print(f"  Энтропия H = {h:.6f} бит/символ")
    print(f"  Максимальная энтропия log2(m) = {h_max:.6f}")


# ---------------------------------------------------------------------------
# Команды
# ---------------------------------------------------------------------------

def command_freq(args):
    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"Файл не найден: {path}")
    counts = byte_frequencies(path.read_bytes())
    print(f"Файл: {path.resolve()}")
    print_freq_report(counts, limit=args.top)


def command_entropy(args):
    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"Файл не найден: {path}")
    counts = byte_frequencies(path.read_bytes())
    print(f"Файл: {path.resolve()}")
    print_freq_report(counts, limit=args.top)
    print_entropy_info(counts)


def command_demo(args):
    size = args.size
    seed = args.seed
    out_dir = Path(args.out_dir) if args.out_dir else Path("samples")
    samples = write_samples(out_dir, size, seed)

    print("Сгенерированные файлы:")
    for label, path in samples:
        print(f"  {label}: {path.resolve()}")

    print("\nЭнтропия образцов:")
    print("(приблизительные значения, зависят от размера выборки)")
    for label, path in samples:
        counts = byte_frequencies(path.read_bytes())
        h = entropy_from_frequencies(counts)
        m = len(counts)
        h_max = max_entropy(m)
        print(f"\n{label}")
        print(f"  Файл: {path.name}")
        print(f"  H = {h:.6f} бит/символ,  log2(m) = {h_max:.6f}")


# ---------------------------------------------------------------------------
# CLI на argparse
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Частоты символов и энтропия файла.")
    sub = parser.add_subparsers(dest="command", required=True)

    # freq
    p_freq = sub.add_parser("freq", help="Частоты байтов в файле")
    p_freq.add_argument("path", help="Путь к файлу")
    p_freq.add_argument("--top", type=int, default=32, help="Сколько частот показать (по умолчанию 32)")

    # entropy
    p_ent = sub.add_parser("entropy", help="Энтропия файла")
    p_ent.add_argument("path", help="Путь к файлу")
    p_ent.add_argument("--top", type=int, default=16, help="Сколько частот показать (по умолчанию 16)")

    # demo
    p_demo = sub.add_parser("demo", help="Сгенерировать образцы и показать энтропию")
    p_demo.add_argument("-n", "--size", type=int, default=200_000, help="Длина каждого образца в байтах")
    p_demo.add_argument("--seed", type=int, default=42, help="Seed ГПСЧ")
    p_demo.add_argument("--out-dir", help="Папка для образцов (по умолчанию samples)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "freq":
        command_freq(args)
    elif args.command == "entropy":
        command_entropy(args)
    elif args.command == "demo":
        command_demo(args)


if __name__ == "__main__":
    main()