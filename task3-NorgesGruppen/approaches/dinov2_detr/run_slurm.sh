#!/bin/bash

#SBATCH --reservation=workshop
#SBATCH --nodes=1             # 1 compute nodes
#SBATCH --cpus-per-task=16     # 2 CPU cores
#SBATCH --mem=256G              # 384 gigabytes memory
#SBATCH --output=out_18.txt    # Log file
#SBATCH --constraint=gpu80g
#SBATCH --gres=gpu:1

module load Python/3.11.5-GCCcore-13.2.0 
python -m venv ./norgesgruppen_venv
source ./norgesgruppen_venv/bin/activate

pip install torch torchvision transformers>=4.56.0 albumentations pillow==11.3.0 torchmetrics tqdm

python "./dinov3_coco_detection_notebook.py"
