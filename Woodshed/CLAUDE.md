# Woodshed — Claude Notes

## Project overview
A single-file browser tool for designing a 3-bay outdoor storage shelter. No build step, no dependencies. Open `utv-storage-planner.html` directly in a browser. Deployed via GitHub Pages at `https://albybarber.github.io/ai-play-projects/Woodshed/utv-storage-planner.html`.

## File structure
```
utv-storage-planner.html   — the entire app (HTML, CSS, JS in one file)
README.md
CLAUDE.md
```

## Architecture
- **Single HTML file** — all CSS, JS, and markup inline. No framework, no bundler, no dependencies to install.
- **Canvas rendering** — all three views (Front, Top/Floor Plan, Side) drawn with the HTML5 Canvas 2D API. Everything redraws on every input change.
- **No state persistence** — intentional; it's a planning scratch pad. Values reset on page reload.

## Key design decisions baked in
- Structure: 3 bays — UTV bay, log splitter bay, wood storage bay
- UTV: Yamaha Wolverine X4 (~61" wide, ~75" tall)
- No interior post between UTV and splitter bays — spanned by an LVL header beam
- Roof: corrugated metal, shed slope (front low, rear high — runoff away from open face)
- Foundation: surface-mount post bases on concrete pads or helical piers (minimal excavation)

## Adjustable parameters (sidebar sliders)
- Total width, depth, front wall height, roof pitch
- UTV bay width, splitter bay width (wood bay auto-calculated as remainder)
- Toggles: wood rack divider wall, side walls, back wall, gravel under wood bay

## Fonts
Loaded from Google Fonts: `Bebas Neue` (display), `IBM Plex Mono` (labels/data), `IBM Plex Sans` (body). Degrades to monospace/sans-serif fallbacks offline.

## LVL sizing note
At the default 18 ft combined span (10 ft UTV + 8 ft splitter), a 3.5"×11.25" LVL is listed. For spans over 14 ft or high snow load areas, verify with a structural engineer — a 3.5"×14" or doubled LVL may be required.
