import numpy as np

from .types import MapState, OCEAN, MOUNTAIN

VIEWPORT_SIZE = 15
MAP_SIZE = 40
MIN_QUERIES_PER_MAP = 5
INTEREST_RADIUS = 8


def plan_viewports(state: MapState, n_queries: int) -> list[tuple[int, int]]:
    """Plan viewport positions to maximize coverage of dynamic cells.

    Args:
        state: Initial map state.
        n_queries: Number of queries to allocate for this map.

    Returns:
        List of (viewport_x, viewport_y) positions for 15x15 viewports.
    """
    interest_map = _compute_interest_map(state)
    viewports = []
    remaining = interest_map.copy()

    for _ in range(n_queries):
        best_pos = _best_viewport_position(remaining)
        viewports.append(best_pos)
        # Mask covered cells so next viewport covers new area
        vx, vy = best_pos
        remaining[vy:vy + VIEWPORT_SIZE, vx:vx + VIEWPORT_SIZE] = 0

    return viewports


def allocate_queries(states: list[MapState], total_queries: int = 50) -> list[int]:
    """Distribute queries across maps proportionally to dynamic cell count.

    Args:
        states: Initial states for all maps in the round.
        total_queries: Total query budget.

    Returns:
        List of query counts per map, summing to total_queries.
    """
    n_maps = len(states)
    dynamic_counts = []

    for state in states:
        interest = _compute_interest_map(state)
        dynamic_counts.append(interest.sum())

    total_interest = sum(dynamic_counts)
    if total_interest == 0:
        # Fallback: equal distribution
        base = total_queries // n_maps
        allocation = [base] * n_maps
        allocation[0] += total_queries - sum(allocation)
        return allocation

    # Proportional allocation with floor
    allocation = []
    for count in dynamic_counts:
        raw = total_queries * (count / total_interest)
        allocation.append(max(MIN_QUERIES_PER_MAP, int(raw)))

    # Adjust to hit total budget exactly
    while sum(allocation) > total_queries:
        # Remove from largest allocation
        idx = np.argmax(allocation)
        allocation[idx] -= 1
    while sum(allocation) < total_queries:
        # Add to smallest allocation (above minimum)
        idx = np.argmin(allocation)
        allocation[idx] += 1

    return allocation


def _compute_interest_map(state: MapState) -> np.ndarray:
    """Score each cell by proximity to initial settlements.

    Cells within INTEREST_RADIUS of any settlement get a score.
    Ocean and mountain cells get 0.
    """
    h, w = state.grid.shape
    interest = np.zeros((h, w), dtype=np.float32)

    settlement_positions = [(s["x"], s["y"]) for s in state.settlements]

    for r in range(h):
        for c in range(w):
            if state.grid[r, c] in (OCEAN, MOUNTAIN):
                continue
            for sx, sy in settlement_positions:
                dist = np.sqrt((c - sx) ** 2 + (r - sy) ** 2)
                if dist <= INTEREST_RADIUS:
                    interest[r, c] += max(0, INTEREST_RADIUS - dist)

    return interest


def _best_viewport_position(interest_map: np.ndarray) -> tuple[int, int]:
    """Find the viewport position that covers the most interest."""
    h, w = interest_map.shape
    max_x = w - VIEWPORT_SIZE
    max_y = h - VIEWPORT_SIZE
    best_score = -1
    best_pos = (0, 0)

    for vy in range(max(0, max_y + 1)):
        for vx in range(max(0, max_x + 1)):
            score = interest_map[vy:vy + VIEWPORT_SIZE, vx:vx + VIEWPORT_SIZE].sum()
            if score > best_score:
                best_score = score
                best_pos = (vx, vy)

    return best_pos
