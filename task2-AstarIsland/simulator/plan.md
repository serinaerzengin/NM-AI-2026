# Astar Island Simulator — Plan

## Goal

Build a simplified probabilistic simulator that predicts the final-state probability distribution for each cell, given the initial state and a single continuous parameter (settlement rate).

We do NOT need to simulate the internal year-by-year mechanics. We need to model the **observable outputs** of the 5-phase lifecycle.

---

## What the real simulator does (5 phases × 50 years)

| Phase | Mechanics | Observable output |
|-------|-----------|-------------------|
| 1. Growth | Settlements produce food from adjacent terrain, grow population, build ports/longships, found new settlements on nearby land | New settlement cells appear near existing ones |
| 2. Conflict | Settlements raid each other, longships extend range, conquered settlements flip allegiance | Some settlements weaken/die, faction boundaries shift |
| 3. Trade | Ports trade food/wealth with ports in range, tech diffuses | Ports slightly more resilient (weak effect empirically) |
| 4. Winter | All settlements lose food, weak ones collapse into Ruins | Settlement cells become Ruin cells |
| 5. Environment | Ruins reclaimed by nearby settlements or overgrown by forest/plains | Ruin cells become Settlement, Forest, or Empty |

Source: `docs/simulation-mechanics.md`

---

## What we can infer from ground truth (rounds 1-5)

### Growth — Expansion probability by distance

Expansion probability decays with manhattan distance from nearest initial settlement.
Measurable per round. The `settlement_rate` parameter controls the scale.

| Distance | R1 (rate=0.18) | R3 (rate=0.003) | R5 (rate=0.14) |
|----------|----------------|------------------|----------------|
| d=1 | 0.264 | ~0 | 0.263 |
| d=2 | 0.238 | ~0 | 0.235 |
| d=3 | 0.235 | ~0 | 0.123 |
| d=4 | 0.205 | ~0 | 0.089 |
| d=5 | 0.110 | ~0 | 0.022 |
| d=6 | 0.083 | ~0 | 0.013 |
| d=7 | 0.053 | ~0 | 0.000 |
| d=8 | 0.029 | ~0 | 0.000 |

Adjacent forests give a small boost to expansion (+2-6%). Source: `Q9`, `Q3` in `questions.md`

### Conflict + Winter — Settlement survival

Survival depends primarily on the settlement rate (global hidden parameter), with weak local effects:
- Adjacent forests (food source): +5-15% survival in high-expansion rounds
- Coastal vs inland: negligible difference
- Port status: negligible effect on survival
- In low-expansion rounds (R3): ~98% collapse regardless of local terrain

Source: `Q11`, `Q12` in `questions.md`

### Trade — Port effects

Empirically negligible. Ports survive at roughly the same rate as inland settlements (39-49% vs 41-42%). Too few ports per seed for reliable measurement. Source: analysis above.

### Environment — Reclamation

Consistent across all rounds:
- ~18-20% of collapsed settlements become Forest
- ~1-3% remain as Ruin (transient state)
- Rest become Empty/Plains
- Forest reclamation rate appears independent of the expansion regime

Source: `Q10`, `Q11` in `questions.md`

---

## Simplified model architecture

Instead of simulating 50 years of 5 phases, model the **end-state probability distribution** directly:

```
Input:  initial_grid[y][x], settlement_positions, settlement_rate (continuous 0.0 - 0.25)
Output: prediction[y][x][6] — probability per class
```

### Per-cell prediction logic

```
For each cell (y, x):
    terrain = initial_grid[y][x]

    if terrain == Ocean:    → [1.0, 0, 0, 0, 0, 0]  (static)
    if terrain == Mountain: → [0, 0, 0, 0, 0, 1.0]  (static)

    if terrain == Forest:
        P(forest)     = f_forest(rate, distance, adj_features)
        P(settlement) = f_settle(rate, distance, adj_features)
        P(empty)      = 1 - P(forest) - P(settlement) - floor_others

    if terrain == Settlement/Port:
        P(settlement) = f_survive(rate, adj_forests, is_coastal)
        P(forest)     = f_reclaim(rate)  # ~0.18-0.20
        P(ruin)       = f_ruin(rate)     # ~0.02-0.03
        P(empty)      = 1 - above

    if terrain == Plains/Empty:
        P(settlement) = f_expand(rate, distance, adj_forests)
        P(forest)     = f_forest_grow(rate, distance)
        P(empty)      = 1 - above
```

### Key functions to fit (from ground truth)

All functions are parameterized by `rate` (the continuous settlement rate) using the linear model from Q46:

```
f(rate, distance, ...) = a * rate + b    (per terrain bucket)
```

Fitted coefficients are in Q46 answer (r=0.94-0.99 correlation).

### Additional features to consider (v2)

