#!/bin/bash
#SBATCH --job-name=model_cmp
#SBATCH --account=ie-idi
#SBATCH --partition=GPUQ
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=80G
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --array=0-3
#SBATCH --output=logs/model_cmp_%A_%a.out
#SBATCH --error=logs/model_cmp_%A_%a.err

set -e

# --- Configure this ---
REPO_DIR="${HOME}/NM-AI-2026"
# ----------------------

echo "=== Model Comparison Worker ${SLURM_ARRAY_TASK_ID} ==="
echo "Node: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
date

cd "${REPO_DIR}"
source .venv/bin/activate

cd task3-NorgesGruppen/approaches/pipeline
python model_comparison.py --model-idx ${SLURM_ARRAY_TASK_ID}

echo "=== Worker ${SLURM_ARRAY_TASK_ID} done ==="
date
