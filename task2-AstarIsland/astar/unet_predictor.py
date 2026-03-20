"""U-Net predictor wrapper — same interface as predictor.py for easy integration.

Usage:
    predictor = UNetPredictor()
    predictor.fit(states, ground_truths, round_stats, epochs=80)
    prediction = predictor.predict(state, round_stats)
"""

import numpy as np
import torch
import torch.nn as nn

from .types import MapState, Prediction, RoundStats, NUM_CLASSES, OCEAN, MOUNTAIN
from .features import compute_features, NUM_FEATURES
from .calibration import round_stats_to_array
from .unet_model import AstarUNet

PROB_FLOOR = 0.0005


class UNetPredictor:
    """U-Net predictor: spatial features + round stats → 6-class distribution per cell."""

    def __init__(self, base_ch: int = 32, device: str | None = None):
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model = AstarUNet(
            in_channels=NUM_FEATURES,
            out_channels=NUM_CLASSES,
            cond_dim=7,
            base_ch=base_ch,
        ).to(self.device)
        self._fitted = False

    def fit(
        self,
        states: list[MapState],
        ground_truths: list[np.ndarray],
        round_stats: list[RoundStats],
        epochs: int = 80,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        augment: bool = True,
        val_fraction: float = 0.0,
        verbose: bool = True,
    ) -> dict:
        """Train on historical data.

        Args:
            states: Initial map states.
            ground_truths: (40, 40, 6) ground truth tensors.
            round_stats: One RoundStats per sample (aligned with states/ground_truths).
            epochs: Training epochs.
            lr: Learning rate.
            weight_decay: L2 regularization.
            augment: Apply 8-fold rotation/flip augmentation.
            val_fraction: Fraction of data for validation (0 = use all for training).
            verbose: Print progress.

        Returns:
            Dict with training history (loss per epoch).
        """
        # Build dataset tensors
        X_list, cond_list, y_list, weight_list = [], [], [], []
        for state, gt, stats in zip(states, ground_truths, round_stats):
            features = compute_features(state)  # (40, 40, 22)
            stats_arr = round_stats_to_array(stats)  # (7,)

            # Transpose features to (C, H, W) for conv input
            x = features.transpose(2, 0, 1)  # (22, 40, 40)
            # Ground truth as (6, H, W)
            y = gt.transpose(2, 0, 1)  # (6, 40, 40)

            # Entropy weight mask: (H, W)
            eps = 1e-12
            entropy = -np.sum(gt * np.log(gt + eps), axis=-1)  # (40, 40)
            weight = entropy + 0.1  # floor so static cells still contribute slightly

            # Static cell mask: zero out weight for ocean/mountain
            static_mask = _build_static_mask(state)  # (40, 40) bool, True = static
            weight[static_mask] = 0.0

            X_list.append(x)
            cond_list.append(stats_arr)
            y_list.append(y)
            weight_list.append(weight)

        X = torch.tensor(np.array(X_list), dtype=torch.float32)
        cond = torch.tensor(np.array(cond_list), dtype=torch.float32)
        Y = torch.tensor(np.array(y_list), dtype=torch.float32)
        W = torch.tensor(np.array(weight_list), dtype=torch.float32)

        # Optional train/val split
        n = len(X)
        if val_fraction > 0 and n >= 4:
            n_val = max(1, int(n * val_fraction))
            perm = torch.randperm(n)
            val_idx, train_idx = perm[:n_val], perm[n_val:]
            X_val, cond_val, Y_val, W_val = (
                X[val_idx], cond[val_idx], Y[val_idx], W[val_idx],
            )
            X, cond, Y, W = X[train_idx], cond[train_idx], Y[train_idx], W[train_idx]
        else:
            X_val = None

        # Apply augmentation (expand dataset 8x with rotations + flips)
        if augment:
            X, cond, Y, W = _augment_batch(X, cond, Y, W)

        # Normalize conditioning features
        self._cond_mean = cond.mean(dim=0)
        self._cond_std = cond.std(dim=0).clamp(min=1e-6)
        cond = (cond - self._cond_mean) / self._cond_std

        # Normalize input features (per-channel)
        self._feat_mean = X.mean(dim=(0, 2, 3), keepdim=True)
        self._feat_std = X.std(dim=(0, 2, 3), keepdim=True).clamp(min=1e-6)
        X = (X - self._feat_mean) / self._feat_std

        X, cond, Y, W = X.to(self.device), cond.to(self.device), Y.to(self.device), W.to(self.device)

        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=lr, weight_decay=weight_decay
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        history = {"train_loss": [], "val_loss": []}
        n_train = len(X)

        self.model.train()
        for epoch in range(epochs):
            # Shuffle
            perm = torch.randperm(n_train, device=self.device)
            X_shuf, cond_shuf = X[perm], cond[perm]
            Y_shuf, W_shuf = Y[perm], W[perm]

            # Mini-batch training
            batch_size = min(32, n_train)
            epoch_loss = 0.0
            n_batches = 0
            for i in range(0, n_train, batch_size):
                xb = X_shuf[i:i + batch_size]
                cb = cond_shuf[i:i + batch_size]
                yb = Y_shuf[i:i + batch_size]
                wb = W_shuf[i:i + batch_size]

                log_probs = self.model(xb, cb)  # (B, 6, H, W)
                loss = _weighted_kl_loss(log_probs, yb, wb)

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            scheduler.step()
            avg_loss = epoch_loss / n_batches
            history["train_loss"].append(avg_loss)

            # Validation
            if X_val is not None:
                val_loss = self._eval_loss(X_val, cond_val, Y_val, W_val)
                history["val_loss"].append(val_loss)

            if verbose and (epoch + 1) % 10 == 0:
                msg = f"  Epoch {epoch + 1:3d}/{epochs}  train_loss={avg_loss:.4f}"
                if X_val is not None:
                    msg += f"  val_loss={history['val_loss'][-1]:.4f}"
                print(msg)

        self._fitted = True
        return history

    def predict(self, state: MapState, round_stats: RoundStats) -> Prediction:
        """Predict distributions for all cells in a map."""
        if not self._fitted:
            raise RuntimeError("UNetPredictor must be fitted before predicting")

        features = compute_features(state)  # (40, 40, 22)
        stats_arr = round_stats_to_array(round_stats)  # (7,)

        x = torch.tensor(
            features.transpose(2, 0, 1)[None], dtype=torch.float32
        )  # (1, 22, 40, 40)
        c = torch.tensor(stats_arr[None], dtype=torch.float32)  # (1, 7)

        # Apply same normalization as training
        x = (x - self._feat_mean.cpu()) / self._feat_std.cpu()
        c = (c - self._cond_mean) / self._cond_std

        x, c = x.to(self.device), c.to(self.device)

        self.model.eval()
        with torch.no_grad():
            log_probs = self.model(x, c)  # (1, 6, H, W)
            probs = torch.exp(log_probs).cpu().numpy()[0]  # (6, H, W)

        # Transpose to (H, W, 6)
        probs = probs.transpose(1, 2, 0)  # (40, 40, 6)

        # Override static cells
        h, w = state.grid.shape
        for r in range(h):
            for c in range(w):
                sp = _static_prediction(state.grid[r, c])
                if sp is not None:
                    probs[r, c] = sp

        # Floor and normalize
        probs = np.maximum(probs, PROB_FLOOR)
        probs = probs / probs.sum(axis=-1, keepdims=True)
        return Prediction(probs=probs)

    def predict_batch_raw(self, X: np.ndarray, cond: np.ndarray) -> np.ndarray:
        """Predict raw probabilities for a batch (for ensemble use).

        Args:
            X: (B, 22, 40, 40) feature tensors.
            cond: (B, 7) round stats.

        Returns:
            (B, 6, 40, 40) probability arrays.
        """
        x = torch.tensor(X, dtype=torch.float32)
        c = torch.tensor(cond, dtype=torch.float32)
        x = (x - self._feat_mean.cpu()) / self._feat_std.cpu()
        c = (c - self._cond_mean) / self._cond_std
        x, c = x.to(self.device), c.to(self.device)

        self.model.eval()
        with torch.no_grad():
            log_probs = self.model(x, c)
            return torch.exp(log_probs).cpu().numpy()

    def save(self, path: str) -> None:
        torch.save({
            "model_state": self.model.state_dict(),
            "feat_mean": self._feat_mean,
            "feat_std": self._feat_std,
            "cond_mean": self._cond_mean,
            "cond_std": self._cond_std,
        }, path)

    def load(self, path: str) -> None:
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(ckpt["model_state"])
        self._feat_mean = ckpt["feat_mean"]
        self._feat_std = ckpt["feat_std"]
        self._cond_mean = ckpt["cond_mean"]
        self._cond_std = ckpt["cond_std"]
        self._fitted = True

    @torch.no_grad()
    def _eval_loss(self, X_val, cond_val, Y_val, W_val) -> float:
        X_v = (X_val.to(self.device) - self._feat_mean.to(self.device)) / self._feat_std.to(self.device)
        c_v = (cond_val.to(self.device) - self._cond_mean.to(self.device)) / self._cond_std.to(self.device)
        Y_v = Y_val.to(self.device)
        W_v = W_val.to(self.device)
        self.model.eval()
        log_probs = self.model(X_v, c_v)
        loss = _weighted_kl_loss(log_probs, Y_v, W_v)
        self.model.train()
        return loss.item()


