"""Anonymize a company's tool exports.

mode="twin"    one identity graph for the whole company (built from the team directory and headers),
               one keyed pseudonym per person/client in every surface form, one date shift (whole weeks)
               and one amount scale for the company, identifiers replaced by valid-format fakes
mode="perdoc"  the same detection, but a fresh mapping/shift/scale per document (what a per-document
               anonymizer does)
mode="regex"   mask emails, phones, IBANs, SIREN/SIRET only
"""
import datetime as dt
import hashlib, hmac, random, re
from . import ids
from .corpus import MOIS, JOURS

PF = ["Claire", "Bastien", "Noémie", "Hugo", "Manon", "Raphaël", "Zoé", "Gaspard", "Romane", "Adrien", "Lison", "Victor",
      "Maëlle", "Simon", "Juliette", "Paul", "Agathe", "Maxime", "Océane", "Louis", "Céleste", "Arthur", "Rose", "Tristan"]
PL = ["Dubreuil", "Marchand", "Leclerc", "Vidal", "Roche", "Barbier", "Renard", "Arnaud", "Collin", "Picard", "Garnier",
      "Lemaire", "Huet", "Bertin", "Carré", "Masson", "Royer", "Brun", "Joly", "Aubert"]
PC = ["Ateliers Morvan", "Société Caillaud", "Maison Ferrand", "Groupe Sabatier", "Établissements Rivet", "Cabinet Pujol"]


def slug(s):
    return ids.fold(s).lower().replace(" ", "")


def parse_directory(arts):
    d = next(a for a in arts if a["id"] == "notion-directory")["text"]
    people = []
    for row in d.splitlines():
        m = re.match(r"\| (.+?) \| (\S+@\S+) \| @(\S+) \| (\S+) \| (.+?) \|", row)
        if m:
            name, email, handle, jira, mgr = m.groups()
            first, last = name.split(" ", 1)
            people.append(dict(first=first, last=last, email=email, handle=handle, jira=jira, manager=mgr))
    return people


def parse_clients(arts):
    names = set()
    for a in arts:
        names.update(re.findall(r"(?:Facture|Suivi|facture) ([A-ZÉ][\w'é]+(?: [A-ZÉ][\w'é]+)+)", a["text"]))
    return sorted(names, key=len, reverse=True)


