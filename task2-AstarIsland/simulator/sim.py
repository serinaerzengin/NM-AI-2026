"""Astar Island phase-based Monte Carlo simulator.

Simplified model of the 5-phase Norse civilization simulation:
  Growth → Conflict → Trade → Winter → Environment  (×50 years)

Run many times with different random seeds to produce probability distributions.
"""

from dataclasses import dataclass, field
import numpy as np

# Terrain codes (internal)
OCEAN = 10
PLAINS = 11
EMPTY = 0
SETTLEMENT = 1
PORT = 2
RUIN = 3
FOREST = 4
MOUNTAIN = 5

# Prediction class indices
GRID_TO_CLASS = {10: 0, 11: 0, 0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
NUM_CLASSES = 6

DIRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class SimParams:
    expansion_rate: float = 0.12       # per-year probability of a qualifying settlement expanding
    winter_severity: float = 0.65      # base food loss per winter
    raid_aggression: float = 0.15      # probability a settlement raids per year
    food_per_forest: float = 0.25      # food gained per adjacent forest
    base_food_production: float = 0.15 # base food production per year
    expand_pop_threshold: float = 4.0  # population needed to attempt expansion
    trade_food_bonus: float = 0.1      # food bonus per trade partner
    trade_range: int = 8               # max manhattan distance for port trade
    reclamation_forest_rate: float = 0.08   # per-year chance ruin → forest
    reclamation_settle_rate: float = 0.08   # per-year chance ruin rebuilt by adjacent settlement
    reclamation_empty_rate: float = 0.20    # per-year chance ruin → empty/plains
    port_build_chance: float = 0.05    # per-year chance coastal settlement builds port
    raid_range: int = 4                # base raid range (manhattan)
    longship_raid_bonus: int = 4       # extra raid range with longship
    init_pop_mean: float = 3.0         # mean initial population
    init_pop_std: float = 1.0          # std of initial population
    init_food: float = 1.0             # initial food


@dataclass
class SettlementState:
    x: int
    y: int
    population: float
    food: float
    has_port: bool
    has_longship: bool
    owner_id: int
    alive: bool = True


class SimState:
    """Full simulation state."""

    def __init__(
        self,
        initial_grid: list[list[int]],
        settlements: list[dict],
        params: SimParams,
        rng: np.random.Generator,
    ):
        self.h = len(initial_grid)
        self.w = len(initial_grid[0])
        self.params = params
        self.rng = rng

        # Grid as numpy array
        self.grid = np.array(initial_grid, dtype=np.int8)
        # Keep original terrain for reference (ocean/mountain never change)
        self.base_terrain = self.grid.copy()

        # Precompute static masks
        self.is_ocean = self.grid == OCEAN
        self.is_mountain = self.grid == MOUNTAIN
        self.is_land = ~self.is_ocean & ~self.is_mountain

        # Coastal mask: land cells adjacent to ocean
        self.is_coastal = np.zeros((self.h, self.w), dtype=bool)
        for y in range(self.h):
            for x in range(self.w):
                if not self.is_land[y, x]:
                    continue
                for dx, dy in DIRS8:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < self.h and 0 <= nx < self.w and self.is_ocean[ny, nx]:
                        self.is_coastal[y, x] = True
                        break

        # Precompute land neighbors for each cell
        self.land_neighbors: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for y in range(self.h):
            for x in range(self.w):
                if not self.is_land[y, x]:
                    continue
                nbrs = []
                for dx, dy in DIRS4:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < self.h and 0 <= nx < self.w and self.is_land[ny, nx]:
                        nbrs.append((ny, nx))
                self.land_neighbors[(y, x)] = nbrs

        # Initialize settlements
        self.settlements: dict[tuple[int, int], SettlementState] = {}
        for i, s in enumerate(settlements):
            sx, sy = s["x"], s["y"]
            pop = max(0.5, params.init_pop_mean + rng.normal() * params.init_pop_std)
            ss = SettlementState(
                x=sx, y=sy,
                population=pop,
                food=params.init_food,
                has_port=s.get("has_port", False),
                has_longship=False,
                owner_id=i,  # each starts as its own faction
            )
            self.settlements[(sy, sx)] = ss

    def count_adjacent_forests(self, y: int, x: int) -> int:
        count = 0
        for dx, dy in DIRS8:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.h and 0 <= nx < self.w and self.grid[ny, nx] == FOREST:
                count += 1
        return count

    def get_living_settlements(self) -> list[SettlementState]:
        return [s for s in self.settlements.values() if s.alive]

    def find_enemy_in_range(self, s: SettlementState, raid_range: int) -> SettlementState | None:
        candidates = []
        for key, other in self.settlements.items():
            if not other.alive or other.owner_id == s.owner_id:
                continue
            dist = abs(s.x - other.x) + abs(s.y - other.y)
            if dist <= raid_range:
                candidates.append((dist, other))
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0])
        return candidates[0][1]


