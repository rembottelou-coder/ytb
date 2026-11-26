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
  ring    ball bounces inside spinning neon rings with gaps, note on every bounce, rings pop as it escapes  [26/11]
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
# 26/11 retention: the first frame carries a question / challenge (hits: "So close at 5°…", "Every bounce is a note",
# "Pure chaos becomes a perfect curve", "Every dice lands on SIX"); plain descriptions got swiped away. No emoji (font).
HOOKS = {
    "nest": ["Will the last one fit?", "Wait for the smallest one", "Perfect fit?"],
    "dice": ["Only sixes?", "Will they ALL fit?", "Wait for the last die"],
    "shapes": ["Will every shape fit?", "Wait for the heart...", "Which one won't fit?"],
    "domino": ["Will they ALL fall?", "Don't look away...", "Wait for the last one"],
    "cloth": ["Watch the cloth...", "So smooth...", "Wait for it..."],
    "galton": ["Chaos... or order?", "Watch the curve appear", "Pure chaos... or not?"],
    "pendulum": ["Wait for them to line up", "Chaos... then perfect order", "Watch closely..."],
    "sort": ["Can you solve it faster?", "Every colour goes home", "Wait for the last tube"],
    "xylo": ["Sound ON", "Every bounce is a note", "Listen to the melody..."],
    "boxfill": ["Will it fill to the top?", "Can it hold them all?", "Wait till it's full"],
    "funnel": ["Which colour lands last?", "Round and round...", "Wait for the last one"],
    "tetris": ["Zero gaps?", "Will the last piece fit?", "Perfect fit?"],
    "ring": ["Will it escape?", "Every bounce is a note", "Wait for it..."],
}
ALL = ["fit", "soft", "nest", "dice", "shapes", "domino", "cloth", "galton", "pendulum", "sort", "xylo", "boxfill", "funnel", "tetris", "ring"]
WEIGHTS = {"fit": 1, "soft": 1, "nest": 1.2, "dice": 1.2, "shapes": 1.1, "domino": 1.1, "cloth": 1, "galton": 1, "pendulum": 1.2, "sort": 1.2, "xylo": 1.2, "boxfill": 1.4, "funnel": 1.4, "tetris": 1.4, "ring": 1.6}
def perf_factors():
    """concept -> multiplier from shorts/stats.json (views + 'stayed' %), clipped to [0.5, 2.5]; unknown -> 1."""
    import math
    try:
        st = json.load(open(os.path.join(ROOT, "shorts", "stats.json")))["shorts"]
    except Exception:
        return {}
    by = {}
    for v in st.values():
        if v.get("views"):
            sc = math.log(v["views"]) + (0.03 * (v["stayed"] - 40) if "stayed" in v else 0.0)
            by.setdefault(v["concept"], []).append(sc)
    if not by:
        return {}
    allv = [x for xs in by.values() for x in xs]
    mean = sum(allv) / len(allv)
    return {c: max(0.5, min(2.5, math.exp(0.6 * (sum(xs) / len(xs) - mean)))) for c, xs in by.items()}


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
    # 26/11: performance-aware. Concepts within 1 use of the least-used stay eligible, weighted by how well the
    # concept actually did on the channel (shorts/stats.json: geometric-mean views vs channel), so winners come back
    # more often while never-used / rarely-used concepts still go first.
    cands = [c for c in cands if uses[c] <= low + 1]
    perf = perf_factors()
    concept = rng.choices(cands, weights=[WEIGHTS[c] * perf.get(c, 1.0) * (1.6 if uses[c] == low else 1.0) for c in cands])[0]
    print("weights", {c: round(WEIGHTS[c] * perf.get(c, 1.0) * (1.6 if uses[c] == low else 1.0), 2) for c in cands}, flush=True)
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
    hook = rng.choice(HOOKS[concept]) if concept in HOOKS else ""
    subprocess.run(["python3", "compose_generic.py", sd] + ([hook] if hook else []), check=True)
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
    elif concept == "ring":
        title = rng.choice([f"Escape {meta['rings']} rings… every bounce is a note 🎶 #satisfying #asmr #shorts",
                            f"{meta['bounces']} bounces to freedom 😳🎵 #satisfying #shorts",
                            "Can the ball escape? Sound ON 🔊 #satisfying #asmr #shorts"])
        desc = (f"A glossy ball bounces inside {meta['rings']} spinning neon rings — every bounce plays the next note and "
                "changes its colour. Will it slip through every gap? 3D physics animation with sound.\n\n")
    else:  # galton
        title = rng.choice(["The bell curve machine never fails 🎯 #satisfying #physics #shorts",
                            f"{meta['balls']} balls, one perfect bell curve 📈 #satisfying #shorts",
                            "Galton board: watch the curve appear 🤯 #shorts"])
        desc = f"{meta['balls']} balls bounce through a peg board and stack into a bell curve. 3D animation.\n\n"
    meta = {k: v for k, v in meta.items() if k not in ("caption",)}
    meta.pop("concept", None)

