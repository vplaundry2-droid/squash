# Squash Sim (Browser Game)

This project now runs as a browser-based squash game using HTML5 Canvas and JavaScript.

## Run
```bash
python3 start.py
```
Then open `http://localhost:8000` in your browser.

## Controls
- Move: `WASD` or arrow keys
- Sprint: `SHIFT` (uses stamina)
- Drive shot: `J`
- Drop shot: `U`
- Lob shot: `I`
- Charge your shot: hold `K`
- Serve: `SPACE` (when you are server)
- Restart after game over: `R`

## Rules implemented (simplified)
- Rally scoring: each rally awards one point.
- Game to 11, must win by 2.
- Ball can bounce once on floor; second bounce loses rally.
