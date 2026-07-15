# 🍁 Real Life Canadian GeoGuessr

**Event window:** 3:00 PM – 6:00 PM &nbsp;|&nbsp; **Start:** office, 302 Bay St &nbsp;|&nbsp; **Prize ceremony:** bar, 6:00 PM sharp

---

## The Rules

You'll get a packet of 12 photos of famous Toronto-area spots — no names, no addresses, just the image and a location number. Figure out where each photo was taken, get your whole team there, and take a photo recreating the shot in the same spot.

Different spots are worth different points based on distance from the office — close ones are quick and safe, far ones are high-risk, high-reward.

---

## Teams

Three teams: **Team Puce**, **Team Salmon**, and **Team Teal**. Each has a captain and a crew of hunters. Pick a team name and update it in the app before the clock starts.

---

## Scoring

You earn points for every location you successfully recreate. No penalty for a wrong guess — only lost time — so choose wisely.

| Location # | Points if matched |
|:---:|:---:|
| 1 | 5 |
| 2 | 20 |
| 3 | 5 |
| 4 | 55 |
| 5 | 10 |
| 6 | 100 |
| 7 | 5 |
| 8 | 35 |
| 9 | 10 |
| 10 | 20 |
| 11 | 10 |
| 12 | 5 |

**Bonus (+5 pts):** entire team (not just 1–2 people) visible in the recreation photo.

### Tie-Breakers

1. Highest total points
2. Most locations correctly matched
3. Earliest final submission timestamp

---

## Locations

| # | Place | Distance from office |
|:---:|---|:---:|
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

---

## How to Submit Photos

- Post to the offsite Slack channel: **#toronto-offsite-2026**
- Caption format: `[place number] + [team name]` — nothing else, no location names!
- **Hard cutoff: 6:00 PM.** Anything submitted after does not count.
- The leaderboard stays hidden during the event — big reveal happens live at the bar.

---

## Timeline

| Time | Event |
|---|---|
| 2:45 PM | Gather at the office — team names locked in |
| 3:00 PM | Photo packet released — clock starts |
| 6:00 PM | Hard submission cutoff — everyone at the bar |
| 6:00 PM | Leaderboard reveal + prizes 🏆 |

---

## Fair Play & Safety

- No sharing guesses or hints with other teams.
- No hired photographers, stock photos, or drone shots.
- Stay together as a team — no splitting up solo to cover more ground.
- Use whatever transport you like (walk, transit, rideshare, car) — obey traffic laws, don't rush for points.
- If a location is closed, under construction, or feels unsafe, skip it. No location is worth an injury.
- If the photo is in a road, stand on the pavement nearby — close enough counts.

---

## Prizes

🏆 **Grand prize:** team trophy + individual prizes

---

## Running the Reveal App

The organiser runs `leaderboard.html` live at the bar for the 6PM reveal.

**Start a local server** (required — photos won't load from `file://`):

```bash
cd IRL-GEO-game
python3 -m http.server 8080
# Open: http://localhost:8080/leaderboard.html
```

**Before the reveal:**
1. Click the team name chips to set the custom team names.
2. Fill in the score grid: check **Matched** for each location a team got right, and **Bonus** if the whole team is visible.

**At 6PM:** hit **Start Reveal** for the full dramatic sequence — each location card appears over a live map showing exactly where it was, with the reference photo and each team's submission photo, then transitions to the winner announcement with confetti.

**Adding team submission photos:**

Place each team's photos in their folder, named by location number:

```
photos/
  1/   ← Team 1 (e.g. 7.jpeg for location 7)
  2/   ← Team 2
  3/   ← Team 3
```

---

## Labeling the Photo Packets

To add number badges to the 12 reference photos for printing:

```bash
pip install pillow
python3 add_labels.py
# Output: photos/labeled/1.jpeg … 12.jpeg
```

---

Good luck — and remember… have fun! 🍁
