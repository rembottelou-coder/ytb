# SatisFit 3D — daily Short runbook

Channel: **SatisFit 3D** (@SatisFit3D), YouTube Studio channel id `UCFs5CBPK9XgrcTTJwGlugGQ`,
signed in inside the Claude desktop app's built-in browser (account of the channel owner).

## Concepts
`make_short.py` picks a concept that none of the last 6 Shorts (2 days) used — every Short of a day must be a different concept and scene (force with `CONCEPT=`):
fit, soft (3-clip "Angle" / "% SOFT" formats) and single-clip scenes `c_nest.py`, `c_dice.py`,
`c_shapes.py`, `c_domino.py`, `c_cloth.py`, `c_galton.py`, `c_pendulum.py` (rainbow pendulum wave, marimba note per swing),
`c_sort.py` (ball-sort puzzle in glass tubes; added 20/11 for more variety), `c_xylo.py` (rainbow xylophone staircase, balls bounce down playing notes; added 21/11),
`c_boxfill.py` (rainbow ball rain filling a glass box / hexagon / jar in layers, multi-angle; added 24/11),
`c_funnel.py` (striped balls spiral down a gravity-well "coin funnel" into a glass tube, multi-angle; added 24/11),
`c_tetris.py` (candy tetrominoes glide, spin and drop into an upright board until it is filled with no gap, rows flash bottom→top; random drop-valid tiling, multi-angle; added 26/11) (helpers in `common.py`, sounds in `sfx.py`,
composited by `compose_generic.py` with SFX synced to `events.json`). Quick preview of any scene:
`STEP=30 python3 pipeline/c_dice.py /tmp/x 1 0.2 4` renders every 30th frame at low quality.

## User feedback (keep applying every day)
- 24/11: "pense à varier, là c'est redondant — ce que tu fais est très bien, garde-le, mais varie : par ex. les boules sous
  différents angles qui rentrent dans une boîte… inspire-toi d'autres chaînes YouTube". Done: two new concepts inspired by
  the big satisfying-3D channels (ball rain into a container, coin-vortex funnel) and a **multi-angle** helper
  `multi_camera(shots)` in `common.py` (camera cuts wide → top-down → close-up → wide via timeline markers, a soft whoosh on
  each cut). Keep all existing concepts in rotation. Next ideas for more variety (add one `c_<name>.py` at a time): marble
  run / tube slide, softbody jelly cubes squeezed through a grid, beads pouring into a heart-shaped mould, (Tetris: done 26/11), balls in a rotating hexagon, kinetic-sand cutting; retrofitting `multi_camera` into dice/shapes/sort.
  Don't use motion blur together with `multi_camera` (black artefacts on the frame after each cut).
- 17/11: "à chaque fois ce sont toujours les mêmes vidéos, varie vraiment" → 3 different concepts per day, none from the previous 6 Shorts, titles never repeated.
- 20/11 (variety): with 8 concepts the "not in the last 6" rule left only fit/soft (old look) every other day, so two new
  concepts were added (pendulum, sort). Adding a new `c_<name>.py` scene is the best way to keep things fresh: register it in
  `make_short.py` (ALL, WEIGHTS, title/desc block); never-used concepts are picked first automatically.
  Glass tip: refractive glass renders black/dark at our bounce counts — use transparent+fresnel gloss and
  `ob.visible_glossy = ob.visible_shadow = False` (see `c_sort.py`).
- 18/11: "plus de couleurs, insister sur les bruitages satisfaisants, des trucs qui changent de ceux d'aujourd'hui, le but c'est vraiment *satisfaisant*, que ça stimule la tête".
  What the pipeline now does for this (concept scenes `c_*.py` + `compose_generic.py`):
  - colours: saturated candy `RAINBOW` (10 hues), vivid backdrops (`VIVID` / `pick_bg()`), "Standard" view transform
    with -0.5 exposure (AgX was washing colours to pastel), +18 % saturation in compositing (`SAT=`), rainbow-gradient cloth;
  - sound: stereo mix with per-event panning + light reverb + soft-clip (louder, headphone ASMR feel); new sounds
    `pop`, `sparkle`, `chord` (big final chord); every landing gets a rising pluck melody; finales are `chord` + `sparkle`;
  - motion: slow camera push-in over the clip (`PUSH=1.06`).
  When checking frames, reject a Short that looks pale/pastel or whose sound is only a few weak clicks.
  (fit / soft still use the older `scene.py` / `compose.py` look — upgrade them the same way before using them again.)

