#!/usr/bin/env python3
"""Logos for dead repositories, from the Wayback Machine.

For each 2023-rescue host without a logo: fetch the archived homepage
(raw HTML via /web/2id_/), extract logo candidates (same patterns as
capture/fetch_logo.py), fetch each via /web/2im_/, save 64-256px PNG.
"""
import io, json, re, subprocess, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
LOGOS = HERE / "logos"
UA = {"User-Agent": "Mozilla/5.0 (etd-wayback-logo; brewster@archive.org)"}
VENDOR = re.compile(r"atmire|dspace|eprints|bepress|powered|wayback|archive.org", re.I)

def get(u, timeout=30, cap=4<<20):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(cap)

def candidates(html, host):
    base = f"http://{host}/"
    pats = [r'rel="apple-touch-icon[^"]*"[^>]*href="([^"]+)"',
            r'<img[^>]+(?:id|class)="[^"]*(?:brand|site-logo|header-logo|banner)[^"]*"[^>]*src="([^"]+)"',
            r'<img[^>]+src="([^"]*logo[^"]*\.(?:png|svg|jpg|jpeg|gif|webp))"',
            r'property="og:image"\s+content="([^"]+)"',
            r'content="([^"]+)"\s+property="og:image"',
            r'<link[^>]+rel="(?:shortcut )?icon"[^>]*href="([^"]+)"']
    for pat in pats:
        for m in re.finditer(pat, html, re.I):
            u = urllib.parse.urljoin(base, m.group(1))
            if u.startswith("http") and not VENDOR.search(u):
                yield u
    yield base + "favicon.ico"

def one(host):
    ident = "etd-catalog-" + re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")
    out = LOGOS / (ident + ".png")
    if out.exists(): return "have"
    try:
        html = get(f"https://web.archive.org/web/2id_/http://{host}/").decode(errors="replace")
    except Exception:
        return "no-capture"
    for cu in candidates(html, host):
        try:
            raw = get(f"https://web.archive.org/web/2im_/{cu}")
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            if min(im.size) < 16: continue
            ex = im.getextrema()
            if all(lo == hi for lo, hi in ex[:3]): continue
            im.thumbnail((256, 256))
            im.save(out, "PNG", optimize=True)
            return "ok"
        except Exception:
            continue
    return "none"

def main():
    # rescue hosts = items titled "(2023 rescue)"
    r = json.loads(subprocess.run(
        ["curl", "-s", "https://archive.org/advancedsearch.php?q=collection%3Aetd-catalogs%20AND%20title%3A(2023)&fl%5B%5D=identifier&rows=1000&output=json"],
        capture_output=True, text=True).stdout)
    ids = [d["identifier"] for d in r["response"]["docs"]]
    hosts = [i[len("etd-catalog-"):].replace("-", ".") for i in ids]
    # dashes are ambiguous (dots vs real dashes); recover true host from item metadata originalurl when needed
    import internetarchive
    from collections import Counter
    c = Counter()
    def resolve_and_fetch(ident):
        try:
            it = internetarchive.get_item(ident)
            ou = (it.metadata or {}).get("originalurl") or ""
            host = urllib.parse.urlsplit(ou).netloc or None
            if not host: return "no-host"
            return one(host if not host.startswith("www.") else host)
        except Exception as e:
            return "err"
    with ThreadPoolExecutor(8) as ex:
        for i, res in enumerate(ex.map(resolve_and_fetch, ids)):
            c[res] += 1
            if (i+1) % 50 == 0: print(i+1, dict(c), flush=True)
    print("DONE", dict(c))

if __name__ == "__main__":
    main()
