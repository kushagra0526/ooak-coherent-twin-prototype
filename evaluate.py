"""Leaks and cross-tool coherence for three anonymizers.  python evaluate.py [dev|heldout] [out.json]"""
import json, sys
from collections import Counter
from twin import corpus, anonymize, audit

MODES = {"regex": "regex-only redaction", "perdoc": "per-document pseudonyms", "twin": "company-wide twin (this)"}


def run(which):
    if which == "heldout":
        h = json.load(open("heldout/config.json", encoding="utf-8"))
        seeds, cfg = range(h["seeds"][0], h["seeds"][1] + 1), h["cfg"]
    else:
        seeds, cfg = range(1, 21), corpus.DEV
    res = {m: dict(leaked=0, original=0, ok=0, checks=0) for m in MODES}
    leaked_kinds = Counter()
    for s in seeds:
        c = corpus.make(s, cfg)
        for m in MODES:
            arts = anonymize.anonymize(c, m)
            a, b, found = audit.leaks(c, arts, cfg)
            ok, tot = audit.coherence(c, arts)
            r = res[m]
            r["leaked"] += a; r["original"] += b; r["ok"] += ok; r["checks"] += tot
            if m == "twin":
                leaked_kinds.update(found)
    return dict(set=which, companies=len(seeds), results=res, twin_leaks=dict(leaked_kinds.most_common(30)))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    r = run(which)
    print(f"{which}: {r['companies']} synthetic companies")
    for m, x in r["results"].items():
        print(f"  {MODES[m]:28s} identifier mentions surviving {x['leaked']:5d}/{x['original']}   cross-tool task facts preserved {x['ok']:4d}/{x['checks']}")
    print("  what leaked through the twin:", r["twin_leaks"])
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
