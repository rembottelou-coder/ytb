"""Pick parameters for the next Short, render it, compose it, write metadata.
Usage (from repo root):  python3 pipeline/make_short.py
Outputs: shorts/sNN.mp4 and shorts/sNN.json (title, description, concept)
If a rendered Short exists that is not in shorts/posted.json, it is reused (prints READY at once).
Rendering takes ~30-45 min on 2 CPUs; run it in the background and poll.
Concepts (picked so that none of the last 6 Shorts' concepts repeats (= the last 2 days); force one with CONCEPT=...):
  fit     sliced wooden sphere / slotted block, "Angle X°" (3 clips)
  soft    0% / 50% / 100% SOFT ball on a gold obstacle (3 clips)
  nest    hollow squares / hexagons / circles dropping into each other, tops flush
  dice    colourful dice tumbling into a grid tray
  shapes  shape-sorter block, every piece slides into its hole
  domino  rainbow domino spiral / wave chain reaction
  cloth   gold / silver / silk cloth draping over an object in slow motion
  galton  bell-curve machine (balls through pegs into bins)
  pendulum rainbow pendulum wave (snakes / splits, all line up again at the end, marimba notes)
  sort    ball-sort puzzle solved in 3D (candy balls hop between glass tubes until each is one colour)
  xylo    rainbow xylophone staircase: balls bounce down the bars, every hit plays a note, all end in a gold tray
  boxfill rainbow ball rain filling a glass box / hexagon / jar in layers, MULTI-ANGLE (wide, top-down, close-up)  [24/11]
  funnel  striped balls spiral down a gravity-well funnel and stack into a glass tube, MULTI-ANGLE  [24/11]
  tetris  candy tetrominoes glide, rotate and drop into an upright board until it is filled with no gap, rows flash, MULTI-ANGLE  [26/11]
"""
import os, sys, json, random, subprocess, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "pipeline")
os.chdir(P)
os.makedirs(os.path.join(ROOT, "shorts"), exist_ok=True)

existing = sorted(glob.glob(os.path.join(ROOT, "shorts", "s*.mp4")), key=lambda q: int(os.path.basename(q)[1:-4]))
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
ALL = ["fit", "soft", "nest", "dice", "shapes", "domino", "cloth", "galton", "pendulum", "sort", "xylo", "boxfill", "funnel", "tetris"]
WEIGHTS = {"fit": 1, "soft": 1, "nest": 1.2, "dice": 1.2, "shapes": 1.1, "domino": 1.1, "cloth": 1, "galton": 1, "pendulum": 1.2, "sort": 1.2, "xylo": 1.2, "boxfill": 1.4, "funnel": 1.4, "tetris": 1.4}
hist = []
for j in sorted(glob.glob(os.path.join(ROOT, "shorts", "s*.json")), key=lambda q: int(os.path.basename(q)[1:-5]))[-6:]:
    try:
        hist.append(json.load(open(j)).get("concept"))
    except Exception:
        pass
concept = os.environ.get("CONCEPT")
if not concept:
    cands = [c for c in ALL if c not in hist] or ALL
    # prefer the concepts used least often overall (user request), then weighted random among them
    uses = {c: 0 for c in ALL}
    for j in glob.glob(os.path.join(ROOT, "shorts", "s*.json")):
        try:
            uses[json.load(open(j)).get("concept")] += 1
        except Exception:
            pass
    low = min(uses[c] for c in cands)
    cands = [c for c in cands if uses[c] == low]
    concept = rng.choices(cands, weights=[WEIGHTS[c] for c in cands])[0]
print("concept", concept, "history", hist, flush=True)

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
elif concept == "soft":
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

