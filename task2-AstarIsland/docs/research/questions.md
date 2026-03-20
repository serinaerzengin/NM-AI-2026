# Astar Island — Research Questions

## Requirements

- Predict terrain types on a 40x40 grid for 5 seeds, output as H×W×6 probability tensors
- 50 simulation queries total per round, shared across all 5 seeds
- Each query reveals a max 15×15 viewport of the post-simulation (50-year) state
- 6 prediction classes: Empty(0), Settlement(1), Port(2), Ruin(3), Forest(4), Mountain(5)
- Scored by entropy-weighted KL divergence — only dynamic cells matter, weighted by uncertainty
- Never assign 0.0 probability — use a floor of ~0.01 and renormalize
- Ground truth is a probability distribution from hundreds of Monte Carlo runs
- Submit all 5 seeds (missing = score 0)
- Prediction window: ~2h45m per round

---

## Known Things (Given in Docs)

- Initial terrain grid per seed (map seed is visible, reconstructible)
- Settlement positions and port status at t=0 (but NOT internal stats)
- Map generation rules: ocean borders, fjords, mountain chains, forest patches, settlement placement
- Simulation lifecycle order: Growth → Conflict → Trade → Winter → Environment (each of 50 years)
- Terrain mapping: Ocean(10), Plains(11), Empty(0) all → class 0 in predictions
- Mountains are static (never change)
- Forests are mostly static but can reclaim ruins
- Simulation is stochastic — same seed + same hidden params → different outcomes each run
- Hidden parameters are shared across all 5 seeds in a round
- Each simulate call uses a different random sim_seed (you can't control it)
- Settlement properties: population, food, wealth, defense, tech level, port status, longship, faction (owner_id)
- Scoring weights dynamic/uncertain cells more (entropy weighting)

---

## Known Unknowns (We know we don't know these)

- Hidden parameters — what are they, what ranges, how many? They control world behavior
- Exact growth mechanics — food production rates from adjacent terrain, population growth thresholds, port/longship building conditions
- Expansion rules — when does a settlement found a new one? How far? What determines location?
- Conflict mechanics — raid probability, range, longship range multiplier, damage formulas, allegiance flip conditions
- Trade mechanics — port trade range, wealth/food generation rates, tech diffusion effects
- Winter severity — distribution, how it varies per year, starvation thresholds for collapse
- Ruin/collapse conditions — exact triggers (food threshold? defense? cumulative damage?)
- Environmental reclamation — how fast forests reclaim ruins, conditions for settlement rebuilding of ruins
- How different the 5 seeds are — do they share hidden params but differ only in initial terrain layout?
- Probability distribution shape — are most cells deterministic (always same outcome) or highly stochastic?
- What fraction of cells are "dynamic" — how many cells actually change across simulation runs?

---

## Unknown Unknowns (Blind spots to watch for)

- Non-obvious interactions between phases (e.g., does trade affect conflict probability?)
- Emergent spatial patterns (e.g., do settlements cluster, form trade networks, create buffer zones?)
- Edge effects / fjord effects on simulation dynamics
- Whether hidden parameters change between rounds or are always the same
- Correlation structure between cells (neighboring cells may be highly correlated)
- Whether the simulation has tipping points / phase transitions (e.g., one strong faction dominates)
- Time-dependent dynamics (early years vs late years behave differently?)
- Whether viewport observations introduce any bias or artifacts

---

## Research Questions

Status legend:
- `DONE` — Definitively answered, no further iteration needed
- `v1` `v2` `v3`... — Answered N times, may need revisiting as we learn more
- `OPEN` — Not yet answered
- `ONGOING` — Actively being refined across rounds

### Category A: Game Mechanics (answer from docs + simulation observations)

#### A1. Understanding the Map (Static Analysis)
- `DONE` Q1. What is the distribution of terrain types in each initial grid?
- `DONE` Q2. How many land cells vs ocean cells vs mountain cells per seed?
- `DONE` Q3. Where are the initial settlements and ports located relative to coastlines, forests, mountains?
- `DONE` Q4. What is the spatial structure of fjords, and which land areas are isolated/connected?
- `DONE` Q5. Which cells are ocean or mountain and therefore guaranteed static (free predictions)?

#### A2. Understanding the Simulation (Query-based)
- `DONE` Q6. If I query the same seed twice with the same viewport, how much do the results differ? (measures stochasticity)
- `DONE` Q7. What is the typical variance across runs for Settlement vs Ruin vs Forest outcomes?
- `DONE` Q8. Do cells far from any initial settlement ever become settlements?
- `DONE` Q9. What is the maximum expansion radius from an initial settlement after 50 years?
- `DONE` Q10. Do forests ever disappear, or only appear/grow?
- `DONE` Q11. How often do settlements survive all 50 years vs collapse into ruins?
- `DONE` Q12. Do ports persist more often than inland settlements?

#### A3. Inferring Hidden Parameters
- `DONE` Q13. Can I estimate hidden parameters (e.g., expansion rate, winter severity) from a few observations?
- `DONE` Q14. If I observe the same seed multiple times, can I build a local probability distribution and extrapolate?
- `DONE` Q15. Are the hidden parameters consistent enough across seeds that observations from one seed inform another?
- `v1` Q16. What is the minimum number of queries per seed to get a useful signal?

#### A4. Post-Round Learning (Analysis Endpoint)
- `OPEN` Q27. After a completed round, what does the ground truth distribution actually look like?
- `OPEN` Q28. Which cells had the highest entropy (hardest to predict)?
- `OPEN` Q29. Where did my predictions diverge most from ground truth?
- `OPEN` Q30. Can ground truth from past rounds train a model for future rounds?

### Category B: Methods & Strategy

#### B1. Query Budget Optimization
- `v1` Q17. What is the optimal split of 50 queries across the 5 seeds? (10 each? focus on fewer?)
- `v1` Q18. Is it better to tile the map with non-overlapping viewports, or repeatedly sample the same area?
- `v1` Q19. Which areas of the map are most uncertain and benefit most from observation?
- `v1` Q20. Should I observe dynamic areas (near settlements) or verify static areas (ocean/mountain borders)?
- `v1` Q21. What viewport size maximizes information? (15×15 covers more, but 5×5 repeated gives variance estimates)

#### B2. Prediction Strategy
- `v1` Q22. What does a good baseline look like? (prior from initial state + static terrain knowledge)
- `v1` Q23. How much score improvement comes from just correctly predicting static cells (ocean, mountains)?
- `v1` Q24. What probability floor is optimal? (0.01? 0.005? 0.02?)
- `v1` Q25. Can I use symmetry or spatial autocorrelation to propagate observations to unobserved areas?
- `v1` Q26. Is a simple heuristic model (distance-from-settlement decay) competitive, or do I need something learned?

#### C. Fundamental Understanding (user questions about core mechanics)
- `DONE` Q31. Does the simulation progress in real-time during the round window, or does each query run a full 50-year sim instantly?
- `DONE` Q32. Does timing of when we send queries during the window matter?
- `DONE` Q33. What exactly are we predicting? Year 51? The final state after 50 years? Probability over time?
- `DONE` Q34. What does round_weight do and why does it increase?
- `DONE` Q35. Should we spread queries over time to track progression, or fire them all at once?
- `DONE` Q36. Can we see the 50-year progression, or only the final state?
- `DONE` Q37. Why are multiple queries of the same seed/area random? What is the sim_seed vs seed_index?
- `DONE` Q38. What exactly is the final state we're predicting — year 50 result or year 51 prediction?
- `DONE` Q39. This is like image inpainting — we see patches and fill in blanks?
- `DONE` Q40. How many cells can we actually observe? 15×15×50 = 11,250 vs 8,000 total — is that really 1.4× coverage?
- `DONE` Q41. 1 observation per cell is useless for probability estimation — what's the real coverage?
- `v1` Q42. What's the optimal tradeoff: tile full map (1 obs/cell + prior) vs deep sample important areas (5-10 obs/cell)?
- `DONE` Q43. In the hundreds of sims for ground truth, does the initial state change or is the map identical every run?
- `DONE` Q44. Should we predict one class at a time (6 separate models) or all classes together (one multiclass model)?
- `DONE` Q45. Our R6 predictions show almost no settlements but the replay shows massive expansion — is our prediction wrong?

- `DONE` Q46. Should regime be discrete (low/medium/high) or a continuous parameter?
- `DONE` Q47. What metrics should we optimize for beyond KL divergence?

#### D. Lessons Learned (post-round)
- `v1` L1. Regime detection from initial-settlement survival is unreliable — use ALL observation data instead
- `v1` L2. The argmax visualization is misleading — it shows the single most likely class, not the probability spread
- `v1` L3. Always cross-check: count settlements in raw observations vs what your prior predicts

---

## Answers

### A1. Understanding the Map (Static Analysis)

**Q1. What is the distribution of terrain types in each initial grid?**
EMPIRICAL (25 seeds across rounds 1-5): Very consistent distribution across all seeds and rounds:
- **Plains**: ~59-63% (dominant terrain, 928-1013 cells)
- **Forest**: ~18-23% (288-366 cells)
- **Ocean**: ~11-15% (182-246 cells)
- **Settlement**: ~1.8-3.7% (29-60 cells)
- **Mountain**: ~0.9-3.1% (15-52 cells)
- **Port**: 0-0.3% (0-5 cells)

The map is mostly open plains with significant forest coverage. Settlements are sparse (30-60 per seed). Mountains and ocean are minority terrain but guaranteed static.

**Q2. How many land cells vs ocean cells vs mountain cells per seed?**
EMPIRICAL: Across all 25 seeds:
- **Static cells (ocean + mountain)**: 13-18% of map (210-290 cells). These are free predictions.
- **Dynamic land (plains + forest + settlements)**: 82-87% of map (1310-1390 cells). These need modeling.
- Ocean alone: 182-246 cells (11-15%)
- Mountain alone: 15-52 cells (1-3%)

Key insight: only ~14-17% of the map is trivially predictable. The remaining ~85% is where scoring happens.

**Q3. Where are initial settlements/ports located relative to coastlines, forests, mountains?**
EMPIRICAL (sampled rounds 1, 3, 5):
- **Adjacent to forest: 77-95%** — vast majority of settlements are placed near forests (food source)
- **Adjacent to ocean (coastal): 3-19%** — only a small fraction are coastal
- **Adjacent to mountain: 2-13%** — rarely near mountains
- **Ports: very few** — typically 0-5 per seed (most seeds have 0-3 ports)

Implication: Forests adjacent to initial settlements are the most "at risk" of becoming settlements/ruins. Settlement placement is strongly correlated with forest proximity.

**Q4. What is the spatial structure of fjords, and which land areas are isolated/connected?**
EMPIRICAL (flood-fill analysis):
- **One dominant land region** in every seed: 1200-1390 cells (the main island)
- **Small isolated pockets**: 0-6 extra regions per seed, typically 1-53 cells each
- **Most settlements are on the main landmass** — isolated pockets sometimes have settlements but are rare
- **Isolated land without settlements**: 0-50 cells per seed — these can be predicted as staying empty/forest

Implication: The map is essentially one big connected island with small fragments cut off by fjords/ocean/mountains. Simulation dynamics are dominated by the main landmass.

**Q5. Which cells are ocean or mountain and therefore guaranteed static?**
EMPIRICAL (verified against ground truth from 25 completed seeds):
- **Ocean: 100% deterministic** — all ocean cells have ground truth [1.0, 0, 0, 0, 0, 0]. Always class 0.
- **Mountain: 100% deterministic** — all mountain cells have ground truth [0, 0, 0, 0, 0, 1.0]. Always class 5.
- **Forest: varies wildly by round** — in low-expansion rounds (R3), 87% of forest cells are deterministic (>0.95 forest). In high-expansion rounds (R1, R5), only 17-31% are deterministic. Avg ground truth for forest cells: 71-97% forest, 0-18% settlement, rest small.
- **Plains: varies by round** — in low-expansion rounds, 91% deterministic (stay empty). In high-expansion rounds, only 18-35% deterministic. Avg: 77-99% empty, 0-17% settlement.
- **Initial settlements: NEVER deterministic** — 0% of settlement cells have >0.95 confidence in any class. They are the most stochastic cells. Avg outcomes vary heavily: some rounds settlements mostly die (68% empty), other rounds they mostly survive (44% settlement).
- **Initial ports: NEVER deterministic** — same as settlements, very uncertain outcomes.

CRITICAL FINDING: Hidden parameters vary dramatically between rounds. Round 3 had very low expansion (settlements mostly died, forests/plains stayed stable). Rounds 1 and 5 had high expansion (settlements grew, forests got replaced). This means the prior MUST be adapted per-round based on simulation observations.

### A2. Understanding the Simulation

**Q8. Do cells far from any initial settlement ever become settlements?**
FROM DOCS: "Prosperous settlements expand by founding new settlements on nearby land." and "Nearby thriving settlements may reclaim and rebuild ruined sites." This implies chain expansion is possible — a settlement expands, then the new settlement expands further. Over 50 years, this could reach cells quite far from initial positions. Exact range is a hidden parameter / unknown.

**Q10. Do forests ever disappear, or only appear/grow?**
FROM DOCS + EMPIRICAL: Forests CAN be replaced by settlements. In high-expansion rounds (R1, R5), forest cells have 13-18% avg probability of becoming settlements. In low-expansion rounds (R3), this drops to <1%. Forests also appear on former settlement/ruin sites ("reclaim ruined land"). So forests both appear AND disappear — they are NOT static.

**Q11. How often do settlements survive all 50 years vs collapse into ruins?**
FROM DOCS: Settlements can collapse from "starvation, sustained raids, or harsh winters — becoming Ruins." Survival rate depends heavily on hidden parameters (winter severity, raid aggression). Needs empirical observation.
EMPIRICAL: Varies enormously by round:
- **Round 3 (low expansion)**: Settlements almost entirely collapse — 68% become empty, ~30% become forest, <2% survive as settlement. Devastating.
- **Round 1 (high expansion)**: ~44% survive as settlement, ~36% become empty, ~18% become forest.
- **Round 5 (medium-high)**: ~34% survive, ~43% empty, ~20% forest.
Ruin probability is generally low in ground truth (1-3%) — ruins seem to be transient states that get reclaimed by forest or rebuilt.

**Q12. Do ports persist more often than inland settlements?**
FROM DOCS: Ports can trade (generating wealth + food), giving them an economic advantage. But they may also be more exposed to longship raids. Net effect unknown — needs empirical data.
EMPIRICAL: Ports are too rare to draw strong conclusions (0-5 per seed). In the data we have, ports show similar survival patterns to settlements — no clear advantage. The port class (2) appears very rarely in ground truth even for initial port cells; most initial ports end up as empty, settlement, or forest.

### A3. Inferring Hidden Parameters

**Q15. Are the hidden parameters consistent across seeds?**
FROM DOCS: "Hidden parameters — values controlling the world's behavior (same for all seeds in a round)." YES — hidden parameters are shared across all 5 seeds. Only the map layout differs per seed. This is crucial: observations from any seed inform predictions for all seeds.

EMPIRICAL CONFIRMATION: Within a round, all seeds show similar dynamics (e.g., R3 all seeds show mass settlement collapse, R1 all seeds show high expansion). Between rounds, dynamics vary dramatically. This confirms hidden params are per-round.

### A2 continued. Query-based findings

**Q6. If I query the same seed twice with the same viewport, how much do the results differ?**
EMPIRICAL (derived from ground truth — disagreement = P(two samples differ) = 1 - Σ pᵢ²):
- **Ocean/Mountain**: 0% disagreement. Two queries always agree. Perfectly deterministic.
- **Initial settlements**: 64% avg disagreement. Two queries will disagree on the outcome ~2/3 of the time. Extremely stochastic.
- **Forest**: varies by round. High-expansion (R1): 33-43% disagreement. Low-expansion (R3): 5% disagreement.
- **Plains**: varies by round. High-expansion (R1): 29-36% disagreement. Low-expansion (R3): 2-3%.
- **Overall dynamic cells with >5% disagreement**: R1: 1200-1300/1600, R3: 188-295/1600, R5: 1000-1156/1600.

KEY INSIGHT: In high-expansion rounds, ~75% of all cells are stochastic enough that two queries will disagree. In low-expansion rounds, only ~15% are. This means a single observation is unreliable for dynamic cells — you need multiple to estimate probabilities.

**Q7. What is the typical variance across runs for Settlement vs Ruin vs Forest outcomes?**
EMPIRICAL (per-class stats for dynamic cells across ground truth):

High-expansion rounds (R1, R5):
- **Empty**: mean=0.59-0.62, appears >50% in 70% of dynamic cells. Dominant class.
- **Settlement**: mean=0.13-0.16, appears >10% in 49-69% of dynamic cells. Very common but rarely dominant.
- **Forest**: mean=0.22, appears >50% in 23-25% of cells. Bimodal — cells either stay forest or don't.
- **Port**: mean=0.01, >10% in only 4-6% of cells. Rare everywhere.
- **Ruin**: mean=0.01, never >10%. Always a minor outcome — ruins are transient.
- **Entropy**: mean=0.57-0.65. Most cells have substantial uncertainty.

Low-expansion round (R3):
- **Empty**: mean=0.74, dominant everywhere.
- **Settlement**: mean=0.003, essentially zero. Settlements almost never survive.
- **Forest**: mean=0.26, either stays forest or doesn't (bimodal).
- **Ruin**: mean=0.0006, negligible.
- **Entropy**: mean=0.08. Most cells (81%) are near-deterministic. Very predictable.

CRITICAL: Ruin (class 3) is ALWAYS a minor class. Never assign high ruin probability. Port (class 2) is also very rare. The main battle is Empty vs Settlement vs Forest.

**Q9. What is the maximum expansion radius from an initial settlement after 50 years?**
EMPIRICAL (manhattan distance from nearest initial settlement to cells with P(settle+port) > threshold):

High-expansion rounds (R1):
- P>5%: up to **8 cells** away, 1000-1260 new cells per seed
- P>10%: up to **7-8 cells** away, 850-1135 cells
- P>25%: up to **5-6 cells** away, 220-265 cells
- Average expansion distance: 2.5-3.5 cells

Medium expansion (R5):
- P>5%: up to **5-6 cells** away
- P>25%: up to **4 cells** away
- Average: 1.6-2.5 cells

Low expansion (R3):
- **Zero new settlement cells at any threshold.** No expansion at all.

CONCLUSION: Maximum expansion radius is ~8 manhattan distance in high-expansion rounds, ~5-6 in medium, 0 in low. Settlements >8 cells from any initial settlement are essentially impossible. This is a hard boundary for predictions.

**Q13. Can I estimate hidden parameters from a few observations?**
EMPIRICAL: YES — the "expansion regime" is the dominant hidden parameter and is easy to detect:

| Round | Initial settle → Empty | Initial settle → Settlement | Regime |
|-------|----------------------|---------------------------|--------|
| R1    | 37%                  | 40%                       | High expansion |
| R2    | 38%                  | 40%                       | High expansion |
| R3    | 68%                  | 2%                        | Low expansion (collapse) |
| R4    | 49%                  | 22%                       | Medium |
| R5    | 44%                  | 32%                       | Medium-high |

Strategy: Query 1-2 viewports centered on initial settlements. Count how many survive vs become empty/forest. If most survive → high expansion round. If most collapse → low expansion. This classification from 3-5 settlement observations is sufficient to select the right prior.

Adjacent plains cells are also diagnostic: P(settlement) on adj plains ranges from 1% (R3) to 24% (R5).

**Q14. If I observe the same seed multiple times, can I build a local probability distribution?**
EMPIRICAL (simulated from ground truth, with 0.01 floor + renormalize):

| Observations | Mean KL | Estimated Score |
|-------------|---------|-----------------|
| 1           | 1.53    | ~1              |
| 2           | 0.86    | ~8              |
| 3           | 0.62    | ~16             |
| 5           | 0.38    | ~32             |
| 10          | 0.15    | ~63             |
| 20          | 0.09    | ~77             |
| 50          | 0.04    | ~88             |

YES — multiple observations dramatically improve predictions. But the budget constraint is severe:
- 50 queries, 15×15 viewport = 225 cells per query
- 10 queries on same viewport → 10 obs for 225 cells = 14% of map well-estimated
- Remaining 86% must rely on prior + extrapolation

OPTIMAL STRATEGY HINT: Don't observe the whole map once. Instead, deeply sample a few viewports around settlements (5-10× each), build empirical distributions for those cells, then extrapolate to unobserved cells using spatial patterns and the regime classification from Q13.

**Q16. What is the minimum number of queries per seed to get a useful signal?**
EMPIRICAL (simulated, avg score across 5 seeds):

| Queries/seed | Round 1 (high) | Round 3 (low) | Round 5 (med-high) |
|-------------|----------------|---------------|---------------------|
| 0           | 52             | 29            | 49                  |
| 2           | 53             | 30            | 50                  |
| 5           | 55             | 32            | 52                  |
| 10          | 57             | 37            | 54                  |
| 15          | 59             | 41            | 57                  |
| 20          | 61             | 45            | 59                  |

2 queries per seed gives enough signal for regime detection (Q13) which is the highest-leverage information. Beyond that, each additional query adds ~0.5-1.0 score points. The marginal return is steady but modest — the static prior with correct regime is already doing most of the work. Minimum useful: **2 queries** (for regime detection). Recommended: **8-10** (good balance).

### B1. Query Budget Optimization

**Q17. What is the optimal split of 50 queries across 5 seeds?**
v1 ANALYSIS: Since hidden parameters are shared across all seeds (Q15), regime detection only needs to happen once. Optimal split:
- **2-3 queries on seed 0**: Regime detection. Observe initial settlements, classify high/medium/low.
- **Remaining 47-48 split ~10 per seed**: Coverage + depth.
- Equal split (10/seed) is fine — there's no benefit to concentrating on fewer seeds since all 5 must be submitted and each uses the same regime prior.
- Exception: if one seed has unusually complex settlement layout, give it 1-2 extra.

REVISIT: Test whether concentrating queries gives better per-seed scores that outweigh worse scores on neglected seeds.

**Q18. Tile the map vs repeatedly sample the same area?**
v1 ANALYSIS: Tiling slightly wins. With 10 queries/seed:
- Tile(8) + settle_repeat(2) = **69-71** score
- Focused 5 viewports x2 = **67-70** score
- Deep 1 viewport x10 = **68-70** score

The differences are small (~2 points). Tiling wins because the distance-decay prior is already decent for observed cells — the main gain comes from coverage (correcting wrong priors on cells you haven't seen). But deep sampling helps more for the specific cells observed. Best hybrid: **tile first for coverage, then repeat settlement-heavy viewports with remaining budget.**

**Q19. Which areas are most uncertain and benefit most from observation?**
v1 ANALYSIS: From Q7, the ranking by uncertainty:
1. **Initial settlement/port cells** — always the most stochastic (64% disagreement rate). Highest entropy.
2. **Plains within distance 0-2 of settlements** — 18-22% settlement probability in high-expansion rounds.
3. **Forest cells near settlements** — can become settlements (14-16% in high rounds).
4. **Plains at distance 3-5** — moderate expansion chance (8-19%).
5. **Plains at distance 6-8** — low but nonzero (3-12%).
6. **Plains at distance 9+** — nearly deterministic (>99% empty). Not worth observing.
7. **Ocean/mountain** — fully deterministic. Never observe these.

Priority: observe settlement clusters first, then nearby plains/forests. Never waste queries on ocean/mountain edges.

**Q20. Dynamic areas vs static verification?**
v1 ANALYSIS: **Always dynamic areas.** Reasons:
- Ocean/mountain are 100% deterministic — the prior already nails them perfectly with zero queries.
- Predicting static cells correctly adds ~0 score improvement (Q23 shows: uniform=4.7, static-only=4.7). Entropy weighting means static cells contribute nothing to the score.
- All scoring weight is on dynamic cells. Every query should target settlements and their surroundings.

**Q21. What viewport size maximizes information?**
v1 ANALYSIS: **Use 15×15 (maximum).** Reasons:
- 15×15 = 225 cells per query. 5×5 = 25 cells = 9× fewer cells for the same budget cost.
- Repeated small viewports give better variance estimates for those specific cells, but you sacrifice coverage.
- Coverage matters more than depth (Q18): the prior is decent, so correcting it across more cells beats precise estimates on fewer cells.
- Exception: if you've already covered the map and have budget left, repeating a settlement-heavy 15×15 viewport is fine.

### B2. Prediction Strategy

**Q22. What does a good baseline look like?**
v1 ANALYSIS: A good zero-query baseline using terrain type + distance-from-settlement:
- Ocean → [1.0, 0, 0, 0, 0, 0]
- Mountain → [0, 0, 0, 0, 0, 1.0]
- Forest → [0.07, 0.14, 0.01, 0.01, 0.76, 0.01] (high regime)
- Settlement → [0.43, 0.32, 0.01, 0.03, 0.20, 0.01] (avg across regimes)
- Plains d≤2 → [0.70, 0.18, 0.01, 0.02, 0.05, 0.01]
- Plains d3-5 → [0.85, 0.10, 0.01, 0.01, 0.02, 0.01]
- Plains d6-8 → [0.95, 0.03, 0.005, 0.005, 0.005, 0.005]
- Plains d9+ → [0.99, 0.005, 0.001, 0.001, 0.001, 0.001]

This scores 52-69 depending on round (without regime adaptation). With regime adaptation: much higher.
REVISIT: need to tune priors per regime, not just use averages.

**Q23. How much score improvement from predicting static cells correctly?**
v1 ANALYSIS: **Zero.** Predicting ocean+mountain correctly vs uniform gives identical scores (4.7 vs 4.7). This is because entropy-weighted scoring assigns zero weight to static cells (they have zero entropy). All score comes from dynamic cells. Static prediction is free but worthless for score.

**Q24. What probability floor is optimal?**
v1 ANALYSIS: Tested floors from 0.001 to 0.05:

| Floor | Round 1 | Round 3 | Round 5 |
|-------|---------|---------|---------|
| 0.001 | 68.7    | 44.5    | 71.5    |
| 0.005 | 69.0    | 44.5    | 71.5    |
| 0.010 | 69.0    | 44.5    | 71.5    |
| 0.020 | 68.2    | 41.6    | 69.6    |
| 0.050 | 59.3    | 32.7    | 59.1    |

**Optimal floor: 0.005.** Slightly better than 0.01 and much better than 0.02+. Below 0.005, no further improvement. 0.05 is catastrophically bad (-10 points). The docs recommendation of 0.01 is fine but 0.005 is marginally better.

**Q25. Can I use spatial autocorrelation to propagate observations?**
v1 ANALYSIS: **Weak effect.** Adjacent cells have KL divergence of 1.9-6.3, while random pairs have 2.1-6.2. The ratio is only 1.0-1.3×. Adjacent cells are barely more similar than random cells. This means spatial smoothing won't help much — the distance-from-settlement feature is already capturing the relevant spatial structure. Don't invest in complex spatial interpolation.

REVISIT: Check if cells of the same terrain type at the same distance are more correlated than raw adjacency.

**Q26. Is a distance-from-settlement heuristic competitive?**
v1 ANALYSIS: **Yes — it's the core strategy.** Distance-decay model fitted to ground truth achieves:
- Round 1: 78.5 (ceiling, same-round fit)
- Round 2: 83.8
- Round 3: 83.6
- Round 4: 89.1
- Round 5: 77.6

This is very strong (78-89). The ceiling means: if you know the exact regime and have perfect per-distance priors, a simple heuristic scores 78-89 with zero queries. The gap between this ceiling and 100 comes from cell-level variance that only direct observation can resolve. A learned model might help bridge that gap but the heuristic captures most of the signal.

REVISIT: Test cross-round transfer — fit on rounds 1-4, test on round 5.

### C. Fundamental Understanding

**Q31. Does the simulation progress in real-time during the round window, or does each query run a full 50-year sim instantly?**
ANSWER: **Each query runs a complete 50-year simulation instantly and returns the FINAL state.** The simulation does NOT progress in real-time during the 2h45m window. From the docs:
- "The simulator runs a procedurally generated Norse world for 50 years"
- "Each call uses a different random sim_seed, so you get a different stochastic outcome"
- The simulate endpoint takes the same parameters every time — there is no "time" or "year" parameter

The 2h45m prediction window is just the deadline for you to observe and submit. It has nothing to do with simulation time. Every query you make, whether at minute 1 or minute 164, runs the same full 50-year simulation and shows you the final result. The "progress" shown on the website (69%) is just how much of the 2h45m submission deadline has elapsed, not simulation progress.

**Q32. Does timing of when we send queries during the window matter?**
ANSWER: **No.** Since each query runs a full independent 50-year simulation, it doesn't matter when during the window you send them. A query at minute 1 and a query at minute 160 both run the exact same simulation (different random seed, same hidden parameters, same initial state, same 50 years). The only timing constraint is:
- Queries must be sent while round status is "active"
- Submissions must be sent before the window closes
- Rate limits: max 5 simulate requests/second, 2 submit requests/second

So there's no benefit to spreading queries over time. Fire them all whenever convenient.

**Q33. What exactly are we predicting?**
ANSWER: **The probability distribution of terrain type for each cell AFTER 50 years of simulation.** From the docs:
- "predict the probability distribution of terrain types across the entire map"
- Ground truth example: "a cell might have ground truth [0.0, 0.60, 0.25, 0.15, 0.0, 0.0] — meaning 60% chance of Settlement, 25% Port, 15% Ruin, after 50 years"
- Ground truth is computed by the organizers "running the simulation hundreds of times"

So we predict: for each cell (y, x), what is the probability that it ends up as each of the 6 terrain classes after the 50-year simulation completes? Not year 51. Not a trajectory over time. Just the final state distribution.

The prediction is a H×W×6 tensor where prediction[y][x] = [P(empty), P(settlement), P(port), P(ruin), P(forest), P(mountain)] and these 6 values sum to 1.0.

Each simulation query gives us ONE random sample from this distribution (one possible 50-year outcome). Multiple queries of the same area give us multiple samples, which we can average to estimate the true probabilities.

**Q34. What does round_weight do and why does it increase?**
ANSWER: From the docs:
- `leaderboard_score = max(round_score × round_weight) across all rounds`
- "Round weights increase over time (1.05^round_number)"
- "Only your single best weighted result matters"

Round weights observed: R1=1.05, R2=1.10, R3=1.16, R4=1.22, R5=1.28, R6=1.34.

This means: **later rounds are worth more on the leaderboard.** A score of 75 on round 6 (×1.34 = 100.5 weighted) beats a score of 90 on round 1 (×1.05 = 94.5 weighted). The increasing weight rewards teams that improve over time and makes later rounds more strategically important. Your leaderboard position is determined by your single best `round_score × round_weight`, so every new round is an opportunity to beat your previous best.

**Q35. Should we spread queries over time to track progression, or fire them all at once?**
ANSWER: **Fire them all at once (or as fast as rate limits allow).** Since each query runs a complete 50-year simulation instantly (Q31), there is no "progression" to track during the window. Every query gives you the same type of information: one random final-state sample. Spreading them over time provides zero additional information.

The optimal strategy is:
1. Fire 2-3 queries immediately for regime detection (Q13)
2. Based on regime, fire remaining queries for map coverage
3. Build predictions and submit
4. If you improve your model, resubmit (last submission counts)

The only reason to wait would be if you need time to analyze results and plan subsequent queries — but the queries themselves are time-independent.

**Q36. Can we see the 50-year progression, or only the final state?**
ANSWER: **Only the final state.** The simulation is a complete black box. You never see intermediate years. Each query runs all 50 years internally and returns only the year-50 snapshot through your viewport. The internal phases (growth, conflict, trade, winter, environment × 50 years) are invisible — you can only infer what happened from the final outcome and the docs description of mechanics.

**Q37. Why are multiple queries of the same seed/area random? What is sim_seed vs seed_index?**
ANSWER: Two distinct sources of randomness:

- **seed_index (0-4)**: You choose this. Determines the **initial map** — terrain layout, settlement positions, port locations. Same seed_index always gives the same starting map. There are 5 per round.
- **sim_seed**: The server picks a NEW random one per query. Determines all **stochastic outcomes during simulation** — which raids succeed, how harsh winters are, where settlements expand, who wins conflicts, etc.

So: same seed_index + same viewport + different queries → **same starting map, different 50-year history, different final state.** That's why cell outcomes are probabilistic. A settlement might survive in 40% of sim_seeds and collapse in 60%. Our job is to estimate these percentages.

The 5 seed_indices give us 5 different maps to predict. The sim_seed randomness within each is what makes it a probability estimation problem rather than a deterministic one.

**Q38. What exactly is the final state we're predicting? Don't we already know parts of it?**
ANSWER: We predict the **probability distribution of the year-50 outcome** for every cell. Not year 51 (there is no year 51). Not a time series. Just: "after running this simulation to completion, what's the chance each cell is Empty/Settlement/Port/Ruin/Forest/Mountain?"

**And yes — each query shows us one sample of exactly this answer.** The queries ARE peeks at the distribution we're trying to predict. The challenge is that each peek is:
- **Partial** — only a 15×15 viewport, not the full 40×40 map
- **Noisy** — one random outcome, not the true probabilities (a cell that's 60% Settlement might show up as Ruin in your one observation)
- **Scarce** — only 50 queries total across 5 seeds

The ground truth is computed from hundreds of sim runs. We get at most ~10 observations per cell (if we focus all queries on one area). So our job is: combine these noisy samples with priors (terrain type, distance from settlements, regime detection) to estimate the full probability distribution for all 1600 cells × 5 seeds.

Example: if we query one cell 8 times and see [Settlement, Settlement, Empty, Settlement, Ruin, Settlement, Empty, Settlement]:
- Empirical estimate: P(settle)=5/8=0.625, P(empty)=2/8=0.25, P(ruin)=1/8=0.125
- True ground truth might be: P(settle)=0.55, P(empty)=0.25, P(ruin)=0.12, P(forest)=0.06, P(port)=0.02
- We'd miss the forest/port probability entirely without a floor — hence the 0.005 floor.

**Q39. This is like image inpainting — we see patches and fill in blanks?**
ANSWER: Yes, exactly. The analogy is:
- **Initial state** = the sketch/outline (fully known)
- **Each query** = seeing a 15×15 patch of the final "photo" (one random version of it)
- **Prediction** = reconstructing the full photo from patches + understanding of the rules that generated it
- **Prior** = what you know about the rules (terrain type, distance from settlements, regime)

The strategic layers:
1. Observe patches → see parts of the final image
2. Infer simulation parameters → understand what rules generated this image
3. Use neighboring pixel behavior → spatial patterns help fill gaps
4. Combine with initial state → the sketch is fully known

**Q40. 15×15×50 = 11,250 cell-observations vs 8,000 cells — is that really 1.4× coverage?**
ANSWER: **The 1.4× number is misleading and practically wrong.** The math is technically correct (11,250 observations / 8,000 cells = 1.4×), but it hides a critical problem: each observation is a SINGLE SAMPLE from a probability distribution, not the distribution itself. Seeing a cell once tells you it was "Settlement" in that run — you cannot tell if it's 90% Settlement or 50% Settlement from one sample.

Real coverage per seed (10 queries, 225 cells each = 2,250 cell-observations for 1,600 cells):
- At 1 obs/cell: cover 100% of map, but each observation is nearly useless alone (score ~1 from pure empirical)
- At 5 obs/cell: cover 28% of map with decent probability estimates
- At 10 obs/cell: cover 14% of map with good estimates (score ~63)
- At 20 obs/cell: cover 7% of map with great estimates (score ~77)

**Q41. 1 observation per cell is useless for probability estimation — what's the real coverage?**
ANSWER: Correct. 1 observation is binary: you see ONE outcome, not probabilities. You can't distinguish a 60/40 cell from a 90/10 cell with 1 sample.

BUT — 1 observation + a good prior is valuable. The observation doesn't estimate the distribution alone; it CORRECTS the prior. If your prior says P(settlement)=0.30 and you observe Settlement, the blended estimate shifts up. If you observe Empty, it shifts down. This correction is noisy but better than nothing.

That's why our R6 tiling scored decently (~55-70 estimated): the prior did 90% of the work, and each single observation nudged it in the right direction.

Without a prior, 1 obs/cell scores ~1. With a good prior, 1 obs/cell scores ~55-70. The prior is the real engine; observations are refinements.

**Q42. What's the optimal tradeoff: tile full map vs deep sample important areas?**
v1 ANALYSIS: Depends on prior quality:
- **Bad prior** → tile everything. 1 noisy observation correcting a wrong prior is high-value.
- **Good prior** → deep sample dynamic cells. Prior already handles the boring 80%; spend budget getting sharp estimates on the ~200-300 cells that actually contribute to the score.

The key insight: **entropy weighting means static cells (ocean, mountain, far plains) contribute ZERO to the score.** Every query on a static area is wasted. Only ~15-20% of cells are dynamic enough to affect scoring.

Proposed hybrid for next round:
1. **Phase 1 (2-3 queries)**: Regime detection on seed 0 settlement areas
2. **Phase 2 (~47 queries)**: ~9 per seed, focused on settlement clusters with repeat observations. Skip tiling ocean/mountain/far plains entirely.

The question is whether overlapping settlement viewports (2-3 obs per dynamic cell) beats full tiling (1 obs per all cells). Need to simulate this against historical ground truth to be sure.

REVISIT: Run simulation comparing tile-all vs deep-sample-settlements on rounds 1-5 ground truth.

**Q43. In the hundreds of sims for ground truth, does the initial state change or is the map identical every run?**
ANSWER: **The initial state is identical every single run.** For a given seed_index in a given round:
- The terrain grid (ocean, plains, forest, mountain) is the same
- Settlement positions are the same
- Port status is the same
- Hidden parameters are the same

The ONLY thing that changes between runs is the sim_seed — the random number that determines stochastic events during the 50-year simulation (raid outcomes, winter severity, expansion targets, etc).

This is confirmed by the docs:
- "Map seed — Determines terrain layout (fixed per seed, visible to you)"
- "Sim seed — Random seed for each simulation run (different every query)"
- "Hidden parameters — values controlling the world's behavior (same for all seeds in a round)"

This means the initial state is a **perfect, noise-free input**. We know it with 100% certainty from the `/rounds/{id}` endpoint. All uncertainty comes from the stochastic simulation, not from the starting conditions.

**Q44. Should we predict one class at a time (6 separate models) or all classes together (one multiclass model)?**
ANSWER: **Multiclass together, absolutely.** The 6 class probabilities are deeply entangled — predicting them separately would lose critical information.

Evidence from correlation analysis:

1. **Strong negative correlations**: Empty ↔ Forest = -0.94. These are essentially a seesaw — if a cell is more likely Forest, it's less likely Empty, and vice versa. A separate model for "Forest" that doesn't know about "Empty" would miss this.

2. **Positive correlations**: Settlement ↔ Ruin = +0.40 to +0.65. Cells that are likely to have settlements are ALSO more likely to have ruins (because ruins come from collapsed settlements). A separate "Ruin" model not knowing about Settlement would miss this.

3. **Sum-to-1 constraint**: The 6 probabilities MUST sum to 1.0. Predicting them independently and then renormalizing would distort the distribution. Multiclass naturally respects this constraint.

4. **Effective dimensionality is only 2**: SVD analysis shows:
   - **Component 1 (91%)**: The Empty ↔ Forest axis. Is this cell land that stays empty, or forest?
   - **Component 2 (8%)**: The Settlement/Ruin axis. Does a settlement appear here?
   - **Components 3-6 (<1%)**: Port, Ruin details — negligible.

   In low-expansion rounds (R3), it's literally 1-dimensional: just Empty vs Forest.

5. **The "real" problem is only 3 classes**: Empty, Settlement, Forest account for 99%+ of probability mass. Port is <2%, Ruin is <3%, Mountain is 0% on dynamic cells. A model that nails the Empty/Settlement/Forest split and assigns minimum floor to Port/Ruin/Mountain would score nearly as well as a perfect model.

CONCLUSION: Use one multiclass model that outputs all 6 probabilities jointly. If building something simple, focus on getting the Empty vs Settlement vs Forest split right, then assign floor values to Port/Ruin/Mountain.

**Q45. Our R6 predictions show almost no settlements but the replay shows massive expansion — is our prediction wrong?**
ANSWER: Two things were happening:

1. **The argmax visualization is misleading.** The prediction visualization shows the MOST LIKELY class per cell. Even if P(settlement)=0.40, if P(empty)=0.45, the cell shows as Empty. The replay viewer shows ONE simulation run where every cell is deterministically one type. A cell with 30% settlement chance will be a settlement in 30% of runs and empty in 70%. The replay always looks "more settled" than the probability prediction.

2. **BUT we also had the wrong regime.** Our regime detection classified R6 as "medium" based on 4/12 initial settlements surviving (33%). This was unreliable — small sample, high noise. When we checked ALL observations: **20-27% of all observed cells were settlements**, settlements grew from ~40 to ~400+ per seed. This is clearly HIGH expansion.

The fix: switched to high-expansion priors (from R1/R2 ground truth) and resubmitted. Result: 26-40 cells with Settlement as argmax, 1,200+ cells with >10% settlement probability.

### D. Lessons Learned

**L1. Regime detection from initial-settlement survival is unreliable.**
Our method: count how many initial settlements survived → classify. Problem: initial settlements have complex dynamics — they can die AND be replaced by new ones nearby. A round with high expansion can still kill many initial settlements (through conflict) while founding hundreds of new ones.

BETTER METHOD: Count total settlement cells in observations vs total observed cells. If settlements are >15% of observed cells → high expansion. If <5% → low expansion. This uses ALL observation data, not just the ~12 initial settlement cells.

**L2. The argmax visualization is misleading.**
It shows the single most likely class, not the probability spread. A cell with [0.45 empty, 0.40 settlement, 0.15 forest] appears as "Empty" in the visualization even though it has near-equal settlement chance. For scoring, the full probability vector matters. Never judge prediction quality from the argmax view alone.

**L3. Always cross-check: count settlements in raw observations vs what your prior predicts.**
Simple sanity check after observations: if 22% of observed cells are settlements but your prior assigns <5% settlement probability on average, something is wrong. This should be an automated check before submission.

**Q46. Should regime be discrete (low/medium/high) or a continuous parameter?**
ANSWER: **Continuous, absolutely.** The discrete buckets were a crude approximation that lost information and caused misclassification on R6.

Observed settlement rates across rounds: R3=0.003, R4=0.10, R5=0.14, R1=0.18, R2=0.21. This is a continuous spectrum, not 3 buckets.

Linear regression of `settlement_rate → per_bucket_priors` fits excellently:
- Per-bucket P(settlement) correlates r=0.94-0.99 with overall rate
- RMSE is 0.01-0.04 per bucket — very low error
- The model is: `prior[bucket][class] = a * observed_rate + b` (simple linear)

The continuous approach:
1. Observe viewport(s), count settlement+port cells / total observed cells = **rate**
2. Plug rate into linear model → get priors for each terrain bucket
3. Apply priors, blend with observations, submit

This eliminates the regime classification step entirely and gives smoothly interpolated priors. No more "is it medium or high?" — just measure the rate (e.g. 0.17) and get exact priors.

Example outputs at different rates:
- rate=0.003: settlement cells get P(settle)=0.03 (nearly all die)
- rate=0.10: settlement cells get P(settle)=0.22 (some survive)
- rate=0.15: settlement cells get P(settle)=0.31 (many survive)
- rate=0.22: settlement cells get P(settle)=0.45 (most survive, heavy expansion)

THIS SHOULD REPLACE THE DISCRETE REGIME SYSTEM in quickstart.py for next round.

**Q47. What metrics should we optimize for beyond KL divergence?**
ANSWER: Tested 5 candidate metrics against final score across rounds 1-5:

**Correlation with score:**
| Metric | r with score | Notes |
|--------|-------------|-------|
| Brier(settlement) | -0.983 | Strongest predictor. Settlement errors dominate. |
| Brier(empty) | -0.957 | Closely tied to settlement (they're a seesaw) |
| Brier(forest) | -0.846 | Second most variable class |
| Top-100 cell concentration | -0.848 | Are errors focused or spread? |
| Settlement rate error | -0.817 | Getting the rate right = getting everything right |

**Metrics to track, in priority order:**

PRIMARY (optimize these — they drive the score):
1. **Settlement rate calibration**: `|predicted_rate - observed_rate|`. This is the single most impactful lever. R4 had rate error 0.026 → score 85. R3 had rate error 0.158 → score 51. Target: < 0.03.
2. **Brier(settlement)** on dynamic cells: Mean squared error of P(settlement) predictions. Target: < 0.005. This is the most expensive class to get wrong because settlement cells have the highest entropy.
3. **Entropy-weighted KL**: The actual competition metric. Target: < 0.05 for score > 86.

DIAGNOSTIC (monitor to find problems):
4. **Per-terrain-bucket KL contribution**: Which terrain type is hurting us? Initial settlements? Forests? Near plains? Tells us where to focus model improvements.
5. **Top-N cell KL concentration**: If top 100 cells account for >50% of KL, we have a few catastrophic predictions. If <30%, errors are spread out (harder to fix, but less critical).
6. **Brier(forest)**: Second most variable class. Forest vs Empty misclassification is the main error on non-settlement cells.

IGNORE (not worth tracking):
- Port/Ruin/Mountain Brier: always < 0.002, negligible impact
- Static cell accuracy: zero entropy weight, zero score impact
- Argmax accuracy: misleading — a correct argmax with wrong probabilities scores worse than a wrong argmax with calibrated probabilities
