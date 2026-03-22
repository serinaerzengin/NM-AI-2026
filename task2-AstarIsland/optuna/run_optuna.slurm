#!/bin/sh
#SBATCH --account=share-ie-idi
#SBATCH --job-name="astar-optuna"
#SBATCH --time=02:00:00
#SBATCH --partition=CPUQ
#SBATCH --mem=16GB
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/optuna_%j.out
#SBATCH --error=logs/optuna_%j.err
#SBATCH --mail-user=ludvigho@ntnu.no
#SBATCH --mail-type=ALL

module load Python/3.11.5-GCCcore-13.2.0

if [ ! -d "./astar_venv" ]; then
    python -m venv ./astar_venv
fi
source ./astar_venv/bin/activate

pip install numpy scipy xgboost scikit-learn optuna python-dotenv requests

mkdir -p logs

python optuna_search.py --n-trials 200 --storage sqlite:///optuna.db
