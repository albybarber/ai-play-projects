// ============================================
// Word Database (~25 words per category/difficulty)
// ============================================
const words = {
  nature: {
    easy: [
      "Tree", "Flower", "Dog", "Cat", "Fish", "Bird", "Sun", "Moon",
      "Star", "Frog", "Snail", "Mushroom", "Snake", "Turtle", "Duck",
      "Rainbow", "Cloud", "Mountain", "Cactus", "Rock", "Egg", "Bone",
      "Nest", "Log", "Hill"
    ],
    medium: [
      "Palm Tree", "Octopus", "Penguin", "Volcano", "Whale",
      "Crocodile", "Sunflower", "Owl", "Elephant", "Giraffe",
      "Deer", "Wolf", "Bat", "Butterfly", "Rabbit", "Parrot",
      "Starfish", "Ladybug", "Hedgehog", "Bee", "Leaf",
      "Seahorse", "Flamingo", "Jellyfish", "Porcupine"
    ],
    hard: [
      "Bonsai Tree", "Venus Flytrap", "Coral", "Narwhal", "Platypus",
      "Pangolin", "Tornado", "Aurora Borealis", "Tsunami", "Stalactite",
      "Toucan", "Komodo Dragon", "Axolotl", "Orchid", "Mangrove",
      "Seahorse Family", "Beehive", "Ant Colony", "Spider Web", "Bird Nest",
      "Fossil", "Geode", "Tidal Pool", "Quicksand", "Glacier"
    ]
  },
  vehicles: {
    easy: [
      "Car", "Truck", "Bus", "Boat", "Train", "Airplane", "Rocket",
      "Tractor", "Taxi", "Van", "Raft", "Sailboat", "Wagon", "Sled",
      "Canoe", "Jet", "Scooter", "Skateboard", "Fire Truck", "Ambulance",
      "Trailer", "Cart", "Ship", "Bike", "Sleigh"
    ],
    medium: [
      "Helicopter", "Submarine", "Monster Truck", "Dump Truck",
      "Bulldozer", "Race Car", "Tow Truck", "Speedboat",
      "Hot Air Balloon", "Motorcycle", "Cruise Ship", "Go-Kart",
      "Ice Cream Truck", "Kayak", "Forklift", "Crane Truck",
      "Cement Mixer", "Bicycle", "Yacht", "Double Decker Bus",
      "Limousine", "Jet Ski", "Unicycle", "Fighter Jet", "Gondola"
    ],
    hard: [
      "Catamaran", "Zeppelin", "Chariot", "Dog Sled", "Lunar Rover",
      "Pirate Ship", "Space Shuttle", "Stealth Bomber", "Snowmobile",
      "Zamboni", "Aircraft Carrier", "Armoured Tank", "Bobsled",
      "Cable Car", "Dune Buggy", "Hydrofoil", "Mars Rover",
      "Oil Tanker", "Rickshaw Bicycle", "Steam Locomotive",
      "Trebuchet", "Biplane", "Penny Farthing", "Amphibious Vehicle",
      "Cargo Ship"
    ]
  },
  buildings: {
    easy: [
      "House", "Tower", "Bridge", "Wall", "Fence", "Gate", "Tent",
      "Barn", "Shed", "Hut", "Igloo", "Well", "Steps", "Chimney",
      "Doghouse", "Castle", "Shop", "Garage", "Arch", "Ramp",
      "Door", "Roof", "Pillar", "Bench", "Table"
    ],
    medium: [
      "Church", "School", "Hospital", "Lighthouse", "Windmill",
      "Treehouse", "Hotel", "Pyramid", "Cabin", "Cottage",
      "Fire Station", "Gas Station", "Pier", "Playground",
      "Skyscraper", "Train Station", "Clock Tower", "Water Tower",
      "Library", "Palace", "Stadium", "Greenhouse", "Mailbox",
      "Gazebo", "Temple"
    ],
    hard: [
      "Colosseum", "Taj Mahal", "Eiffel Tower", "Great Wall",
      "Sydney Opera House", "Suspension Bridge", "Space Station",
      "Oil Rig", "Dam", "Aqueduct", "Amphitheatre", "Minaret",
      "Drawbridge", "Bunker", "Catacomb", "Flying Buttress",
      "Moat and Castle", "Parthenon", "Stonehenge", "Trojan Horse",
      "Underground Bunker", "Victorian Mansion", "Log Cabin",
      "Haunted House", "Skate Park"
    ]
  },
  things: {
    easy: [
      "Chair", "Table", "Cup", "Hat", "Bed", "Shoe", "Book",
      "Lamp", "Sword", "Crown", "Ladder", "Candle", "Flag",
      "Hammer", "Pencil", "Cake", "Box", "Bottle", "Bowl",
      "Spoon", "Cross", "Ring", "Arrow", "Boat", "Ball"
    ],
    medium: [
      "Guitar", "Clock", "Camera", "Umbrella", "Trophy",
      "Glasses", "Bell", "Scissors", "Pizza", "Key",
      "Robot", "Treasure Chest", "Anchor", "Toaster",
      "Backpack", "Birdhouse", "Watering Can", "Fishing Rod",
      "Wheelchair", "Globe", "Hourglass", "Telescope",
      "Pirate Flag", "Drum Set", "Thermometer"
    ],
    hard: [
      "DNA Helix", "Solar System", "Rube Goldberg Machine",
      "Swiss Army Knife", "Venetian Mask", "Chess Set",
      "Cuckoo Clock", "Gramophone", "Kaleidoscope", "Matryoshka Doll",
      "Periscope", "Rubik's Cube", "Sextant", "Stethoscope",
      "Sundial", "Abacus", "Dreamcatcher", "Lava Lamp",
      "Newton's Cradle", "Snow Globe", "Theremin", "Gyroscope",
      "Music Box", "Pinball Machine", "Jukebox"
    ]
  }
};

