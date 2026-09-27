# Module 3 Labs: Retouching (Session 4)

Module 3 runs on **one portrait file** that grows across all three lessons:
`portrait-working.psd` (retouch layer in L08 → LOW/HIGH frequency separation in
L09 → D&B layer, masked Curves, and export in L10). The deliverable is
`portrait-final.jpg`.

**Demo on the practice faces, never on a learner's face.** The practice
portraits are simple illustrated faces with flaws placed on purpose, so every
demo works and nobody's appearance is discussed in front of the room.

```
practice/                          generated synthetic files (see specs below)
  l08-portrait-blemishes.jpg       temporary blemishes + permanent features to keep
  l09-portrait-blotchy.jpg         uneven skin tone with strong pore texture + a flyaway hair
  l09-skin-swatch.jpg              small flat skin patch: fast frequency-separation drill
  l10-portrait-flat.jpg            flat lighting (light from the left), dull eyes and teeth
instructor/                        instructor only: do NOT hand out
  l08-flaw-map-INSTRUCTOR.png      the L08 face with every temporary/permanent item circled
```

**Licensing note.** Do **not** use or hand out anything from the course's
`images/` folder. Those are licensed Adobe Stock images and are not
redistributable. Every file here is synthetic and can be shared with enrolled
learners (except the `instructor/` flaw map, which is an answer key).

## Lab flow

**L08, Retouch a Portrait (20 min).** Learners open their own consented portrait
or `l08-portrait-blemishes.jpg` → Save As `portrait-working.psd` → survey at 100%
and write the temporary/permanent lists in the workbook → empty `retouch` layer →
Spot Healing (Content-Aware, Sample All Layers) on open-skin spots → Healing
Brush (Sample: Current & Below, Alt/⌥-click source) on the two hairline spots →
retouch opacity ~85–90% → Save.

**L09, Separate & Smooth (30 min).** On `portrait-working.psd` or
`l09-portrait-blotchy.jpg`: Stamp Visible → duplicate ×2 → LOW (Gaussian Blur
~6–12 px) → HIGH (Apply Image: Layer LOW, Subtract, Scale 2, Offset 128) →
Linear Light → checkpoint "identical?" → even blotches on LOW → remove the
flyaway hair on HIGH (Sample: Current Layer) → Save. Struggling learners start
on `l09-skin-swatch.jpg`.

**L10, Sculpt & Finish (25 min).** On the portrait or `l10-portrait-flat.jpg`:
write the light direction first → Alt/⌥-click New Layer, Soft Light, 50% gray
fill, name `D&B` → dodge at ~10% (white) → burn (black) → Curves layer, mask
black, paint white over eye whites and teeth → Save PSD → Export As JPG ~80% →
`portrait-final.jpg`.

Do not hand out the answer key or the flaw map before the lab.

## Practice file specs (for the generator script)

All files: sRGB, **8 bits per channel** (the L09 Apply Image recipe in the lesson
is the 8-bit one), generated with Python 3 + Pillow (NumPy allowed for noise and
per-pixel math). Fixed random seed. JPEGs at quality 92, `subsampling=0`.
Write learner files into `labs/module-3/practice/` and the flaw map into
`labs/module-3/instructor/`.

**Draw shapes at 2× size and downsample with LANCZOS** for smooth edges; add
all noise and small marks *after* downsampling so they stay crisp at 100% zoom.
All coordinates below are in final-size pixels.

### Shared base face (used by all three portrait files)
- **Canvas:** 2000 × 2400 px, portrait orientation.
- **Background:** vertical gradient RGB (190,200,212) at the top to
  (150,160,175) at the bottom (L10 overrides this, see below).
- **Clothing/shoulders:** a dark blue-gray shape (RGB 60,80,110) filling the
  bottom of the frame from y ≈ 1880 down, wider than the head (a large ellipse
  centered at (1000, 2500), rx 900, ry 620).
- **Neck:** rectangle x 850–1150, y 1450–1950 in skin tone, slightly darker
  (×0.9) in its top 120 px to suggest the jaw shadow.
- **Hair (back):** dark brown (55,40,30) ellipse centered (1000, 930), rx 480,
  ry 540.
- **Face:** skin-tone ellipse centered (1000, 1120), rx 400, ry 520,
  base RGB (224,178,150). Ears: ellipses at (600, 1080) and (1400, 1080),
  rx 45, ry 90, skin ×0.93.