class Mapper:
    def __init__(self, key, people, clients, domain, project, rng):
        self.key, self.rng = key, rng
        h = lambda s: int(hmac.new(key, s.encode(), hashlib.sha256).hexdigest(), 16)
        firsts = sorted(PF, key=lambda x: h("f" + x))
        lasts = sorted(PL, key=lambda x: h("l" + x))
        self.rules = []
        first_count, accented = {}, {}
        for p in people:
            first_count[ids.fold(p["first"]).lower()] = first_count.get(ids.fold(p["first"]).lower(), 0) + 1
            accented.setdefault(ids.fold(p["first"]).lower(), set()).update({p["first"], ids.fold(p["first"])})
        for i, p in enumerate(sorted(people, key=lambda p: h(p["email"]))):
            q = dict(first=firsts[i % len(firsts)], last=lasts[(i * 7) % len(lasts)])
            qf, ql = q["first"], q["last"]
            qs = slug(qf), slug(ql)
            loc_o = p["email"].split("@")[0]
            loc_q = f"{qs[0]}.{qs[1]}" if "." in loc_o else f"{qs[0][0]}{qs[1]}"
            pairs = [(f"{p['first']} {p['last']}", f"{qf} {ql}"), (ids.fold(f"{p['first']} {p['last']}"), ids.fold(f"{qf} {ql}")),
                     (f"{p['last'].upper()} {p['first']}", f"{ql.upper()} {qf}"), (f"{p['last']}, {p['first']}", f"{ql}, {qf}"),
                     (f"{p['first'][0]}. {p['last']}", f"{qf[0]}. {ql}"), (p["email"], f"{loc_q}@DOMAIN"), (loc_o, loc_q),
                     ("@" + p["handle"], f"@{qs[0]}.{qs[1][0]}"), (p["handle"], f"{qs[0]}.{qs[1][0]}"), (p["jira"], f"{qs[0][0]}{qs[1]}"),
                     (p["last"], ql)]
            if first_count[ids.fold(p["first"]).lower()] == 1:
                pairs += [(p["first"], qf), (ids.fold(p["first"]), ids.fold(qf))]
            self.rules += pairs
        for f, n in first_count.items():                       # shared first names: one neutral stand-in, no leak
            if n > 1:
                self.rules += [(form, "Alex") for form in accented[f]]
        for c, pc in zip(clients, sorted(PC, key=lambda x: h("c" + x))):
            self.rules.append((c, pc))
        self.rules.append((domain, "example-co.fr"))
        self.rules.append((project, "PRJ"))
        self.rules.append((project.lower(), "prj"))
        self.rules.sort(key=lambda x: -len(x[0]))
        self.pat = re.compile("|".join(r"(?<![\w@.])" + re.escape(o) + r"(?![\w])" for o, _ in self.rules))
        self.lookup = {o: n for o, n in self.rules}
        self.shift = 7 * rng.randint(-20, 20) or 7
        self.scale = rng.uniform(0.7, 1.4)
        self.idmap = {}

    def fake_id(self, kind, orig):
        if orig not in self.idmap:
            r = random.Random(hmac.new(self.key, orig.encode(), hashlib.sha256).digest())
            self.idmap[orig] = {"siren": lambda: ids.siren(r), "siret": lambda: ids.siret(r, ids.siren(r)[:9]),
                                "iban": lambda: ids.iban_fr(r), "phone": lambda: ids.phone(r)}[kind]()
        return self.idmap[orig]

    def text(self, t):
        t = re.sub(r"FR\d{25}", lambda m: self.fake_id("iban", m[0]), t)
        t = re.sub(r"\+33 6(?: \d\d){4}", lambda m: self.fake_id("phone", m[0]), t)
        t = re.sub(r"(?<!\d)\d{14}(?!\d)", lambda m: self.fake_id("siret", m[0]) if ids.luhn_ok(m[0]) else m[0], t)
        t = re.sub(r"(?<!\d)\d{9}(?!\d)", lambda m: self.fake_id("siren", m[0]) if ids.luhn_ok(m[0]) else m[0], t)
        t = self.dates(t)
        t = self.amounts(t)
        t = self.pat.sub(lambda m: self.lookup[m[0]], t)
        return t.replace("@DOMAIN", "@example-co.fr")

    def dates(self, t):
        sh = dt.timedelta(days=self.shift)
        t = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", lambda m: (dt.date(int(m[1]), int(m[2]), int(m[3])) + sh).isoformat(), t)
        t = re.sub(r"\b(\d{2})/(\d{2})/(\d{4})\b", lambda m: (dt.date(int(m[3]), int(m[2]), int(m[1])) + sh).strftime("%d/%m/%Y"), t)
        mo = "|".join(MOIS)

        def long(m):
            x = dt.date(int(m[3]), MOIS.index(m[2]) + 1, int(m[1])) + sh
            return f"{JOURS[x.weekday()]} {x.day} {MOIS[x.month - 1]} {x.year}"
        t = re.sub(rf"\b(?:{'|'.join(JOURS)}) (\d{{1,2}}) ({mo}) (\d{{4}})\b", long, t)

        def short(m):
            x = dt.date(2025, MOIS.index(m[2]) + 1, int(m[1])) + sh
            return f"{x.day} {MOIS[x.month - 1]}"
        return re.sub(rf"(?<![\w/])(\d{{1,2}}) ({mo})\b(?! \d{{4}})", short, t)

    def amounts(self, t):
        k = self.scale

        def fr(m):
            v = float(m[1].replace(" ", "").replace(" ", "") + "." + m[2]) * k
            w, c = f"{v:,.2f}".split(".")
            return f"{w.replace(',', ' ')},{c} €"
        t = re.sub(r"(\d{1,3}(?: \d{3})*),(\d{2}) €", fr, t)
        t = re.sub(r"€(\d{1,3}(?:,\d{3})*\.\d{2})", lambda m: f"€{float(m[1].replace(',', '')) * k:,.2f}", t)
        return re.sub(r"\b(\d+) EUR\b", lambda m: f"{float(m[1]) * k:.0f} EUR", t)


def anonymize(corpus, mode="twin", secret=b"per-delivery-secret"):
    arts = corpus["arts"]
    if mode == "regex":
        out = []
        for a in arts:
            t = re.sub(r"\S+@\S+\.\w+", "[EMAIL]", a["text"])
            t = re.sub(r"FR\d{25}", "[IBAN]", t)
            t = re.sub(r"\+33 6(?: \d\d){4}", "[PHONE]", t)
            t = re.sub(r"(?<!\d)\d{9}(?:\d{5})?(?!\d)", "[SIREN]", t)
            out.append(dict(a, text=t))
        return out
    people, clients = parse_directory(arts), parse_clients(arts)
    if mode == "twin":
        m = Mapper(secret, people, clients, corpus["domain"], corpus["project"], random.Random(secret + b"x"))
        return [dict(a, text=m.text(a["text"])) for a in arts]
    out = []
    for a in arts:
        m = Mapper(secret + a["id"].encode(), people, clients, corpus["domain"], corpus["project"], random.Random(secret + a["id"].encode()))
        out.append(dict(a, text=m.text(a["text"])))
    return out
