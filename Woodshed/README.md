# SxS Shelter Planner

A single-file browser tool for planning a simple single-bay equipment shelter sized for a **2026 Can-Am Defender MAX Limited HD11**. Designed to be buildable in place on uneven ground with minimal site prep.

Live: https://albybarber.github.io/ai-play-projects/Woodshed/utv-storage-planner.html

---

## Files

```
Woodshed/
├── utv-storage-planner.html   # The entire app — no build step, open in any browser
├── README.md
└── CLAUDE.md
```

No dependencies. No server required. Open the HTML file directly.

The filename is kept from the v1 project to preserve the public GitHub Pages URL.

---

## What it shows

- **Three architectural views** — Front, Top/Floor Plan, Side (cross-section)
- **Materials estimate** organized by foundation, framing, roofing, back wall, and hardware
- **Build notes** covering foundation leveling on uneven ground, roof details, and Defender HD11 clearance

---

## Fixed design (no sliders)

| Parameter | Value |
|---|---|
| Vehicle | 2026 Can-Am Defender MAX Limited HD11 (162.4 × 65 × 81.4 in) |
| Bay width | 10 ft |
| Bay depth | 16 ft |
| Front wall height | 8 ft |
| Roof pitch | 3/12 shed slope (front low, rear high) |
| Rear wall height | ~12 ft (derived) |
| Posts | 6× PT 6×6 ground-contact, 4 corners + 2 mid-span |
| Foundation | Posts set in concrete to 48 in frost line, cut to level |
| Roof | 26 ga corrugated metal, 2×6 rafters @ 24" OC, 2×4 purlins |
| Walls | Back wall only (T1-11 or LP SmartSide). Front and sides open. |

---

## Foundation strategy for uneven ground

1. Lay out 6 post locations.
2. Dig each hole to the local frost line (48 in assumed for Catskills, NY).
3. Set a PT 6×6 ground-contact post in concrete in each hole, plumb. Each post lands at whatever ground elevation it sits at.
4. After the concrete cures, snap a level line across all 6 post tops with a laser or water level.
5. Cut each post to that line. The top-plate plane is now perfectly level even though the ground isn't.
6. Set double 2×8 PT beams on top.

This avoids site grading, helical piers, and surface piers. The only excavation is the 6 post holes.

---

## Technical notes

- **Single HTML file** — all CSS, JS, and markup inline. No framework, no bundler.
- **Canvas 2D rendering** — three views drawn with vanilla Canvas API. Redraws on window resize.
- **Fonts** — Google Fonts: Barlow Condensed, JetBrains Mono, Barlow. Degrades to fallbacks offline.
- **Print-friendly** — `@media print` styles invert to a black-on-white layout for the materials list and notes.
- **No state, no persistence** — fixed dimensions, no inputs.

---

## Origin

Built as a Claude AI experiment. Part of the `ai-play-projects` collection. Originally a 3-bay UTV/splitter/wood-storage planner; rewritten in May 2026 as a single-bay shelter for a different SxS.
