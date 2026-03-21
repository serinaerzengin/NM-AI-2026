#!/bin/sh
#SBATCH --account=share-ie-idi
#SBATCH --job-name="yolov8-ng"
#SBATCH --time=12:00:00
#SBATCH --partition=GPUQ
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=64GB
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --reservation=workshop
#SBATCH --output=logs/yolo_%j.out
#SBATCH --error=logs/yolo_%j.err

module load Python/3.11.5-GCCcore-13.2.0

if [ ! -d "./norgesgruppen_venv" ]; then
    python -m venv ./norgesgruppen_venv
fi
source ./norgesgruppen_venv/bin/activate

pip install ultralytics==8.1.0 torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124

mkdir -p logs
python "./train.py"