// ============================================
// Game State
// ============================================
let game = {
  players: [],
  scores: [],
  currentPlayerIndex: 0,
  currentRound: 1,
  totalRounds: 3,
  currentCategory: null,
  currentDifficulty: null,
  currentWord: null,
  usedWords: new Set(),
  turnsThisRound: 0,
  diceRolled: false,
  timerEnabled: true,
  timerDuration: 60,
  timerInterval: null,
  timerRemaining: 0,
  history: []
};

const categories = ["nature", "vehicles", "buildings", "things"];
const categoryIcons = {
  nature: "🌿",
  vehicles: "🚗",
  buildings: "🏠",
  things: "🔧"
};
const difficultyPoints = { easy: 1, medium: 2, hard: 3 };

// ============================================
// Screen Management
// ============================================
function showScreen(name) {
  const current = document.querySelector('.screen.active');
  const next = document.getElementById(`screen-${name}`);

  // Show/hide scoreboard bar during gameplay screens
  const bar = document.getElementById('scoreboard-bar');
  const gameScreens = ['turn', 'word', 'guess', 'select-guesser', 'score'];
  if (gameScreens.includes(name) && game.players.length > 0) {
    bar.classList.remove('hidden');
    updateScoreboardBar();
  } else {
    bar.classList.add('hidden');
  }

  if (current && current !== next) {
    current.classList.add('fading-out');
    current.classList.remove('visible');
    setTimeout(() => {
      current.classList.remove('active', 'fading-out');
      next.classList.add('active');
      // Force reflow so the opacity transition triggers
      void next.offsetWidth;
      next.classList.add('visible');
    }, 250);
  } else {
    if (current) current.classList.remove('active', 'visible');
    next.classList.add('active');
    void next.offsetWidth;
    next.classList.add('visible');
  }
}

// ============================================
// Running Scoreboard Bar
// ============================================
function updateScoreboardBar() {
  const container = document.getElementById('scoreboard-bar-inner');
  const maxScore = Math.max(...game.scores);

  container.innerHTML = game.players.map((name, i) => {
    const isActive = i === game.currentPlayerIndex;
    const isLeading = game.scores[i] === maxScore && maxScore > 0;
    let cls = 'sb-player';
    if (isActive) cls += ' active';
    if (isLeading) cls += ' leading';
    return `<div class="${cls}"><span>${name}</span><span class="sb-score">${game.scores[i]}</span></div>`;
  }).join('');
}

