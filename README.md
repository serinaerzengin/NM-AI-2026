# NM i AI 2026

Competition repository for the Norwegian AI Championship (NM i AI) 2026. Three independent tasks spanning LLM agents, probabilistic prediction, and computer vision.

## Task 1 — Tripletex Accounting Agent

An LLM-powered agent that autonomously solves accounting tasks against the Tripletex sandbox API. Receives natural-language prompts (in 7 languages) describing accounting operations — customer creation, invoicing, payroll, travel expenses, ledger corrections, etc. — and executes them via API calls.

**Approach:** Tool-calling agent loop where the LLM has direct access to four HTTP tools (GET, POST, PUT, DELETE). A hardened payload correction layer silently fixes ~20 categories of common LLM mistakes before requests are sent (wrong field names, missing defaults, structural errors). Dynamic system prompt includes detailed domain knowledge for 30+ task types and adapts pressure warnings based on time/turn/error budgets.

**Key components:**
- **Agent loop** with Gemini as the backbone LLM, 4 tool functions with caching and auto-recovery
- **Payload correction system** — pattern-based fixes for vouchers, orders, salary, travel expenses, dimensions, etc.
- **Proactive setup helpers** — auto-registers bank accounts, onboards employees, creates employment records
- **Domain knowledge** — 40+ API endpoint patterns, Norwegian chart of accounts, VAT types, 25 business rules

**Stack:** Python, FastAPI, Gemini API, Docker, Google Cloud Run

---

## Task 2 — Astar Island

Predict terrain-type probability distributions on a 40x40 island grid after a 50-year stochastic simulation. Given 5 maps per round with hidden simulation parameters, and a budget of only 50 observation queries (15x15 viewports) shared across all maps.

**Approach:** Two-layer prediction system with adaptive blending.

1. **CatBoost base model** — trained on historical rounds using 28 engineered features per cell (terrain flags, settlement proximity, density counts, BFS reachability, distance metrics, round-level statistics, interaction features). Entropy-weighted training to match the scoring formula.

2. **Empirical bins** — built from 50 live queries (~11,250 observed cells). Cells are partitioned into hierarchical bins by distance-to-settlement, coastal/inland, terrain type, and settlement density. Fine bins fall back to coarser bins when observations are sparse.

3. **Adaptive blending** — `final = w * empirical + (1-w) * model` where the weight adapts based on observation count and settlement activity rate. Sigmoid-parameterized stat blending interpolates between observed and historical round statistics. All hyperparameters (k values, sigmoid coefficients, CatBoost params) tuned via Optuna with leave-one-round-out cross-validation.

**Query strategy:** Greedy viewport placement prioritizing settlement-dense areas, with proportional allocation across maps and a minimum floor per map.

**Stack:** Python, CatBoost, Optuna, NumPy

---

## Task 3 — NorgesGruppen Object Detection

Detect and classify grocery products on Norwegian store shelf images. Scoring: 70% detection mAP@0.5 + 30% classification mAP@0.5 across 357 product categories.

**Approach:** Multi-model ensemble with test-time augmentation.

- **2-model ONNX ensemble** at different input scales (1280x1280 and 800x800) to capture products at different sizes
- **Test-time augmentation** with horizontal flips — shelf products are spatially symmetric
- **Weighted Boxes Fusion (WBF)** to merge predictions across models and augmentations, outperforming standard NMS
- Low confidence threshold (0.05) to catch small/occluded products, with post-fusion filtering

**Training:** RTDETRv2-x and YOLOv8 variants trained on 248 annotated shelf images with mosaic augmentation, rotation, scaling, and random erasing. Extended with offline augmentation (albumentations) and synthetic data generation (product cutouts pasted onto empty shelf backgrounds generated via Gemini API).

**Models explored:** YOLOv8 (n/s/m/l/x), RTDETRv2-l/x, DINOv2-DETR, MambaVision, RF-DETR

**Stack:** Python, PyTorch, Ultralytics, ONNX Runtime (CUDA), Optuna

---

## Repository Structure

```
task1-Tripletex/       # Accounting agent (FastAPI + Gemini + Tripletex API)
task2-AstarIsland/     # Terrain prediction (CatBoost + empirical bins)
task3-NorgesGruppen/   # Object detection (YOLO/RTDETR ensemble + WBF)
```

## License

MIT
