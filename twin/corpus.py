"""A synthetic company's exported tools: Gmail, Slack, Jira, Notion (+ Teams in held-out), with the
same people, clients and invoices appearing in many surface forms. No real people or companies."""
import random
from . import ids

FIRST = ["Hélène", "Éric", "Chloé", "Théo", "Léa", "Mathéo", "Inès", "Jérôme", "Thomas", "Camille", "Julien", "Sophie",
         "Amélie", "Nicolas", "Margaux", "Lucas", "Élodie", "Antoine", "Jean-Marc", "Anne-Sophie"]
LAST = ["Martin", "Dubois", "Lefèvre", "Moreau", "Laurent", "Girard", "Bonnet", "Rousseau", "Fontaine", "Chevalier",
        "Mercier", "Blanchard", "Gauthier", "Perrin", "Robin", "Faure"]
CLIENTS = ["Boulangerie Lemoine", "Atelier Vautrin", "Cabinet Delorme", "Transports Fabre", "Maison Rigaud", "Garage Lacombe"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def slug(s):
    return ids.fold(s).lower().replace(" ", "")


def date_fr(d, style):
    import datetime as dt
    x = dt.date.fromordinal(d)
    return {"iso": x.isoformat(), "dmy": x.strftime("%d/%m/%Y"),
            "long": f"{JOURS[x.weekday()]} {x.day} {MOIS[x.month - 1]} {x.year}", "short": f"{x.day} {MOIS[x.month - 1]}"}[style]


def money(v, style):
    whole, cents = f"{v:,.2f}".split(".")
    return {"fr": f"{whole.replace(',', ' ')},{cents} €", "eur": f"{v:.0f} EUR", "en": f"€{v:,.2f}"}[style]


def make(seed, cfg):
    import datetime as dt
    r = random.Random(seed)
    domain = r.choice(["acme-conseil.fr", "vautrin-group.fr", "lumen-studio.fr", "novaterre.fr"])
    fmt = r.choice(["first.last", "flast"])
    people = []
    used = set()
    for i in range(r.randint(10, 18)):
        while True:
            f, l = r.choice(FIRST), r.choice(LAST)
            if (f, l) not in used:
                used.add((f, l)); break
        fs, ls = slug(f), slug(l)
        email = (f"{fs}.{ls}" if fmt == "first.last" else f"{fs[0]}{ls}") + "@" + domain
        people.append(dict(id=f"P{i}", first=f, last=l, email=email, handle=f"{fs}.{ls[0]}", jira=f"{fs[0]}{ls}", manager=None))
    for p in people[1:]:
        p["manager"] = r.choice(people[:max(1, len(people) // 3)])["id"]
    clients = []
    for name in r.sample(CLIENTS, r.randint(3, 5)):
        s = ids.siren(r)
        clients.append(dict(name=name, siren=s, siret=ids.siret(r, s), iban=ids.iban_fr(r), phone=ids.phone(r)))
    proj = r.choice(["ACM", "VTR", "LMN", "NVT"])
    P = {p["id"]: p for p in people}

    def mention(p, k=None):
        forms = cfg["forms"]
        k = k or r.choice(forms)
        return {"full": f"{p['first']} {p['last']}", "first": p["first"], "folded": ids.fold(f"{p['first']} {p['last']}"),
                "initial": f"{p['first'][0]}. {p['last']}", "upper_last": f"{p['last'].upper()} {p['first']}",
                "handle": "@" + p["handle"], "email": p["email"], "comma": f"{p['last']}, {p['first']}",
                "nick": cfg.get("nicks", {}).get(p["first"], p["first"]),
                "initials": "".join(x[0] for x in p["first"].split("-")) + " " + p["last"]}[k]

    arts, tasks = [], []
    base = dt.date(2025, 1, 6).toordinal() + r.randint(0, 200)
    directory = "\n".join(f"| {p['first']} {p['last']} | {p['email']} | @{p['handle']} | {p['jira']} | "
                          f"{(P[p['manager']]['first'] + ' ' + P[p['manager']]['last']) if p['manager'] else '-'} |" for p in people)
    arts.append(dict(id="notion-directory", tool="notion", text="Annuaire de l'équipe\n| Nom | Email | Slack | Jira | Manager |\n" + directory))
    for k in range(r.randint(5, 9)):
        c = r.choice(clients)
        a, b, mgr = r.choice(people[1:]), r.choice(people), None
        key = f"{proj}-{100 + k * 7 + r.randint(0, 6)}"
        amount = round(r.uniform(800, 48_000), 2)
        due = base + r.randint(5, 60)
        deadline = due + r.randint(-5, 10)
        arts.append(dict(id=f"jira-{key}", tool="jira", text=f"{key}: Facture {c['name']}\nAssignee: {a['jira']}\nReporter: {b['jira']}\n"
                         f"Due: {date_fr(due, 'iso')}\nMontant: {money(amount, 'eur')}\nSIRET client: {c['siret']}"))
        arts.append(dict(id=f"gmail-{key}", tool="gmail", text=f"From: {b['first']} {b['last']} <{b['email']}>\nTo: {a['email']}\n"
                         f"Subject: Re: {key} facture {c['name']}\n\nBonjour {mention(a, r.choice(['first', 'nick']) if cfg.get('nicks') else 'first')},\n"
                         f"Le client valide {money(amount, r.choice(['fr', 'en']))} pour le {date_fr(due, r.choice(['long', 'dmy']))}. "
                         f"Merci de voir avec {mention(P[a['manager']])} si besoin.\nIBAN: {c['iban']}\n--\n{mention(b, 'full')}\n{c['phone']}"))
        arts.append(dict(id=f"slack-{key}", tool="slack", text=f"#{proj.lower()}-facturation\n@{b['handle']}: {mention(a)} peux-tu envoyer {key} ? "
                         f"Montant validé {money(amount, 'fr')}, échéance {date_fr(due, 'short')}."))
        arts.append(dict(id=f"notion-{key}", tool="notion", text=f"Suivi {c['name']} (SIREN {c['siren']})\nResponsable: {mention(a, r.choice(['full', 'upper_last', 'initial']))}\n"
                         f"Deadline interne: {date_fr(deadline, 'dmy')}\nContact client: {c['phone']}"))
        if "teams" in cfg.get("tools", []):
            arts.append(dict(id=f"teams-{key}", tool="teams", text=f"[{mention(b, 'comma')}] {mention(a, 'comma')}, le dossier {key} est prêt ? ({c['name']})"))
        tasks.append(dict(key=key, assignee=a["id"], manager=a["manager"], amount_equal=True, gap=deadline - due))
    return dict(seed=seed, domain=domain, people=people, clients=clients, project=proj, arts=arts, tasks=tasks)


DEV = dict(forms=["full", "first", "folded", "initial", "upper_last", "handle", "email"])