def _growth_phase(state: SimState):
    p = state.params
    rng = state.rng
    living = state.get_living_settlements()

    for s in living:
        # Food production — resets each year (no stockpiling)
        adj_forests = state.count_adjacent_forests(s.y, s.x)
        food_income = p.base_food_production + p.food_per_forest * adj_forests
        s.food = food_income  # food is ANNUAL income, not cumulative

        # Population growth (logistic)
        max_pop = 2.0 + adj_forests * 1.5
        if s.food > 0.3 and s.population < max_pop:
            s.population += 0.15 * (1 - s.population / max_pop)

        # Port building
        if not s.has_port and state.is_coastal[s.y, s.x] and rng.random() < p.port_build_chance:
            s.has_port = True
            state.grid[s.y, s.x] = PORT

        # Longship
        if s.has_port and s.population > 3.0 and not s.has_longship:
            if rng.random() < 0.1:
                s.has_longship = True

        # Expansion — can try multiple times for high pop
        if s.population > p.expand_pop_threshold and rng.random() < p.expansion_rate:
            _try_expand(state, s)


def _try_expand(state: SimState, parent: SettlementState):
    rng = state.rng
    candidates = []

    # Search within distance 1-5 for expansion targets
    py, px = parent.y, parent.x
    for dy in range(-5, 6):
        for dx in range(-5, 6):
            if dy == 0 and dx == 0:
                continue
            ny, nx = py + dy, px + dx
            if not (0 <= ny < state.h and 0 <= nx < state.w):
                continue
            dist = abs(dy) + abs(dx)
            if dist > 5:
                continue
            cell = state.grid[ny, nx]
            if cell in (OCEAN, MOUNTAIN, SETTLEMENT, PORT):
                continue
            if not state.is_land[ny, nx]:
                continue
            # Weight: strong distance decay, plains preferred
            weight = 1.0 / (dist * dist)  # inverse square distance decay
            if cell in (PLAINS, EMPTY):
                weight *= 2.0
            elif cell == FOREST:
                weight *= 1.0
            candidates.append((ny, nx, weight))

    if not candidates:
        return

    weights = np.array([c[2] for c in candidates])
    weights /= weights.sum()
    idx = rng.choice(len(candidates), p=weights)
    ny, nx, _ = candidates[idx]

    # Found new settlement
    new_settle = SettlementState(
        x=nx, y=ny,
        population=1.0,
        food=0.5,
        has_port=False,
        has_longship=False,
        owner_id=parent.owner_id,
    )
    state.settlements[(ny, nx)] = new_settle

    if state.is_coastal[ny, nx]:
        state.grid[ny, nx] = PORT
        new_settle.has_port = True
    else:
        state.grid[ny, nx] = SETTLEMENT

    parent.population -= 1.0


