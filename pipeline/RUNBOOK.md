# SatisFit 3D — daily Short runbook

Channel: **SatisFit 3D** (@SatisFit3D), YouTube Studio channel id `UCFs5CBPK9XgrcTTJwGlugGQ`,
signed in inside the Claude desktop app's built-in browser (account of the channel owner).

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
