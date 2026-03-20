"""Lightweight U-Net with FiLM conditioning for grid-to-distribution prediction.

Architecture:
    Input:  (B, C_in, 40, 40) feature maps from compute_features()
    Cond:   (B, 7) round stats vector — injected via FiLM at each decoder block
    Output: (B, 6, 40, 40) per-cell probability distributions (softmax)

Encoder:  3 blocks  40→20→10→5
Decoder:  3 blocks  5→10→20→40  with skip connections + FiLM
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock(nn.Module):
    """Two conv layers with BatchNorm and GELU activation."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.gelu(self.bn1(self.conv1(x)))
        x = F.gelu(self.bn2(self.conv2(x)))
        return x


class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation: gamma * x + beta, conditioned on a vector."""

    def __init__(self, cond_dim: int, n_channels: int):
        super().__init__()
        self.fc = nn.Linear(cond_dim, n_channels * 2)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        params = self.fc(cond)  # (B, 2*C)
        gamma, beta = params.chunk(2, dim=-1)  # each (B, C)
        gamma = gamma[:, :, None, None]  # (B, C, 1, 1)
        beta = beta[:, :, None, None]
        return gamma * x + beta


class EncoderBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = ConvBlock(in_ch, out_ch)
        self.pool = nn.MaxPool2d(2)

    def forward(self, x: torch.Tensor):
        skip = self.conv(x)
        down = self.pool(skip)
        return down, skip


class DecoderBlock(nn.Module):
    def __init__(self, in_ch: int, skip_ch: int, out_ch: int, cond_dim: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_ch, in_ch, 2, stride=2)
        self.conv = ConvBlock(in_ch + skip_ch, out_ch)
        self.film = FiLMLayer(cond_dim, out_ch)

    def forward(self, x: torch.Tensor, skip: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        x = torch.cat([x, skip], dim=1)
        x = self.conv(x)
        x = self.film(x, cond)
        return x


class AstarUNet(nn.Module):
    """U-Net for Astar Island: spatial features in, probability distributions out.

    Args:
        in_channels:  Number of input feature channels (default 22 from compute_features).
        out_channels: Number of prediction classes (default 6).
        cond_dim:     Dimension of conditioning vector (default 7 from round_stats).
        base_ch:      Base channel width (doubled at each encoder level).
    """

    def __init__(
        self,
        in_channels: int = 22,
        out_channels: int = 6,
        cond_dim: int = 7,
        base_ch: int = 32,
    ):
        super().__init__()
        self.out_channels = out_channels
        c1, c2, c3 = base_ch, base_ch * 2, base_ch * 4

        # Encoder
        self.enc1 = EncoderBlock(in_channels, c1)   # 40→20, skip=c1
        self.enc2 = EncoderBlock(c1, c2)             # 20→10, skip=c2
        self.enc3 = EncoderBlock(c2, c3)             # 10→5,  skip=c3

        # Bottleneck
        self.bottleneck = ConvBlock(c3, c3)
        self.bottleneck_film = FiLMLayer(cond_dim, c3)

        # Decoder
        self.dec3 = DecoderBlock(c3, c3, c2, cond_dim)  # 5→10
        self.dec2 = DecoderBlock(c2, c2, c1, cond_dim)  # 10→20
        self.dec1 = DecoderBlock(c1, c1, c1, cond_dim)  # 20→40

        # Output head
        self.head = nn.Conv2d(c1, out_channels, 1)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x:    (B, in_channels, H, W) spatial feature tensor.
            cond: (B, cond_dim) round statistics vector.

        Returns:
            (B, out_channels, H, W) log-softmax probabilities.
        """
        # Encode
        x, skip1 = self.enc1(x)   # x: (B,c1,20,20), skip1: (B,c1,40,40)
        x, skip2 = self.enc2(x)   # x: (B,c2,10,10), skip2: (B,c2,20,20)
        x, skip3 = self.enc3(x)   # x: (B,c3,5,5),   skip3: (B,c3,10,10)

        # Bottleneck + FiLM
        x = self.bottleneck(x)
        x = self.bottleneck_film(x, cond)

        # Decode
        x = self.dec3(x, skip3, cond)  # (B,c2,10,10)
        x = self.dec2(x, skip2, cond)  # (B,c1,20,20)
        x = self.dec1(x, skip1, cond)  # (B,c1,40,40)

        # Output
        logits = self.head(x)  # (B, 6, H, W)
        return F.log_softmax(logits, dim=1)
