import argparse
import secrets
import struct
import sys
from pathlib import Path

BLOCK_SIZE = 8
KEY_SIZE = 16
DELTA = 0x9E3779B9
DEFAULT_ROUNDS = 64


def xor_bytes(a: bytes, b: bytes) -> bytes:
    """Побайтовый XOR двух последовательностей одинаковой длины."""
    return bytes(x ^ y for x, y in zip(a, b))


class XTEA:
    """XTEA: блочный шифр с длиной блока 8 байт и ключом 16 байт."""

    def __init__(self, key: bytes, rounds: int = DEFAULT_ROUNDS):
        if len(key) != KEY_SIZE:
            raise ValueError(f"Ключ должен быть {KEY_SIZE} байт")
        if rounds <= 0:
            raise ValueError("Число раундов должно быть > 0")
        self.key = struct.unpack("<4I", key)
        self.rounds = rounds

    def encrypt_block(self, block: bytes) -> bytes:
        if len(block) != BLOCK_SIZE:
            raise ValueError(f"Блок должен быть длиной {BLOCK_SIZE} байт")
        v0, v1 = struct.unpack("<II", block)
        k = self.key
        s = 0
        for _ in range(self.rounds):
            v0 = (v0 + ((((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + k[s & 3]))) & 0xFFFFFFFF
            s = (s + DELTA) & 0xFFFFFFFF
            v1 = (v1 + ((((v0 << 4) ^ (v0 >> 5)) + v0) ^ (s + k[(s >> 11) & 3]))) & 0xFFFFFFFF
        return struct.pack("<II", v0, v1)

    def decrypt_block(self, block: bytes) -> bytes:
        if len(block) != BLOCK_SIZE:
            raise ValueError(f"Блок должен быть длиной {BLOCK_SIZE} байт")
        v0, v1 = struct.unpack("<II", block)
        k = self.key
        s = (DELTA * self.rounds) & 0xFFFFFFFF
        for _ in range(self.rounds):
            v1 = (v1 - ((((v0 << 4) ^ (v0 >> 5)) + v0) ^ (s + k[(s >> 11) & 3]))) & 0xFFFFFFFF
            s = (s - DELTA) & 0xFFFFFFFF
            v0 = (v0 - ((((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + k[s & 3]))) & 0xFFFFFFFF
        return struct.pack("<II", v0, v1)


def pkcs7_pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """Дополнение PKCS#7."""
    n = block_size - (len(data) % block_size)
    return data + bytes([n]) * n


def pkcs7_unpad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """Снятие дополнения PKCS#7."""
    if not data or len(data) % block_size != 0:
        raise ValueError("Некорректная длина данных для снятия PKCS#7")
    n = data[-1]
    if n < 1 or n > block_size or data[-n:] != bytes([n]) * n:
        raise ValueError("Некорректное заполнение PKCS#7 (ключ или файл повреждены)")
    return data[:-n]


class CBC:
    """Режим CBC: перед данными хранится IV (один блок)."""

    def __init__(self, cipher: XTEA):
        self.cipher = cipher

    def encrypt(self, plaintext: bytes, iv: bytes = None) -> bytes:
        if iv is None:
            iv = secrets.token_bytes(BLOCK_SIZE)
        if len(iv) != BLOCK_SIZE:
            raise ValueError("IV должен быть длиной один блок")
        body = pkcs7_pad(plaintext)
        out = bytearray(iv)
        prev = iv
        for i in range(0, len(body), BLOCK_SIZE):
            block = body[i:i + BLOCK_SIZE]
            xored = xor_bytes(block, prev)
            enc = self.cipher.encrypt_block(xored)
            out.extend(enc)
            prev = enc
        return bytes(out)

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < BLOCK_SIZE * 2 or len(blob) % BLOCK_SIZE != 0:
            raise ValueError("Файл слишком короткий или длина не кратна блоку")
        iv = blob[:BLOCK_SIZE]
        ct = blob[BLOCK_SIZE:]
        prev = iv
        plain = bytearray()
        for i in range(0, len(ct), BLOCK_SIZE):
            enc_block = ct[i:i + BLOCK_SIZE]
            dec = self.cipher.decrypt_block(enc_block)
            plain.extend(xor_bytes(dec, prev))
            prev = enc_block
        return pkcs7_unpad(bytes(plain))

    def encrypt_file(self, input_path: Path, output_path: Path) -> None:
        data = input_path.read_bytes()
        output_path.write_bytes(self.encrypt(data))

    def decrypt_file(self, input_path: Path, output_path: Path) -> None:
        blob = input_path.read_bytes()
        output_path.write_bytes(self.decrypt(blob))


def prepare_samples(samples_dir: Path) -> tuple:
    """Создаёт plain.txt и key.bin (ключ 16 байт)."""
    samples_dir.mkdir(parents=True, exist_ok=True)
    plain = samples_dir / "plain.txt"
    key = samples_dir / "key.bin"
    plain.write_text("Hello, XTEA + CBC file encryption demo.\n", encoding="utf-8")
    key.write_bytes(bytes(range(KEY_SIZE)))
    return plain, key


def load_key(path_or_hex: Path | None, key_hex: str | None) -> bytes:
    """Загружает 16-байтный ключ из файла или hex-строки."""
    if key_hex is not None:
        h = key_hex.strip().lower().replace(" ", "")
        if len(h) != 32:
            raise ValueError("Hex-ключ должен содержать ровно 32 символа (128 бит)")
        return bytes.fromhex(h)
    if path_or_hex is None:
        raise ValueError("Укажите --key-file или --key-hex")
    p = Path(path_or_hex)
    raw = p.read_bytes()
    if len(raw) != KEY_SIZE:
        raise ValueError(f"Файл ключа: ожидалось {KEY_SIZE} байт, получено {len(raw)}")
    return raw


def demo_callback(work_dir: Path = None):
    """Демонстрация одного блока и файлового шифрования."""
    base = Path.cwd() / "samples" if work_dir is None else work_dir
    base.mkdir(parents=True, exist_ok=True)
    key = bytes(range(16))
    xtea = XTEA(key)
    block = b"abcdefgh"
    enc = xtea.encrypt_block(block)
    dec = xtea.decrypt_block(enc)
    print("=" * 58)
    print("1. XTEA: один блок (8 байт)")
    print("=" * 58)
    print(f"Блок (plain):  {block!r}")
    print(f"После encrypt: {enc.hex()}")
    print(f"После decrypt: {dec!r}")

    plain_path, key_path = prepare_samples(base)
    key = key_path.read_bytes()
    xtea = XTEA(key)
    cbc = CBC(xtea)
    cipher_path = base / "cipher.bin"
    back_path = base / "restored.txt"
    cbc.encrypt_file(plain_path, cipher_path)
    cbc.decrypt_file(cipher_path, back_path)
    print("\n" + "=" * 58)
    print("2. Файл через CBC")
    print("=" * 58)
    print(f"Записано: {plain_path}")
    print(f"Шифртекст: {cipher_path} ({cipher_path.stat().st_size} байт)")
    print(f"Восстановлено: {back_path.read_text(encoding='utf-8')!r}")


def build_parser():
    parser = argparse.ArgumentParser(description="XTEA (блочный шифр) в режиме CBC")
    sub = parser.add_subparsers(dest="command", required=True)

    # encrypt
    p_enc = sub.add_parser("encrypt", help="Зашифровать файл")
    p_enc.add_argument("plaintext", type=Path, help="Открытый текст")
    p_enc.add_argument("ciphertext", type=Path, help="Выходной шифртекст")
    p_enc.add_argument("--key-file", type=Path, help="Файл ключа (16 байт)")
    p_enc.add_argument("--key-hex", help="Ключ в hex (32 символа)")
    p_enc.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="Число раундов XTEA")

    # decrypt
    p_dec = sub.add_parser("decrypt", help="Расшифровать файл")
    p_dec.add_argument("ciphertext", type=Path, help="Шифртекст")
    p_dec.add_argument("plaintext", type=Path, help="Выходной открытый текст")
    p_dec.add_argument("--key-file", type=Path, help="Файл ключа (16 байт)")
    p_dec.add_argument("--key-hex", help="Ключ в hex (32 символа)")
    p_dec.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="Число раундов XTEA")

    # prepare-samples
    p_prep = sub.add_parser("prepare-samples", help="Создать образцы plain.txt и key.bin")
    p_prep.add_argument("--dir", type=Path, default="samples", help="Папка для образцов")

    # demo
    p_demo = sub.add_parser("demo", help="Запустить демонстрацию")
    p_demo.add_argument("--dir", type=Path, help="Папка для демо-файлов")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "encrypt":
        key = load_key(args.key_file, args.key_hex)
        cipher = XTEA(key, rounds=args.rounds)
        cbc = CBC(cipher)
        args.ciphertext.parent.mkdir(parents=True, exist_ok=True)
        cbc.encrypt_file(args.plaintext, args.ciphertext)
        print(f"Шифртекст: {args.ciphertext}")

    elif args.command == "decrypt":
        key = load_key(args.key_file, args.key_hex)
        cipher = XTEA(key, rounds=args.rounds)
        cbc = CBC(cipher)
        args.plaintext.parent.mkdir(parents=True, exist_ok=True)
        cbc.decrypt_file(args.ciphertext, args.plaintext)
        print(f"Открытый текст: {args.plaintext}")

    elif args.command == "prepare-samples":
        plain_path, key_path = prepare_samples(args.dir)
        print(f"Открытый текст: {plain_path}")
        print(f"Ключ: {key_path} ({key_path.stat().st_size} байт)")

    elif args.command == "demo":
        demo_callback(args.dir)


if __name__ == "__main__":
    main()