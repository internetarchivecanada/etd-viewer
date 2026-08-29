#!/usr/bin/env python3
"""Drive capture/fetch_logo.py across every catalog host (xargs-proof)."""
import csv, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
FL = "/Users/brewster/tmp/etd/capture/fetch_logo.py"
def itemid(h): return "etd-catalog-" + re.sub(r"[^a-z0-9]+","-",h.lower()).strip("-")
hosts = []
with open("/Users/brewster/tmp/etd/report/data/disposition.tsv", newline="") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        h = (r.get("host") or "").strip()
        if h and re.match(r"^[a-z0-9.:-]+$", h):
            hosts.append(h)
def one(h):
    out = HERE / "logos" / (itemid(h) + ".png")
    if out.exists(): return "have"
    r = subprocess.run(["timeout","90","python3",FL,f"https://{h}/",str(out)],
                       capture_output=True)
    return "ok" if out.exists() else "none"
from collections import Counter
c = Counter()
with ThreadPoolExecutor(8) as ex:
    for i, res in enumerate(ex.map(one, hosts)):
        c[res] += 1
        if (i+1) % 250 == 0: print(i+1, dict(c), flush=True)
print("DONE", dict(c))
