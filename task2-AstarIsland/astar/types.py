from dataclasses import dataclass

import numpy as np


@dataclass
class MapState:
    grid: np.ndarray  # (40, 40) initial terrain codes
    settlements: list[dict]  # [{x, y, has_port, alive}, ...]


@dataclass
class Observation:
    grid: np.ndarray  # (H, W) final terrain codes from one query
    settlements: list[dict]  # settlement details from response
    viewport: tuple[int, int, int, int]  # (x, y, w, h)
    seed_index: int


@dataclass
class RoundStats:
    ruin_rate: float
    settlement_rate: float
    port_rate: float
    expansion_distance: float
    forest_rate: float  # fraction of dynamic cells that are forest
    empty_rate: float  # fraction of dynamic cells that are empty
    settlement_to_ruin_ratio: float  # settlement / (settlement + ruin), measures survival


@dataclass
class Prediction:
    probs: np.ndarray  # (40, 40, 6) probability distribution


# Terrain code constants
OCEAN = 10
PLAINS = 11
EMPTY = 0
SETTLEMENT = 1
PORT = 2
RUIN = 3
FOREST = 4
MOUNTAIN = 5

# Prediction class indices
CLASS_EMPTY = 0
CLASS_SETTLEMENT = 1
CLASS_PORT = 2
CLASS_RUIN = 3
CLASS_FOREST = 4
CLASS_MOUNTAIN = 5
NUM_CLASSES = 6

# Terrain code → prediction class
TERRAIN_TO_CLASS = {
    OCEAN: CLASS_EMPTY,
    PLAINS: CLASS_EMPTY,
    EMPTY: CLASS_EMPTY,
    SETTLEMENT: CLASS_SETTLEMENT,
    PORT: CLASS_PORT,
    RUIN: CLASS_RUIN,
    FOREST: CLASS_FOREST,
    MOUNTAIN: CLASS_MOUNTAIN,
}
