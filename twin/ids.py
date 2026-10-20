"""French identifiers: SIREN/SIRET (Luhn), FR IBAN (mod 97), phone numbers; plus accent folding."""
import unicodedata


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def luhn_ok(s):
    tot = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        tot += d
    return tot % 10 == 0


def luhn_complete(body):
    for d in "0123456789":
        if luhn_ok(body + d):
            return body + d


def siren(r):
    return luhn_complete("".join(str(r.randint(0, 9)) for _ in range(8)))


def siret(r, sir):
    return luhn_complete(sir + "".join(str(r.randint(0, 9)) for _ in range(4)))


def iban_fr(r):
    bban = "".join(str(r.randint(0, 9)) for _ in range(23))
    num = int(bban + "152700")                     # "FR00" moved to the end, letters as numbers (F=15, R=27)
    check = 98 - num % 97
    return f"FR{check:02d}{bban}"


def iban_ok(s):
    s = s.replace(" ", "")
    moved = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in moved)) % 97 == 1


def phone(r):
    return "+33 6 " + " ".join(f"{r.randint(0, 99):02d}" for _ in range(4))
