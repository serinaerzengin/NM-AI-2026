"""Export MambaVision detector checkpoint (FP32 + FP16).

Mamba's selective_scan_cuda kernel cannot be exported to ONNX or TorchScript.
This script saves clean inference-ready checkpoints in FP32 and FP16.
"""

import argparse
import torch
torch.serialization.add_safe_globals([argparse.Namespace])

import mambavision  # noqa: F401
from pathlib import Path
from mambatest2 import MambaVisionDetector, FPN_CHANNELS


def export(checkpoint_path: str, img_size: int = 1120):
    device = torch.device("cuda")

    ckpt = torch.load(checkpoint_path, map_location=device)
    config = ckpt["config"]

    model = MambaVisionDetector(
        num_classes=config["num_classes"],
        model_name=config["model_name"],
        freeze_stages=0,
        fpn_ch=config.get("fpn_ch", FPN_CHANNELS),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"], strict=False)
    model.eval()

    base = Path(checkpoint_path).with_suffix("")
    meta = {
        "config": config,
        "id2label": ckpt.get("id2label"),
        "label_to_cat_id": ckpt.get("label_to_cat_id"),
        "img_size": img_size,
        "best_map50": ckpt.get("best_map50"),
        "epoch": ckpt.get("epoch"),
    }

    # FP32
    fp32_path = str(base) + ".inference.pt"
    torch.save({"model_state_dict": model.state_dict(), **meta}, fp32_path)
    fp32_size = Path(fp32_path).stat().st_size / 1e6
    print(f"FP32: {fp32_path} ({fp32_size:.1f} MB)")

    # FP16
    model_fp16 = model.half()
    fp16_state = {k: v.half() if v.is_floating_point() else v for k, v in model_fp16.state_dict().items()}
    fp16_path = str(base) + ".inference.fp16.pt"
    torch.save({"model_state_dict": fp16_state, "fp16": True, **meta}, fp16_path)
    fp16_size = Path(fp16_path).stat().st_size / 1e6
    print(f"FP16: {fp16_path} ({fp16_size:.1f} MB, {fp16_size/fp32_size*100:.0f}% of FP32)")

    # Verify both produce output
    dummy = torch.randn(1, 3, img_size, img_size, device=device)
    with torch.no_grad():
        out_fp32 = model.float()(dummy)
        out_fp16 = model.half()(dummy.half())
    print(f"\nVerification — FP32 output scales: {len(out_fp32[0])}, FP16 output scales: {len(out_fp16[0])}")
    for i, (a, b) in enumerate(zip(out_fp32[0], out_fp16[0])):
        diff = (a.float() - b.float()).abs().max().item()
        print(f"  scale {i} cls max FP32/FP16 diff: {diff:.4f}")

    print(f"\nTo load FP16 for inference:")
    print(f"  ckpt = torch.load('{fp16_path}')")
    print(f"  model = MambaVisionDetector(...).half().to(device)")
    print(f"  model.load_state_dict(ckpt['model_state_dict'])")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", help="Path to best.pt")
    parser.add_argument("--img-size", type=int, default=1120)
    args = parser.parse_args()

    export(args.checkpoint, args.img_size)
