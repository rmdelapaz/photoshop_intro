# Module 2 Labs: Light & Color (Session 3)

Module 2 runs on **one working file** that grows across all three lessons:
`grade-working.psd` (Camera Raw develop in L05 → Curves in L06 → Smart Filters
and export in L07). The practice files below give every learner a photo with a
known, fixable flaw, and a fallback if their own file goes missing.

```
practice/                         generated synthetic files (see specs below)
  l05-flat-cast.jpg               warm cast + flat tone: the main L05 develop file
  l05-green-indoor.jpg            green fluorescent cast: needs Tint, not just Temperature
  l06-flat-landscape.jpg          neutral but low-contrast: S-curve, channel grade, masked region
  l06-tone-ramp.png               black-to-white ramp + steps: "reading the curve" demo
  l07-badge-crisp.png             fine lines + small text: Smart Object vs normal scale test
  l07-subject-busy-bg.jpg         sharp subject on a busy background: filter-mask / fake depth of field
```

**Licensing note.** Do **not** use or hand out anything from the course's
`images/` folder. Those are licensed Adobe Stock images and are not
redistributable. Every file here is synthetic (generated from code) and can be
shared freely with enrolled learners.

## Lab flow

**L05, Develop a Flat Photo (22 min).** Open `l05-flat-cast.jpg` (or the
learner's own flat/indoor photo) → Save As `grade-working.psd` → Convert to
Smart Object → Filter ▸ Camera Raw Filter → White Balance eyedropper on the gray
card or white wall → Exposure → Contrast → Highlights/Shadows → Whites/Blacks
(Alt/⌥ clipping preview) → OK → Save. If time: `l05-green-indoor.jpg` (Tint).

**L06, Contrast & Color (25 min).** Demo reading the curve on
`l06-tone-ramp.png`. Learners continue on `grade-working.psd` (fallback: open
`l06-flat-landscape.jpg`, convert and develop quickly, Save As
`grade-working.psd`) → S-curve → Blue (and Red) channel grade → second Curves
layer, black mask, paint white over one region (the tree or the sky) → Save.

**L07, Finish the Grade (25 min).** Demo the scale test on
`l07-badge-crisp.png` (duplicate, convert one copy, scale both to 30% then back
to 100%). Learners add a Smart Filter to `grade-working.psd`, paint its mask,
run the scale test, Save the PSD, then File ▸ Export ▸ Export As ▸ JPG 80% →
`module2-grade-final.jpg`. If time: fake depth of field on
`l07-subject-busy-bg.jpg`.

Do not hand out the answer key before the lab.

## Practice file specs (for the generator script)

All files: sRGB, 8 bits per channel, generated with Python 3 + Pillow (NumPy
allowed for noise and per-channel math). Use a fixed random seed so files are
reproducible. JPEGs at quality 92, no chroma subsampling if possible
(`subsampling=0`). Write into `labs/module-2/practice/`.

### `l05-flat-cast.jpg`: warm cast + flat tone (main L05 file)
- **Size:** 2400 × 1600 px, landscape.
- **Clean scene first (before the flaw):**
  - Sky: top 55% of the frame, vertical gradient from RGB (70,130,200) at the top
    to (200,222,240) at the horizon. A pale sun disk (radius 70 px, RGB
    250,245,225) at about (1850, 260), edges softened with a 6 px Gaussian blur.
  - Ground: bottom 45%, green (70,130,60) with a slightly lighter band near the
    horizon; add luminance noise (σ ≈ 6) so it isn't a flat fill.
  - House (neutral targets): a white wall rectangle (RGB 240,240,240) at
    x 500–1100, y 700–1080; a dark gray roof triangle (RGB 60,60,60) above it
    from (460,700) to (1140,700) to apex (800,470); a near-black shadow band
    (RGB 12,12,12) 30 px tall directly under the roof edge; a mid-gray door
    (RGB 90,90,90) at x 760–860, y 880–1080; two windows (RGB 40,55,70).
  - Pavement: a neutral gray strip (RGB 128,128,128) across the bottom 140 px.
  - Gray card: at x 1700–2200, y 1180–1420 draw three patches side by side:
    black (8,8,8), 18% gray (118,118,118), white (248,248,248), with the label
    `GRAY CARD` in dark text (any legible sans font, ~36 px) above them.
- **Apply the flaw (in this order):**
  1. Warm/orange cast, per channel on 0–255 values: R = R × 1.10 + 12,
     G = G × 1.00 + 2, B = B × 0.72. Clip to 0–255.
  2. Flatten the tone: v = 45 + v × 0.60 (so nothing is darker than ~45 or
     brighter than ~200).
  3. Add mild Gaussian luminance noise (σ ≈ 3).
- **What learners must fix:** the eyedropper on the gray card or white wall
  removes the cast; Whites/Blacks restore a true black (roof shadow, black patch)
  and a clean white (wall, white patch).

### `l05-green-indoor.jpg`: green fluorescent cast (L05 if time)
- **Size:** 2400 × 1600 px.
- **Clean scene:** an off-white back wall (RGB 232,230,224) in the top 60%; a
  window rectangle (x 1500–2150, y 150–750) filled with a soft sky gradient
  (150,190,230 → 215,230,245) and a 20 px white frame; a wooden table in the
  bottom 40% (RGB 150,100,60, with thin darker horizontal "grain" lines every
  ~18 px and noise σ ≈ 8); a white mug (body rectangle x 600–820, y 820–1080,
  ellipse rim on top, handle as a thick arc, RGB 245,245,245 with a soft gray
  shadow side); a white plate (ellipse x 950–1400, y 1000–1130, RGB 240,240,240)
  and a gray card (black / 18% gray / white patches as above) lying at
  x 300–520, y 1150–1290.
- **Flaw:** fluorescent green-cyan cast and slight underexposure:
  R = R × 0.86, G = G × 1.06 + 8, B = B × 0.98, then all channels × 0.82.
  Add noise σ ≈ 4.
- **What learners must fix:** Temperature alone won't do it; they need **Tint**
  toward magenta after the eyedropper, and Exposure up.

### `l06-flat-landscape.jpg`: neutral but low contrast (L06 fallback + demo)
- **Size:** 2400 × 1600 px.
- **Scene:** sky gradient (top 50%, RGB 110,160,215 → 210,225,240) with 4–5 soft
  white cloud ellipses (blurred 25 px); two layers of mountain silhouettes near
  the horizon (polygons, RGB 110,130,150 and 80,100,115); a green meadow
  (RGB 95,140,70, noise σ ≈ 10) in the bottom half; one lone tree as the
  "subject" at about x 1600 (trunk rectangle 40 × 260 px RGB 80,55,35, canopy
  of three overlapping circles radius ~150 px RGB 45,100,45) so it's easy to
  mask.
- **Flaw:** white balance is already neutral; contrast is flat. Remap all
  channels with v = 70 + v × 0.45 (range ~70–185). Noise σ ≈ 3.
- **What learners do:** S-curve for contrast, a channel grade, and a masked
  Curves layer that lifts just the tree or darkens just the sky.

### `l06-tone-ramp.png`: reading the curve (L06 demo)
- **Size:** 2400 × 800 px, PNG, stored as RGB (R = G = B).
- **Top half (y 0–380):** a smooth horizontal gradient from 0 (left) to 255
  (right).
- **Bottom half (y 420–800):** 11 equal-width vertical steps with values
  0, 26, 51, 77, 102, 128, 153, 179, 204, 230, 255. In each step print its
  percentage (`0%`, `10%` … `100%`) in ~40 px text, white on the dark steps and
  black on the light steps.
- **Gap (y 380–420):** mid-gray (128) band with the words `shadows`,
  `midtones`, `highlights` at left, center, and right (~28 px text).
- **Use:** add a Curves layer and drag the midpoint up/down; learners see exactly
  which steps move.

### `l07-badge-crisp.png`: Smart Object scale test (L07 demo + exercise)
- **Size:** 1600 × 1600 px, PNG, white background.
- **Content:** a circular badge centered on the canvas: three concentric circles
  (radii 700, 660, 520 px) drawn with 2 px dark-blue lines (RGB 20,40,90); the
  ring between radii 660 and 520 filled with fine 1 px diagonal hatch lines
  spaced 4 px apart; a bold `Ps` in the center (~420 px tall, RGB 20,115,230);
  under it, three rows of small text (~22 px, ~16 px, ~12 px) reading
  `SMART OBJECT TEST · SCALE 30% → 100%`; a 240 × 240 px checkerboard of
  2 × 2 px black/white squares in the lower center.
- **Why:** thin lines, hatch, small text, and the fine checkerboard turn visibly
  soft or blotchy when a normal layer is scaled down and back up, and stay
  perfect on a Smart Object.

### `l07-subject-busy-bg.jpg`: filter-mask drill (L07 if time)
- **Size:** 2400 × 1600 px.
- **Background:** a brick wall filling the frame: bricks 160 × 60 px in running
  bond, RGB around (150,70,50) with ±15 per-brick variation, 6 px mortar lines
  (RGB 200,195,185), plus luminance noise σ ≈ 8; scatter ~60 small warm-white
  dots (radius 6–10 px, RGB 255,235,180) across the upper half like string
  lights.
- **Subject:** a teal vase centered in the lower-middle (body = ellipse
  x 1000–1400, y 700–1300 plus a neck rectangle x 1130–1270, y 560–720,
  RGB 20,140,150 with a lighter vertical highlight stripe), holding three yellow
  flowers (each: 8 circular petals radius 45 px, RGB 250,200,40, around an orange
  center radius 30 px) on dark green stems. Hard, crisp edges.
- **Use:** Gaussian Blur Smart Filter (~15–25 px) on the whole image, then paint
  the Smart Filters mask black over the vase and flowers so only the wall blurs.

## Learners' own photos (bring to Session 3)

Ask each learner to bring **2–3 of their own photos**, ideally the largest
original files (straight from the phone or camera, not a messaging-app copy):

- **One flat or wrongly colored photo:** an overcast day, an indoor shot under
  warm bulbs, or anything with a visible color cast. Best if it contains
  something that should be neutral (a white shirt, gray pavement, a white wall).
- **One photo with a sky**, for masked Curves on the sky.
- **One photo with a clear subject** (a person, a pet, an object) for the
  masked "spotlight" Curves layer and the filter-mask drill.

Photos of other people should be of people who don't mind being shown on the
projector. Learners without suitable photos can use free-license images (for
example from Pexels or Unsplash); tell them to check the current license on the
download page before using or sharing an edited version.
