# Photoshop: Instructor Kit ("Course-in-a-Box")

A ready-to-teach package that lets another instructor deliver the course
**Photoshop: From First Win to Finished Work** without building it from scratch.
The live course site (<https://rays-photoshop-intro.netlify.app/>) is the learner's
textbook; this kit is everything the instructor needs around it.

**Format:** 8 sessions × 3 hours (24 instructional hours), one module per session.
Every session ends with one finished, exported deliverable. Run it weekly (8 weeks),
twice a week (4 weeks), or as a 4-day intensive (two sessions a day).

| Session | Module | Lessons | Tier | Deliverable |
|---------|--------|---------|------|-------------|
| S1 | 0 · Your First Win | L01 (+ orientation, setup check, workspace tour) | Foundations | One photo, fixed and exported |
| S2 | 1 · Foundations | L02–L04 | Foundations | A messy photo cleaned up |
| S3 | 2 · Light & Color | L05–L07 | Foundations | A flat photo graded and alive |
| S4 | 3 · Retouching | L08–L10 | Practitioner | A natural portrait retouch |
| S5 | 4 · Compositing | L11–L13 | Practitioner | A believable two-image composite |
| S6 | 5 · Design & Type | L14–L16 | Practitioner | A finished poster |
| S7 | 6 · AI & Speed | L17–L19 (+ capstone briefs) | Advanced | A generative edit plus an automated batch |
| S8 | 7 · Capstone | L20–L22 | Advanced | A self-directed portfolio piece, presented |

Alongside the path runs the **Recipes library** (`recipes.html` on the course site):
25 standalone how-to cards in six groups (Fix & Prepare, Select & Cut Out, Color &
Light, Retouch, Design & Type, AI/Speed & Export). Point learners to it for
between-session practice and after the course ends.

**Why this shape:** each module already ends in a finished piece, and each module's
lessons add up to about 2½ hours of guided build, so one module fits one 3-hour
session with a break, a recap, and a deliverable check. Session 1 pads the short
Module 0 with orientation and runs the first win twice (practice file, then the
learner's own photo). The capstone brief is chosen at the end of Session 7 and most
of the build happens as homework, so Session 8 can be plan review, a final studio
block, presentations, and peer critique.

### Primary documents: the combined books (start here)

These are the **canonical** print/hand-out documents: the whole course in one file each,
with a cover, table of contents, and continuous pagination.

| File | Audience | Contents |
|------|----------|----------|
| `participant-workbook.{html,pdf}` | Learner | The complete workbook: all 8 modules as chapters |
| `facilitator-guide.{html,pdf}` | Instructor | The complete teaching manual: all 8 modules |
| `answer-key.{html,pdf}` | Instructor | Every quiz answered + lab reference notes, all modules (confidential) |

**Quiz items (self-checks) per module, all answered in the answer key:**
M0 6 · M1 18 · M2 18 · M3 18 · M4 18 · M5 18 · M6 16 · M7 15 = **127**.

The editable per-module docs live in `source/module-N/` (also usable for teaching a
single module standalone). **If you edit a module's doc, run `python3 build-combined.py`
to regenerate the three books, then re-render their PDFs.** Per-module PDFs are not
shipped; the combined PDFs replace them.

### Kit-wide documents (at this folder's root)

| File | Audience | Purpose |
|------|----------|---------|
| `setup-guide.html` | Learner | Pre-course "before you begin" handout: install Photoshop, reset the workspace, preferences, course folder, what photos to bring to each session. Send it before Session 1 |
| `final-assessment.html` | Instructor | Capstone briefs (the six from Lesson 20), a 9-row rubric (Lesson 22's six Honest Critique rows word for word, plus plan, file, and presentation), matching the Module 7 guide and answer key, peer-critique protocol, scoring sheet |
| `sell-sheet.html` | Prospective instructors | Marketing one-pager: what's inside, who it's for, license tiers |
| `README.md` · `LICENSE.md` | — | This overview and the tiered license template |

The 8-session **syllabus** lives in the course root, one level up, so it stays public:
`syllabus.html` (screen, light/dark) and `syllabus-print.html` (print-first, with a
Print / Save as PDF button). PDFs of the kit-wide documents sit beside them once rendered.

**Still to do:** the `LICENSE.md` is a plain-language **template**; have it reviewed by
a lawyer before commercial distribution. Pricing in the sell sheet is a suggested
anchor within the license's ranges; adjust to your market.

---

## Folder layout

```
instructor-kit/
├─ participant-workbook.{html,pdf}   ← canonical hand-out books (all 8 modules)
├─ facilitator-guide.{html,pdf}
├─ answer-key.{html,pdf}
├─ setup-guide / final-assessment / sell-sheet  (.html + .pdf)
├─ slides/            one self-contained deck per module: module-N-<topic>.html (N = 0 … 7)
├─ labs/              module-0/ … module-7/  + build_practice_files.py (see labs/README.md)
│  └─ module-N/practice/   generated practice images for that module's labs
├─ source/            module-0/ … module-7/  editable per-module docs (build the books)
├─ kit.css            single shared print-first stylesheet (Photoshop-blue accent)
├─ build-combined.py  regenerate the 3 books from source/
└─ README.md · LICENSE.md
```

Every document is print-ready (a **Print / Save as PDF** button + a tuned `@media print`
layout, US Letter). Slide decks are single-file and need no server (arrow keys / space
to advance).

The whole `instructor-kit/` folder is kept **off the live site**: the course root's
`_redirects` returns 404 for `/instructor-kit/*`. It lives in the repository only.

### How to teach from it
1. Send learners the **setup guide** a week before Session 1 (it lists which photos to
   bring to which session, including a consented portrait for Session 4 and two images
   for compositing in Session 5).
2. Skim the **facilitator guide** for the module and each lesson's timing.
3. Present from the module's deck in **`slides/`** (full-screen the browser), and demo
   live in Photoshop.
4. Learners follow the lesson's **Guided Build** on a practice file from
   `labs/module-N/practice/` or on their own photo, and finish the session's
   deliverable against the lesson's **Project Completion Checklist**.
5. Learners work in the **participant workbook** (printed or on screen) and keep a
   **learning journal** (a prompt ends every lesson).
6. Grade quizzes with the **answer key**, and the capstone with **final-assessment.html**.

Each module's facilitator guide opens with a minute-by-minute 0:00–3:00 agenda; the
public syllabus uses the same timings on a 9:00 clock.

Before Session 7, confirm every learner is signed in and has generative credits:
Generative Fill and Expand need an internet connection and run in Adobe's cloud.
Capstone learners should do any generative steps at home, before Session 8.

### Requirements (for you and your learners)
- **Adobe Photoshop 2025 or newer**, desktop app, current release recommended.
- An **Adobe account** with a plan that includes Photoshop.
- **Internet + generative credits** for Module 6 (Session 7).
- Practice files from `labs/` plus learners' own photos. **Never** hand out the course
  site's `images/` folder: those are Adobe Stock images licensed to the author for the
  website only, not for redistribution.

### Editing and building
The three books at the root are **generated** from `source/module-N/` by
`build-combined.py`. Don't hand-edit the combined `.html`: your changes will be
overwritten on the next build.

```bash
cd instructor-kit
python3 build-combined.py              # regenerate the 3 books from source/
python3 labs/build_practice_files.py   # regenerate labs/module-N/practice/ images
```

Then re-render the PDFs: open each document and use **Print / Save as PDF**
(Destination: Save as PDF, Paper: Letter, Margins: Default, Background graphics: on),
or use headless Chrome, for example:

```bash
google-chrome --headless --no-pdf-header-footer \
  --print-to-pdf=facilitator-guide.pdf facilitator-guide.html
```

Repeat for `participant-workbook`, `answer-key`, `setup-guide`, `final-assessment`,
and `sell-sheet`, and (from the course root) `syllabus-print.html`.

---

## License

See `LICENSE.md`. Short version: this kit is licensed to a **single instructor or
organization** to teach the course; it is **not** to be resold, and the facilitator
guide and answer keys are **not** for learner distribution. Tiers (Solo / Organization /
White-label, plus an optional updates add-on) are set at point of sale.

© 2026 Ray de la Paz. Photoshop: From First Win to Finished Work. All rights reserved.
