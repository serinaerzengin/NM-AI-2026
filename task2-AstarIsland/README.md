# Task 2 - Astar Island

Predict terrain types on a 40x40 island grid using limited simulator queries.

## Setup

Dependencies are managed at the repo root with `uv`:

```bash
uv sync
```

## Authentication

1. Log in at https://app.ainm.no
2. Open browser DevTools → Application → Cookies
3. Copy the `access_token` value
4. Export it:

```bash
export AINM_TOKEN="your_jwt_token_here"
```

## Run

```bash
uv run python task2-AstarIsland/quickstart.py
```

This will:
1. Find the active round
2. Fetch round details (map size, seeds, initial states)
3. Query the simulator once (center viewport, seed 0)
4. Submit uniform baseline predictions for all seeds (scores ~1-5)

## Terrain Classes

| Index | Type       |
|-------|------------|
| 0     | Empty      |
| 1     | Settlement |
| 2     | Port       |
| 3     | Ruin       |
| 4     | Forest     |
| 5     | Mountain   |

## Key Constraints

- **50 queries per round** shared across all seeds
- Viewport size: 5-15 cells wide
- Predictions: `height x width x 6` probability tensor (must sum to 1.0 per cell)
- **Never assign probability 0.0** to any class — use a minimum floor (e.g. 0.01) and renormalize
