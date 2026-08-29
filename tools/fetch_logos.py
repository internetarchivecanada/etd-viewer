#!/usr/bin/env python3
"""Fetch a decent logo per repository into logos/<itemid>.png (64px).

Order of preference per host:
  1. live homepage's declared icons: apple-touch-icon (usually 180px),
     og:image, then <link rel=icon> variants -- largest first
  2. live /favicon.ico
  3. the Wayback Machine's archived favicon (web.archive.org/web/2im_/...)
     -- the right source for archive-only repositories
Anything smaller than 16px, unparseable, or blank is rejected.
Resumable: existing logos/<id>.png are skipped.
"""
import csv
import io
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent
LOGOS = HERE / "logos"
DISP = Path("/Users/brewster/tmp/etd/report/data/disposition.tsv")
UA = {"User-Agent": "Mozilla/5.0 (etd-logo-fetch; brewster@archive.org)"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def itemid(host):
    return "etd-catalog-" + re.sub(r"[^a-z0-9]+", "-", host.lower())


def get(url, timeout=20, cap=3 << 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read(cap), r.url


def icon_candidates(host):
    cands = []
    try:
        html, base = get(f"https://{host}/", timeout=15)
        html = html.decode(errors="replace")
        for m in re.finditer(
                r'<link[^>]+rel=["\']?([^"\'>]*icon[^"\'>]*)["\']?[^>]*?'
                r'href=["\']?([^"\'> ]+)', html, re.I):
            rel, href = m.group(1).lower(), m.group(2)
            score = 3 if "apple" in rel else 1
            m2 = re.search(r"sizes=[\"']?(\d+)", m.group(0))
            if m2:
                score += min(int(m2.group(1)), 256) / 64
            cands.append((score, urllib.parse.urljoin(base, href)))
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
                      html, re.I)
        if m:
            cands.append((2, urllib.parse.urljoin(base, m.group(1))))
    except Exception:
        pass
    cands.sort(key=lambda x: -x[0])
    urls = [u for _, u in cands]
    urls.append(f"https://{host}/favicon.ico")
    urls.append(f"http://{host}/favicon.ico")
    urls.append(f"https://web.archive.org/web/2im_/http://{host}/favicon.ico")
    return urls


def save_logo(host):
    out = LOGOS / (itemid(host) + ".png")
    if out.exists():
        return "have"
    for u in icon_candidates(host):
        try:
            raw, _ = get(u, timeout=20)
            im = Image.open(io.BytesIO(raw))
            if hasattr(im, "n_frames") and getattr(im, "n_frames", 1) > 1:
                # .ico: pick the biggest frame
                best = max(getattr(im, "ico", None).sizes()) \
                    if hasattr(im, "ico") and im.ico else im.size
                try:
                    im = im.ico.getimage(best)
                except Exception:
                    pass
            im = im.convert("RGBA")
            if min(im.size) < 16:
                continue
            ex = im.getextrema()
            if all(lo == hi for lo, hi in ex[:3]):     # solid color = blank
                continue
            im.thumbnail((64, 64))
            im.save(out, "PNG", optimize=True)
            return "ok"
        except Exception:
            continue
    return "none"


def main():
    LOGOS.mkdir(exist_ok=True)
    hosts = []
    with open(DISP, newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r.get("host"):
                hosts.append(r["host"])
    print(f"{len(hosts)} hosts")
    from collections import Counter
    c = Counter()
    with ThreadPoolExecutor(16) as ex:
        for i, res in enumerate(ex.map(save_logo, hosts)):
            c[res] += 1
            if (i + 1) % 250 == 0:
                print(f"  {i+1}: {dict(c)}", flush=True)
    print("DONE:", dict(c))


if __name__ == "__main__":
    main()
