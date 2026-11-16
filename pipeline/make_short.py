"""Pick parameters for the next Short, render it, compose it, write metadata.
Usage (from repo root):  python3 pipeline/make_short.py
Outputs: shorts/sNN.mp4 and shorts/sNN.json (title, description, concept)
If a rendered Short exists that is not in shorts/posted.json, it is reused (prints READY at once).
Rendering takes ~30-45 min on 2 CPUs; run it in the background and poll.
Concepts alternate: "fit" (sliced wooden sphere / slotted block, Angle X°)
                    "soft" (0% / 50% / 100% SOFT ball on a gold obstacle, marble pedestal)
"""
import os, sys, json, random, subprocess, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "pipeline")
os.chdir(P)
os.makedirs(os.path.join(ROOT, "shorts"), exist_ok=True)

existing = sorted(glob.glob(os.path.join(ROOT, "shorts", "s*.mp4")))
try:
    posted = {p["name"] for p in json.load(open(os.path.join(ROOT, "shorts", "posted.json")))}
except Exception:
    posted = set()
if not os.environ.get("IDX"):
    for mp4 in existing:
        n = os.path.basename(mp4)[:-4]
        if n not in posted and os.path.exists(mp4[:-4] + ".json"):
            print("READY", n, json.load(open(mp4[:-4] + ".json"))["title"], "(already rendered)")
            sys.exit(0)

idx = int(os.environ.get("IDX", len(existing) + 1))
name = "s%02d" % idx
rng = random.Random(idx * 7919)
concept = os.environ.get("CONCEPT") or ("soft" if idx % 2 == 0 else "fit")

if concept == "fit":
    pal = ["oak", "walnut", "maple", "cherry"][idx % 4]
    nslab = rng.choice([7, 9, 9, 11])
    a1 = rng.choice([25, 30, 35, 40, 45, 50, 60, 75]); a2 = rng.choice([2, 3, 5, 8, 10, 12, 15])
    seed = rng.randint(1, 999); angles = [a1, a2, 0]
    subprocess.run(["bash", "render_short.sh", name, pal, str(seed), str(nslab)] + [str(a) for a in angles], check=True)
    sd = os.path.join(P, "shorts", name)
    subprocess.run(["python3", "compose.py", sd, "Angle"] + [f"{a}°" for a in angles], check=True)
    wood = {"oak": "oak", "walnut": "walnut", "maple": "maple", "cherry": "cherry wood"}[pal]
    title = rng.choice([
        "Only ONE angle fits perfectly 🪵 #satisfying #3d #shorts",
        f"{a1}° vs {a2}° vs 0°… which one fits? 🤯 #satisfying #shorts",
        "Wait for the PERFECT FIT 😮‍💨 #satisfying #3danimation #shorts",
        f"This {wood} sphere needs the exact angle 🎯 #satisfying #shorts",
        f"So close at {a2}°… #satisfying #oddlysatisfying #shorts"])
    desc = (f"{a1}°? Crash. {a2}°? Still no. 0°... PERFECT FIT ✅\n"
            f"A sliced {wood} sphere ({nslab} slices) dropped into a slotted block — 3D physics simulation.\n\n")
    meta = {"palette": pal, "angles": angles, "nslab": nslab}
else:
    obst = rng.choice(["cone", "cone", "pipe", "spikes"])
    ball = rng.choice(["marble", "marble", "gold", "pink", "mint", "silver"])
    seed = rng.randint(1, 999)
    subprocess.run(["bash", "render_soft.sh", name, str(seed), obst, ball, "0", "50", "100"], check=True)
    sd = os.path.join(P, "shorts", name)
    subprocess.run(["python3", "compose_soft.py", sd, "SOFT"], check=True)
    obj = {"cone": "Cone", "pipe": "Pipe", "spikes": "Spikes"}[obst]
    title = rng.choice([
        f"0% vs 100% Soft Ball x {obj} 🫠 #satisfying #3d #shorts",
        f"Which one is the most satisfying? 0% vs 100% SOFT #shorts",
        f"Soft body vs gold {obst} 😳 #satisfying #softbody #shorts",
        f"Hard vs Soft ball on a {obst}… wait for 100% 🫠 #shorts"])
    desc = (f"0% SOFT, 50% SOFT, 100% SOFT — a {ball} ball dropped on a gold {obst}. Soft body 3D physics simulation.\n\n")
    meta = {"obstacle": obst, "ball": ball}

desc += "Subscribe to @SatisFit3D for more satisfying 3D simulations!\n#satisfying #oddlysatisfying #3danimation #physics #asmr #shorts"
shutil.copy(os.path.join(sd, "final.mp4"), os.path.join(ROOT, "shorts", name + ".mp4"))
json.dump(dict(name=name, concept=concept, title=title, description=desc, **meta),
          open(os.path.join(ROOT, "shorts", name + ".json"), "w"), ensure_ascii=False, indent=1)
print("READY", name, title)