# ── Helpers ──────────────────────────────────────────────────────────────


def _build_static_mask(state: MapState) -> np.ndarray:
    """Boolean mask: True for cells that are always static (ocean/mountain)."""
    grid = state.grid
    return (grid == OCEAN) | (grid == MOUNTAIN)


def _static_prediction(terrain_code: int) -> np.ndarray | None:
    if terrain_code == OCEAN:
        pred = np.zeros(NUM_CLASSES, dtype=np.float32)
        pred[0] = 1.0
        return pred
    if terrain_code == MOUNTAIN:
        pred = np.zeros(NUM_CLASSES, dtype=np.float32)
        pred[5] = 1.0
        return pred
    return None


def _weighted_kl_loss(
    log_pred: torch.Tensor,
    target: torch.Tensor,
    weight: torch.Tensor,
) -> torch.Tensor:
    """Entropy-weighted KL divergence loss matching the competition metric.

    Args:
        log_pred: (B, 6, H, W) log probabilities from model.
        target:   (B, 6, H, W) ground truth distributions.
        weight:   (B, H, W) per-cell entropy weights.
    """
    eps = 1e-12
    # KL(target || pred) = sum_c target_c * (log(target_c) - log(pred_c))
    kl_per_cell = (target * (torch.log(target + eps) - log_pred)).sum(dim=1)  # (B, H, W)

    # Weighted mean
    total_weight = weight.sum() + eps
    loss = (weight * kl_per_cell).sum() / total_weight
    return loss


def _augment_batch(
    X: torch.Tensor,
    cond: torch.Tensor,
    Y: torch.Tensor,
    W: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Apply 8-fold augmentation: 4 rotations × 2 flips.

    Args:
        X: (N, C, H, W)
        cond: (N, D)
        Y: (N, 6, H, W)
        W: (N, H, W)
    """
    X_aug = [X]
    cond_aug = [cond]
    Y_aug = [Y]
    W_aug = [W]

    for k in range(1, 4):  # 90°, 180°, 270° rotations
        X_aug.append(torch.rot90(X, k, [2, 3]))
        cond_aug.append(cond)
        Y_aug.append(torch.rot90(Y, k, [2, 3]))
        W_aug.append(torch.rot90(W, k, [1, 2]))

    # Horizontal flip of each rotation
    for i in range(4):
        X_aug.append(torch.flip(X_aug[i], [3]))
        cond_aug.append(cond)
        Y_aug.append(torch.flip(Y_aug[i], [3]))
        W_aug.append(torch.flip(W_aug[i], [2]))

    return (
        torch.cat(X_aug, dim=0),
        torch.cat(cond_aug, dim=0),
        torch.cat(Y_aug, dim=0),
        torch.cat(W_aug, dim=0),
    )
