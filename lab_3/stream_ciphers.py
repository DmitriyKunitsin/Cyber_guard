import argparse
import hashlib
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

# ---------------------------------------------------------------------------
# Генератор LCG
# ---------------------------------------------------------------------------

class LCG:
    """Линейный конгруэнтный генератор (A=1664525, C=1013904223, M=2**32)."""

    A = 1664525
    C = 1013904223
    M = 2 ** 32

    def __init__(self, seed):
        self.state = seed % self.M

    def next_byte(self):
        """Очередной байт из младших 8 бит состояния."""
        self.state = (self.A * self.state + self.C) % self.M
        return self.state & 0xFF

    def generate(self, n):
        """Генерация n случайных байтов."""
        return bytes(self.next_byte() for _ in range(n))


# ---------------------------------------------------------------------------
# Генерация ключевого файла
# ---------------------------------------------------------------------------

def generate_key_file(path, nbytes, method="secrets", seed=None):
    """Создаёт файл ключа указанного размера."""
    if method == "lcg":
        if seed is None:
            raise ValueError("Для LCG необходимо указать seed")
        data = LCG(seed).generate(nbytes)
    else:
        data = secrets.token_bytes(nbytes)
    Path(path).write_bytes(data)
    if verbose:
        print(f"[DEBUG] {method}: записано {nbytes} байт в {path}")


# ---------------------------------------------------------------------------
# Шифр Вернама (XOR)
# ---------------------------------------------------------------------------

def vernam_xor(in_path, key_path, out_path):
    """Операция XOR между файлами. Ключ должен быть не короче входного файла."""
    plain = Path(in_path).read_bytes()
    key = Path(key_path).read_bytes()
    if len(key) < len(plain):
        raise ValueError(f"Ключ ({len(key)} байт) короче данных ({len(plain)} байт)")
    cipher = bytes(p ^ k for p, k in zip(plain, key))
    Path(out_path).write_bytes(cipher)


def vernam_encrypt(plain_path, key_path, cipher_path):
    vernam_xor(plain_path, key_path, cipher_path)


def vernam_decrypt(cipher_path, key_path, plain_path):
    vernam_xor(cipher_path, key_path, plain_path)


# ---------------------------------------------------------------------------
# ChaCha20 через cryptography
# ---------------------------------------------------------------------------

def chacha_key_from_file(key_file):
    """SHA-256 от содержимого ключевого файла -> 32 байта."""
    data = Path(key_file).read_bytes()
    if not data:
        raise ValueError("Файл ключа для ChaCha20 пуст")
    return hashlib.sha256(data).digest()


def chacha_encrypt_file(input_file, key_file, output_file):
    """Шифрование ChaCha20 с записью 16-байтового nonce в начало."""
    key32 = chacha_key_from_file(key_file)
    nonce = secrets.token_bytes(16)
    algo = algorithms.ChaCha20(key32, nonce)
    encryptor = Cipher(algo, mode=None).encryptor()

    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        fout.write(nonce)
        while True:
            block = fin.read(64 * 1024)
            if not block:
                break
            fout.write(encryptor.update(block))
        fout.write(encryptor.finalize())


def chacha_decrypt_file(input_file, key_file, output_file):
    """Расшифрование ChaCha20 (первые 16 байт – nonce)."""
    key32 = chacha_key_from_file(key_file)
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        nonce = fin.read(16)
        if len(nonce) != 16:
            raise ValueError("Неверный формат зашифрованного файла: нет nonce")
        algo = algorithms.ChaCha20(key32, nonce)
        decryptor = Cipher(algo, mode=None).decryptor()
        while True:
            block = fin.read(64 * 1024)
            if not block:
                break
            fout.write(decryptor.update(block))
        fout.write(decryptor.finalize())


# ---------------------------------------------------------------------------
# Демонстрация
# ---------------------------------------------------------------------------

