"""Merge view counts (and optional 'stayed' %) read from YouTube Studio into shorts/perf.json.
make_short.py uses perf.json to bring back the concepts that perform best on the channel.

Usage: python3 pipeline/update_perf.py rows.json
rows.json = [[title, views], ...]  or  [[title, views, stayed_percent], ...]
(get it in Studio > Contenu > Shorts with the JS snippet in RUNBOOK.md; titles are matched to shorts/sNN.json)
"""
import sys, os, json, glob, re, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pf = os.path.join(ROOT, "shorts", "perf.json")
perf = json.load(open(pf)) if os.path.exists(pf) else {"shorts": {}}
rows = json.load(open(sys.argv[1]))
norm = lambda t: re.sub(r"\s+", " ", t).strip().lower()
by_title = {}
for j in glob.glob(os.path.join(ROOT, "shorts", "s[0-9]*.json")):
    d = json.load(open(j))
    by_title[norm(d["title"])[:40]] = (d["name"], d.get("concept"))
n = 0
for r in rows:
    key = norm(r[0])[:40]
    hit = by_title.get(key) or next((v for k, v in by_title.items() if k.startswith(key[:30])), None)
    if not hit or r[1] is None:
        continue
    name, concept = hit
    e = perf["shorts"].setdefault(name, {"concept": concept})
    e["views"] = int(str(r[1]).replace(" ", "").replace("\xa0", "").replace(" ", ""))
    if len(r) > 2 and r[2] is not None:
        e["stayed"] = float(str(r[2]).replace(",", "."))
    n += 1
perf["updated"] = datetime.date.today().isoformat()
json.dump(perf, open(pf, "w"), indent=1, ensure_ascii=False)
print("updated", n, "shorts in", pf)