else:
    seed = rng.randint(1, 999)
    sd = os.path.join(P, "shorts", name)
    os.makedirs(sd, exist_ok=True)
    subprocess.run(["python3", f"c_{concept}.py", sd, str(seed), os.environ.get("RES", "0.4"), os.environ.get("SAMPLES", "10")], check=True)
    meta = json.load(open(os.path.join(sd, "events.json")))["meta"]
    subprocess.run(["python3", "compose_generic.py", sd], check=True)
    if concept == "nest":
        what = {4: "Squares", 6: "Hexagons", 64: "Circles"}[meta["shape"]]
        title = rng.choice([f"{what} inside {what.lower()}… perfect fit 😮‍💨 #satisfying #shorts",
                            f"{meta['n']} {what.lower()}, ONE perfect stack 🌈 #satisfying #shorts",
                            f"Wait for the smallest one 🤏 #satisfying #perfectfit #shorts"])
        desc = f"{meta['n']} hollow {what.lower()} drop into each other and end perfectly flush. 3D animation.\n\n"
    elif concept == "dice":
        title = {"six": "Every dice lands on SIX 🎲 #satisfying #shorts",
                 "count": "1, 2, 3, 4, 5, 6… perfectly in order 🎲 #satisfying #shorts",
                 "random": rng.choice(["Dice fitting perfectly into the tray 🎲 #satisfying #shorts",
                                       "So satisfying: every dice finds its slot 🎲 #shorts"])}[meta["faces"]]
        desc = f"{meta['grid']}x{meta['grid']} colourful dice tumbling into a tray, one perfect fit after another. 3D animation.\n\n"
    elif concept == "shapes":
        title = rng.choice(["Every shape finds its hole ⭐❤️🔺 #satisfying #shorts",
                            "The most satisfying shape sorter 🧩 #satisfying #shorts",
                            "Star, heart, hexagon… all PERFECT FIT ✅ #shorts"])
        desc = "Square, circle, triangle, star, hexagon and heart pieces sliding into their holes. 3D animation.\n\n"
    elif concept == "domino":
        title = rng.choice([f"{meta['n']} rainbow dominoes 🌈 wait for it… #satisfying #shorts",
                            "Rainbow domino chain reaction 🌈 #satisfying #dominoes #shorts",
                            "The most satisfying domino spiral 🌀 #shorts"])
        desc = f"{meta['n']} rainbow dominoes in a {meta['path']} — 3D physics chain reaction.\n\n"
    elif concept == "cloth":
        cl = {"gold": "Gold", "silver": "Silver", "silk": "Silk", "rainbow": "Rainbow"}[meta["cloth"]]
        title = rng.choice([f"{cl} cloth vs {meta['obj']} ✨ #satisfying #clothsimulation #shorts",
                            f"Slow-motion {cl.lower()} cloth wrapping a {meta['obj']} 😍 #satisfying #shorts",
                            f"So smooth… {cl.lower()} cloth simulation ✨ #shorts"])
        desc = f"A {cl.lower()} cloth falls in slow motion and wraps a glossy {meta['obj']}. 3D cloth simulation.\n\n"
    elif concept == "pendulum":
        title = rng.choice([f"{meta['n']} balls, one perfect wave 🌈 #satisfying #physics #shorts",
                            "Wait for them to line up again… 😮‍💨 #satisfying #shorts",
                            "Pendulum wave hypnosis 🌀 #satisfying #physics #shorts"])
        desc = (f"{meta['n']} rainbow pendulums with tuned lengths drift into snakes, splits and swirls, "
                f"then line up perfectly again after {meta['cycle']:.0f} s. Every ball plays a note. 3D animation.\n\n")
    elif concept == "sort":
        title = rng.choice([f"Ball sort solved in {meta['moves']} moves 🧪 #satisfying #shorts",
                            "Every ball back to its colour 🌈 #satisfying #shorts",
                            "The most satisfying ball sort puzzle 🧪 #oddlysatisfying #shorts"])
        desc = (f"{meta['colors']} colours, {meta['colors'] + 2} glass tubes, {meta['moves']} moves — "
                "every candy ball hops home until each tube is one colour. 3D animation.\n\n")
    elif concept == "xylo":
        title = rng.choice([f"{meta['balls']} balls play a xylophone staircase 🎶 #satisfying #shorts",
                            "Every bounce is a note 🎵🌈 #satisfying #asmr #shorts",
                            "Rainbow xylophone stairs… turn the sound ON 🔊 #satisfying #shorts"])
        desc = (f"{meta['balls']} candy balls bounce down {meta['bars']} rainbow xylophone bars — every hit plays its note, "
                "the melodies overlap, and each ball lands in its slot. 3D animation with sound.\n\n")
    elif concept == "boxfill":
        what = {"box": "glass box", "hex": "hexagon jar", "jar": "glass jar"}[meta["shape"]]
        if meta["mode"] == "bands":
            title = rng.choice([f"{meta['n']} balls fill a {what} in rainbow layers 🌈 #satisfying #shorts",
                                f"Rainbow ball rain from every angle 🌈📦 #satisfying #shorts",
                                f"Filling a {what} to the brim… 😮‍💨🌈 #satisfying #asmr #shorts"])
        else:
            title = rng.choice([f"{meta['n']} candy balls vs one {what} 🍬 #satisfying #shorts",
                                f"Candy ball rain fills the {what} 🍬📦 #satisfying #asmr #shorts",
                                "Watch it fill up… from every angle 👀 #satisfying #shorts"])
        desc = (f"{meta['n']} glossy candy balls rain into a {what} and fill it to the brim — seen from above, "
                "from the side and up close through the glass. 3D physics simulation with sound.\n\n")
    elif concept == "funnel":
        title = rng.choice([f"{meta['n']} balls spiral down the funnel 🌀🌈 #satisfying #shorts",
                            "Round and round… into the tube 🌀 #satisfying #asmr #shorts",
                            "The most hypnotic coin-funnel ever 🌀😵‍💫 #satisfying #shorts"])
        desc = (f"{meta['n']} striped candy balls roll round and round a gravity-well funnel, faster and faster, "
                "then drop one by one into a glass tube that ends up perfectly full. 3D animation.\n\n")
    elif concept == "tetris":
        title = rng.choice([f"{meta['n']} Tetris pieces, ZERO gaps 🧩🌈 #satisfying #shorts",
                            "The most satisfying Tetris ever… wait for the last piece 🧩 #satisfying #shorts",
                            f"Filling a {meta['cols']}x{meta['rows']} board perfectly 🧩✨ #satisfying #asmr #shorts"])
        desc = (f"{meta['n']} glossy candy Tetris pieces glide in, spin and drop into a{'n' if meta['cols'] == 8 else ''} {meta['cols']}x{meta['rows']} board "
                "until it is filled with not a single gap — then every row lights up. 3D animation with sound.\n\n")
    else:  # galton
        title = rng.choice(["The bell curve machine never fails 🎯 #satisfying #physics #shorts",
                            f"{meta['balls']} balls, one perfect bell curve 📈 #satisfying #shorts",
                            "Galton board: watch the curve appear 🤯 #shorts"])
        desc = f"{meta['balls']} balls bounce through a peg board and stack into a bell curve. 3D animation.\n\n"
    meta = {k: v for k, v in meta.items() if k not in ("caption",)}
    meta.pop("concept", None)