// ============================================
// Player Setup
// ============================================
function addPlayer() {
  const container = document.getElementById('player-inputs');
  const count = container.children.length;
  if (count >= 8) return;

  const row = document.createElement('div');
  row.className = 'player-input-row';
  row.innerHTML = `
    <span class="player-number">${count + 1}</span>
    <input type="text" class="player-name-input" placeholder="Player ${count + 1}" maxlength="20">
    <button class="btn-remove-player" onclick="removePlayer(this)" title="Remove">&times;</button>
  `;
  container.appendChild(row);

  if (count + 1 >= 8) {
    document.getElementById('btn-add-player').classList.add('hidden');
  }
}

function removePlayer(btn) {
  const container = document.getElementById('player-inputs');
  if (container.children.length <= 2) return;
  btn.parentElement.remove();
  document.getElementById('btn-add-player').classList.remove('hidden');
  // Re-number
  container.querySelectorAll('.player-input-row').forEach((row, i) => {
    row.querySelector('.player-number').textContent = i + 1;
    const input = row.querySelector('.player-name-input');
    if (!input.value) input.placeholder = `Player ${i + 1}`;
  });
}

// ============================================
// Start Game
// ============================================
function startGame() {
  const inputs = document.querySelectorAll('.player-name-input');
  const players = [];
  inputs.forEach((input, i) => {
    const name = input.value.trim() || `Player ${i + 1}`;
    players.push(name);
  });

  if (players.length < 2) return;

  game.players = players;
  game.scores = new Array(players.length).fill(0);
  game.currentPlayerIndex = 0;
  game.currentRound = 1;
  game.totalRounds = parseInt(document.getElementById('rounds-select').value);
  game.timerEnabled = document.getElementById('timer-enabled').checked;
  game.timerDuration = parseInt(document.getElementById('timer-duration').value);
  game.usedWords = new Set();
  game.turnsThisRound = 0;
  game.history = [];

  startTurn();
}

// ============================================
// Turn Management
// ============================================
function startTurn() {
  game.diceRolled = false;
  game.currentCategory = null;
  game.currentDifficulty = null;
  game.currentWord = null;

  const player = game.players[game.currentPlayerIndex];
  document.getElementById('builder-name').textContent = player;
  document.getElementById('round-info').textContent =
    `Round ${game.currentRound} of ${game.totalRounds}`;

  // Reset dice
  const dice = document.getElementById('dice');
  dice.className = 'dice';
  document.getElementById('dice-text').textContent = '?';
  document.querySelector('.dice-hint').textContent = 'Tap to roll category';

  // Hide difficulty
  document.getElementById('difficulty-selection').classList.add('hidden');

  showScreen('turn');
}

// ============================================
// Dice Roll
// ============================================
function rollDice() {
  if (game.diceRolled) return;
  game.diceRolled = true;

  const dice = document.getElementById('dice');
  const diceText = document.getElementById('dice-text');

  // Shake for anticipation first
  dice.classList.add('shaking');

  setTimeout(() => {
    dice.classList.remove('shaking');
    dice.classList.add('rolling');

    let ticks = 0;
    const interval = setInterval(() => {
      const cat = categories[ticks % 4];
      diceText.textContent = `${categoryIcons[cat]} ${cat.charAt(0).toUpperCase() + cat.slice(1)}`;
      dice.className = `dice rolling ${cat}`;
      ticks++;
    }, 80);

    setTimeout(() => {
      clearInterval(interval);
      const chosen = categories[Math.floor(Math.random() * 4)];
      game.currentCategory = chosen;
      dice.className = `dice landed ${chosen}`;
      diceText.textContent = `${categoryIcons[chosen]} ${chosen.charAt(0).toUpperCase() + chosen.slice(1)}`;
      document.querySelector('.dice-hint').textContent = '';

      // Remove landed class after animation completes
      setTimeout(() => dice.classList.remove('landed'), 350);

      document.getElementById('difficulty-selection').classList.remove('hidden');
    }, 500);
  }, 300);
}