- **Hairline (fringe):** redraw hair over the top of the face as a polygon whose
  lower edge is a gentle wave between y ≈ 640 (center) and y ≈ 900 (at the
  temples, x ≈ 640 and x ≈ 1360). This defines a clear hair/skin edge.
- **Eyebrows:** arcs 14 px thick, RGB (70,50,40), centered above each eye at
  y ≈ 905, spanning x 760–920 and 1080–1240.
- **Eyes:** almond whites (ellipses 150 × 66 px) centered at (840, 1000) and
  (1160, 1000), RGB (235,232,225); iris circles r 32, RGB (90,60,40); pupils r 14,
  RGB (15,15,15); a white catchlight r 5 at the pupil's upper-left; a 4 px dark
  upper-lid line.
- **Nose:** a soft shadow stroke (8 px, skin ×0.85, blurred 4 px) along the
  viewer's-right side of the nose bridge from (1025, 1010) to (1045, 1210); two
  nostril ellipses (26 × 14 px, skin ×0.6) at (970, 1235) and (1030, 1235).
- **Mouth:** a slight smile. Upper and lower lip shapes, RGB (185,95,95), spanning
  x 890–1110 around y 1330–1400, with a visible band of teeth (rounded
  rectangle x 925–1075, y 1345–1372), teeth RGB (240,235,220).
- **Skin mask:** face + ears + neck (not hair, eyes, lips, teeth). Compute this
  mask; the skin effects below apply only inside it.
- **Pore texture (after downsampling, skin mask only):** add luminance noise
  in two scales: σ ≈ 7 at 1 px, plus σ ≈ 4 generated at half size and upscaled
  2× (nearest or bilinear). This must be clearly visible at 100% zoom: it's the
  "texture" learners must preserve.
- **Permanent features (keep these, all three files):**
  - **Freckles:** 30 dots, radius 3–5 px, RGB (175,120,90) at ~70% opacity,
    randomly placed within an ellipse centered (1000, 1110), rx 260, ry 90
    (nose bridge and upper cheeks), none inside the eyes.
  - **Mole:** one dark-brown dot, radius 9 px, RGB (90,55,40), at (835, 1360),
    beside the mouth on the viewer's left.
  - **Laugh lines:** two soft arcs, 4 px wide, skin ×0.87, blurred 3 px, from
    (900, 1290) curving down to (885, 1420) and mirrored from (1100, 1290) to
    (1115, 1420).

### `l08-portrait-blemishes.jpg`: heal the temporary, keep the permanent (L08)
- Base face as above, with soft shading: multiply the skin by a horizontal
  gradient from 1.03 (viewer's left) to 0.95 (viewer's right).
- **Temporary flaws to heal (14 items):**
  - **10 red spots in open skin**, radius 7–13 px, center RGB (200,90,85)
    fading to the skin color by 1.6 × radius, with a 1–2 px lighter highlight
    on the upper-left edge: forehead (880, 760), (1010, 720), (1120, 790);
    cheeks (760, 1150), (820, 1240), (1220, 1130), (1180, 1260), (1270, 1190);
    chin (960, 1520), (1060, 1500). Keep every spot at least 25 px from any
    freckle **except** (1220, 1130), which should deliberately sit on top of one
    freckle (the "reduce, not erase" drill).
  - **2 hairline spots**, same style, radius 10 px, placed so about a third of
    each spot overlaps the hair edge: near (900, 668) and (1110, 662) (adjust to
    the actual drawn hairline). These are the Healing Brush / Clone Stamp cases.
  - **1 stray hair:** a 2 px dark curve (RGB 50,35,25) from (1150, 1050) to
    (1330, 1320) across the viewer's-right cheek (a quadratic Bezier bowing
    outward is fine).
  - **1 lint speck:** 3–4 overlapping tiny white circles (total ~10 px across),
    RGB (250,250,250), at (1000, 1565) on the chin.
- **What learners must do:** remove all 14 temporary items; keep the 30
  freckles, the mole, and both laugh lines.

### `l08-flaw-map-INSTRUCTOR.png` (instructor only)
- The L08 image scaled to 1000 × 1200 px with overlays: a red numbered circle
  around each of the 14 temporary items (1–10 open-skin spots, 11–12 hairline
  spots, 13 stray hair, 14 lint), a green circle around the mole and each laugh
  line, and a dashed green ellipse around the freckle region. Add a small legend
  at the top: `RED = temporary (heal)   GREEN = permanent (keep)`.
- Save into `labs/module-3/instructor/`, **not** `practice/`.

