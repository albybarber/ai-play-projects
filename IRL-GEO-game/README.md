# IRL GeoGuessr — Toronto Office Offsite 2026

A real-life GeoGuessr scoring and reveal app built for an office offsite event. Teams explore Toronto locations, photograph where they think each numbered image was taken, and score points for correct guesses. The organiser runs the reveal live at the end of the day.

## How it works

**Before the event**

1. Run `add_labels.py` to add numbered badges to the 12 location photos (output goes in `photos/labeled/`). Print and distribute those to players — they need to identify where each numbered photo was taken.
2. Drop the labeled prints at 12 locations around the city.

**During the event**

Teams photograph each location they visit and name their photo by the location number (e.g. `7.jpeg`). Place each team's photos in their folder:

```
photos/
  1/   ← Team 1 photos
  2/   ← Team 2 photos
  3/   ← Team 3 photos
```

**At the reveal (6PM)**

Open `leaderboard.html` via a local server:

```bash
python3 -m http.server 8080
# → http://localhost:8080/leaderboard.html
```

1. Click the team name chips to set custom team names.
2. Fill in scores: check **Matched** for each location a team got right, and **Bonus** if the whole team got it.
3. Hit **Start Reveal** for the full dramatic reveal sequence — each location card shows on a live map background with reference photo and team submission photos, then transitions to the winner announcement with confetti.

## Scoring

| Distance from office | Points |
|---|---|
| < 1 km | 5 |
| 1–2 km | 10 |
| 2–5 km | 20 |
| 5–10 km | 35 |
| 10–20 km | 55 |
| 130 km (Niagara) | 100 |

**+5 bonus** if all three teams correctly identified the same location.

## Locations

| # | Place | Distance |
|---|---|---|
| 1 | CN Tower | 0.9 km |
| 2 | Casa Loma | 3.9 km |
| 3 | St. Lawrence Market | 0.7 km |
| 4 | Scarborough Bluffs | 13.6 km |
| 5 | Kensington Market | 1.8 km |
| 6 | Niagara Falls | ~130 km |
| 7 | Nathan Phillips Square | 0.4 km |
| 8 | High Park | 6.7 km |
| 9 | Graffiti Alley | 1.5 km |
| 10 | Toronto Islands | 3.5 km |
| 11 | Distillery District | 1.7 km |
| 12 | Raccoon Artwork | 0.9 km |

## Files

```
IRL-GEO-game/
  leaderboard.html   — self-contained scoring & reveal app
  add_labels.py      — adds number badges to location photos
  photos/
    1.jpeg–12.jpeg   — reference location photos (unlabeled)
    1/               — Team 1 submission photos (named by location #)
    2/               — Team 2 submission photos
    3/               — Team 3 submission photos
```

## Requirements

- Python 3 + Pillow (for `add_labels.py`)
- Any modern browser served via local HTTP (not `file://`) — team submission photos load from the local filesystem
