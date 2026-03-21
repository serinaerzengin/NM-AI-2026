#!/bin/bash
#SBATCH --job-name=hp_search
#SBATCH --account=ie-idi
#SBATCH --partition=GPUQ
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=80G
#SBATCH --cpus-per-task=8
#SBATCH --time=24:00:00
#SBATCH --array=0-7
#SBATCH --output=logs/hp_search_%A_%a.out
#SBATCH --error=logs/hp_search_%A_%a.err

set -e

# --- Configure this ---
REPO_DIR="${HOME}/NM-AI-2026"
# ----------------------

echo "=== HP Search Worker ${SLURM_ARRAY_TASK_ID} ==="
echo "Node: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
date

cd "${REPO_DIR}"
source .venv/bin/activate

cd task3-NorgesGruppen/approaches/pipeline
python hyperparam_search.py \
    --study-name hp_search \
    --n-trials 10 \
    --db-path ../../results/optuna_hp_study.db

echo "=== Worker ${SLURM_ARRAY_TASK_ID} done ==="
date