### `l09-portrait-blotchy.jpg`: uneven tone, texture intact (L09)
- Base face with the same soft left-to-right shading as L08. **No** L08 spots,
  stray hair, or lint. Freckles, mole, and laugh lines present.
- **Blotches (low frequency):** apply 7 soft color patches to the skin **before**
  adding the pore noise, each a Gaussian falloff with σ = radius / 2:
  - cheeks (800, 1180) and (1200, 1180), radius 140: R +22, G −8, B −6
  - forehead (1000, 800), radius 110: R +15, G −5
  - nose tip (1000, 1215), radius 60: R +25, G −10
  - chin (1000, 1520), radius 90: R +18, G −4
  - jaw, viewer's left (720, 1400), radius 80: R −5, G −15, B +5 (purplish)
  - temple, viewer's right (1160, 890), radius 90: G +8, B −10 (sallow)
- **Pores (high frequency):** stronger than the base: σ ≈ 8 at 1 px plus σ ≈ 4 at
  2 px, applied after the blotches so the texture is uniform across them.
- **1 flyaway hair (texture to fix on HIGH):** a 1.5–2 px dark curve
  (RGB 50,35,25) across the forehead from (860, 700) to (1180, 860).
- **What learners must do:** a Gaussian Blur of ~6–12 px on LOW should hide the
  patches' edges and the pores at once; evening the patches on LOW must leave the
  pore grain untouched; the hair comes out on HIGH.

### `l09-skin-swatch.jpg`: fast frequency-separation drill (L09 support)
- **Size:** 1200 × 1200 px, filled edge to edge with skin RGB (224,178,150).
- Three blotches (same Gaussian method): (350, 400) radius 200 R +22 G −8;
  (820, 760) radius 160 R +18 G −6; (600, 950) radius 120 G +8 B −10.
- 12 freckles (as in the base face), pore noise as in L09, and one flyaway hair
  (2 px dark curve from (150, 1000) to (1050, 700)).
- **Use:** struggling learners build the whole LOW/HIGH setup here first; the
  result (even color, same grain, hair gone) is obvious in seconds.

### `l10-portrait-flat.jpg`: flat light, dull eyes and teeth (L10)
- Base face, clean skin (no blotches, no L08 flaws), pore noise σ ≈ 6,
  freckles/mole/laugh lines present.
- **Flat lighting:** do **not** apply the L08/L09 shading gradient to the face.
  Keep the nose shadow very faint (skin ×0.93 instead of ×0.85).
- **Readable light direction (from the viewer's left):**
  - background: horizontal gradient from (205,212,222) on the left to
    (140,150,165) on the right, instead of the vertical one;
  - one soft highlight bump on the viewer's-left cheek: +12 luminance, Gaussian
    σ ≈ 60 px, centered (800, 1120);
  - the left edge of the hair 10–15% lighter than the right edge;
  - eye catchlights placed on the upper-left of each pupil (as in the base).
- **Dull eyes and teeth (for the masked Curves step):** eye whites RGB
  (200,195,185) instead of (235,232,225); teeth RGB (220,205,160).
- **What learners must do:** dodge the forehead center, nose bridge, cheekbone
  tops (more on the left), and chin; burn the right side, temples, under the
  cheekbones and jaw; brighten eye whites and teeth subtly with a masked Curves
  layer; export `portrait-final.jpg`.

## Learners' own portraits (bring to Session 4)

Ask each learner to bring **one or two portraits**, as large original files
(straight from the camera or phone, not a messaging-app copy):

- **Who:** a self-portrait is ideal. Any other person must have agreed to being
  photographed, **edited, and shown to the class**. Avoid photos of children.
- **What makes a good practice portrait:** the face fills at least a third of the
  frame; at least ~2000 px on the long side; sharp focus on the eyes; soft,
  directional light (a window to one side is perfect for L10); a smile that
  shows teeth helps with the L10 eyes-and-teeth step.
- **Avoid:** photos already run through a beauty filter or "portrait smoothing"
  mode (there's no texture left to protect), heavy makeup or stylized filters,
  and group shots where the face is tiny.
- **Free-license option:** portraits from free-license sources (for example
  Pexels or Unsplash) are fine for practice. Check the current license on the
  download page first, and remind learners that retouching a real person's face
  carries the same respect rules: practice only, no misleading or unflattering
  edits, and don't publish edited faces of strangers.
- Learners who would rather not use a real face can do the whole module on the
  practice portraits. That's a complete, valid path.
