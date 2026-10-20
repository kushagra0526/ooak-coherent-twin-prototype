import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

r = json.load(open("out/heldout_first_run.json", encoding="utf-8"))["results"]
names = {"regex": "regex-only\nredaction", "perdoc": "per-document\npseudonyms", "twin": "company-wide\ntwin (this)"}
col = ["#bbb", "#888", "#2a7"]
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].bar(list(names.values()), [100 * r[m]["leaked"] / r[m]["original"] for m in names], color=col); ax[0].set_title("% of identifier mentions that survive (leaks)")
ax[1].bar(list(names.values()), [100 * r[m]["ok"] / r[m]["checks"] for m in names], color=col); ax[1].set_title("% of cross-tool task facts preserved")
fig.suptitle("Held-out, first run: 20 synthetic companies incl. Teams exports, nicknames, hyphen initials")
fig.tight_layout(); fig.savefig("docs/result.png", dpi=110)