def _conflict_phase(state: SimState):
    p = state.params
    rng = state.rng
    living = state.get_living_settlements()
    rng.shuffle(living)

    for s in living:
        if not s.alive:
            continue

        # Desperate settlements (low food) raid more
        aggression = p.raid_aggression
        if s.food < 0.3:
            aggression *= 2.0

        if rng.random() > aggression:
            continue

        raid_range = p.raid_range
        if s.has_longship:
            raid_range += p.longship_raid_bonus

        target = state.find_enemy_in_range(s, raid_range)
        if target is None:
            continue

        # Resolve raid
        attacker_strength = s.population * (1.2 if s.has_longship else 1.0)
        defender_strength = target.population
        total = attacker_strength + defender_strength
        if total < 0.01:
            continue

        win_prob = attacker_strength / total
        if rng.random() < win_prob:
            # Attacker wins
            loot = 0.3 * target.food
            s.food += loot
            target.food -= loot
            target.population *= 0.8
            # Allegiance flip if defender is very weak
            if target.population < 1.0:
                target.owner_id = s.owner_id
        else:
            # Defender wins
            s.population *= 0.9


def _trade_phase(state: SimState):
    p = state.params
    ports = [s for s in state.get_living_settlements() if s.has_port]

    for i, port_a in enumerate(ports):
        for port_b in ports[i + 1:]:
            if port_a.owner_id != port_b.owner_id:
                continue  # only friendly trade
            dist = abs(port_a.x - port_b.x) + abs(port_a.y - port_b.y)
            if dist > p.trade_range:
                continue
            port_a.food += p.trade_food_bonus
            port_b.food += p.trade_food_bonus


def _winter_phase(state: SimState):
    p = state.params
    rng = state.rng

    # Variable severity per year
    severity = p.winter_severity * (0.5 + rng.random())

    living = state.get_living_settlements()
    for s in living:
        # Survival check: food income vs winter cost
        # Settlements with low food income (few forests) are vulnerable
        food_need = severity * (0.5 + 0.1 * s.population)
        survival_margin = s.food - food_need

        if survival_margin < 0 or (survival_margin < 0.1 and rng.random() < 0.3):
            # Settlement collapses
            s.alive = False
            state.grid[s.y, s.x] = RUIN

            # Disperse population to nearby friendly settlements
            for ny, nx in state.land_neighbors.get((s.y, s.x), []):
                neighbor = state.settlements.get((ny, nx))
                if neighbor and neighbor.alive and neighbor.owner_id == s.owner_id:
                    neighbor.population += 0.15 * s.population


def _environment_phase(state: SimState):
    p = state.params
    rng = state.rng

    ruin_cells = [
        (y, x) for y in range(state.h) for x in range(state.w)
        if state.grid[y, x] == RUIN
    ]

    for y, x in ruin_cells:
        # Check for adjacent thriving settlement to rebuild
        rebuilt = False
        for ny, nx in state.land_neighbors.get((y, x), []):
            neighbor = state.settlements.get((ny, nx))
            if neighbor and neighbor.alive and neighbor.population > 2.0:
                if rng.random() < p.reclamation_settle_rate:
                    # Rebuild as settlement
                    new_s = SettlementState(
                        x=x, y=y,
                        population=0.8,
                        food=0.3,
                        has_port=state.is_coastal[y, x],
                        has_longship=False,
                        owner_id=neighbor.owner_id,
                    )
                    state.settlements[(y, x)] = new_s
                    state.grid[y, x] = PORT if new_s.has_port else SETTLEMENT
                    rebuilt = True
                    break

        if rebuilt:
            continue

        # Forest reclamation
        if rng.random() < p.reclamation_forest_rate:
            state.grid[y, x] = FOREST
            if (y, x) in state.settlements:
                del state.settlements[(y, x)]
        # Fade to empty
        elif rng.random() < p.reclamation_empty_rate:
            state.grid[y, x] = PLAINS
            if (y, x) in state.settlements:
                del state.settlements[(y, x)]


def run_simulation(
    initial_grid: list[list[int]],
    settlements: list[dict],
    params: SimParams,
    seed: int = 42,
) -> np.ndarray:
    """Run one 50-year simulation. Returns final grid (h×w) of terrain codes."""
    rng = np.random.default_rng(seed)
    state = SimState(initial_grid, settlements, params, rng)

    for year in range(50):
        _growth_phase(state)
        _conflict_phase(state)
        _trade_phase(state)
        _winter_phase(state)
        _environment_phase(state)

    return state.grid


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
