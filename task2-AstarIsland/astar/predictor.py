import numpy as np
import xgboost as xgb

from .types import MapState, Prediction, RoundStats, NUM_CLASSES, CLASS_EMPTY, CLASS_MOUNTAIN, CLASS_FOREST
from .features import compute_features, NUM_FEATURES, FEATURE_NAMES
from .calibration import round_stats_to_array

PROB_FLOOR = 0.0005

# Cell features to interact with round-level settlement_rate
_DIST_IDX = FEATURE_NAMES.index("dist_nearest_settlement")
_SETTLE_R5_IDX = FEATURE_NAMES.index("settlements_r5")
_COASTAL_IDX = FEATURE_NAMES.index("adjacent_ocean")
_FOREST_ADJ_IDX = FEATURE_NAMES.index("adjacent_forests")


def _build_row(cell_feats: np.ndarray, stats_arr: np.ndarray) -> np.ndarray:
    """Build model input row: cell features + round stats + interaction features."""
    # Key interactions: round stats * cell features that matter most
    settle_rate = stats_arr[1]  # settlement_rate
    ruin_rate = stats_arr[0]
    dist = cell_feats[_DIST_IDX]
    settle_r5 = cell_feats[_SETTLE_R5_IDX]
    coastal = cell_feats[_COASTAL_IDX]
    forest_adj = cell_feats[_FOREST_ADJ_IDX]

    interactions = np.array([
        settle_rate * dist,          # expansion reach
        settle_rate * settle_r5,     # settlement density effect
        settle_rate * coastal,       # port formation potential
        ruin_rate * dist,            # ruin spread
        settle_rate * forest_adj,    # food-driven growth
        settle_rate / (dist + 1),    # settlement influence decay
    ], dtype=np.float32)

    return np.concatenate([cell_feats, stats_arr, interactions])


class Predictor:
    """XGBoost predictor: cell features + round stats → 6-class distribution."""

    def __init__(self, params: dict | None = None):
        """Initialize with XGBoost hyperparameters.

        Args:
            params: Dict with keys like n_estimators, max_depth, etc.
                    If None, uses defaults. Can be loaded from best_params.json.
        """
        defaults = {
            "n_estimators": 500,
            "max_depth": 7,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.01,
            "reg_lambda": 1.0,
            "min_child_weight": 1,
        }
        if params:
            defaults.update({k: v for k, v in params.items()
                            if k in defaults})
        self.prob_floor = params.get("prob_floor", PROB_FLOOR) if params else PROB_FLOOR
        self.model = xgb.XGBRegressor(
            n_estimators=defaults["n_estimators"],
            max_depth=defaults["max_depth"],
            learning_rate=defaults["learning_rate"],
            subsample=defaults["subsample"],
            colsample_bytree=defaults["colsample_bytree"],
            reg_alpha=defaults["reg_alpha"],
            reg_lambda=defaults["reg_lambda"],
            min_child_weight=defaults["min_child_weight"],
            multi_strategy="multi_output_tree",
            tree_method="hist",
            objective="reg:squarederror",
            n_jobs=-1,
        )
        self._fitted = False

    def fit(
        self,
        states: list[MapState],
        ground_truths: list[np.ndarray],
        round_stats: list[RoundStats],
    ) -> None:
        """Train on historical data with entropy-weighted samples.

        Args:
            states: List of initial map states.
            ground_truths: List of (40, 40, 6) ground truth tensors.
            round_stats: One RoundStats per round (shared across seeds of the same round).
        """
        X_rows = []
        y_rows = []
        w_rows = []

        for state, gt, stats in zip(states, ground_truths, round_stats):
            features = compute_features(state)  # (40, 40, N_FEATURES)
            stats_arr = round_stats_to_array(stats)  # (4,)
            h, w = gt.shape[:2]

            # Compute entropy for sample weighting
            eps = 1e-12
            entropy = -np.sum(gt * np.log(gt + eps), axis=-1)  # (H, W)

            for r in range(h):
                for c in range(w):
                    if _is_static_cell(state.grid[r, c], gt[r, c]):
                        continue
                    row = _build_row(features[r, c], stats_arr)
                    X_rows.append(row)
                    y_rows.append(gt[r, c])
                    # Weight: entropy + small floor so low-entropy cells still contribute
                    w_rows.append(entropy[r, c] + 0.1)

        X = np.array(X_rows, dtype=np.float32)
        y = np.array(y_rows, dtype=np.float32)
        sample_weight = np.array(w_rows, dtype=np.float32)

        self.model.fit(X, y, sample_weight=sample_weight)
        self._fitted = True

    def predict(self, state: MapState, round_stats: RoundStats) -> Prediction:
        """Predict distributions for all cells in a map.

        Returns a Prediction with (40, 40, 6) probability tensor.
        Static cells get deterministic predictions.
        """
        if not self._fitted:
            raise RuntimeError("Predictor must be fitted before predicting")

        features = compute_features(state)
        stats_arr = round_stats_to_array(round_stats)
        h, w = state.grid.shape
        probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)

        # Collect non-static cells for batch prediction
        dynamic_indices = []
        X_rows = []

        for r in range(h):
            for c in range(w):
                static_pred = _static_prediction(state.grid[r, c])
                if static_pred is not None:
                    probs[r, c] = static_pred
                else:
                    dynamic_indices.append((r, c))
                    row = _build_row(features[r, c], stats_arr)
                    X_rows.append(row)

        if X_rows:
            X = np.array(X_rows, dtype=np.float32)
            preds = self.model.predict(X)  # (N, 6)

            for (r, c), pred in zip(dynamic_indices, preds):
                probs[r, c] = pred

        # Floor and renormalize
        probs = _floor_and_normalize(probs, self.prob_floor)
        return Prediction(probs=probs)

    def save(self, path: str) -> None:
        self.model.save_model(path)

    def load(self, path: str) -> None:
        self.model.load_model(path)
        self._fitted = True


def _is_static_cell(terrain_code: int, ground_truth: np.ndarray) -> bool:
    """Check if a cell is trivially predictable (ocean, mountain, or pure forest)."""
    gt_max = ground_truth.max()
    return gt_max > 0.99


def _static_prediction(terrain_code: int) -> np.ndarray | None:
    """Return deterministic prediction for static terrain, or None."""
    from .types import OCEAN, MOUNTAIN, FOREST
    if terrain_code == OCEAN:
        pred = np.zeros(NUM_CLASSES, dtype=np.float32)
        pred[CLASS_EMPTY] = 1.0
        return pred
    if terrain_code == MOUNTAIN:
        pred = np.zeros(NUM_CLASSES, dtype=np.float32)
        pred[CLASS_MOUNTAIN] = 1.0
        return pred
    return None


def _floor_and_normalize(probs: np.ndarray, floor: float = PROB_FLOOR) -> np.ndarray:
    """Floor all probabilities and renormalize."""
    probs = np.maximum(probs, floor)
    sums = probs.sum(axis=-1, keepdims=True)
    probs = probs / sums
    return probs
