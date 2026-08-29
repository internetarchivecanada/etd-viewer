#!/bin/bash
# Reuse the etd repo's quality logo pipeline for the viewer's logos/ dir.
cd "$(dirname "$0")/.."
FL=/Users/brewster/tmp/etd/capture/fetch_logo.py
cut -f1 /Users/brewster/tmp/etd/report/data/disposition.tsv | tail -n +2 | \
while read h; do
  id="etd-catalog-$(echo "$h" | tr -c 'a-z0-9' '-' | sed 's/-*$//;s/--*/-/g')"
  [ -s "logos/$id.png" ] && continue
  echo "$h $id"
done | xargs -P 8 -L1 bash -c 'timeout 90 python3 '"$FL"' "https://$0/" "logos/$1.png" >/dev/null 2>&1 || true'
echo DONE $(ls logos | wc -l)
