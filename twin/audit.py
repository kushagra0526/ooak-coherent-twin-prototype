"""Leaks (did any original identifier survive?) and coherence (are cross-tool tasks still solvable,
with the same answer?)."""
import datetime as dt
import re
from . import ids
from .corpus import MOIS


def originals(corpus, cfg):
    toks = set()
    for p in corpus["people"]:
        for x in (p["first"], p["last"], ids.fold(p["first"]), ids.fold(p["last"]), p["email"], p["email"].split("@")[0],
                  p["handle"], p["jira"], cfg.get("nicks", {}).get(p["first"], "")):
            if x:
                toks.add(x)
        if "-" in p["first"]:
            toks.add("".join(s[0] for s in p["first"].split("-")) + " " + p["last"])
    for c in corpus["clients"]:
        generic = {"Boulangerie", "Atelier", "Ateliers", "Cabinet", "Transports", "Maison", "Garage", "Société", "Groupe", "Établissements"}
        toks.update([c["name"], c["siren"], c["siret"], c["iban"], c["phone"]] + [w for w in c["name"].split() if len(w) > 3 and w not in generic])
    toks.add(corpus["domain"])
    return toks


def leaks(corpus, arts, cfg):
    toks = sorted(originals(corpus, cfg), key=len, reverse=True)
    pat = re.compile("|".join(r"(?<![\w])" + re.escape(t) + r"(?![\w])" for t in toks), re.I)
    before = sum(len(pat.findall(a["text"])) for a in corpus["arts"])
    after = sum(len(pat.findall(a["text"])) for a in arts)
    found = [m for a in arts for m in pat.findall(a["text"])]
    return after, before, found


def _directory(arts):
    d = next(a for a in arts if a["id"] == "notion-directory")["text"]
    rows = {}
    for row in d.splitlines():
        m = re.match(r"\| (.+?) \| (\S+@\S+) \| @(\S+) \| (\S+) \| (.+?) \|", row)
        if m:
            rows[m[4]] = dict(name=m[1], email=m[2], handle=m[3], manager=m[5])
    return rows


def _amount(t):
    m = re.search(r"(\d{1,3}(?: \d{3})*),(\d{2}) €", t)
    if m:
        return round(float(m[1].replace(" ", "") + "." + m[2]))
    m = re.search(r"€(\d{1,3}(?:,\d{3})*\.\d{2})", t)
    if m:
        return round(float(m[1].replace(",", "")))
    m = re.search(r"\b(\d+) EUR\b", t)
    return int(m[1]) if m else None


def solve(arts, key):
    """The same solver runs on the original and on the twin: (assignee name, manager name, amounts agree, day gap, email-recipient == directory person)."""
    A = {a["id"]: a["text"] for a in arts}
    jira, mail, slack, notion = A[f"jira-{key}"], A[f"gmail-{key}"], A[f"slack-{key}"], A[f"notion-{key}"]
    d = _directory(arts)
    m = re.search(r"Assignee: (\S+)", jira)
    row = d.get(m[1]) if m else None
    amts = [_amount(jira), _amount(mail), _amount(slack)]   # one source drops the cents: agree within 1 EUR
    due = re.search(r"Due: (\d{4}-\d{2}-\d{2})", jira)
    dl = re.search(r"Deadline interne: (\d{2})/(\d{2})/(\d{4})", notion)
    gap = (dt.date(int(dl[3]), int(dl[2]), int(dl[1])) - dt.date.fromisoformat(due[1])).days if (due and dl) else None
    to = re.search(r"To: (\S+)", mail)
    same = bool(row and to and to[1] == row["email"])
    return dict(assignee=row["name"] if row else None, manager=row["manager"] if row else None,
                amounts_agree=None not in amts and max(amts) - min(amts) <= 1, gap=gap, recipient_is_assignee=same)


def coherence(corpus, arts):
    """Fraction of task facts preserved: the twin answer must be the image of the original answer."""
    ok = tot = 0
    for t in corpus["tasks"]:
        o, w = solve(corpus["arts"], t["key"]), solve(arts, t["key"])
        checks = [w["assignee"] is not None and o["assignee"] is not None,
                  w["manager"] is not None,
                  w["amounts_agree"] == o["amounts_agree"],
                  w["gap"] == o["gap"],
                  w["recipient_is_assignee"] == o["recipient_is_assignee"]]
        ok += sum(checks)
        tot += len(checks)
    return ok, tot
