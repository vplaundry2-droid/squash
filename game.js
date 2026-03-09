const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const WIDTH = canvas.width;
const HEIGHT = canvas.height;

const SCALE = 90;
const COURT_W = Math.round(6.4 * SCALE);
const COURT_L = Math.round(9.75 * SCALE);
const LEFT_WALL_X = (WIDTH - COURT_W) / 2;
const RIGHT_WALL_X = LEFT_WALL_X + COURT_W;
const FRONT_WALL_Y = 80;
const BACK_WALL_Y = FRONT_WALL_Y + COURT_L;
const FLOOR_Y = HEIGHT - 70;
const TIN_Y = FLOOR_Y - Math.round(0.48 * SCALE);
const OUT_LINE_Y = FLOOR_Y - Math.round(4.57 * SCALE);
const SERVICE_Y = FLOOR_Y - Math.round(1.78 * SCALE);

const PLAYER_RADIUS = 28;
const BALL_RADIUS = Math.round(0.035 * SCALE);
const HIT_RANGE = 115;

const keys = new Set();
window.addEventListener('keydown', (e) => keys.add(e.code));
window.addEventListener('keyup', (e) => keys.delete(e.code));

const score = { player: 0, ai: 0, server: 'player', gameOver: false, winner: null };

const player = { x: WIDTH * 0.44, y: FLOOR_Y - PLAYER_RADIUS, vx: 0, vy: 0, stamina: 1, charge: 0 };
const ai = { x: WIDTH * 0.56, y: FLOOR_Y - PLAYER_RADIUS, vx: 0, vy: 0 };
const ball = { x: WIDTH / 2, y: FLOOR_Y - 180, vx: 0, vy: 0, inPlay: false, bounces: 0, hitBy: null, frontWallHit: false, spin: 0 };

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function len(x, y) { return Math.hypot(x, y); }

function resetServe() {
  ball.x = score.server === 'player' ? WIDTH * 0.42 : WIDTH * 0.58;
  ball.y = FLOOR_Y - 120;
  ball.vx = ball.vy = 0;
  ball.inPlay = false;
  ball.bounces = 0;
  ball.frontWallHit = false;
  ball.hitBy = null;
  ball.spin = 0;
}

function serve(fromPlayer) {
  const speed = 16 + Math.random() * 4;
  const dir = fromPlayer ? (80 * Math.PI / 180) : (100 * Math.PI / 180);
  ball.vx = Math.cos(dir) * speed;
  ball.vy = -Math.sin(dir) * speed;
  ball.inPlay = true;
  ball.bounces = 0;
  ball.frontWallHit = false;
  ball.spin = (Math.random() * 2 - 1);
  ball.hitBy = fromPlayer ? 'player' : 'ai';
}

function swing(hitter, shot = 'drive', charge = 0) {
  const actor = hitter === 'player' ? player : ai;
  const dx = ball.x - actor.x;
  const dy = ball.y - actor.y;
  const d = len(dx, dy);
  if (d > HIT_RANGE) return false;

  let basePower = 20, side = (Math.random() * 1.3 - 0.65), lift = -(3.5 + Math.random() * 3);
  if (shot === 'drop') { basePower = 10 + Math.random() * 3; side = (Math.random() * 0.5 - 0.25); lift = -(2 + Math.random() * 2); }
  if (shot === 'lob') { basePower = 15 + Math.random() * 3; side = (Math.random() * 0.7 - 0.35); lift = -(9 + Math.random() * 3); }

  const power = basePower + charge * 7.5;
  ball.vx = side * power;
  ball.vy = -power + lift;

  if (ball.y > FLOOR_Y - 140) ball.vy -= (3 + Math.random() * 2.5);
  ball.spin = side * 4 + charge * (hitter === 'player' ? 1.4 : 0.8);
  ball.inPlay = true;
  ball.bounces = 0;
  ball.hitBy = hitter;
  ball.frontWallHit = false;
  return true;
}

function awardPoint(winner) {
  score[winner] += 1;
  score.server = winner;
  if ((score.player >= 11 || score.ai >= 11) && Math.abs(score.player - score.ai) >= 2) {
    score.gameOver = true;
    score.winner = winner;
  }
  resetServe();
}