# never reuse a title (user feedback 17/11): fall back to generic variants if the picked one already exists
prev_titles = set()
for j in glob.glob(os.path.join(ROOT, "shorts", "s*.json")):
    if os.path.basename(j) != name + ".json":
        try:
            prev_titles.add(json.load(open(j))["title"])
        except Exception:
            pass
if title in prev_titles:
    for alt in ["Wait for the ending 😮‍💨 #satisfying #shorts", "Turn the sound ON 🔊✨ #satisfying #asmr #shorts",
                "Your brain will love this 🧠✨ #satisfying #shorts", "Watch till the end 👀🌈 #satisfying #shorts",
                f"Satisfying 3D {concept} #{idx} ✨ #shorts"]:
        if alt not in prev_titles:
            title = alt
            break
desc += "Subscribe to @SatisFit3D for more satisfying 3D simulations!\n#satisfying #oddlysatisfying #3danimation #physics #asmr #shorts"
shutil.copy(os.path.join(sd, "final.mp4"), os.path.join(ROOT, "shorts", name + ".mp4"))
json.dump(dict(name=name, concept=concept, title=title, description=desc, **meta),
          open(os.path.join(ROOT, "shorts", name + ".json"), "w"), ensure_ascii=False, indent=1)
print("READY", name, title)
