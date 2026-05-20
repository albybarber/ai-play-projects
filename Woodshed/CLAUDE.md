# Woodshed — Claude Notes

## Project overview
Single-file browser tool for planning a single-bay equipment shelter. Sized for a 2026 Can-Am Defender MAX Limited HD11. No build step, no dependencies. Open `utv-storage-planner.html` directly in a browser. Deployed via GitHub Pages at `https://albybarber.github.io/ai-play-projects/Woodshed/utv-storage-planner.html`.

The filename `utv-storage-planner.html` is kept from the v1 project to preserve the public URL — do not rename it.

## File structure
```
utv-storage-planner.html   — the entire app (HTML, CSS, JS in one file)
README.md
CLAUDE.md
docs/superpowers/specs/    — design specs
docs/superpowers/plans/    — implementation plans
```

## Architecture
- **Single HTML file** — all CSS, JS, and markup inline. No framework, no bundler.
- **Canvas 2D rendering** — three views (Front, Top, Side) drawn with vanilla Canvas API. Redraws on window resize.
- **No state, no sliders, no toggles** — all dimensions are baked into a `SHELTER` constants object at the top of the `<script>` block.
- **Materials list** rendered from a static `MATERIALS` data array — values don't change at runtime, but the data-driven render keeps the code clean.
- **Build notes** are static HTML cards (no JS templating).

## Key design decisions baked in
- 1 bay sized for the Defender MAX HD11 (162.4 × 65 × 81.4 in)
- 10 ft wide × 16 ft deep × 8 ft front wall, 3/12 shed pitch
- 6× ground-contact PT 6×6 posts (4 corners + 2 mid-span on the 16 ft sides), set in concrete to 48 in frost line
- Posts are cut to a snapped level line after concrete cures — this is the strategy for building on uneven ground
- Roof: corrugated metal, shed slope (front low, rear high)
- Back wall only — front and both sides open

## Fonts
Loaded from Google Fonts: `Barlow Condensed` (display), `JetBrains Mono` (labels/data), `Barlow` (body). Degrades gracefully offline.

## Snow load note
The materials and build notes assume ~50 psf ground snow load (Catskills, NY). 2×6 rafters at 24 in OC across a 10 ft span are adequate. Verify locally for higher snow zones.

## Out of scope (explicitly removed in v2)
- Cost estimator, CSV/PDF export, save/load
- Sliders, toggles, sidebar UI
- Wood storage, log splitter bay, divider wall, LVL header
- Helical pier and surface-pier foundation options
- Gable roof option, concrete pad floor option
