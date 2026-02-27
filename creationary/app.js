// ============================================
// Word Database (~25 words per category/difficulty)
// ============================================
const words = {
  nature: {
    easy: [
      "Tree", "Flower", "Dog", "Cat", "Fish", "Bird", "Sun", "Moon",
      "Star", "Butterfly", "Frog", "Snail", "Bee", "Mushroom", "Leaf",
      "Snake", "Turtle", "Rabbit", "Duck", "Ladybug", "Rainbow", "Cloud",
      "Mountain", "Cactus", "Whale"
    ],
    medium: [
      "Palm Tree", "Octopus", "Penguin", "Seahorse", "Scorpion",
      "Volcano", "Waterfall", "Coral Reef", "Porcupine", "Bat",
      "Crocodile", "Jellyfish", "Parrot", "Sunflower", "Dragonfly",
      "Owl", "Flamingo", "Peacock", "Starfish", "Hedgehog",
      "Chameleon", "Elephant", "Giraffe", "Deer", "Wolf"
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
      "Car", "Truck", "Bus", "Boat", "Train", "Airplane", "Bicycle",
      "Motorcycle", "Helicopter", "Rocket", "Tractor", "Taxi",
      "Ambulance", "Fire Truck", "Canoe", "Skateboard", "Scooter",
      "Van", "Jet", "Raft", "Sailboat", "Wagon", "Sled",
      "Hot Air Balloon", "Submarine"
    ],
    medium: [
      "Monster Truck", "Cruise Ship", "Fighter Jet", "Dump Truck",
      "Double Decker Bus", "Speedboat", "Hang Glider", "Bulldozer",
      "Forklift", "Gondola", "Hovercraft", "Ice Cream Truck",
      "Limousine", "Race Car", "Rickshaw", "Segway", "Tandem Bicycle",
      "Tow Truck", "Unicycle", "Yacht", "Cement Mixer", "Crane Truck",
      "Go-Kart", "Jet Ski", "Kayak"
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
      "House", "Castle", "Bridge", "Tower", "Church", "School",
      "Hospital", "Barn", "Lighthouse", "Tent", "Igloo", "Garage",
      "Shed", "Shop", "Hotel", "Hut", "Fence", "Gate", "Well",
      "Doghouse", "Treehouse", "Windmill", "Mailbox", "Chimney",
      "Playground"
    ],
    medium: [
      "Skyscraper", "Stadium", "Museum", "Pyramid", "Temple",
      "Prison", "Airport", "Train Station", "Clock Tower", "Greenhouse",
      "Library", "Observatory", "Palace", "Pier", "Water Tower",
      "Amusement Park", "Aquarium", "Fire Station", "Gas Station",
      "Shopping Mall", "Cabin", "Cottage", "Pagoda", "Arch", "Gazebo"
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
      "Chair", "Table", "Cup", "Hat", "Key", "Shoe", "Book",
      "Clock", "Lamp", "Guitar", "Sword", "Crown", "Camera",
      "Umbrella", "Ladder", "Glasses", "Candle", "Bell", "Flag",
      "Trophy", "Hammer", "Scissors", "Pencil", "Pizza", "Cake"
    ],
    medium: [
      "Telescope", "Typewriter", "Treasure Chest", "Robot",
      "Roller Coaster", "Pirate Flag", "Drum Set", "Chandelier",
      "Grandfather Clock", "Globe", "Anchor", "Binoculars",
      "Compass", "Hourglass", "Microscope", "Sewing Machine",
      "Thermometer", "Toaster", "Watering Can", "Wheelchair",
      "Backpack", "Birdhouse", "Cuckoo Clock", "Fishing Rod",
      "Spinning Wheel"
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
  diceRolled: false
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
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${name}`).classList.add('active');

  // Show/hide scoreboard bar during gameplay screens
  const bar = document.getElementById('scoreboard-bar');
  const gameScreens = ['turn', 'word', 'guess', 'select-guesser', 'score'];
  if (gameScreens.includes(name) && game.players.length > 0) {
    bar.classList.remove('hidden');
    updateScoreboardBar();
  } else {
    bar.classList.add('hidden');
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
  game.usedWords = new Set();
  game.turnsThisRound = 0;

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
    dice.className = `dice ${chosen}`;
    diceText.textContent = `${categoryIcons[chosen]} ${chosen.charAt(0).toUpperCase() + chosen.slice(1)}`;
    document.querySelector('.dice-hint').textContent = '';

    document.getElementById('difficulty-selection').classList.remove('hidden');
  }, 800);
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
}

function somebodyGuessed() {
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
  resolveGuess(null);
}

// ============================================
// Scoring
// ============================================
function resolveGuess(guesserIndex) {
  const pts = difficultyPoints[game.currentDifficulty];
  const builderIndex = game.currentPlayerIndex;
  let resultHTML = '';

  if (guesserIndex !== null) {
    game.scores[builderIndex] += pts;
    game.scores[guesserIndex] += pts;
    resultHTML = `
      <p>The word was: <strong>${game.currentWord}</strong></p>
      <p><span class="points-gained">${game.players[guesserIndex]} +${pts}</span> (guessed correctly)</p>
      <p><span class="points-gained">${game.players[builderIndex]} +${pts}</span> (builder)</p>
    `;
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
  showScreen('gameover');
}

function playAgain() {
  game.scores = new Array(game.players.length).fill(0);
  game.currentPlayerIndex = 0;
  game.currentRound = 1;
  game.usedWords = new Set();
  game.turnsThisRound = 0;
  startTurn();
}
