"""Pick parameters for the next Short, render it, compose it, write metadata.
Usage (from repo root):  python3 pipeline/make_short.py            -> renders next index
Outputs: shorts/sNN.mp4 and shorts/sNN.json (title, description)
Rendering takes ~25-35 min on 2 CPUs; run it in the background and poll.
"""
import os, sys, json, random, subprocess, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "pipeline")
os.chdir(P)

existing = sorted(glob.glob(os.path.join(ROOT, "shorts", "s*.mp4")))
# If a Short is already rendered but not yet posted, use it (buffer) instead of rendering.
try:
    posted = {p["name"] for p in json.load(open(os.path.join(ROOT, "shorts", "posted.json")))}
except Exception:
    posted = set()
for mp4 in existing:
    n = os.path.basename(mp4)[:-4]
    if n not in posted and os.path.exists(mp4[:-4] + ".json") and not os.environ.get("IDX"):
        print("READY", n, json.load(open(mp4[:-4] + ".json"))["title"], "(already rendered)")
        sys.exit(0)
idx = int(os.environ.get("IDX", len(existing) + 1))
name = "s%02d" % idx
rng = random.Random(idx * 7919)

palettes = ["oak", "walnut", "maple", "cherry"]
pal = palettes[idx % len(palettes)]
nslab = rng.choice([7, 9, 9, 11])
a1 = rng.choice([25, 30, 35, 40, 45, 50, 60, 75])
a2 = rng.choice([2, 3, 5, 8, 10, 12, 15])
seed = rng.randint(1, 999)
angles = [a1, a2, 0]

work = os.path.join(P, "work")
os.makedirs(work, exist_ok=True)
env = dict(os.environ)
cmd = ["bash", "render_short.sh", name, pal, str(seed), str(nslab)] + [str(a) for a in angles]
subprocess.run(cmd, check=True, env=env)
sd = os.path.join(P, "shorts", name)
subprocess.run(["python3", "compose.py", sd, "Angle"] + [f"{a}°" for a in angles], check=True)

wood = {"oak": "oak", "walnut": "walnut", "maple": "maple", "cherry": "cherry wood"}[pal]
titles = [
    f"Only ONE angle fits perfectly 🪵 #satisfying #3d #shorts",
    f"{a1}° vs {a2}° vs 0°… which one fits? 🤯 #satisfying #shorts",
    f"Wait for the PERFECT FIT 😮‍💨 #satisfying #3danimation #shorts",
    f"This {wood} sphere needs the exact angle 🎯 #satisfying #shorts",
    f"So close at {a2}°… #satisfying #oddlysatisfying #shorts",
]
title = titles[idx % len(titles)]
desc = (f"{a1}°? Crash. {a2}°? Still no. 0°... PERFECT FIT ✅\n"
        f"A sliced {wood} sphere ({nslab} slices) dropped into a slotted block — 3D physics simulation.\n\n"
        "Subscribe to @SatisFit3D for more satisfying fits!\n"
        "#satisfying #oddlysatisfying #3danimation #physics #asmr #shorts")
os.makedirs(os.path.join(ROOT, "shorts"), exist_ok=True)
import shutil
shutil.copy(os.path.join(sd, "final.mp4"), os.path.join(ROOT, "shorts", name + ".mp4"))
json.dump({"name": name, "title": title, "description": desc, "palette": pal, "angles": angles, "nslab": nslab},
          open(os.path.join(ROOT, "shorts", name + ".json"), "w"), ensure_ascii=False, indent=1)
print("READY", name, title)
