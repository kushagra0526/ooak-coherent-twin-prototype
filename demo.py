"""One synthetic company: the same invoice thread in Jira, Gmail, Slack and Notion, three ways."""
import sys
from twin import corpus, anonymize, audit

sys.stdout.reconfigure(encoding="utf-8")
c = corpus.make(3, corpus.DEV)
key = c["tasks"][0]["key"]
for mode, title in (("original", "ORIGINAL (never leaves the company)"), ("perdoc", "per-document pseudonyms"),
                    ("regex", "regex-only redaction"), ("twin", "company-wide twin (this)")):
    arts = c["arts"] if mode == "original" else anonymize.anonymize(c, mode)
    A = {a["id"]: a["text"] for a in arts}
    print("=" * 96 + f"\n{title}")
    print("  jira : " + A[f"jira-{key}"].split("\n")[1] + " | " + A[f"jira-{key}"].split("\n")[4])
    print("  gmail: " + A[f"gmail-{key}"].split("\n")[1] + " | " + A[f"gmail-{key}"].split("\n")[5][:70])
    print("  slack: " + A[f"slack-{key}"].split("\n")[1][:90])
    s = audit.solve(arts, key)
    print(f"  task 'who owns {key}, who is their manager, do the amounts agree?' -> {s['assignee']} / {s['manager']} / {s['amounts_agree']}")
    if mode != "original":
        a, b, found = audit.leaks(c, arts, corpus.DEV)
        ok, tot = audit.coherence(c, arts)
        print(f"  whole company: {a} of {b} identifier mentions survive; {ok}/{tot} cross-tool task facts preserved")