## 1. Render the next Short (cloud workspace)

```bash
pip install --break-system-packages bpy numpy pillow   # bpy ~ Blender 5.x, CPU Cycles
cd <repo> && nohup python3 pipeline/make_short.py > pipeline/run.log 2>&1 &
```
Takes ~25–35 min on 2 CPUs. Poll `tail pipeline/run.log` until it prints `READY sNN <title>`.
Output: `shorts/sNN.mp4` (1080x1920, ~8 s, with synthesized SFX) and `shorts/sNN.json` (title + description).
Look at a few frames before publishing (e.g. `ffmpeg -i shorts/sNN.mp4 -vf "select='eq(n\,60)+eq(n\,200)',scale=270:480,tile=2x1" -frames:v 1 /tmp/x.jpg`).

## 2. Push the files to GitHub (they are fetched by the browser from raw.githubusercontent.com)

```bash
git add shorts/sNN.mp4 shorts/sNN.json && git commit -m "Add short sNN" && git -c push.negotiate=true push origin HEAD
```

## 3. Upload in YouTube Studio (built-in browser, no native file dialog needed)

1. Navigate to `https://studio.youtube.com/channel/UCFs5CBPK9XgrcTTJwGlugGQ/videos/upload?d=ud`, wait ~4 s.
2. Inject the file with javascript:
   ```js
   const b = await (await fetch('https://raw.githubusercontent.com/rembottelou-coder/ytb/main/shorts/sNN.mp4')).blob();
   const dt = new DataTransfer(); dt.items.add(new File([b], 'sNN.mp4', {type:'video/mp4'}));
   const inp = document.querySelector('ytcp-uploads-file-picker input[type=file]');
   inp.files = dt.files; inp.dispatchEvent(new Event('change', {bubbles:true}));
   ```
3. Set title + description (contenteditable boxes): for each of
   `document.querySelectorAll('ytcp-uploads-dialog #textbox')` [0]=title, [1]=description:
   `el.focus(); document.execCommand('selectAll'); document.execCommand('insertText', false, TEXT)`.
   Verify with `.innerText`.
4. Audience: click the radio "Non, elle n'est pas conçue pour les enfants"
   (`find` it by that text and click it, or in JS: the `tp-yt-paper-radio-button` whose innerText contains "pas conçue").
5. Click `#next-button` three times (2 s apart). On the Visibility step, SCHEDULE for 18:00 (Paris) the same day:
   - click the "Programmer" section header (find "Programmer") to expand it;
   - date: `document.querySelector('ytcp-uploads-dialog #datepicker-trigger').click()`, then focus
     `ytcp-date-picker input`, select it, `execCommand('insertText', false, '<D> <mois abrégé>. <YYYY>')`
     (format shown, e.g. "17 nov. 2026"), then press Return with the browser `computer` key tool (a JS keydown is ignored);
     check `#datepicker-trigger` innerText shows the new date;
   - time: focus `ytcp-uploads-dialog #time-of-day-container input`, select, insertText "18:00", press Return (computer key);
   - click `#done-button` (label "Programmer"). The dialog then says "Vidéo programmée ... à 18:00".
   If it's already past 17:50 when you reach this step, publish immediately instead (radio `name="PUBLIC"`, then `#done-button`).
   **If the browser pane is hidden** (`document.hasFocus()` false), `execCommand`/typed keys do nothing. What works then:
   - title/description: `find` "Ajoutez un titre" / "Présentez votre vidéo" and use `form_input` on those refs (verify `.innerText`);
   - schedule: `find` "Programmer" and click that ref (the JS `#visibility-title` click doesn't expand it); click `#datepicker-trigger`,
     screenshot, click the day number in the calendar; click the time input (opens a list of 15-min slots), `scroll_to` the
     `find "18:00"` option ref, take a NEW screenshot and click the option by coordinate; verify the fields show the right values.
6. Read the share link from the dialog (`[...document.querySelectorAll('a')].map(a=>a.href).find(h=>h.includes('youtube.com/shorts'))`), close it.
7. Append `{name, url, date, scheduled}` to `shorts/posted.json`, commit, push.