# 26/11: hook-style titles (curiosity / tension / impossible outcome / sound) win on this channel; use them most of the time
TITLE_HOOKS = {
    "nest": ["The last one barely fits… 😮‍💨 #satisfying #shorts", "Wait for the tiniest one 🤏😳 #satisfying #shorts"],
    "dice": ["They ALL land perfectly?! 🎲🤯 #satisfying #shorts", "Not a single die missed 🎲😳 #satisfying #shorts"],
    "shapes": ["The heart was the hardest… ❤️😮‍💨 #satisfying #shorts", "Every. Single. Shape. Fits. ✅🤯 #shorts"],
    "domino": ["I couldn't look away… 🌈😵‍💫 #satisfying #shorts", "Wait for the very last domino 👀 #satisfying #shorts"],
    "cloth": ["This cloth feels illegal to watch 😍 #satisfying #shorts", "Smoothest thing you'll see today ✨ #satisfying #shorts"],
    "galton": ["Random chaos… perfect curve?! 🤯📈 #satisfying #shorts", "Math is SO satisfying 🤯 #satisfying #physics #shorts"],
    "pendulum": ["Watch them line up again… 😮‍💨 #satisfying #physics #shorts", "Chaos… then PERFECT order 🤯 #satisfying #shorts"],
    "sort": ["Only 1% can solve this fast 🧪🧠 #satisfying #shorts", "My brain needed this 🧪😌 #satisfying #shorts"],
    "xylo": ["Turn the sound ON 🔊🎶 #satisfying #asmr #shorts", "Every bounce plays a note 🎵🤯 #satisfying #asmr #shorts"],
    "boxfill": ["Will it fill to the very top? 😳🌈 #satisfying #shorts", "It filled PERFECTLY… 🤯🌈 #satisfying #asmr #shorts"],
    "funnel": ["Which colour lands last? 🌀👀 #satisfying #shorts", "So hypnotic I watched it 10 times 🌀😵‍💫 #satisfying #shorts"],
    "tetris": ["Zero gaps. Not one. 🧩🤯 #satisfying #shorts", "The last piece was SO close… 🧩😮‍💨 #satisfying #shorts"],
    "ring": ["Will it escape? 😳🎶 #satisfying #asmr #shorts", "Every bounce is a note… wait for it 🎵 #satisfying #shorts"],
}
if concept in TITLE_HOOKS and rng.random() < 0.65:
    title = rng.choice(TITLE_HOOKS[concept])
# never reuse a title (user feedback 17/11): fall back to generic variants if the picked one already exists
prev_titles = set()
for j in glob.glob(os.path.join(ROOT, "shorts", "s*.json")):
    if os.path.basename(j) != name + ".json":
        try:
            prev_titles.add(json.load(open(j))["title"])
        except Exception:
            pass
if title in prev_titles:
    for alt in TITLE_HOOKS.get(concept, []) + ["Wait for the ending 😮‍💨 #satisfying #shorts", "Turn the sound ON 🔊✨ #satisfying #asmr #shorts",
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