// ============================================
// Difficulty Selection & Word Pick
// ============================================
function selectDifficulty(difficulty) {
  game.currentDifficulty = difficulty;
  game.currentWord = pickWord(game.currentCategory, difficulty);

  const catBadge = document.getElementById('category-badge');
  catBadge.textContent = `${categoryIcons[game.currentCategory]} ${game.currentCategory}`;
  catBadge.className = `category-badge ${game.currentCategory}`;

  const diffBadge = document.getElementById('difficulty-badge');
  diffBadge.textContent = `${difficulty} (${difficultyPoints[difficulty]} pt${difficultyPoints[difficulty] > 1 ? 's' : ''})`;
  diffBadge.className = `difficulty-badge ${difficulty}`;

  document.getElementById('secret-word').textContent = game.currentWord;

  const wordCard = document.getElementById('word-card');
  wordCard.classList.add('word-hidden');
  document.getElementById('word-hint').textContent = 'Only the builder should look!';

  showScreen('word');
}

function pickWord(category, difficulty) {
  const pool = words[category][difficulty].filter(w => !game.usedWords.has(w));
  if (pool.length === 0) {
    words[category][difficulty].forEach(w => game.usedWords.delete(w));
    return pickWord(category, difficulty);
  }
  const word = pool[Math.floor(Math.random() * pool.length)];
  game.usedWords.add(word);
  return word;
}

// ============================================
// Word Reveal (Tap to peek)
// ============================================
function toggleWord() {
  const card = document.getElementById('word-card');
  const hint = document.getElementById('word-hint');
  card.classList.toggle('word-hidden');
  if (card.classList.contains('word-hidden')) {
    hint.textContent = 'Only the builder should look!';
  } else {
    hint.textContent = 'Tap card to hide again';
  }
}

// ============================================
// Guessing Phase
// ============================================
function startGuessing() {
  const catBadge = document.getElementById('guess-category-badge');
  catBadge.textContent = `${categoryIcons[game.currentCategory]} ${game.currentCategory}`;
  catBadge.className = `category-badge ${game.currentCategory}`;

  const diffBadge = document.getElementById('guess-difficulty-badge');
  diffBadge.textContent = `${game.currentDifficulty} (${difficultyPoints[game.currentDifficulty]} pt${difficultyPoints[game.currentDifficulty] > 1 ? 's' : ''})`;
  diffBadge.className = `difficulty-badge ${game.currentDifficulty}`;

  document.getElementById('guess-builder-name').textContent =
    game.players[game.currentPlayerIndex];

  showScreen('guess');
  startTimer();
}

// ============================================
// Countdown Timer
// ============================================
function startTimer() {
  stopTimer();
  const container = document.getElementById('timer-container');
  if (!game.timerEnabled) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');
  container.classList.remove('warning');

  const ring = document.getElementById('timer-ring-progress');
  const text = document.getElementById('timer-text');
  const circumference = 2 * Math.PI * 45; // r=45
  game.timerRemaining = game.timerDuration;

  ring.classList.remove('warning');
  ring.style.strokeDashoffset = '0';
  text.textContent = game.timerRemaining;

  game.timerInterval = setInterval(() => {
    game.timerRemaining--;
    text.textContent = game.timerRemaining;

    const progress = 1 - (game.timerRemaining / game.timerDuration);
    ring.style.strokeDashoffset = (circumference * progress).toFixed(2);

    if (game.timerRemaining <= 10) {
      ring.classList.add('warning');
      container.classList.add('warning');
    }

    if (game.timerRemaining <= 0) {
      stopTimer();
      nobodyGuessed();
    }
  }, 1000);
}

function stopTimer() {
  if (game.timerInterval) {
    clearInterval(game.timerInterval);
    game.timerInterval = null;
  }
  const container = document.getElementById('timer-container');
  container.classList.remove('warning');
}

function somebodyGuessed() {
  stopTimer();
  const container = document.getElementById('guesser-buttons');
  container.innerHTML = '';
  game.players.forEach((name, i) => {
    if (i === game.currentPlayerIndex) return;
    const btn = document.createElement('button');
    btn.className = 'btn-guesser';
    btn.textContent = name;
    btn.onclick = () => resolveGuess(i);
    container.appendChild(btn);
  });
  showScreen('select-guesser');
}

function nobodyGuessed() {
  stopTimer();
  resolveGuess(null);
}

