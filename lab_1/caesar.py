"""
Шифр Цезаря – альтернативная реализация в процедурно-ООП стиле.
Использует argparse, минимум зависимостей.
"""
import argparse
import re
import string
import sys
from collections import Counter
from pathlib import Path


# ---------------------------------------------------------------------------
class CaesarCipher:
    """Шифр Цезаря с операциями над символами латиницы."""

    ALPHABET_SIZE = len(string.ascii_lowercase)

    def _shift(self, text: str, key: int) -> str:
        """Сдвиг букв на key позиций (по модулю алфавита)."""
        res = []
        for ch in text:
            if 'a' <= ch <= 'z':
                base = ord('a')
            elif 'A' <= ch <= 'Z':
                base = ord('A')
            else:
                res.append(ch)
                continue
            offset = (ord(ch) - base + key) % self.ALPHABET_SIZE
            res.append(chr(base + offset))
        return ''.join(res)

    def encrypt(self, text: str, key: int) -> str:
        return self._shift(text, key)

    def decrypt(self, text: str, key: int) -> str:
        return self._shift(text, -key)

    def known_plaintext_key(self, plain: str, cipher: str) -> int | None:
        """KPA: ключ по известной паре открытого и шифрованного текстов."""
        diffs = []
        for p, c in zip(plain.lower(), cipher.lower()):
            if p.isalpha() and c.isalpha():
                diffs.append((ord(c) - ord(p)) % self.ALPHABET_SIZE)
        if not diffs:
            return None
        return Counter(diffs).most_common(1)[0][0]

    def brute_force(self, ciphertext: str) -> list[tuple[int, str]]:
        """Все 26 вариантов расшифрования."""
        return [(k, self.decrypt(ciphertext, k)) for k in range(self.ALPHABET_SIZE)]


# ---------------------------------------------------------------------------
class WordDictionary:
    """Словарь для подбора ключа по качеству расшифровки."""

    FALLBACK_WORDS = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "was",
        "one", "our", "out", "day", "get", "has", "him", "his", "how", "man",
        "new", "now", "old", "see", "two", "way", "who", "hello", "world",
        "this", "that", "with", "from", "attack", "cipher", "plain", "text",
    }

    def __init__(self, words: set[str] | None = None):
        self.words = words or self.FALLBACK_WORDS

    @classmethod
    def from_file(cls, path: str | Path) -> "WordDictionary":
        p = Path(path)
        if not p.is_file():
            print(f"Файл словаря '{p}' не найден, использую встроенный набор.")
            return cls()
        raw = {w.strip().lower() for w in p.read_text(encoding='utf-8').splitlines() if w.strip().isalpha()}
        if not raw:
            print("Словарь пуст, использую встроенный набор.")
            return cls()
        print(f"Загружено слов: {len(raw)}")
        return cls(raw)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z]+", text.lower())

    def score(self, text: str) -> tuple[int, int]:
        """Число словарных слов и общее число токенов."""
        tokens = self._tokenize(text)
        hits = sum(1 for t in tokens if t in self.words)
        return hits, len(tokens)

    def best_key(self, ciphertext: str, cipher: CaesarCipher) -> tuple[int, str, float]:
        """Возвращает (ключ, расшифрованный_текст, доля_словарных_слов)."""
        best_k, best_ratio = 0, -1.0
        best_plain = ""
        for k, plain in cipher.brute_force(ciphertext):
            hits, total = self.score(plain)
            ratio = hits / total if total > 0 else 0.0
            if ratio > best_ratio:
                best_ratio = ratio
                best_k = k
                best_plain = plain
        return best_k, best_plain, best_ratio


# ---------------------------------------------------------------------------
def demo(cipher: CaesarCipher, dictionary: WordDictionary) -> None:
    """Сценарий демонстрации всех возможностей."""
    plain = "Hello world attack cipher"
    key = 3
    encrypted = cipher.encrypt(plain, key)
    decrypted = cipher.decrypt(encrypted, key)

    print("=" * 60)
    print("1. Шифрование / расшифрование")
    print(f"  Исходный текст : {plain}")
    print(f"  Зашифрован (k={key}): {encrypted}")
    print(f"  Расшифрован     : {decrypted}")

    print("\n" + "=" * 60)
    print("2. Атака по известному открытому тексту (KPA)")
    found_key = cipher.known_plaintext_key(plain, encrypted)
    print(f"  Найденный ключ: {found_key}")

    print("\n" + "=" * 60)
    print("3. Полный перебор (26 вариантов)")
    for k, variant in cipher.brute_force(encrypted):
        print(f"  k={k:2d}: {variant}")

    print("\n" + "=" * 60)
    print("4. Подбор ключа по словарю")
    k, recovered, ratio = dictionary.best_key(encrypted, cipher)
    h, t = dictionary.score(recovered)
    print(f"  Ключ: {k}")
    print(f"  Текст: {recovered}")
    print(f"  Совпадений: {h}/{t} ({ratio:.0%})")


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Шифр Цезаря – шифрование, расшифрование, атаки.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Подробный вывод")
    parser.add_argument("--words", type=Path, help="Файл словаря (по умолчанию words.txt рядом)")
    sub = parser.add_subparsers(dest="command", required=True)

    # encrypt
    p_enc = sub.add_parser("encrypt", help="Зашифровать текст")
    p_enc.add_argument("text", help="Текст для шифрования")
    p_enc.add_argument("-k", "--key", type=int, required=True, help="Ключ (0-25)")

    # decrypt
    p_dec = sub.add_parser("decrypt", help="Расшифровать с известным ключом")
    p_dec.add_argument("ciphertext", help="Шифртекст")
    p_dec.add_argument("-k", "--key", type=int, required=True, help="Ключ")

    # kpa
    p_kpa = sub.add_parser("kpa", help="Атака по известному открытому тексту")
    p_kpa.add_argument("--plain", required=True, help="Открытый текст")
    p_kpa.add_argument("--cipher", required=True, help="Шифртекст")

    # brute
    p_brute = sub.add_parser("brute", help="Полный перебор ключей")
    p_brute.add_argument("ciphertext", help="Шифртекст")

    # dict-attack
    p_dict = sub.add_parser("dict-attack", help="Подбор ключа по словарю")
    p_dict.add_argument("ciphertext", help="Шифртекст")

    # demo
    sub.add_parser("demo", help="Демонстрация всех возможностей")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Словарь
    dictionary = WordDictionary.from_file(args.words) if args.words else WordDictionary()
    cipher = CaesarCipher()

    if args.command == "encrypt":
        print(cipher.encrypt(args.text, args.key))
    elif args.command == "decrypt":
        print(cipher.decrypt(args.ciphertext, args.key))
    elif args.command == "kpa":
        key = cipher.known_plaintext_key(args.plain, args.cipher)
        if key is None:
            print("Ключ не найден", file=sys.stderr)
            sys.exit(1)
        print(key)
    elif args.command == "brute":
        for k, txt in cipher.brute_force(args.ciphertext):
            print(f"k={k:2d}\t{txt}")
    elif args.command == "dict-attack":
        k, plain, ratio = dictionary.best_key(args.ciphertext, cipher)
        h, t = dictionary.score(plain)
        print(f"key={k}\n{plain}\nscore={h}/{t} ({ratio:.0%})")
    elif args.command == "demo":
        demo(cipher, dictionary)


if __name__ == "__main__":
    main()