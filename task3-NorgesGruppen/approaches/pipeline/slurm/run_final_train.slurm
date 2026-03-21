#!/bin/bash
#SBATCH --job-name=final_train
#SBATCH --account=ie-idi
#SBATCH --partition=GPUQ
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=80G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --output=logs/final_train_%j.out
#SBATCH --error=logs/final_train_%j.err

set -e

# --- Configure this ---
REPO_DIR="${HOME}/NM-AI-2026"
# ----------------------

echo "=== Final Training ==="
echo "Node: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
date

cd "${REPO_DIR}"
source .venv/bin/activate

cd task3-NorgesGruppen/approaches/pipeline

# Phase 4a: Train final model
python final_train.py --epochs 300 --patience 50

# Phase 4b: Export and generate optimized run.py
python export_and_submit.py --tune-conf --imgsz 1280

echo "=== Final training done ==="
date

echo ""
echo "Next steps:"
echo "  1. Check model size: ls -la ../../models/best.pt"
echo "  2. Test locally: python ../../run.py --input ../../data/raw/train/images --output /tmp/preds.json"
echo "  3. Submit: python ../../api.py go"