// ============================================
// Scoring
// ============================================
function resolveGuess(guesserIndex) {
  const pts = difficultyPoints[game.currentDifficulty];
  const builderIndex = game.currentPlayerIndex;

  // Record history
  game.history.push({
    round: game.currentRound,
    builder: game.players[builderIndex],
    category: game.currentCategory,
    difficulty: game.currentDifficulty,
    word: game.currentWord,
    guesser: guesserIndex !== null ? game.players[guesserIndex] : null,
    points: pts
  });

  let resultHTML = '';

  if (guesserIndex !== null) {
    game.scores[builderIndex] += pts;
    game.scores[guesserIndex] += pts;
    resultHTML = `
      <p>The word was: <strong>${game.currentWord}</strong></p>
      <p><span class="points-gained points-animate">${game.players[guesserIndex]} +${pts}</span> (guessed correctly)</p>
      <p><span class="points-gained points-animate" style="animation-delay:0.2s">${game.players[builderIndex]} +${pts}</span> (builder)</p>
    `;
    // Fire confetti on correct guess
    setTimeout(() => launchConfetti(), 300);
  } else {
    resultHTML = `
      <p>The word was: <strong>${game.currentWord}</strong></p>
      <p>Nobody guessed it — no points this round.</p>
    `;
  }

  document.getElementById('score-result').innerHTML = resultHTML;
  updateFullScoreboard('scoreboard-full');
  updateScoreboardBar();
  showScreen('score');
}

// ============================================
// Confetti
// ============================================
function launchConfetti() {
  const container = document.createElement('div');
  container.className = 'confetti-container';
  document.body.appendChild(container);

  const colors = ['#d01012', '#0057a8', '#ffd700', '#00852b', '#f57c20'];
  const shapes = ['square', 'circle'];

  for (let i = 0; i < 40; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    const color = colors[Math.floor(Math.random() * colors.length)];
    const shape = shapes[Math.floor(Math.random() * shapes.length)];
    piece.style.background = color;
    piece.style.left = Math.random() * 100 + '%';
    piece.style.animationDelay = Math.random() * 0.5 + 's';
    piece.style.animationDuration = (1 + Math.random() * 1) + 's';
    if (shape === 'circle') piece.style.borderRadius = '50%';
    container.appendChild(piece);
  }

  setTimeout(() => container.remove(), 2500);
}

function updateFullScoreboard(containerId) {
  const sorted = game.players
    .map((name, i) => ({ name, score: game.scores[i] }))
    .sort((a, b) => b.score - a.score);

  const container = document.getElementById(containerId);
  container.innerHTML = sorted.map((p, i) => {
    const isFirst = i === 0 && p.score > 0;
    return `
      <div class="score-row${isFirst ? ' first-place' : ''}">
        <span class="rank">#${i + 1}</span>
        <span class="name">${p.name}</span>
        <span class="score">${p.score}</span>
      </div>
    `;
  }).join('');
}

// ============================================
// How to Play
// ============================================
function showHowToPlay() {
  document.getElementById('how-to-play').classList.remove('hidden');
}

function hideHowToPlay() {
  document.getElementById('how-to-play').classList.add('hidden');
}

function closeHowToPlay(e) {
  if (e.target === e.currentTarget) hideHowToPlay();
}

// ============================================
// Modal / Confirmation
// ============================================
function showModal(message, onConfirm) {
  const modal = document.getElementById('confirm-modal');
  document.getElementById('confirm-message').textContent = message;
  modal.classList.remove('hidden');

  const yesBtn = document.getElementById('confirm-yes');
  // Clone to remove old listeners
  const newYes = yesBtn.cloneNode(true);
  yesBtn.parentNode.replaceChild(newYes, yesBtn);
  newYes.addEventListener('click', () => {
    hideModal();
    onConfirm();
  });
}

function hideModal() {
  document.getElementById('confirm-modal').classList.add('hidden');
}

function closeModal(e) {
  if (e.target === e.currentTarget) hideModal();
}

function confirmEndGame() {
  showModal('End the game early?', () => {
    stopTimer();
    endGame();
  });
}

function confirmGoHome() {
  showModal('Return to the home screen?', () => {
    stopTimer();
    showScreen('home');
  });
}

function backToDifficulty() {
  showScreen('turn');
}

