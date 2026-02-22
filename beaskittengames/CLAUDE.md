# Bea's Kitten Games — Claude Notes

## Project overview
A collection of pure HTML/CSS/JS browser games using Bea's personal cat photos. No build step, no dependencies. Deployed via GitHub Pages at `https://albybarber.github.io/ai-play-projects/beaskittengames/`.

## File structure
```
index.html       — game selection hub
memory.html      — Memory Match (1–2 player)
catcher.html     — Kitten Catcher (1 player, whack-a-mole)
puzzle.html      — Sliding Puzzle (1 player)
bingo.html       — Kitten Bingo (2 player)
photos/          — all kitten photos (JPG), referenced as relative paths
README.md
CLAUDE.md
```

## Style conventions
- **Colour palette:** pink (`#d4467a`, `#f48ab4`, `#fddde6`, `#fce4ec`) on cream (`#fef6f0`)
- **Font:** Georgia, serif throughout
- **Sparkles:** every page has a floating pink sparkle canvas animation — copy the `#sparkles` canvas + Sparkle class from any existing game
- **Header:** gradient `linear-gradient(135deg, #f8a4c8, #fddde6, #f9b0d0)` with a `← Home` button (`.home-btn`) absolute top-left
- **Buttons:** rounded pill shape, `border-radius: 30px`, `#d4467a` background
- **Tags on index:** `.tag.solo` = `#e84393`, `.tag.multi` = `#6c5ce7`

## When adding a new game
1. Create `<gamename>.html` following the colour/sparkle/header conventions above
2. Add a new `.game-card` entry in `index.html` — include a new preview class with a pastel gradient and update the CSS for it
3. Update `README.md` with a one-line description

## Bingo game specifics (`bingo.html`)
- **Word list (24 words):** Bea, Minton, Barbie, Ken, Cat, Kitten, Dog, Taco, Banana, Baseball, Go, Hide, Bingo, Rainbow, Cool, Cute, Kind, Love, To, Have, And, I, Dot, Meow
- 5×5 grid, FREE square at centre (index 12), kitten photo as the FREE cell image
- Setup screen on load: players enter names → glitter "Let's Play!" button → `startGame()` sets names and calls `newGame()`
- "New Game" / "Play Again" both call `showSetup()` to return to the name entry screen
- Win detection checks all rows, cols, and both diagonals via `WIN_LINES` array

## Photos
- Stored in `photos/` — use relative paths like `photos/filename.jpg`
- Pick photos randomly from a hardcoded `PHOTOS` array in each game that needs them
- Avoid reusing the same photo for multiple roles (player avatar, FREE square, win screen) in the same game — use an `exclude` list when picking
