#!/bin/sh
#SBATCH --account=share-ie-idi
#SBATCH --job-name="rtdetr-ships"
#SBATCH --time=23:29:00
#SBATCH --partition=GPUQ
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=80GB
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32
#SBATCH --reservation=workshop
#SBATCH --output=logs/train_%j.out
#SBATCH --error=logs/train_%j.err
#SBATCH --mail-user=ludvigho@ntnu.no
#SBATCH --mail-type=ALL

module load Python/3.11.5-GCCcore-13.2.0

if [ ! -d "./norgesgruppen_venv" ]; then
    python -m venv ./norgesgruppen_venv
fi
source ./norgesgruppen_venv/bin/activate

pip install torch torchvision "transformers>=4.56.0" albumentations "pillow==11.3.0" torchmetrics tqdm pycocotools

python "./dinov3_coco_detection_notebook.py"