function update(dt) {
  // player move
  let dx = 0, dy = 0;
  if (keys.has('KeyA') || keys.has('ArrowLeft')) dx -= 1;
  if (keys.has('KeyD') || keys.has('ArrowRight')) dx += 1;
  if (keys.has('KeyW') || keys.has('ArrowUp')) dy -= 1;
  if (keys.has('KeyS') || keys.has('ArrowDown')) dy += 1;
  const moveLen = len(dx, dy) || 1;
  dx /= moveLen; dy /= moveLen;

  const sprint = (keys.has('ShiftLeft') || keys.has('ShiftRight')) && player.stamina > 0.08;
  const topSpeed = (6.5 * (sprint ? 1.28 : 1)) * SCALE;
  if (sprint && (dx || dy)) player.stamina = Math.max(0, player.stamina - 0.55 * dt);
  else player.stamina = Math.min(1, player.stamina + 0.22 * dt);

  player.vx += ((dx * topSpeed) - player.vx) * Math.min(1, 30 * dt);
  player.vy += ((dy * topSpeed) - player.vy) * Math.min(1, 30 * dt);
  if (!dx) player.vx *= Math.max(0, 1 - 12 * dt);
  if (!dy) player.vy *= Math.max(0, 1 - 12 * dt);
  player.x += player.vx * dt;
  player.y += player.vy * dt;
  player.x = clamp(player.x, LEFT_WALL_X + PLAYER_RADIUS, RIGHT_WALL_X - PLAYER_RADIUS);
  player.y = clamp(player.y, FRONT_WALL_Y + 230, BACK_WALL_Y - PLAYER_RADIUS);

  // ai
  const tx = ball.inPlay ? clamp(ball.x + (Math.random() * 40 - 20), LEFT_WALL_X + PLAYER_RADIUS, RIGHT_WALL_X - PLAYER_RADIUS) : WIDTH * 0.56;
  const ty = ball.inPlay ? clamp(ball.y + 120, FRONT_WALL_Y + 230, BACK_WALL_Y - PLAYER_RADIUS) : FRONT_WALL_Y + COURT_L * 0.42;
  const adx = tx - ai.x, ady = ty - ai.y;
  const al = len(adx, ady) || 1;
  ai.vx += (((adx / al) * 6.5 * 0.86 * SCALE) - ai.vx) * Math.min(1, 30 * 0.8 * dt);
  ai.vy += (((ady / al) * 6.5 * 0.86 * SCALE) - ai.vy) * Math.min(1, 30 * 0.8 * dt);
  ai.x += ai.vx * dt;
  ai.y += ai.vy * dt;
  ai.x = clamp(ai.x, LEFT_WALL_X + PLAYER_RADIUS, RIGHT_WALL_X - PLAYER_RADIUS);
  ai.y = clamp(ai.y, FRONT_WALL_Y + 230, BACK_WALL_Y - PLAYER_RADIUS);

  // inputs
  if (keys.has('KeyK')) player.charge = Math.min(1, player.charge + 1.7 * dt);
  else player.charge = Math.max(0, player.charge - 1.4 * dt);

  if (!score.gameOver) {
    if (!ball.inPlay) {
      if (score.server === 'player' && keys.has('Space')) serve(true);
      else if (score.server === 'ai') serve(false);
    }

    if (keys.has('KeyJ')) { swing('player', 'drive', player.charge); player.charge = 0; }
    if (keys.has('KeyU')) { swing('player', 'drop', player.charge * 0.5); player.charge = 0; }
    if (keys.has('KeyI')) { swing('player', 'lob', player.charge); player.charge = 0; }

    if (ball.inPlay && len(ball.x - ai.x, ball.y - ai.y) < HIT_RANGE * 0.9 && ball.y > FRONT_WALL_Y + 140 && Math.random() < 0.18) {
      let shot = 'drive';
      if (ball.y < FRONT_WALL_Y + 260) shot = 'lob';
      else if (Math.random() < 0.22) shot = 'drop';
      swing('ai', shot, Math.random() * 0.6);
    }
  }

  // physics
  if (ball.inPlay) {
    ball.vy += 28 * dt;
    const drag = Math.max(0, 1 - 0.08 * dt);
    ball.vx *= drag; ball.vy *= drag;
    ball.vx += ball.spin * 6 * dt;
    ball.x += ball.vx * SCALE * dt;
    ball.y += ball.vy * SCALE * dt;
    ball.spin *= Math.max(0, 1 - 0.92 * dt);

    if (ball.x - BALL_RADIUS < LEFT_WALL_X) { ball.x = LEFT_WALL_X + BALL_RADIUS; ball.vx *= -0.92; ball.spin *= -0.7; }
    if (ball.x + BALL_RADIUS > RIGHT_WALL_X) { ball.x = RIGHT_WALL_X - BALL_RADIUS; ball.vx *= -0.92; ball.spin *= -0.7; }
    if (ball.y - BALL_RADIUS < FRONT_WALL_Y) { ball.y = FRONT_WALL_Y + BALL_RADIUS; ball.vy *= -0.96; ball.frontWallHit = true; }
    if (ball.y + BALL_RADIUS > BACK_WALL_Y) { ball.y = BACK_WALL_Y - BALL_RADIUS; ball.vy *= -0.85; }
    if (ball.y + BALL_RADIUS >= FLOOR_Y) {
      ball.y = FLOOR_Y - BALL_RADIUS;
      ball.vy *= -0.68;
      ball.vx = ball.vx * 0.94 + ball.spin * 1.8;
      ball.bounces += 1;
      ball.spin *= 0.75;
      if (Math.abs(ball.vy) < 1.6) ball.vy = 0;
    }

    const fault = ball.bounces > 1 || (ball.y > BACK_WALL_Y - 4 && !ball.frontWallHit);
    if (fault || ball.y < OUT_LINE_Y - 15) {
      const winner = ball.hitBy === 'player' ? 'ai' : 'player';
      awardPoint(winner);
    }
  }

  if (score.gameOver && keys.has('KeyR')) {
    score.player = score.ai = 0;
    score.server = 'player';
    score.gameOver = false;
    score.winner = null;
    player.charge = 0;
    player.stamina = 1;
    resetServe();
  }
}

