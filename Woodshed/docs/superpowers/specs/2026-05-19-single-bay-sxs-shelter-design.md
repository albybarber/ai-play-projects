# Single-Bay SxS Shelter — Design

**Date:** 2026-05-19
**Status:** Approved direction; ready for implementation plan
**File scope:** `utv-storage-planner.html`, `README.md`, `CLAUDE.md`

---

## Goal

Rework the existing 3-bay UTV/splitter/wood shelter planner into a single-bay equipment shelter sized for a **2026 Can-Am Defender MAX Limited HD11**. The structure must be simple enough to build in place on uneven ground, with the user leveling the site only roughly by hand.

The output remains a single-file static HTML planner deployed via GitHub Pages.

---

## Vehicle (driver of all dimensions)

2026 Can-Am Defender MAX Limited HD11:

| Dimension | Value |
|---|---|
| Length | 162.4 in (13.5 ft) |
| Width | 65 in (5.4 ft) |
| Height | 81.4 in (6.8 ft) |
| Wheelbase | 117.5 in |

---

## Scope changes vs. v1

**Removed:**
- Splitter bay
- Wood storage bay and wood rack
- Divider wall between splitter and wood
- LVL open-span header
- Side walls (UTV/splitter)
- Gravel-under-wood-bay toggle
- Entire sidebar UI (all sliders + toggles)
- Cost estimator, 2-bay mode toggle, center-post option (if present)
- "Airflow for wood storage" build note card

**Kept:**
- Single-file HTML, no dependencies, Canvas 2D rendering
- Three views: Front, Top/Floor Plan, Side (cross-section)
- Dynamically generated materials list
- Build-notes cards below the canvas
- Print-friendly layout
- Fonts: Bebas Neue / IBM Plex Mono / IBM Plex Sans
- GitHub Pages deployment at the existing URL (filename unchanged)

**Added:**
- Ground-contact 6×6 PT post foundation, with "cut posts to a level line" procedure for uneven ground
- Defender HD11 silhouette in the Front and Top views (rough cab-shaped rectangle is acceptable)
- "Uneven grade" dashed line under the level top plate in the Side view

---

## Fixed dimensions (baked in, no sliders)

| Parameter | Value | Rationale |
|---|---|---|
| Bay width | 10 ft | 65" machine + ~2.5 ft total side clearance for door swing / walking |
| Bay depth | 16 ft | 162.4" machine + ~1.5 ft front + ~1 ft rear clearance |
| Front wall height | 8 ft | 81.4" machine + clearance under front header beam |
| Roof pitch | 3/12 | Shed slope, front low → rear high; rear wall ≈ 12 ft |
| Rear wall height | ~12 ft | Computed: 8 ft + (16 ft × 3/12) = 12 ft |
| Eave overhang | 12 in | Sheds runoff away from front face |
| Number of posts | 6 | 4 corners + 2 mid-span on the 16 ft sides |
| Post spacing (long sides) | 8 ft on center | Matches mid-span post placement |

---

## Foundation: ground-contact 6×6 PT posts (uneven-ground strategy)

The user does light hand-leveling of the site, then:

1. Lay out post locations using a string-line rectangle. 6 holes total.
2. Dig each hole to **frost line** (assume **48 in** for Catskills, NY; note in build cards that this varies by region).
3. Set a PT 6×6 ground-contact-rated post in each hole, plumb, in concrete. Each post lands at whatever ground elevation it sits at — variation is absorbed by how far the post sticks out above grade.
4. After concrete cures, **snap a level line across all 6 post tops** using a laser level or water level.
5. **Cut each post to that line.** Result: a level top-plate plane even though the ground beneath is uneven.
6. Set double 2×8 PT beams on the cut tops, fastened with structural screws or Simpson connectors.

This replaces all v1 foundation options (helical piers, surface-mount post bases, sonotube piers).

---

## Structural design

- **Posts:** 6× 6×6 PT, ground-contact rated
- **Top plates / beams:** Double 2×8 PT on the long (16 ft) sides; single 2×8 PT cross-headers at front and rear
- **Rafters:** 2×6, 24 in OC, spanning the 10 ft width
- **Purlins:** 2×4 across rafters as required by metal roofing manufacturer
- **Hurricane ties / rafter connectors:** Simpson H1 or equivalent at every rafter-to-beam connection
- **Roofing:** 26-gauge corrugated metal, ridge cap, closure strips, roofing screws
- **Back wall:** T1-11 or LP SmartSide sheathing across rear face only

