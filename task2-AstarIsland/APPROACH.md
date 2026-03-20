# Astar Island — Our Approach

## Overview

Two-layer prediction: XGBoost base model for general patterns + empirical bins from live observations for round-specific calibration.

**Validated scores (no data leakage — held-out evaluation):**
- Round 6: 87.1 (trained on R1-5, first place was 88.5)
- Round 7: 72.4 (trained on R1-6)
- Average: 79.7

---

## Layer 1: XGBoost Base Model

For each live round, trains on all COMPLETED rounds (never the current one). Predicts a 6-class probability distribution per cell. For round 8: trained on rounds 1-7 (35 maps). For round 9: will train on rounds 1-8 (40 maps).

### Features per cell (28 total)

**Cell features (22)** — computed from the visible initial state:
- Terrain flags: is_ocean, is_mountain, is_forest, is_land
- Settlement: is_initial_settlement, is_initial_port
- Distance to nearest initial settlement (Euclidean)
- Settlement density: count within radius 3, 5, 10
- 8-neighbor counts: adjacent forests, ocean, mountains
- BFS reachability from any settlement over land
- Distance to nearest ocean, distance to nearest forest
- Broader terrain: forests/ocean/land count in radius 5
- Map-level: total settlements, total ports, land fraction

**Round-level stats (7)** — proxy for hidden parameters:
- Settlement rate, ruin rate, port rate, forest rate, empty rate
- Expansion distance (how far new settlements appear from initial ones)
- Settlement-to-ruin ratio (survival measure)

During training: computed from ground truth. During live rounds: estimated from the 50 observations.

**Interaction features (6)** — help the model learn how hidden params affect cells at different distances:
- settlement_rate × distance, settlement_rate × settlements_r5
- settlement_rate × coastal, ruin_rate × distance
- settlement_rate × adjacent_forests, settlement_rate / (distance + 1)

### Training

- Entropy-weighted samples: high-entropy cells (uncertain outcomes) get more weight, matching the scoring formula
- Hyperparameters optimized via Optuna (200 trials, validated on rounds 6+7)
- Static cells (ocean, mountain) are excluded from training and predicted deterministically

---

## Layer 2: Empirical Bins

Built from the 50 live simulation queries (~11,000 cell observations per round).

### How it works

1. Each observed cell is assigned to a bin based on its features:
   - Distance to settlement (d0, d1, d2, d3-4, d5-7, d8+)
   - Coastal vs inland
   - Terrain type (forest, settlement, plain)
   - Settlement density (hi/lo based on settlements within radius 5)

2. Count outcomes per bin across all observations → empirical distribution

3. Hierarchical fallback: if a fine bin has <10 observations, fall back to coarser bin (drops the density dimension)

### Why this works

- 50 queries × 225 cells = 11,250 observations spread across ~40 bins
- Most bins have 100-500+ observations — enough for reliable distributions
- The distributions are calibrated to THIS round's hidden parameters (no generalization needed)
- Cells in the same bin behave similarly (validated: within-bin variance is small)

---

## Blending: Adaptive k

For each cell, blend model and empirical bin predictions:

```
weight = n / (n + k)
prediction = weight × empirical_bin + (1 - weight) × model
```

Where `n` is the observation count for the cell's bin.

**Adaptive k based on round activity:**
- `settle_rate < 5%` → k=50 (low activity: trust bins heavily)
- `settle_rate < 10%` → k=100
- `settle_rate >= 10%` → k=361 (Optuna-optimized default)

Low-activity rounds have less outcome variance, so empirical bins are more reliable. This was validated on round 3: k=50 scored 79.5 vs k=361 scored 69.5 (+10 points).

---

## Query Strategy

- Allocate 50 queries proportionally to each map's dynamic cell count (floor: 5 per map)
- Place 15×15 viewports greedily to maximize coverage of settlement-dense areas
- Settlement-focused viewports naturally capture all distance bins (d0 through d8+)

---

## Pipeline (`run_round.py`)

```
1. Train XGBoost on rounds 1-N (using best_params.json from Optuna)
2. Fetch initial states for current round
3. Execute 50 queries → save observations
4. Compute round stats from observations
5. Build empirical bins from all observations across all 5 seeds
6. For each seed:
   a. Model predicts all cells
   b. Adaptive blend with empirical bins
   c. Floor probabilities at 0.001, renormalize
   d. Submit
```

---

## Key Files

| File | Purpose |
|------|---------|
| `astar/predictor.py` | XGBoost model (train + predict) |
| `astar/empirical_bins.py` | Bin construction + adaptive blending |
| `astar/features.py` | Cell feature extraction (22 features) |
| `astar/calibration.py` | Round-level stats computation |
| `astar/query_strategy.py` | Viewport placement |
| `astar/scoring.py` | Local scoring (entropy-weighted KL) |
| `astar/types.py` | Dataclasses + terrain constants |
| `run_round.py` | Live round orchestrator |
| `optuna_search.py` | Hyperparameter optimization |
| `backtest.py` | Leave-one-round-out validation |
| `best_params.json` | Optimized hyperparameters |

---

## Known Limitations

- **Round 3-like regimes** (very low activity): model struggles because it's rare in training data. Empirical bins compensate but ceiling is lower (~79 vs ~87 for normal rounds).
- **Only 7 training rounds**: more data would help the model generalize to new parameter regimes.
- **Oracle bin ceiling**: ~85 on normal rounds. Within-bin variance limits how much bins can help. Going beyond requires per-cell spatial modeling.
