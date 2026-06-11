import argparse
import hashlib
import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    """SHA-256 в виде hex-строки."""
    return hashlib.sha256(data).hexdigest()

def sha256_bytes(data: bytes) -> bytes:
    """SHA-256 как байты."""
    return hashlib.sha256(data).digest()

def truncated_bits(data: bytes, n_bits: int) -> int:
    """
    Первые n_bits бит SHA-256(data) как целое число.
    n_bits должно быть от 1 до 256.
    """
    if not (1 <= n_bits <= 256):
        raise ValueError("n_bits должен быть от 1 до 256")
    h = int.from_bytes(sha256_bytes(data), "big")
    return h >> (256 - n_bits)

def expected_trials(n_bits: int) -> float:
    """
    Ожидаемое число попыток до первой коллизии
    для пространства размера 2^n_bits.
    """
    if n_bits <= 0:
        return 0.0
    m = 2.0 ** n_bits
    return math.sqrt(math.pi * m / 2.0)

def find_collision(n_bits: int, max_trials: int = 5_000_000):
    """
    Ищет два разных сообщения, у которых совпадают первые n_bits бит SHA-256.
    Сообщения генерируются как строковые представления целых чисел (0, 1, 2, ...).
    Возвращает (msg_a, msg_b, количество проверенных сообщений, усечённое значение).
    """
    if not (1 <= n_bits <= 256):
        raise ValueError("n_bits вне диапазона 1..256")
    seen = {}
    for i in range(max_trials):
        msg = str(i).encode("utf-8")
        t = truncated_bits(msg, n_bits)
        prev = seen.get(t)
        if prev is not None and prev != msg:
            # коллизия найдена
            return prev, msg, i + 1, t
        seen[t] = msg
    raise RuntimeError(
        f"За {max_trials} попыток коллизия не найдена (n_bits={n_bits})."
    )

def verify_collision(a: bytes, b: bytes, n_bits: int) -> bool:
    """Проверяет, что у двух разных сообщений совпадают первые n_bits бит."""
    if a == b:
        return False
    return truncated_bits(a, n_bits) == truncated_bits(b, n_bits)


# ---------------------------------------------------------------------------
# Обработчики команд
# ---------------------------------------------------------------------------

def handle_hash_hex(args):
    if args.file:
        data = Path(args.file).read_bytes()
    else:
        data = args.text.encode("utf-8")
    print(sha256_hex(data))

def handle_truncate(args):
    data = args.text.encode("utf-8")
    bits = args.bits
    t = truncated_bits(data, bits)
    width = (bits + 3) // 4  # минимальное количество hex-цифр
    print(f"truncated ({bits} бит, int): {t}")
    print(f"truncated ({bits} бит, hex): {t:0{width}x}")

def handle_birthday_search(args):
    bits = args.bits
    max_trials = args.max_trials
    exp = expected_trials(bits)
    space = 2 ** bits
    print(f"n_bits={bits}")
    print(f"Размер пространства префиксов: 2^{bits} = {space}")
    print(f"Ожидаемый порядок до первой коллизии: около sqrt(2^{bits}) ≈ {exp:.1f} сообщений")
    print("Идея: это как дни рождения – людей намного меньше 365, но совпадение дня уже вероятно.")
    a, b, n, val = find_collision(bits, max_trials=max_trials)
    print(f"Найдено за n={n} сообщений.")
    print(f"Сообщение A (repr): {a!r}")
    print(f"Сообщение B (repr): {b!r}")
    print(f"Общий префикс ({bits} бит, int): {val}")
    print(f"SHA256(A) hex: {sha256_hex(a)}")
    print(f"SHA256(B) hex: {sha256_hex(b)}")

def handle_demo(args):
    bar = "=" * 58
    s = b"birthday"
    print(f"\n{bar}\n1. SHA-256 (полный hex)\n{bar}")
    print(f"SHA256({s!r}) =\n{sha256_hex(s)}")

    nb = 18
    print(f"\n{bar}\n2. Первые {nb} бит как целое\n{bar}")
    tv = truncated_bits(s, nb)
    print(f"truncated_{nb}_bits = {tv} (hex width {(nb + 3) // 4}: {tv:0{(nb + 3) // 4}x})")

    print(f"\n{bar}\n3. Коллизия усечённого хеша ({nb} бит)\n{bar}")
    exp = expected_trials(nb)
    print(f"Префиксов всего: 2^{nb} = {2**nb}")
    print(f"По парадоксу дней рождения коллизия обычно появляется уже примерно через ~{exp:.0f} попыток.")
    print("Причина: число пар растет как n^2/2, поэтому совпадение возникает сильно раньше, чем перебор всего пространства.")
    a, b, n, val = find_collision(nb, max_trials=500_000)
    print(f"Получено за {n} сообщений; префикс (int) = {val}")
    print(f"A = {a!r}\nB = {b!r}")
    print(f"Проверка: совпадают первые {nb} бит: {verify_collision(a, b, nb)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="SHA-256 и парадокс дней рождения"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # hash-hex
    p_hash = subparsers.add_parser("hash-hex", help="Полный SHA-256 в hex")
    p_hash.add_argument("text", nargs="?", default="", help="Текст (если не указан файл)")
    p_hash.add_argument("--file", type=str, help="Хешировать файл")
    p_hash.set_defaults(func=handle_hash_hex)

    # truncate
    p_trunc = subparsers.add_parser("truncate", help="Первые N бит хеша")
    p_trunc.add_argument("text", help="Текст")
    p_trunc.add_argument("--bits", type=int, required=True, help="Число бит (1-256)")
    p_trunc.set_defaults(func=handle_truncate)

    # birthday-search
    p_birth = subparsers.add_parser("birthday-search", help="Найти коллизию усечённого хеша")
    p_birth.add_argument("--bits", type=int, required=True, help="Длина префикса в битах")
    p_birth.add_argument("--max-trials", type=int, default=2_000_000, help="Максимум попыток")
    p_birth.set_defaults(func=handle_birthday_search)

    # demo
    p_demo = subparsers.add_parser("demo", help="Демонстрация")
    p_demo.set_defaults(func=handle_demo)

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