// ============================================
// Skip Turn
// ============================================
function skipTurn() {
  nextTurn();
}

// ============================================
// Next Turn / Game Over
// ============================================
function nextTurn() {
  game.currentPlayerIndex++;
  game.turnsThisRound++;

  if (game.turnsThisRound >= game.players.length) {
    game.turnsThisRound = 0;
    game.currentPlayerIndex = 0;
    game.currentRound++;

    if (game.currentRound > game.totalRounds) {
      endGame();
      return;
    }
  }

  if (game.currentPlayerIndex >= game.players.length) {
    game.currentPlayerIndex = 0;
  }

  startTurn();
}

function endGame() {
  const sorted = game.players
    .map((name, i) => ({ name, score: game.scores[i] }))
    .sort((a, b) => b.score - a.score);

  const winner = sorted[0];
  const tied = sorted.filter(p => p.score === winner.score);

  let winnerHTML = '';
  if (winner.score === 0) {
    winnerHTML = `<span class="trophy">🏆</span>No winners this time!`;
  } else if (tied.length > 1) {
    winnerHTML = `<span class="trophy">🏆</span>It's a tie!<br>${tied.map(p => p.name).join(' & ')}`;
  } else {
    winnerHTML = `<span class="trophy">🏆</span>${winner.name} wins!<br>with ${winner.score} points`;
  }

  document.getElementById('winner-display').innerHTML = winnerHTML;
  updateFullScoreboard('final-scores');
  renderGameSummary();
  showScreen('gameover');
}

function renderGameSummary() {
  const h = game.history;
  const totalCorrect = h.filter(e => e.guesser !== null).length;
  const hardGuessed = h.filter(e => e.guesser !== null && e.difficulty === 'hard');
  const hardestWord = hardGuessed.length > 0 ? hardGuessed[hardGuessed.length - 1].word : '—';
  const maxPts = h.reduce((max, e) => e.guesser !== null && e.points > max ? e.points : max, 0);

  const statsHTML = `
    <div class="stat-card"><div class="stat-value">${totalCorrect}</div><div class="stat-label">Correct Guesses</div></div>
    <div class="stat-card"><div class="stat-value">${hardestWord}</div><div class="stat-label">Hardest Guessed</div></div>
    <div class="stat-card"><div class="stat-value">${maxPts > 0 ? maxPts + 'pts' : '—'}</div><div class="stat-label">Best Turn</div></div>
  `;
  document.getElementById('game-stats').innerHTML = statsHTML;

  const historyHTML = h.map(e => {
    const result = e.guesser
      ? `<span class="history-result correct">${e.guesser} +${e.points}</span>`
      : `<span class="history-result">No guess</span>`;
    return `
      <div class="history-row">
        <span class="category-badge ${e.category}" style="padding:0.2rem 0.5rem;font-size:0.7rem">${categoryIcons[e.category]}</span>
        <span class="history-word">${e.word}</span>
        <span style="font-size:0.75rem;color:var(--text-muted)">${e.builder}</span>
        ${result}
      </div>
    `;
  }).join('');
  document.getElementById('game-history').innerHTML = historyHTML;
}

function playAgain() {
  game.scores = new Array(game.players.length).fill(0);
  game.currentPlayerIndex = 0;
  game.currentRound = 1;
  game.usedWords = new Set();
  game.turnsThisRound = 0;
  game.history = [];
  startTurn();
}

// ============================================
// Keyboard Support
// ============================================
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;

  // Setup screen: Enter starts game (unless in an input that's not the last)
  const setupScreen = document.getElementById('screen-setup');
  if (setupScreen.classList.contains('active')) {
    const inputs = setupScreen.querySelectorAll('.player-name-input');
    const focused = document.activeElement;
    const focusedIndex = Array.from(inputs).indexOf(focused);
    if (focusedIndex >= 0 && focusedIndex < inputs.length - 1) {
      inputs[focusedIndex + 1].focus();
    } else {
      startGame();
    }
    e.preventDefault();
    return;
  }

  // Score screen: Enter advances to next turn
  const scoreScreen = document.getElementById('screen-score');
  if (scoreScreen.classList.contains('active')) {
    nextTurn();
    e.preventDefault();
  }
});
