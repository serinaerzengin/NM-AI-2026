#!/bin/bash
#SBATCH --job-name=aug_search
#SBATCH --account=ie-idi
#SBATCH --partition=GPUQ
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --time=24:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/aug_search_%A_%a.out
#SBATCH --error=logs/aug_search_%A_%a.err

set -e

# --- Configure this ---
REPO_DIR="${HOME}/NM-AI-2026"
# ----------------------

echo "=== Aug Search Worker ${SLURM_ARRAY_TASK_ID} ==="
echo "Node: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
date

cd "${REPO_DIR}"
source .venv/bin/activate

cd task3-NorgesGruppen/approaches/pipeline

# Ensure splits exist (only first worker creates, others read)
python kfold_split.py

# Run stage 1 augmentation search
python augmentation_search.py \
    --stage 1 \
    --study-name aug_search \
    --n-trials 8 \
    --db-path ../../results/optuna_aug_study.db

echo "=== Worker ${SLURM_ARRAY_TASK_ID} done ==="
date
