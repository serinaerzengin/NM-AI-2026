"""Astar Island simulator v2 — probabilistic state machine.

Instead of simulating food/population mechanics, model settlements as
having per-year probabilities of: surviving, expanding, and collapsing.
These probabilities are the parameters we optimize.

This avoids the food-accumulation problem and directly captures the
observable outcomes.
"""

from dataclasses import dataclass
import numpy as np

OCEAN = 10
PLAINS = 11
EMPTY = 0
SETTLEMENT = 1
PORT = 2
RUIN = 3
FOREST = 4
MOUNTAIN = 5

GRID_TO_CLASS = {10: 0, 11: 0, 0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
NUM_CLASSES = 6

DIRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class SimParams:
    # Per-year probability a settlement expands to a new cell
    expand_prob: float = 0.15
    # Max expansion distance (manhattan)
    expand_range: int = 4
    # Per-year probability a settlement collapses
    collapse_base: float = 0.08
    # Collapse reduction per adjacent forest (forests protect)
    collapse_forest_bonus: float = 0.01
    # Per-year probability a ruin becomes forest
    ruin_to_forest: float = 0.08
    # Per-year probability a ruin becomes empty
    ruin_to_empty: float = 0.15
    # Per-year probability a ruin is rebuilt by adjacent settlement
    ruin_rebuild: float = 0.06
    # Preference for expanding onto plains vs forest (1.0 = equal)
    plains_preference: float = 2.0
    # Per-year probability coastal settlement gets port
    port_chance: float = 0.05


def run_simulation(
    initial_grid: list[list[int]],
    settlements: list[dict],
    params: SimParams,
    seed: int = 42,
) -> np.ndarray:
    """Run one 50-year simulation. Returns final grid."""
    rng = np.random.default_rng(seed)
    grid = np.array(initial_grid, dtype=np.int8)
    h, w = grid.shape

    # Precompute static masks
    is_ocean = grid == OCEAN
    is_mountain = grid == MOUNTAIN
    is_land = ~is_ocean & ~is_mountain

    is_coastal = np.zeros((h, w), dtype=bool)
    for y in range(h):
        for x in range(w):
            if not is_land[y, x]:
                continue
            for dx, dy in DIRS8:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and is_ocean[ny, nx]:
                    is_coastal[y, x] = True
                    break

    # Initialize settlement tracking: set of (y, x) + owner_id
    settle_set: dict[tuple[int, int], int] = {}  # (y,x) -> owner_id
    for i, s in enumerate(settlements):
        settle_set[(s["y"], s["x"])] = i

    def count_adj_forests(y: int, x: int) -> int:
        c = 0
        for dx, dy in DIRS8:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and grid[ny, nx] == FOREST:
                c += 1
        return c

    def get_expansion_candidates(y: int, x: int) -> list[tuple[int, int, float]]:
        candidates = []
        for dy in range(-params.expand_range, params.expand_range + 1):
            for dx in range(-params.expand_range, params.expand_range + 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                dist = abs(dy) + abs(dx)
                if dist > params.expand_range:
                    continue
                if not (0 <= ny < h and 0 <= nx < w):
                    continue
                if not is_land[ny, nx]:
                    continue
                cell = grid[ny, nx]
                if cell in (SETTLEMENT, PORT, OCEAN, MOUNTAIN):
                    continue
                # Weight by distance and terrain
                weight = 1.0 / (dist * dist)
                if cell in (PLAINS, EMPTY):
                    weight *= params.plains_preference
                candidates.append((ny, nx, weight))
        return candidates

    for year in range(50):
        # --- EXPANSION ---
        new_settlements = []
        living = list(settle_set.items())
        rng.shuffle(living)

        for (sy, sx), owner in living:
            if grid[sy, sx] not in (SETTLEMENT, PORT):
                continue
            if rng.random() < params.expand_prob:
                candidates = get_expansion_candidates(sy, sx)
                if candidates:
                    weights = np.array([c[2] for c in candidates])
                    weights /= weights.sum()
                    idx = rng.choice(len(candidates), p=weights)
                    ny, nx, _ = candidates[idx]
                    new_settlements.append((ny, nx, owner))

        for ny, nx, owner in new_settlements:
            if grid[ny, nx] in (SETTLEMENT, PORT):
                continue  # already taken by another expansion this turn
            if is_coastal[ny, nx]:
                grid[ny, nx] = PORT
            else:
                grid[ny, nx] = SETTLEMENT
            settle_set[(ny, nx)] = owner

        # --- PORT BUILDING ---
        for (sy, sx) in list(settle_set.keys()):
            if grid[sy, sx] == SETTLEMENT and is_coastal[sy, sx]:
                if rng.random() < params.port_chance:
                    grid[sy, sx] = PORT

        # --- COLLAPSE ---
        to_remove = []
        for (sy, sx) in list(settle_set.keys()):
            if grid[sy, sx] not in (SETTLEMENT, PORT):
                continue
            adj_forests = count_adj_forests(sy, sx)
            collapse_prob = max(0.0, params.collapse_base - adj_forests * params.collapse_forest_bonus)
            if rng.random() < collapse_prob:
                grid[sy, sx] = RUIN
                to_remove.append((sy, sx))

        for key in to_remove:
            del settle_set[key]

        # --- ENVIRONMENT (ruin reclamation) ---
        ruin_cells = [(y, x) for y in range(h) for x in range(w) if grid[y, x] == RUIN]
        for ry, rx in ruin_cells:
            # Check for adjacent settlement to rebuild
            rebuilt = False
            for dx, dy in DIRS4:
                ny, nx = ry + dy, rx + dx
                if 0 <= ny < h and 0 <= nx < w and (ny, nx) in settle_set:
                    if rng.random() < params.ruin_rebuild:
                        owner = settle_set[(ny, nx)]
                        if is_coastal[ry, rx]:
                            grid[ry, rx] = PORT
                        else:
                            grid[ry, rx] = SETTLEMENT
                        settle_set[(ry, rx)] = owner
                        rebuilt = True
                        break

            if rebuilt:
                continue

            if rng.random() < params.ruin_to_forest:
                grid[ry, rx] = FOREST
            elif rng.random() < params.ruin_to_empty:
                grid[ry, rx] = PLAINS

    return grid


def run_monte_carlo(
    initial_grid: list[list[int]],
    settlements: list[dict],
    params: SimParams,
    n_runs: int = 300,
    base_seed: int = 42,
    floor: float = 0.005,
) -> np.ndarray:
    """Run n_runs simulations, return probability distribution (h×w×6)."""
    h = len(initial_grid)
    w = len(initial_grid[0])
    counts = np.zeros((h, w, NUM_CLASSES), dtype=np.float64)

    for i in range(n_runs):
        final_grid = run_simulation(initial_grid, settlements, params, seed=base_seed + i)
        for y in range(h):
            for x in range(w):
                cls = GRID_TO_CLASS.get(int(final_grid[y, x]), 0)
                counts[y, x, cls] += 1

    probs = counts / n_runs
    probs = np.clip(probs, floor, None)
    probs /= probs.sum(axis=-1, keepdims=True)
    return probs