function draw() {
  ctx.fillStyle = '#12161f';
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  ctx.fillStyle = '#232e41';
  ctx.fillRect(LEFT_WALL_X, FRONT_WALL_Y, COURT_W, COURT_L);
  ctx.fillStyle = '#5d6576';
  ctx.fillRect(LEFT_WALL_X, FLOOR_Y, COURT_W, HEIGHT - FLOOR_Y);

  ctx.strokeStyle = '#f0f0f0';
  ctx.strokeRect(LEFT_WALL_X, FRONT_WALL_Y, COURT_W, COURT_L);
  ctx.beginPath();
  ctx.moveTo(LEFT_WALL_X, TIN_Y); ctx.lineTo(RIGHT_WALL_X, TIN_Y);
  ctx.moveTo(LEFT_WALL_X, SERVICE_Y); ctx.lineTo(RIGHT_WALL_X, SERVICE_Y);
  ctx.moveTo(LEFT_WALL_X, OUT_LINE_Y); ctx.lineTo(RIGHT_WALL_X, OUT_LINE_Y);
  ctx.stroke();

  ctx.fillStyle = '#242424';
  ctx.beginPath(); ctx.arc(ball.x, FLOOR_Y - 2, BALL_RADIUS + 4, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff15a';
  ctx.beginPath(); ctx.arc(ball.x, ball.y, BALL_RADIUS, 0, Math.PI * 2); ctx.fill();

  ctx.fillStyle = '#58c8ff';
  ctx.beginPath(); ctx.arc(player.x, player.y, PLAYER_RADIUS, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#ff7f7f';
  ctx.beginPath(); ctx.arc(ai.x, ai.y, PLAYER_RADIUS, 0, Math.PI * 2); ctx.fill();

  ctx.fillStyle = '#f5f5f5';
  ctx.font = 'bold 38px Consolas, monospace';
  ctx.fillText(`You ${score.player}  -  ${score.ai} AI`, 40, 50);

  ctx.font = '22px Consolas, monospace';
  ctx.fillStyle = '#d0d6e0';
  ctx.fillText(`Server: ${score.server.toUpperCase()}`, 40, 80);

  ctx.fillStyle = '#383b45';
  ctx.fillRect(40, 102, 210, 12);
  ctx.fillStyle = '#75de8a';
  ctx.fillRect(40, 102, 210 * player.stamina, 12);

  ctx.fillStyle = '#383b45';
  ctx.fillRect(40, 122, 210, 10);
  ctx.fillStyle = '#f2c65f';
  ctx.fillRect(40, 122, 210 * player.charge, 10);

  if (score.gameOver) {
    ctx.font = 'bold 38px Consolas, monospace';
    ctx.fillStyle = '#ffe678';
    ctx.fillText(`${score.winner.toUpperCase()} WINS! Press R to restart`, WIDTH / 2 - 320, 130);
  }
}

resetServe();
let last = performance.now();
function loop(ts) {
  const dt = Math.min(0.033, (ts - last) / 1000);
  last = ts;
  update(dt);
  draw();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
