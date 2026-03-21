"""Phase 1a: Create stratified K-fold splits.

Builds a binary image×class matrix and uses MultilabelStratifiedKFold
to ensure rare classes appear in every fold's validation set.
Falls back to greedy assignment if iterstrat is unavailable.

Usage:
    python kfold_split.py [--n-splits 5] [--output data/splits/kfold_5.json]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from utils import SPLITS_DIR, load_annotations


def build_class_matrix(coco: dict) -> tuple[list[int], np.ndarray]:
    """Build binary (n_images × n_classes) matrix."""
    image_ids = sorted([img["id"] for img in coco["images"]])
    id_to_idx = {img_id: i for i, img_id in enumerate(image_ids)}
    n_classes = len(coco["categories"])

    matrix = np.zeros((len(image_ids), n_classes), dtype=np.int8)
    for ann in coco["annotations"]:
        idx = id_to_idx[ann["image_id"]]
        matrix[idx, ann["category_id"]] = 1

    return image_ids, matrix


def stratified_kfold(image_ids: list[int], matrix: np.ndarray, n_splits: int = 5,
                     seed: int = 42) -> dict:
    """Create multilabel-stratified K-fold splits."""
    try:
        from iterstrat.ml_stratifiers import MultilabelStratifiedKFold
        skf = MultilabelStratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        folds = {}
        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(matrix, matrix)):
            folds[f"fold_{fold_idx}"] = {
                "train": [image_ids[i] for i in train_idx],
                "val": [image_ids[i] for i in val_idx],
            }
        return folds
    except ImportError:
        print("iterstrat not available, using greedy stratified fallback")
        return greedy_stratified_kfold(image_ids, matrix, n_splits, seed)


def greedy_stratified_kfold(image_ids: list[int], matrix: np.ndarray,
                            n_splits: int = 5, seed: int = 42) -> dict:
    """Greedy fallback: assign images to folds trying to balance class counts."""
    rng = np.random.RandomState(seed)
    n_images = len(image_ids)

    # Shuffle image order
    indices = np.arange(n_images)
    rng.shuffle(indices)

    # Track per-fold class counts
    fold_counts = np.zeros((n_splits, matrix.shape[1]), dtype=np.int32)
    assignments = np.zeros(n_images, dtype=np.int32)

    for idx in indices:
        row = matrix[idx]
        # Assign to the fold with the lowest total count for classes in this image
        class_mask = row > 0
        if class_mask.any():
            fold_scores = fold_counts[:, class_mask].sum(axis=1)
        else:
            fold_scores = fold_counts.sum(axis=1)
        # Break ties by total size
        fold_scores = fold_scores.astype(float) + fold_counts.sum(axis=1) * 0.001
        best_fold = int(np.argmin(fold_scores))
        assignments[idx] = best_fold
        fold_counts[best_fold] += row

    folds = {}
    for fold_idx in range(n_splits):
        val_mask = assignments == fold_idx
        train_mask = ~val_mask
        folds[f"fold_{fold_idx}"] = {
            "train": [image_ids[i] for i in range(n_images) if train_mask[i]],
            "val": [image_ids[i] for i in range(n_images) if val_mask[i]],
        }

    return folds


def print_split_stats(folds: dict, matrix: np.ndarray, image_ids: list[int]):
    """Print statistics about the splits."""
    id_to_idx = {img_id: i for i, img_id in enumerate(image_ids)}

    for fold_name, split in folds.items():
        val_ids = split["val"]
        val_idx = [id_to_idx[i] for i in val_ids]
        val_matrix = matrix[val_idx]

        classes_present = (val_matrix.sum(axis=0) > 0).sum()
        total_classes = matrix.shape[1]

        print(f"  {fold_name}: {len(split['train'])} train, {len(val_ids)} val, "
              f"{classes_present}/{total_classes} classes in val")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    coco = load_annotations()
    print(f"Dataset: {len(coco['images'])} images, {len(coco['categories'])} classes, "
          f"{len(coco['annotations'])} annotations")

    image_ids, matrix = build_class_matrix(coco)

    # Class distribution stats
    class_counts = matrix.sum(axis=0)
    rare_classes = (class_counts <= 3).sum()
    singleton_classes = (class_counts == 1).sum()
    print(f"Class distribution: {rare_classes} classes in ≤3 images, "
          f"{singleton_classes} singletons")

    folds = stratified_kfold(image_ids, matrix, args.n_splits, args.seed)
    print(f"\nCreated {args.n_splits}-fold splits:")
    print_split_stats(folds, matrix, image_ids)

    output_path = Path(args.output) if args.output else SPLITS_DIR / f"kfold_{args.n_splits}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(folds, f, indent=2)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
