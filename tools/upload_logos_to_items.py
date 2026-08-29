#!/usr/bin/env python3
"""Upload fetched logos into their etd-catalog items (as logo.png).

Skips items that already have a logo file or an __ia_thumb; ledgered and
resumable. The derive step then builds the item tile, improving
archive.org pages, services/img, and the viewer everywhere at once.
"""
import json, time
from pathlib import Path
import internetarchive
HERE = Path(__file__).resolve().parent.parent
LOGOS = HERE / "logos"
LEDGER = HERE / "tools" / "logo_upload_ledger.jsonl"
done = set()
if LEDGER.exists():
    for ln in open(LEDGER):
        try: done.add(json.loads(ln)["item"])
        except Exception: pass
todo = sorted(p.stem for p in LOGOS.glob("etd-catalog-*.png"))
print(f"{len(todo)} logos on disk, {len(done)} already processed")
ok = skip = miss = fail = 0
for ident in todo:
    if ident in done: continue
    try:
        it = internetarchive.get_item(ident)
        if not it.exists:
            miss += 1; res = "no-item"
        elif any(f.get("name") in ("logo.png", "logo.jpg")
                 for f in (it.files or [])):
            skip += 1; res = "has-logo"
        else:
            r = it.upload(files={"logo.png": str(LOGOS / (ident + ".png"))},
                          retries=3)
            good = all(getattr(x, "status_code", 0) == 200 for x in r)
            ok += good; fail += (not good)
            res = "uploaded" if good else "upload-failed"
            time.sleep(0.5)
    except Exception as e:
        fail += 1; res = f"err:{type(e).__name__}"
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"item": ident, "res": res}) + "\n")
    n = ok + skip + miss + fail
    if n % 100 == 0:
        print(f"{n}: up {ok}, had {skip}, no-item {miss}, fail {fail}", flush=True)
print(f"DONE: uploaded {ok}, had-logo {skip}, no-item {miss}, failed {fail}")
