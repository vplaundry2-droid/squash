# Squash Sim (Desktop App)

A runnable desktop squash simulation with:
- Real-time player movement
- Ball physics (gravity, bounces, wall collisions)
- AI opponent behavior
- Core squash-style rally scoring logic to 11 (win by 2)

## Requirements
- Python 3.10+
- `pip install -r requirements.txt`

## Run
```bash
python3 main.py
```

## Controls
- Move: `WASD` or arrow keys
- Sprint: `SHIFT` (uses stamina)
- Drive shot: `J`
- Drop shot: `U`
- Lob shot: `I`
- Charge your shot: hold `K`
- Serve: `SPACE` (when you are server)
- Restart after game over: `R`
- Quit: `ESC`

## Rules implemented (simplified)
- Rally scoring: each rally awards one point.
- Game to 11, must win by 2.
- Ball can bounce once on floor; second bounce loses rally.
- Out/invalid return conditions award point to opponent.

## Realism upgrades in this version
- Ball drag + spin curve in the air.
- Spin influences side-wall and floor bounce behavior.
- Shot quality depends on timing and positioning (mishits are possible).
- Distinct shot types (drive, drop, lob) with different trajectories.
- Stamina + sprint management for a steeper learning curve.

## Notes
This is a realistic **prototype** focused on playable physics and squash flow. For truly photoreal graphics and advanced biomechanics, the next step is a full 3D engine pipeline (Unity/Unreal with mocap animations, advanced collision volumes, and PBR assets).
