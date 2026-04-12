# UTV Storage Shelter Planner

An interactive, single-file browser tool for designing and planning an outdoor storage shelter covering a UTV, a log splitter, and a firewood stack. Designed around a **Yamaha Wolverine X4** but the bay dimensions are fully adjustable via sliders.

---

## Files

```
utv-storage-planner/
├── utv-storage-planner.html   # The entire app — no build step, open in any browser
└── README.md
```

No dependencies to install. No server required. Open the HTML file directly.

---

## What It Does

The planner lets you configure a three-bay shed structure and instantly see:

- **Live architectural drawings** across three views (Front, Top/Floor Plan, Side)
- **Auto-generated materials list** that recalculates as you adjust dimensions
- **Quick stats** — total footprint, wood bay width, and estimated cord capacity
- **Build notes** covering foundation approach, airflow, roof details, and UTV clearance

---

## Design Assumptions

These are the fixed design decisions baked into the current version:

| Parameter | Value / Approach |
|---|---|
| UTV | Yamaha Wolverine X4 (~61" wide, ~75" tall) |
| Wood storage target | 1–2 cords |
| Primary structure | Pressure-treated lumber posts and beams |
| Roof | Corrugated metal (26-gauge), shed slope |
| Roof slope direction | Front low, rear high — runoff goes away from the open face |
| Open face | All three bays open at the front |
| UTV + splitter span | No interior post — spanned by a LVL header beam |
| Foundation | Surface-mount post bases on concrete pads, or helical piers — minimal excavation |
| Wood bay floor | PT 2×4 runners laid on grade — no gravel bed required |

---

## Adjustable Parameters (Sidebar Sliders)

### Structure Dimensions
| Slider | Range | Default | Effect |
|---|---|---|---|
| Total Width | 20–40 ft | 28 ft | Overall structure width |
| Total Depth | 14–30 ft | 20 ft | Front-to-back depth |
| Front Wall Height | 8–12 ft | 9 ft | Height at the open (front) face |
| Roof Pitch | 2/12–8/12 | 4/12 | Rise per 12" of run; affects rear wall height and rafter length |

### Bay Layout
| Slider | Range | Default | Effect |
|---|---|---|---|
| UTV Bay Width | 8–14 ft | 10 ft | Dedicated bay for the Wolverine X4 |
| Splitter Bay Width | 6–10 ft | 8 ft | Dedicated bay for the log splitter |

Wood bay width is calculated automatically: `Total Width − UTV Bay − Splitter Bay`.

### Toggles
| Toggle | Default | Notes |
|---|---|---|
| Wood rack divider wall | ON | Partial wall between splitter and wood bays |
| Side walls (UTV + splitter) | ON | Encloses the left and right sides of the machine bays |
| Back wall (all bays) | ON | T1-11 or LP SmartSide on the rear |
| Gravel (wood bay only) | OFF | Optional 4" crushed gravel layer under wood bay only |

---

## Views

### Front View
Shows the open face of the structure. Key elements:
- Three labeled bays with their widths
- UTV silhouette (green cage outline) in the UTV bay
- Log splitter silhouette in the splitter bay
- Wood stack with log-end detail in the wood bay
- LVL header beam labeled across the UTV+splitter span (no interior post)
- Shed roof with corrugated rib detail
- Dimension callouts for front wall height and total width

### Top / Floor Plan
Birds-eye view showing:
- Bay footprints with UTV and splitter equipment outlines
- Wood stack rows across the wood bay
- Wall thickness for side walls and back wall
- LVL header shown as a beam across the front of the open-span bays
- Open front marked with a dashed line
- Dimension callouts for total width and depth

### Side View (Cross-Section)
Profile view showing:
- Shed roof slope from front (low) to rear (high)
- Front and rear wall height callouts
- Pitch triangle annotation
- Rafter lines
- Wood stack log-end detail in the rear portion of the bay

---

## Materials List

The materials list is generated dynamically based on all current slider values. It is organized into these categories:

1. **Foundation — Minimal Groundwork** — posts, surface-mount concrete pads, adjustable post bases, helical pier option, optional gravel
2. **Open-Span Header (UTV + Splitter Bay)** — front and rear LVL beams sized to the combined UTV+splitter span, plus post cap hardware
3. **Framing** — 6×6 PT beams, 2×6 rafters (24" OC), purlins, hurricane ties
4. **Roofing** — corrugated metal panels (sq ft with 10% waste factor), ridge cap, closure strips, roofing screws
5. **Siding / Walls** — T1-11 or LP SmartSide sq footage for back wall, side walls, and divider wall (conditional on toggles)
6. **Wood Storage Rack** — 4×4 uprights, 2×4 horizontal rails, PT ground runners
7. **Hardware & Fasteners** — structural screws, joist hangers, lag screws

> **Note on LVL sizing:** At the default 18 ft combined span (10 ft UTV + 8 ft splitter), a 3.5"×11.25" LVL is listed. For spans over 14 ft or high snow load areas (e.g. Catskills, NY), verify sizing with your lumber yard or a structural engineer — a 3.5"×14" or doubled LVL may be required.

---

## Build Notes (In-App)

Four guidance cards are shown below the drawing canvas:

- **Foundation & Footings — Minimal Groundwork**: helical piers vs. surface pads, frost line depth, ground prep approach
- **Airflow for Wood Storage**: open front strategy, back wall ventilation gaps, stacking on runners, orientation to prevailing wind
- **Roof Details**: rafter spacing, ridge cap and closure strip installation, eave overhang for runoff management
- **Wolverine X4 Clearance**: bay width vs. machine width, recommended side clearance, wheel stop placement

---

## Technical Notes

- **Single HTML file** — all CSS, JS, and markup in one file. No framework, no bundler.
- **Canvas rendering** — all three views drawn with the HTML5 Canvas 2D API. Redraws on every input change.
- **Fonts** — loaded from Google Fonts: `Bebas Neue` (display), `IBM Plex Mono` (labels/data), `IBM Plex Sans` (body). Requires internet connection to load fonts; degrades gracefully to monospace/sans-serif fallbacks offline.
- **Responsive** — canvas resizes to container width on window resize. Layout switches to single column below ~900px.
- **No state persistence** — all values reset on page reload. This is intentional; it's a planning scratch pad.

---

## Possible Extensions

- Add a cost estimator (price-per-unit inputs for each material line)
- Export the materials list to CSV or PDF
- Add a gable roof option as an alternative to the shed slope
- Add a concrete pad option for the UTV/splitter bay floor
- Mobile-optimized layout with collapsible sidebar
- Save/load configurations via URL params or localStorage

---

## Origin

Built as a Claude AI experiment — designed interactively in a single conversation, iterating on layout, structural decisions (open-span LVL header, minimal groundwork foundation), and the materials list. Part of the `ai-play-projects` collection.