No LVL header. With only a 10 ft span across the front (post-to-post), a standard double 2×8 or 2×10 PT header is sufficient.

---

## App / UI changes

### Removed UI
- Entire sidebar (all sliders, all toggles)

### Page layout
- Canvas area (three views, stacked or grid) — full page width
- Materials list — below canvas
- Build notes cards — below materials list
- Title block — top of page
- Single-page printable

### Canvas rendering
- All three views redrawn for the new fixed geometry
- **Front view:** Show the Defender HD11 silhouette as a cab-shaped rectangle (roof line + windshield rake is acceptable but not required), centered in the bay. Dimension callouts: bay width, front wall height
- **Top view:** Single bay footprint, 6 post positions clearly marked, Defender footprint inside. Dimension callouts: bay width, bay depth. Open front marked with dashed line
- **Side view:** Shed slope front-low/rear-high. **Add a dashed "uneven grade" line** under the level top plate to communicate the foundation concept visually. Pitch triangle annotation, front and rear wall height callouts

### Materials list categories
1. **Foundation** — 6× 6×6 PT ground-contact posts, concrete (estimated bag count for ~48" deep holes), gravel for hole bottoms, structural screws/connectors
2. **Framing** — double 2×8 PT beams, 2×8 cross-headers, 2×6 rafters @ 24" OC, 2×4 purlins, hurricane ties
3. **Roofing** — corrugated metal panels (sq ft with 10% waste), ridge cap, closure strips, roofing screws
4. **Back wall** — T1-11 or LP SmartSide sheathing sq footage, siding nails/screws
5. **Hardware & fasteners** — structural screws, lag screws, joist hangers as needed

Note: since all dimensions are fixed, the materials list values are constants in the code (not computed from inputs). The list still renders dynamically from a data structure so it's easy to tweak.

### Build notes cards (3 cards, replacing the v1 set of 4)
1. **Foundation & Leveling on Uneven Ground** — frost-line depth note (region-dependent), the "set posts, then cut to a level line" procedure, why this works for uneven sites
2. **Roof Details** — rafter spacing, ridge cap and closure strip installation, eave overhang for runoff
3. **Defender HD11 Clearance** — bay-width-vs-machine-width math, recommended side clearance, height clearance under the front header

Snow load note retained in the foundation/framing materials section: "Catskills NY ≈ 50 psf ground snow load. 2×6 rafters at 24" OC across a 10 ft span are adequate, but verify locally if building in higher snow zones."

---

## File / docs changes

- **`utv-storage-planner.html`** — rewritten. Filename kept to preserve the existing GitHub Pages URL.
- **`README.md`** — rewritten to reflect single-bay scope, Defender HD11, fixed dimensions, uneven-ground foundation.
- **`CLAUDE.md`** — rewritten to match new architecture (no sidebar, fixed defaults, single bay).

Page `<title>` and main heading updated to something like **"SxS Shelter Planner — Can-Am Defender MAX HD11"**.

---

## What's explicitly out of scope

- Cost estimator
- CSV/PDF export
- Save/load configurations
- Mobile sidebar (no sidebar to collapse)
- Gable roof option (shed slope only)
- Concrete pad floor option
- Any wood storage features

---

## Acceptance criteria

- Opening `utv-storage-planner.html` directly in a browser shows three views, a materials list, and three build-note cards for a single 10×16×8 ft (front) shed-roof shelter
- No sidebar, no sliders, no toggles
- Defender HD11 silhouette visible in the front and top views
- Side view shows the "uneven grade" dashed line concept under a level top plate
- Materials list reflects the 6-post ground-contact foundation (no LVL, no helical piers, no wood rack)
- Build notes describe the cut-posts-to-level-line procedure
- README and CLAUDE.md reflect the new scope; no stale references to wood storage, splitter, LVL, sliders, or toggles
- GitHub Pages URL still resolves (filename unchanged)
