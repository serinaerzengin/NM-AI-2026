#!/bin/bash
set -euo pipefail

# System deps
apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    build-essential git wget

# Install CUDA 12.8 toolkit (needed to compile mamba extensions matching torch)
wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
dpkg -i cuda-keyring_1.1-1_all.deb
apt-get update
apt-get install -y cuda-toolkit-12-8
export CUDA_HOME=/usr/local/cuda-12.8
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

# Create venv
python3.11 -m venv ~/mamba-det
source ~/mamba-det/bin/activate

# PyTorch + torchvision for CUDA 12.8
pip install --upgrade pip
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128

# Mamba deps (must come after torch — they compile against it)
pip install packaging setuptools wheel ninja
export CUDA_HOME=/usr/local/cuda-12.8
export CUDA_PATH=$CUDA_HOME
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
export TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
pip install git+https://github.com/Dao-AILab/causal-conv1d.git@v1.5.0.post8 --no-build-isolation
pip install git+https://github.com/state-spaces/mamba.git@v2.2.4 --no-build-isolation

# MambaVision + timm
pip install git+https://github.com/NVlabs/MambaVision.git timm==1.0.14

# Remaining deps
pip install opencv-python-headless==4.10.0.84 \
            albumentations==1.4.22 \
            torchmetrics==1.6.1 \
            numpy==1.26.4 \
            Pillow==11.1.0 \
            tqdm==4.67.1

echo "Done. Activate with: source ~/mamba-det/bin/activate"
