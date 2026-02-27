# Make-a-Thing — Claude Notes

## Project overview
Companion web app for the physical LEGO Creationary board game. Handles game flow, scoring, category/word selection, and difficulty while players build with real LEGO bricks. Pure HTML/CSS/JS, no dependencies. Deployed via GitHub Pages at `https://albybarber.github.io/ai-play-projects/make-a-thing/`.

## File structure
```
index.html      — app shell, all screen sections
style.css       — LEGO-themed styling, animations, responsive design
app.js          — game logic, state management, word database (300 words)
rules.pdf       — original board game rules reference
CLAUDE.md
```

## Game flow
1. **Home** → 2. **Player Setup** (2-8 players, rounds config) → 3. **Turn Screen** (dice roll for category, difficulty pick) → 4. **Word Reveal** (tap to peek/hide) → 5. **Guessing Phase** → 6. **Score Update** → repeat → 7. **Game Over**

## Style conventions
- **Theme:** LEGO-inspired — bright, playful, brick-like
- **Font:** Fredoka (Google Fonts), weights 400/600/700
- **Colours:** LEGO red `#d01012`, blue `#0057a8`, yellow `#ffd700`, green `#00852b`, orange `#f57c20`
- **Category colours:** Nature=green, Vehicles=blue, Buildings=red, Things=orange
- **Background:** warm cream `#fef9e7` with subtle dot grid
- **Cards:** white with bottom box-shadow for 3D brick depth effect (`var(--card-shadow)`)
- **Buttons:** 3D press effect — box-shadow shrinks + translateY on `:active`
- **LEGO studs:** decorative circular elements on key cards (`.stud-row > .stud`)

## Architecture
- Single-page app: screens toggled via `showScreen(name)` adding/removing `.active` class
- Game state in a single `game` object (players, scores, round, category, difficulty, word, usedWords set)
- **Running scoreboard:** fixed bottom bar (`.scoreboard-bar`) visible on all gameplay screens, auto-updates via `updateScoreboardBar()`
- **Word database:** JS object `words[category][difficulty]` — 25 words each, 300 total
- **No duplicates:** `game.usedWords` Set tracks used words; resets per category/difficulty when exhausted

## Key functions
- `showScreen(name)` — screen navigation + scoreboard bar visibility
- `rollDice()` — animated category selection
- `selectDifficulty(level)` — picks word, transitions to reveal screen
- `pickWord(category, difficulty)` — random unused word selection
- `toggleWord()` — tap to reveal/hide mechanic
- `resolveGuess(guesserIndex)` — scoring logic (both builder and guesser get points, or null for nobody)
- `updateScoreboardBar()` — refreshes the persistent bottom scoreboard
- `updateFullScoreboard(containerId)` — sorted rankings for score/gameover screens

## Scoring
- Easy = 1pt, Medium = 2pts, Hard = 3pts
- Correct guess: both guesser AND builder receive points
- Nobody guesses: no points awarded
