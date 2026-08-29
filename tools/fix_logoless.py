#!/usr/bin/env python3
"""Finish the job: every etd-catalog item without a logo gets our best shot.

1. Enumerate all items in etd-catalogs; subtract those we uploaded to.
2. For each remainder: resolve its host (originalurl), hunt a logo via the
   Wayback Machine (archived homepage HTML -> brand/icon candidates, URL
   variants) -- works for dead hosts and bot-hostile live ones alike.
3. Upload finds as logo.png; report the final logoless count.
"""
import io, json, re, subprocess, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
import internetarchive

HERE = Path(__file__).resolve().parent.parent
LOGOS = HERE / "logos"
LEDGER = HERE / "tools" / "logo_upload_ledger.jsonl"
UA = {"User-Agent": "Mozilla/5.0 (etd-logo-fix; brewster@archive.org)"}
VENDOR = re.compile(r"atmire|dspace|eprints|bepress|powered|wayback|archive\.org", re.I)

def get(u, timeout=30, cap=4<<20):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(cap)

def wb_logo(host, out):
    html = None
    for v in (f"http://{host}/", f"https://{host}/",
              f"http://www.{host}/", f"https://www.{host}/"):
        try:
            html = get(f"https://web.archive.org/web/2id_/{v}").decode(errors="replace")
            break
        except Exception:
            continue
    if html is None: return False
    cands = []
    for pat in (r'rel="apple-touch-icon[^"]*"[^>]*href="([^"]+)"',
                r'<img[^>]+(?:id|class)="[^"]*(?:brand|site-logo|header-logo|banner)[^"]*"[^>]*src="([^"]+)"',
                r'<img[^>]+src="([^"]*logo[^"]*\.(?:png|svg|jpg|jpeg|gif|webp))"',
                r'property="og:image"\s+content="([^"]+)"',
                r'<link[^>]+rel="(?:shortcut )?icon"[^>]*href="([^"]+)"'):
        for m in re.finditer(pat, html, re.I):
            u = urllib.parse.urljoin(f"http://{host}/", m.group(1))
            if u.startswith("http") and not VENDOR.search(u):
                cands.append(u)
    cands.append(f"http://{host}/favicon.ico")
    for cu in cands:
        try:
            raw = get(f"https://web.archive.org/web/2im_/{cu}")
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            if min(im.size) < 16: continue
            ex = im.getextrema()
            if all(lo == hi for lo, hi in ex[:3]): continue
            im.thumbnail((256, 256)); im.save(out, "PNG", optimize=True)
            return True
        except Exception:
            continue
    return False

def main():
    # one query: items with no PNG file at all; minus items whose fetched
    # logo sits on disk awaiting the (parallel) uploader
    r = json.loads(subprocess.run(
        ["curl","-s","https://archive.org/advancedsearch.php?q=collection%3Aetd-catalogs%20AND%20NOT%20format%3APNG&fl%5B%5D=identifier&rows=10000&output=json"],
        capture_output=True, text=True).stdout)
    nopng = [d["identifier"] for d in r["response"]["docs"]
             if d["identifier"].startswith("etd-catalog-")]
    missing = [i for i in nopng if not (LOGOS / (i + ".png")).exists()]
    print(f"{len(nopng)} items lack a PNG; {len(missing)} need a wayback "
          f"hunt (rest are queued for the parallel uploader)")
    from collections import Counter
    c = Counter()
    def fix(ident):
        out = LOGOS / (ident + ".png")
        if not out.exists():
            try:
                ou = (internetarchive.get_item(ident).metadata or {}).get("originalurl") or ""
                host = urllib.parse.urlsplit(ou).netloc
            except Exception:
                return "meta-err"
            if not host: return "no-host"
            if not wb_logo(host, out): return "not-found"
        try:
            rr = internetarchive.get_item(ident).upload(
                files={"logo.png": str(out)}, retries=3)
            return "uploaded" if all(getattr(x,"status_code",0)==200 for x in rr) else "upload-fail"
        except Exception:
            return "upload-fail"
    with ThreadPoolExecutor(8) as ex:
        for i, res in enumerate(ex.map(fix, missing)):
            c[res] += 1
            if (i+1) % 50 == 0: print(i+1, dict(c), flush=True)
    print("DONE", dict(c))
    print(f"final logoless: {c['not-found']+c['no-host']+c['meta-err']+c['upload-fail']}")

if __name__ == "__main__":
    main()