def run_demo(work_dir):
    """Сценарий демонстрации всех возможностей."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)

    plain_path = work / "demo_plain.txt"
    key_path = work / "demo_key.bin"
    cipher_path = work / "demo_vernam.bin"
    recovered_path = work / "demo_recovered.txt"
    chacha_out = work / "demo_chacha.bin"
    chacha_back = work / "demo_chacha_plain.txt"

    plain = b"Vernam one-time pad and ChaCha20 (cryptography) demo.\n"
    plain_path.write_bytes(plain)

    print("=== 1. Генерация ключа (secrets) ===")
    generate_key_file(key_path, len(plain), method="secrets")
    print(f"Открытый текст: {plain_path} ({len(plain)} байт)")
    print(f"Ключ:           {key_path} ({key_path.stat().st_size} байт)")

    print("\n=== 2. Вернам (XOR) ===")
    vernam_encrypt(plain_path, key_path, cipher_path)
    vernam_decrypt(cipher_path, key_path, recovered_path)
    ok = recovered_path.read_bytes() == plain
    print(f"Шифртекст:      {cipher_path}")
    print(f"Расшифровка:  {recovered_path} (совпадает: {ok})")

    print("\n=== 3. ChaCha20 (ключ = SHA-256 от файла ключа) ===")
    chacha_encrypt_file(plain_path, key_path, chacha_out)
    chacha_decrypt_file(chacha_out, key_path, chacha_back)
    ok2 = chacha_back.read_bytes() == plain
    print(f"ChaCha20 out: {chacha_out}")
    print(f"ChaCha20 plain: {chacha_back} (round-trip: {ok2})")


# ---------------------------------------------------------------------------
# CLI на argparse
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Потоковые шифры: Вернам и ChaCha20")
    sub = parser.add_subparsers(dest="command", required=True)

    # gen-key
    p_gen = sub.add_parser("gen-key", help="Сгенерировать файл ключа")
    p_gen.add_argument("output", type=Path, help="Выходной файл")
    p_gen.add_argument("-n", "--bytes", type=int, required=True, help="Количество байт")
    p_gen.add_argument("--method", choices=["lcg", "secrets"], default="secrets", help="Метод генерации")
    p_gen.add_argument("--seed", type=int, help="Seed для LCG")

    # prepare-samples
    p_prep = sub.add_parser("prepare-samples", help="Создать образцы plain.txt и key.bin")
    p_prep.add_argument("--dir", type=Path, default="samples", help="Каталог для образцов")
    p_prep.add_argument("--method", choices=["lcg", "secrets"], default="secrets")
    p_prep.add_argument("--seed", type=int)

    # vernam-encrypt
    p_ve = sub.add_parser("vernam-encrypt", help="Зашифровать файл (XOR)")
    p_ve.add_argument("plaintext", type=Path, help="Открытый текст")
    p_ve.add_argument("key", type=Path, help="Файл ключа")
    p_ve.add_argument("ciphertext", type=Path, help="Выходной шифртекст")

    # vernam-decrypt
    p_vd = sub.add_parser("vernam-decrypt", help="Расшифровать файл (XOR)")
    p_vd.add_argument("ciphertext", type=Path)
    p_vd.add_argument("key", type=Path)
    p_vd.add_argument("plaintext", type=Path)

    # chacha-encrypt
    p_ce = sub.add_parser("chacha-encrypt", help="Зашифровать ChaCha20")
    p_ce.add_argument("input", type=Path, help="Входной файл")
    p_ce.add_argument("keyfile", type=Path, help="Файл ключа (из него SHA-256 -> 32 байта)")
    p_ce.add_argument("output", type=Path)

    # chacha-decrypt
    p_cd = sub.add_parser("chacha-decrypt", help="Расшифровать ChaCha20")
    p_cd.add_argument("input", type=Path)
    p_cd.add_argument("keyfile", type=Path)
    p_cd.add_argument("output", type=Path)

    # demo
    p_demo = sub.add_parser("demo", help="Запустить демонстрацию")
    p_demo.add_argument("--dir", type=Path, default="samples", help="Папка для демо-файлов")

    # Глобальный флаг verbose
    parser.add_argument("-v", "--verbose", action="store_true", help="Подробный вывод")

    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    if args.command == "gen-key":
        if args.bytes <= 0:
            sys.exit("Ошибка: размер должен быть > 0")
        if args.method == "lcg" and args.seed is None:
            sys.exit("Ошибка: для LCG укажите --seed")
        generate_key_file(args.output, args.bytes, args.method, args.seed)
        print(f"Создан ключевой файл: {args.output}")

    elif args.command == "prepare-samples":
        plain_path = args.dir / "plain.txt"
        key_path = args.dir / "key.bin"
        plain = b"Stream ciphers lab3 demo text.\n"
        args.dir.mkdir(parents=True, exist_ok=True)
        plain_path.write_bytes(plain)
        generate_key_file(key_path, len(plain), args.method, args.seed)
        print(f"Созданы: {plain_path}, {key_path}")

    elif args.command == "vernam-encrypt":
        vernam_encrypt(args.plaintext, args.key, args.ciphertext)
        print(f"Зашифровано: {args.ciphertext}")

    elif args.command == "vernam-decrypt":
        vernam_decrypt(args.ciphertext, args.key, args.plaintext)
        print(f"Расшифровано: {args.plaintext}")

    elif args.command == "chacha-encrypt":
        chacha_encrypt_file(args.input, args.keyfile, args.output)
        print(f"ChaCha20 шифртекст: {args.output}")

    elif args.command == "chacha-decrypt":
        chacha_decrypt_file(args.input, args.keyfile, args.output)
        print(f"ChaCha20 открытый текст: {args.output}")

    elif args.command == "demo":
        run_demo(args.dir)


if __name__ == "__main__":
    verbose = False
    main()