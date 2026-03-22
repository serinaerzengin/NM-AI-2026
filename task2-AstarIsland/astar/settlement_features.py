import numpy as np

NEIGHBORHOOD_RADIUS = 5.0


def compute_settlement_cell_features(
    cell_x: int,
    cell_y: int,
    observed_settlements: list[dict],
) -> np.ndarray:
    """Per-cell features derived from nearby observed settlements.

    Args:
        cell_x, cell_y: Cell position on the 40x40 grid.
        observed_settlements: List of settlement dicts with
            x, y, population, food, wealth, defense, alive, has_port, owner_id.

    Returns:
        Feature array of shape (NUM_SETTLEMENT_CELL_FEATURES,).
    """
    if not observed_settlements:
        return np.zeros(NUM_SETTLEMENT_CELL_FEATURES, dtype=np.float32)

    # Compute distances to all observed settlements
    dists = np.array([
        np.sqrt((cell_x - s["x"]) ** 2 + (cell_y - s["y"]) ** 2)
        for s in observed_settlements
    ])

    # Nearest settlement features
    nearest_idx = np.argmin(dists)
    nearest = observed_settlements[nearest_idx]
    nearest_dist = dists[nearest_idx]

    # Neighborhood: settlements within radius
    nearby_mask = dists <= NEIGHBORHOOD_RADIUS
    nearby = [s for s, m in zip(observed_settlements, nearby_mask) if m]

    if nearby:
        n_food = np.mean([s["food"] for s in nearby])
        n_pop = np.mean([s["population"] for s in nearby])
        n_alive = np.mean([1.0 if s["alive"] else 0.0 for s in nearby])
        n_factions = len(set(s["owner_id"] for s in nearby))
        n_count = len(nearby)
        n_ports = np.mean([1.0 if s["has_port"] else 0.0 for s in nearby])
    else:
        n_food = 0.0
        n_pop = 0.0
        n_alive = 0.0
        n_factions = 0
        n_count = 0
        n_ports = 0.0

    return np.array([
        nearest["population"],
        nearest["food"],
        nearest["wealth"],
        nearest["defense"],
        1.0 if nearest["alive"] else 0.0,
        nearest_dist,
        n_food,
        n_pop,
        n_alive,
        float(n_factions),
        float(n_count),
        n_ports,
    ], dtype=np.float32)


SETTLEMENT_CELL_FEATURE_NAMES = [
    "nearest_obs_population",
    "nearest_obs_food",
    "nearest_obs_wealth",
    "nearest_obs_defense",
    "nearest_obs_alive",
    "nearest_obs_dist",
    "neighborhood_avg_food",
    "neighborhood_avg_population",
    "neighborhood_alive_fraction",
    "neighborhood_n_factions",
    "neighborhood_n_settlements",
    "neighborhood_port_fraction",
]

NUM_SETTLEMENT_CELL_FEATURES = len(SETTLEMENT_CELL_FEATURE_NAMES)


def compute_settlement_round_stats(
    all_observed_settlements: list[dict],
) -> np.ndarray:
    """Round-level aggregate stats from all observed settlements.

    Args:
        all_observed_settlements: All settlements observed across all queries.

    Returns:
        Feature array of shape (NUM_SETTLEMENT_ROUND_FEATURES,).
    """
    if not all_observed_settlements:
        return np.zeros(NUM_SETTLEMENT_ROUND_FEATURES, dtype=np.float32)

    populations = [s["population"] for s in all_observed_settlements]
    foods = [s["food"] for s in all_observed_settlements]
    defenses = [s["defense"] for s in all_observed_settlements]
    wealths = [s["wealth"] for s in all_observed_settlements]
    alive_flags = [1.0 if s["alive"] else 0.0 for s in all_observed_settlements]
    factions = set(s["owner_id"] for s in all_observed_settlements)

    return np.array([
        np.mean(foods),
        np.mean(populations),
        np.mean(defenses),
        np.mean(alive_flags),
        float(len(factions)),
        np.mean(wealths),
    ], dtype=np.float32)


SETTLEMENT_ROUND_FEATURE_NAMES = [
    "round_avg_food",
    "round_avg_population",
    "round_avg_defense",
    "round_alive_fraction",
    "round_n_factions",
    "round_avg_wealth",
]

NUM_SETTLEMENT_ROUND_FEATURES = len(SETTLEMENT_ROUND_FEATURE_NAMES)


def collect_all_settlements(observations: list[dict]) -> list[dict]:
    """Extract all settlement dicts from a list of raw observation dicts.

    Deduplicates by (x, y) — if the same cell appears in multiple observations,
    keeps all instances (they represent different simulation runs).
    """
    all_settlements = []
    for obs in observations:
        for s in obs.get("settlements", []):
            all_settlements.append(s)
    return all_settlements