- **Adjacent forest count**: slight boost to expansion and survival (+2-6%)
- **Connected land region size**: isolated pockets behave differently
- **Distance to ocean**: coastal effects (port formation)
- **Settlement density in neighborhood**: competition vs cooperation effects

---

## Implementation plan

### v1: Linear rate model (current approach, improved)

1. Observe viewports → compute settlement_rate
2. Use linear model: `prior[bucket][class] = a * rate + b`
3. Blend with observations
4. Submit

Expected score: 70-85 (based on ceiling analysis in Q26)

### v2: Feature-enriched model

1. Add per-cell features: adj_forests, distance_to_ocean, connected_region_size
2. Fit multivariate regression on ground truth from R1-R5
3. Test with cross-validation (fit on 4 rounds, test on 1)

Expected score: 80-90

### v3: Phase-based Monte Carlo simulator

Why simulate phases instead of just using a static model?

**Empirical evidence for emergent dynamics:**
- **Chain expansion**: Settlements reach d=13 from initial positions (R2). A→B→C chain expansion. Static model caps at d=8.
- **Competition**: Cells near 2+ settlements have 24% lower P(settle) than cells near 1. First-come-first-served.
- **Faction territories**: 24 factions in R6, avg internal distance 4-7 cells. Spatial entities that block each other.
- **Cascading collapse**: Settlement dies → neighbor loses food/trade → also collapses.

These affect ~8% of cells, worth ~2-5 score points (85→90).

1. Build a simplified simulator with 5 phases per year × 50 years:

   **Per year loop:**
   ```
   for year in range(50):
       # Phase 1: GROWTH
       - Each living settlement produces food = f(adjacent_forests, tech_level)
       - If food > growth_threshold: population grows
       - If population > expand_threshold: found new settlement on random adjacent land cell
       - Coastal settlements with enough wealth → build port
       - Settlements with enough resources → build longship

       # Phase 2: CONFLICT
       - Each settlement may raid neighbors within range (longships extend range)
       - Desperate (low food) settlements raid more aggressively
       - Winner loots food/wealth, loser takes damage
       - Low-defense losers may flip allegiance (faction change)

       # Phase 3: TRADE
       - Ports within trade_range of friendly ports → exchange food/wealth
       - Tech diffuses between trade partners

       # Phase 4: WINTER
       - All settlements lose food (severity varies per year)
       - Settlements with food < 0 → collapse into Ruin
       - Collapsed settlements disperse population to nearby friendly settlements

       # Phase 5: ENVIRONMENT
       - Ruins adjacent to thriving settlements → may be rebuilt (as settlement or port)
       - Ruins not rebuilt → chance of forest overgrowth, or fade to empty
   ```

2. **Hidden parameters to fit** (from observations + ground truth):
   - `expansion_rate`: how aggressively settlements expand (KEY parameter)
   - `winter_severity`: distribution of food loss per winter
   - `raid_aggression`: how often/hard settlements raid
   - `food_per_forest`: food production from adjacent forest cells
   - `expand_threshold`: population needed to found new settlement
   - `trade_range`: max distance for port-to-port trade
   - `reclamation_rate`: how fast ruins get reclaimed by forest (~0.20, constant)

3. **Calibration loop:**
   - Run simulator with candidate parameters
   - Compare output distribution to ground truth from R1-R5
   - Optimize parameters to minimize KL divergence
   - The settlement_rate from observations constrains the search space

4. Run 200-500 Monte Carlo simulations per seed
5. Count outcomes per cell → probability distribution
6. Blend with viewport observations
7. Submit

Expected score: 85-95

### Simulation details to get right

**Must simulate** (captures emergent dynamics worth ~2-5 points):
- Sequential expansion (chain expansion: A→B→C)
- Spatial competition (one settlement per cell, first-come-first-served)
- Faction territories (owner_id determines who expands where)
- Cascading collapse (death of one settlement weakens neighbors)
- Year-by-year food/population dynamics (determines WHO expands and WHO dies)

**Can simplify** (weak or negligible effects):
- Trade mechanics → just a small food/wealth bonus for ports
- Tech diffusion → flat bonus, not worth detailed modeling
- Longship building → just extend raid range by a constant
- Individual stats → use simplified food/population model

**Can skip entirely**:
- Exact damage formulas for raids → use probabilistic survival
- Wealth mechanics beyond food → weak predictor of outcomes
- Allegiance flip details → just model faction expansion

---

## Data sources

- Ground truth: `data/round_{1-5}/seed_{0-4}/ground_truth.json` (25 seeds)
- Initial states: `data/round_{1-5}/seed_{0-4}/initial_state.json`
- Observations: `data/round_6/seed_{0-4}/observations/`
- API endpoints: `docs/API-Endpoints.md`
- Simulation mechanics: `docs/simulation-mechanics.md`
- Research findings: `docs/research/questions.md` (Q1-Q47, L1-L3)
