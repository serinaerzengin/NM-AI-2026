# mamba_vision_detector.py — optimized + high-accuracy

import argparse
import copy
import json
import math
import random
from pathlib import Path

import albumentations as A
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import mambavision  # noqa: F401 — registers mamba_vision_* models with timm
import timm
torch.serialization.add_safe_globals([argparse.Namespace])
import cv2
from albumentations.pytorch import ToTensorV2
from torch.utils.data import DataLoader, Dataset
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from torchvision.ops import batched_nms, complete_box_iou_loss
from tqdm.auto import tqdm

# ----------------------------
# config
# ----------------------------
DATA_DIR = "/home/devstar18131/task2/task2/train"
MODEL_NAME = "mamba_vision_B"
IMG_SIZE = 1120
VAL_RATIO = 0.1

BATCH_SIZE = 16
GRAD_ACCUM_STEPS = 2
NUM_WORKERS = 26
EPOCHS = 5000
LR = 2e-4
BACKBONE_LR_MULT = 0.25      # differential LR for unfrozen backbone layers
WARMUP_EPOCHS = 50             # linear warmup to avoid early NaN
WEIGHT_DECAY = 1e-2
SEED = 42
VAL_EVERY = 15
FREEZE_BACKBONE_STAGES = 0   # freeze first 2 (of 4), train last 2 + neck/heads
EMA_DECAY = 0.9               # EMA for eval model (50% after 7 epochs)
MULTI_CELL_RADIUS = 1         # assign GT to center + neighbors (3x3)
LABEL_SMOOTHING = 0.05
FPN_CHANNELS = 256            # unified FPN channel dim

SAVE_DIR = "./mamba_vision_detector"


# ----------------------------
# utils
# ----------------------------
def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def xywh_to_xyxy_norm(boxes_xywh, w, h):
    if len(boxes_xywh) == 0:
        return []
    arr = np.array(boxes_xywh)
    x1 = arr[:, 0] / w
    y1 = arr[:, 1] / h
    x2 = (arr[:, 0] + arr[:, 2]) / w
    y2 = (arr[:, 1] + arr[:, 3]) / h
    return np.stack([x1, y1, x2, y2], axis=1).tolist()


def make_dirs(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def _unwrap_compiled(model):
    return model._orig_mod if hasattr(model, "_orig_mod") else model


def _to_scalar(val):
    return val.detach().item() if isinstance(val, torch.Tensor) else val


# ----------------------------
# EMA
# ----------------------------
class ModelEMA:
    def __init__(self, model, decay=0.9998):
        self.ema = copy.deepcopy(model)
        self.ema.eval()
        self.decay = decay
        for p in self.ema.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model, step=None, warmup_steps=100):
        # Ramp decay from 0 to target over warmup_steps so EMA tracks fast early on
        if step is not None and step < warmup_steps:
            decay = self.decay * (step / warmup_steps)
        else:
            decay = self.decay
        for ema_p, model_p in zip(self.ema.parameters(), model.parameters()):
            ema_p.lerp_(model_p.data, 1.0 - decay)
        for ema_b, model_b in zip(self.ema.buffers(), model.buffers()):
            ema_b.copy_(model_b)


# ----------------------------
# Mosaic augmentation
# ----------------------------
class MosaicWrapper(Dataset):
    """Wraps a CocoDetDataset and applies 4-image mosaic with probability p."""

    def __init__(self, dataset, p=0.5):
        self.ds = dataset
        self.p = p

    def __len__(self):
        return len(self.ds)

    def __getitem__(self, idx):
        if random.random() > self.p:
            return self.ds[idx]

        indices = [idx] + random.choices(range(len(self.ds)), k=3)
        imgs, tgts = [], []
        for i in indices:
            img, tgt = self.ds[i]
            imgs.append(img)
            tgts.append(tgt)

        C, H, W = imgs[0].shape
        hH, hW = H // 2, W // 2

        mosaic = torch.zeros(C, H, W, dtype=imgs[0].dtype)
        all_boxes = []
        all_labels = []

        placements = [(0, 0, hH, hW), (0, hW, hH, W), (hH, 0, H, hW), (hH, hW, H, W)]

        for (r1, c1, r2, c2), img, tgt in zip(placements, imgs, tgts):
            qh, qw = r2 - r1, c2 - c1

            # Random crop 1/8 to 1/3 of source image area, then resize to quadrant
            area_frac = random.uniform(1/8, 1/3)
            crop_scale = area_frac ** 0.5
            crop_h = max(1, int(H * crop_scale))
            crop_w = max(1, int(W * crop_scale))
            top = random.randint(0, H - crop_h)
            left = random.randint(0, W - crop_w)
            cropped = img[:, top:top + crop_h, left:left + crop_w]

            resized = F.interpolate(
                cropped.unsqueeze(0).float(), size=(qh, qw), mode="bilinear", align_corners=False
            ).squeeze(0).to(img.dtype)
            mosaic[:, r1:r2, c1:c2] = resized

            boxes = tgt["boxes"]
            labels = tgt["labels"]
            if boxes.numel() == 0:
                continue

            # Clip boxes to the crop region (in normalized coords)
            crop_x1, crop_y1 = left / W, top / H
            crop_x2, crop_y2 = (left + crop_w) / W, (top + crop_h) / H

            clipped = boxes.clone()
            clipped[:, 0] = clipped[:, 0].clamp(crop_x1, crop_x2)
            clipped[:, 1] = clipped[:, 1].clamp(crop_y1, crop_y2)
            clipped[:, 2] = clipped[:, 2].clamp(crop_x1, crop_x2)
            clipped[:, 3] = clipped[:, 3].clamp(crop_y1, crop_y2)

            # Remap to crop-local [0,1] then to mosaic coords
            local_x1 = (clipped[:, 0] - crop_x1) / (crop_x2 - crop_x1)
            local_y1 = (clipped[:, 1] - crop_y1) / (crop_y2 - crop_y1)
            local_x2 = (clipped[:, 2] - crop_x1) / (crop_x2 - crop_x1)
            local_y2 = (clipped[:, 3] - crop_y1) / (crop_y2 - crop_y1)

            scaled = torch.stack([
                local_x1 * (qw / W) + c1 / W,
                local_y1 * (qh / H) + r1 / H,
                local_x2 * (qw / W) + c1 / W,
                local_y2 * (qh / H) + r1 / H,
            ], dim=1)
            scaled.clamp_(0, 1)

            w = scaled[:, 2] - scaled[:, 0]
            h = scaled[:, 3] - scaled[:, 1]
            keep = (w > 0.005) & (h > 0.005)
            all_boxes.append(scaled[keep])
            all_labels.append(labels[keep])

        target = {
            "boxes": torch.cat(all_boxes) if all_boxes else torch.zeros((0, 4), dtype=torch.float32),
            "labels": torch.cat(all_labels) if all_labels else torch.zeros((0,), dtype=torch.long),
            "image_id": tgts[0]["image_id"],
        }
        return mosaic, target


# ----------------------------
# dataset
# ----------------------------
class CocoDetDataset(Dataset):
    def __init__(self, root, indices=None, augment=False, img_size=448):
        self.root = Path(root)
        self.augment = augment
        self.img_size = img_size

        with open(self.root / "annotations.json", "r", encoding="utf-8") as f:
            coco = json.load(f)

        self.images_dir = self.root / "images"
        self.images = coco["images"]
        self.categories = coco["categories"]

        self.cat_ids = sorted(c["id"] for c in self.categories)
        self.cat_id_to_label = {cid: i + 1 for i, cid in enumerate(self.cat_ids)}
        self.label_to_cat_id = {i + 1: cid for i, cid in enumerate(self.cat_ids)}

        self.id2label = {0: "background"}
        for i, cid in enumerate(self.cat_ids, start=1):
            name = next(c["name"] for c in self.categories if c["id"] == cid)
            self.id2label[i] = name

        self.label2id = {v: k for k, v in self.id2label.items()}
        self.num_classes = len(self.id2label)

        anns_by_image = {}
        for ann in coco["annotations"]:
            if ann.get("iscrowd", 0) == 0:
                anns_by_image.setdefault(ann["image_id"], []).append(ann)

        if indices is None:
            indices = list(range(len(self.images)))

        self.samples = [(self.images[i], anns_by_image.get(self.images[i]["id"], [])) for i in indices]

        # No Normalize here — done on GPU in model forward. Output uint8 tensor.
        self.train_tf = A.Compose(
            [
                A.RandomResizedCrop((img_size, img_size), scale=(0.4, 1.0)),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(),
                A.RandomRotate90(),
                A.ChannelDropout(),
                A.RandomBrightnessContrast(p=0.7),
                A.ColorJitter(brightness=(0.3, 1.7), contrast=(0.3, 1.7), saturation=(0.3, 1.7), p=0.95),
                A.GaussianBlur(),
                A.GaussNoise(p=0.8),
                A.ToGray(p=0.25),
                ToTensorV2(),
            ],
            bbox_params=A.BboxParams(
                format="coco",
                label_fields=["class_labels"],
                min_visibility=0.1,
            ),
        )

        self.val_tf = A.Compose(
            [
                A.Resize(img_size, img_size),
                ToTensorV2(),
            ],
            bbox_params=A.BboxParams(
                format="coco",
                label_fields=["class_labels"],
            ),
        )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_info, anns = self.samples[idx]
        image = cv2.imread(str(self.images_dir / img_info["file_name"]))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes_xywh = []
        labels = []

        for ann in anns:
            x, y, w, h = ann["bbox"]
            if w > 1 and h > 1:
                boxes_xywh.append([x, y, w, h])
                labels.append(self.cat_id_to_label[ann["category_id"]])

        tf = self.train_tf if self.augment else self.val_tf
        out = tf(image=image, bboxes=boxes_xywh, class_labels=labels)

        img_h, img_w = out["image"].shape[1:]
        boxes_xyxy = xywh_to_xyxy_norm(out["bboxes"], img_w, img_h)

        target = {
            "boxes": torch.tensor(boxes_xyxy, dtype=torch.float32)
            if len(boxes_xyxy) > 0
            else torch.zeros((0, 4), dtype=torch.float32),
            "labels": torch.tensor(out["class_labels"], dtype=torch.long)
            if len(out["class_labels"]) > 0
            else torch.zeros((0,), dtype=torch.long),
            "image_id": torch.tensor(img_info["id"], dtype=torch.long),
        }

        return out["image"], target


def collate_fn(batch):
    images = torch.stack([x[0] for x in batch], dim=0)
    targets = [x[1] for x in batch]
    return images, targets


class InfiniteDataLoader:
    """Wraps a DataLoader to restart seamlessly without worker respawn delay."""

    def __init__(self, loader):
        self.loader = loader
        self.iterator = iter(loader)
        self.epoch_len = len(loader)

    def __iter__(self):
        for _ in range(self.epoch_len):
            try:
                yield next(self.iterator)
            except StopIteration:
                self.iterator = iter(self.loader)
                yield next(self.iterator)

    def __len__(self):
        return self.epoch_len


class CUDAPrefetcher:
    """Prefetches batches to GPU using a ring buffer on a separate CUDA stream."""

    def __init__(self, loader, device, buffer_size=50):
        self.loader = loader
        self.device = device
        self.buffer_size = buffer_size
        self.stream = torch.cuda.Stream()

    def __iter__(self):
        self.iter = iter(self.loader)
        self.buffer = []
        # Fill the buffer
        for _ in range(self.buffer_size):
            if not self._enqueue():
                break
        return self

    def _enqueue(self):
        try:
            images, targets = next(self.iter)
        except StopIteration:
            return False
        with torch.cuda.stream(self.stream):
            images = images.to(self.device, non_blocking=True)
        self.buffer.append((images, targets))
        return True

    def __next__(self):
        if not self.buffer:
            raise StopIteration
        torch.cuda.current_stream().wait_stream(self.stream)
        images, targets = self.buffer.pop(0)
        self._enqueue()
        return images, targets

    def __len__(self):
        return len(self.loader)


# ----------------------------
# model: full FPN + multi-scale heads + centerness
# ----------------------------
CE_WEIGHT_RAW = torch.tensor([0.1, 0.4348,  0.5718,  3.1751,  0.2498,  2.1646,  0.7006,  0.6891,  0.3685,  0.5140,  3.1751,  1.8879,  0.5792,
     0.2840,  1.7779,  0.6675,  0.3711,  3.1751,  4.3035,  1.7779,  1.2871,  1.2871,  0.1822,  1.3929,  0.3512,
     0.7953,  0.8841, 12.1722,  0.8645,  3.1751,  0.2360,  0.3180,  1.4539,  0.5198,  0.2693,  0.2467,  0.3633,
     1.6818,  0.9740,  0.1853,  0.3357,  0.4000,  2.0152,  1.1983,  1.0887,  7.2376,  0.7249,  0.3633,  0.4236,
     2.5589,  0.4098,  0.3296,  3.6403,  0.2081,  0.2744,  2.1646,  3.6403,  0.3821, 12.1722,  3.1751,  2.5589,
     7.2376,  0.2928,  0.3091,  0.3821,  0.8459,  1.0277,  0.3336,  2.5589,  0.4729, 12.1722,  1.5970,  1.0000,
     0.4387,  0.2498,  3.6403,  0.3007, 12.1722,  4.3035,  0.3821, 12.1722,  0.1978, 12.1722,  0.2247,  0.8841,
     0.3608,  0.3007,  0.1366,  0.5140,  1.5970,  0.4729,  7.2376, 12.1722,  0.1954,  1.1590, 12.1722, 12.1722,
     0.1954,  0.2379,  2.8284,  1.6818,  0.1449,  1.7779,  0.6474,  0.5946,  5.3398,  1.5970,  0.8645, 12.1722,
     0.3765,  0.1431,  1.8879,  0.4131,  3.6403,  1.5970,  5.3398, 12.1722, 12.1722,  0.3466,  2.0152,  5.3398,
     7.2376,  0.6675,  0.5509, 12.1722,  4.3035,  3.6403,  2.3425,  2.3425,  1.2871,  3.1751,  0.2913,  1.1983,
     0.1689,  3.6403,  7.2376, 12.1722,  0.9265,  0.6110,  1.6818,  0.3073, 12.1722,  0.5443,  0.5577,  0.3180,
     1.3375,  0.5084,  0.6110,  4.3035,  1.0000, 12.1722,  1.4539,  0.4925,  0.2427, 12.1722, 12.1722,  5.3398,
     5.3398,  0.4166,  0.6027,  4.3035,  0.4824,  5.3398,  0.6891,  3.1751,  0.3336,  3.6403,  2.5589, 12.1722,
     1.2408,  0.8841,  2.5589,  0.2054,  7.2376,  0.4000,  0.5718,  0.6781,  2.1646,  0.9047,  0.4874,  4.3035,
     7.2376,  0.2379,  1.7779,  3.6403,  0.8282,  1.0000,  0.3237,  0.3685,  0.2333,  0.4925,  7.2376,  0.5084,
     0.7800,  0.6474,  0.2975,  2.1646,  0.9496,  0.5718,  1.1590, 12.1722,  0.5140,  0.2928, 12.1722,  2.0152,
     0.2508,  0.2731,  1.6818,  0.1701,  0.2706,  1.4539,  1.2871, 12.1722,  0.2991,  0.5379,  0.3659,  0.6110,
     1.7779,  0.2928,  0.2498,  0.5443,  2.3425,  1.4539,  0.6110,  0.4310,  1.3929,  0.4824,  1.8879, 12.1722,
     1.0887,  1.3375, 12.1722,  0.7249,  0.2620,  0.1880, 12.1722,  0.3466,  0.2407,  0.5257,  0.9496,  0.1996,
     1.1226, 12.1722, 12.1722,  0.2306,  0.3659,  4.3035,  0.1601,  1.7779,  3.1751,  2.3425,  0.1822,  1.5970,
     4.3035,  1.2871,  7.2376, 12.1722, 12.1722,  2.8284, 12.1722,  0.4508,  0.3633,  0.2928,  1.6818, 12.1722,
     0.3444,  0.3336,  0.6027,  1.3375,  0.2508,  0.8841,  1.6818,  0.1660,  0.5198,  1.5215, 12.1722,  0.2109,
     7.2376,  1.8879,  2.1646, 12.1722,  0.1869,  1.6818,  0.3908,  0.3217,  0.2608,  7.2376,  2.3425,  1.1590,
     5.3398,  1.3929,  0.9740, 12.1722,  0.8459,  7.2376,  1.8879,  2.8284,  0.1652,  0.6675,  0.3608,  5.3398,
    12.1722,  3.1751,  2.3425,  1.3375,  0.2883,  0.3316,  0.6781,  0.1764,  1.3929,  0.5198, 12.1722,  0.8841,
     0.8841,  4.3035,  1.3929,  0.3091,  1.1590, 12.1722, 12.1722,  5.3398,  0.9496,  5.3398,  2.5589,  3.6403,
     0.9740,  0.5792,  0.7006, 12.1722,  0.7653,  0.2585,  0.3765,  2.8284,  1.8879,  0.3821,  0.6474, 12.1722,
     1.3375,  3.1751,  0.2718,  0.5868,  0.6110,  0.4729,  0.2620,  1.2871,  0.8841,  0.2109,  5.3398,  0.6197,
     1.1226,  0.1461, 12.1722,  1.0572,  1.3929,  3.6403,  7.2376,  0.1307]).pow(0.75)
CE_WEIGHT_RAW[0] = 0.1


class FPNBlock(nn.Module):
    """Single FPN lateral + smooth block."""
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.lateral = nn.Conv2d(in_ch, out_ch, 1)
        self.smooth = nn.Conv2d(out_ch, out_ch, 3, padding=1)

    def forward(self, x, top_down=None):
        lat = self.lateral(x)
        if top_down is not None:
            lat = lat + F.interpolate(top_down, size=lat.shape[2:], mode="bilinear", align_corners=False)
        return self.smooth(lat)


class DetectionHead(nn.Module):
    """Shared FCOS-style head: cls + box + centerness."""

    @staticmethod
    def _make_tower(ch, n_layers=4):
        layers = []
        for _ in range(n_layers):
            layers += [nn.Conv2d(ch, ch, 3, padding=1), nn.GroupNorm(32, ch), nn.GELU()]
        return nn.Sequential(*layers)

    def __init__(self, in_ch, num_classes):
        super().__init__()
        self.cls_tower = self._make_tower(in_ch)
        self.cls_out = nn.Conv2d(in_ch, num_classes, 1)

        self.box_tower = self._make_tower(in_ch)
        self.box_out = nn.Conv2d(in_ch, 4, 1)

        self.ctr_out = nn.Conv2d(in_ch, 1, 1)

        nn.init.constant_(self.cls_out.bias, -math.log(99))

    def forward(self, feat):
        cls_feat = self.cls_tower(feat)
        box_feat = self.box_tower(feat)

        cls_logits = self.cls_out(cls_feat)
        box_raw = self.box_out(box_feat).sigmoid()
        centerness = self.ctr_out(cls_feat)

        box_perm = box_raw.permute(0, 2, 3, 1)
        cx, cy, bw, bh = box_perm.unbind(-1)
        x1 = (cx - 0.5 * bw).clamp(0, 1)
        y1 = (cy - 0.5 * bh).clamp(0, 1)
        x2 = (cx + 0.5 * bw).clamp(0, 1)
        y2 = (cy + 0.5 * bh).clamp(0, 1)
        pred_boxes = torch.stack([x1, y1, x2, y2], dim=-1)

        return cls_logits, pred_boxes, centerness


class MambaVisionDetector(nn.Module):
    def __init__(self, num_classes, model_name="mamba_vision_L", freeze_stages=2, fpn_ch=256):
        super().__init__()
        self.backbone = timm.create_model(model_name, pretrained=True)
        self.num_classes = num_classes

        # Remove classification head (we only need features)
        self.backbone.norm = nn.Identity()
        self.backbone.avgpool = nn.Identity()
        self.backbone.head = nn.Identity()

        # Freeze patch_embed + early stages
        for param in self.backbone.patch_embed.parameters():
            param.requires_grad = False
        for i in range(min(freeze_stages, len(self.backbone.levels))):
            for param in self.backbone.levels[i].parameters():
                param.requires_grad = False

        # MambaVision-B feature channels:
        # levels 2 and 3 have same spatial size, so we use 3 FPN scales
        channels = [256, 512, 1024]

        self.fpn2 = FPNBlock(channels[2], fpn_ch)
        self.fpn1 = FPNBlock(channels[1], fpn_ch)
        self.fpn0 = FPNBlock(channels[0], fpn_ch)

        self.head = DetectionHead(fpn_ch, num_classes)

        self.register_buffer("ce_weight", CE_WEIGHT_RAW[:num_classes].clone())
        # ImageNet normalization on GPU (images arrive as uint8 0-255)
        self.register_buffer("img_mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("img_std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, images):
        # Normalize on GPU: uint8 → float32 → ImageNet norm
        images = images.float().div_(255.0).sub_(self.img_mean).div_(self.img_std)
        # Run backbone in FP32 — mamba's selective_scan_cuda produces NaN in FP16
        with torch.amp.autocast("cuda", enabled=False):
            x = self.backbone.patch_embed(images)
            feats = []
            for level in self.backbone.levels:
                x = level(x)
                feats.append(x)

        # feats: [level0 (392,H/8,W/8), level1 (784,H/16,W/16), level2 (1568,H/32,W/32), level3 (1568,H/32,W/32)]
        # Merge level 2+3 (same spatial size) by addition
        f0 = feats[0]
        f1 = feats[1]
        f2 = feats[2] + feats[3]

        # Top-down FPN
        p4 = self.fpn2(f2)
        p3 = self.fpn1(f1, top_down=p4)
        p2 = self.fpn0(f0, top_down=p3)

        fpn_feats = [p2, p3, p4]
        all_cls, all_boxes, all_ctr = [], [], []

        for feat in fpn_feats:
            cls_logits, pred_boxes, centerness = self.head(feat)
            all_cls.append(cls_logits)
            all_boxes.append(pred_boxes)
            all_ctr.append(centerness)

        return all_cls, all_boxes, all_ctr


# ----------------------------
# multi-scale + multi-cell dense target assignment
# ----------------------------
def build_dense_targets(targets, grid_h, grid_w, device, radius=1):
    B = len(targets)

    cls_t = torch.zeros((B, grid_h, grid_w), dtype=torch.long, device=device)
    box_t = torch.zeros((B, grid_h, grid_w, 4), dtype=torch.float32, device=device)
    obj_t = torch.zeros((B, grid_h, grid_w), dtype=torch.bool, device=device)
    ctr_t = torch.zeros((B, grid_h, grid_w), dtype=torch.float32, device=device)

    for b, t in enumerate(targets):
        boxes = t["boxes"].to(device, non_blocking=True)
        labels = t["labels"].to(device, non_blocking=True)

        if boxes.numel() == 0:
            continue

        cx = 0.5 * (boxes[:, 0] + boxes[:, 2])
        cy = 0.5 * (boxes[:, 1] + boxes[:, 3])
        bw = boxes[:, 2] - boxes[:, 0]
        bh = boxes[:, 3] - boxes[:, 1]

        gx_center = (cx * grid_w).long().clamp(0, grid_w - 1)
        gy_center = (cy * grid_h).long().clamp(0, grid_h - 1)

        # Compute centerness targets
        # centerness = sqrt(min(l,r)/max(l,r) * min(t,b)/max(t,b))
        l = cx - boxes[:, 0]
        r = boxes[:, 2] - cx
        t_dist = cy - boxes[:, 1]
        b_dist = boxes[:, 3] - cy
        lr = torch.min(l, r) / (torch.max(l, r) + 1e-6)
        tb = torch.min(t_dist, b_dist) / (torch.max(t_dist, b_dist) + 1e-6)
        centerness = torch.sqrt(lr * tb)

        areas = bw * bh
        order = areas.argsort(descending=False)  # smallest last wins scatter

        # Build all (dy, dx) offsets for multi-cell assignment
        offsets = [(dy, dx) for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)]
        n_off = len(offsets)
        dy_off = torch.tensor([o[0] for o in offsets], device=device)
        dx_off = torch.tensor([o[1] for o in offsets], device=device)
        dist_off = torch.tensor([max(abs(o[0]), abs(o[1])) for o in offsets], dtype=torch.float32, device=device)

        N = len(order)
        # Expand each box to all offsets: [N * n_off]
        gy_exp = gy_center[order].unsqueeze(1) + dy_off.unsqueeze(0)  # [N, n_off]
        gx_exp = gx_center[order].unsqueeze(1) + dx_off.unsqueeze(0)
        gy_flat = gy_exp.reshape(-1)
        gx_flat = gx_exp.reshape(-1)

        # Filter out-of-bounds
        valid = (gy_flat >= 0) & (gy_flat < grid_h) & (gx_flat >= 0) & (gx_flat < grid_w)
        gy_flat = gy_flat[valid]
        gx_flat = gx_flat[valid]

        # Repeat labels/boxes/centerness for each offset
        labels_exp = labels[order].unsqueeze(1).expand(-1, n_off).reshape(-1)[valid]
        boxes_exp = boxes[order].unsqueeze(1).expand(-1, n_off, 4).reshape(-1, 4)[valid]
        ctr_decay = (1.0 / (1.0 + dist_off)).unsqueeze(0).expand(N, -1).reshape(-1)[valid]
        ctr_exp = centerness[order].unsqueeze(1).expand(-1, n_off).reshape(-1)[valid] * ctr_decay

        flat = gy_flat * grid_w + gx_flat
        cls_t[b].view(-1).scatter_(0, flat, labels_exp)
        box_t[b].view(-1, 4).scatter_(0, flat.unsqueeze(1).expand(-1, 4), boxes_exp)
        obj_t[b].view(-1).scatter_(0, flat, torch.ones_like(flat, dtype=torch.bool))
        ctr_t[b].view(-1).scatter_(0, flat, ctr_exp)

    return cls_t, box_t, obj_t, ctr_t


# ----------------------------
# YOLO-style focal loss for classification
# ----------------------------
def focal_cross_entropy(logits, targets, weight=None, gamma=1.5, label_smoothing=0.05):
    """Focal modulated cross-entropy (YOLO v8 style)."""
    ce = F.cross_entropy(logits, targets, weight=weight, label_smoothing=label_smoothing, reduction="none")
    probs = logits.softmax(dim=1)
    # Gather the prob of the target class
    B = targets.shape[0]
    if targets.dim() == 1:
        pt = probs[torch.arange(B, device=targets.device), targets]
    else:
        # Spatial targets [B, H, W]
        pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
    focal_weight = (1.0 - pt).pow(gamma)
    return (focal_weight * ce).mean()


# ----------------------------
# multi-scale loss (YOLO-style: focal cls + CIoU + DFL-like L1 + centerness)
# ----------------------------
def detection_loss_multiscale(all_cls, all_boxes, all_ctr, targets, ce_weight, radius=1, label_smoothing=0.05):
    device = all_cls[0].device
    total_cls = 0.0
    total_ciou = 0.0
    total_l1 = 0.0
    total_ctr = 0.0
    n_scales = len(all_cls)

    for cls_logits, pred_boxes, centerness in zip(all_cls, all_boxes, all_ctr):
        _, _, H, W = cls_logits.shape

        cls_t, box_t, obj_t, ctr_t = build_dense_targets(targets, H, W, device, radius=radius)

        # Focal cross-entropy (YOLO v8 style — focuses on hard examples)
        total_cls += focal_cross_entropy(cls_logits, cls_t, weight=ce_weight, label_smoothing=label_smoothing)

        # Centerness loss
        ctr_pred = centerness.squeeze(1)
        total_ctr += F.binary_cross_entropy_with_logits(ctr_pred[obj_t], ctr_t[obj_t]) if obj_t.any() else 0.0

        if obj_t.any():
            pred_obj = pred_boxes[obj_t]
            tgt_obj = box_t[obj_t]

            # CIoU loss (YOLO v5/v8 style)
            ciou = complete_box_iou_loss(pred_obj, tgt_obj, reduction="mean")
            total_ciou += ciou

            # Plain L1 (no IoU weighting — IoU=0 early in training would zero out gradients)
            total_l1 += F.l1_loss(pred_obj, tgt_obj)

    total_cls /= n_scales
    total_ciou /= n_scales
    total_l1 /= n_scales
    total_ctr /= n_scales

    total = 1.0 * total_cls + 5.0 * total_ciou + 2.0 * total_l1 + 1.0 * total_ctr
    parts = {
        "cls": _to_scalar(total_cls),
        "ciou": _to_scalar(total_ciou),
        "l1": _to_scalar(total_l1),
        "ctr": _to_scalar(total_ctr),
    }
    return total, parts


# ----------------------------
# multi-scale inference with centerness weighting
# ----------------------------
@torch.no_grad()
def predict_from_outputs_multiscale(all_cls, all_boxes, all_ctr, score_thresh=0.05, iou_thresh=0.5):
    B = all_cls[0].shape[0]

    preds = [[] for _ in range(B)]

    for cls_logits, pred_boxes, centerness in zip(all_cls, all_boxes, all_ctr):
        _, K, H, W = cls_logits.shape
        ctr_score = centerness.squeeze(1).sigmoid()  # [B, H, W]

        probs = cls_logits.softmax(dim=1)[:, 1:, :, :]
        probs = probs.permute(0, 2, 3, 1).reshape(B, H * W, K - 1)
        scores, labels = probs.max(dim=-1)
        labels = labels + 1

        # Weight classification score by centerness
        scores = scores * ctr_score.reshape(B, H * W)

        boxes = pred_boxes.reshape(B, H * W, 4)

        for b in range(B):
            keep = scores[b] > score_thresh
            preds[b].append((boxes[b][keep], scores[b][keep], labels[b][keep]))

    results = []
    for b in range(B):
        all_b = preds[b]
        if not all_b or all(len(x[0]) == 0 for x in all_b):
            results.append({
                "boxes": torch.zeros((0, 4), dtype=torch.float32),
                "scores": torch.zeros((0,), dtype=torch.float32),
                "labels": torch.zeros((0,), dtype=torch.long),
            })
            continue

        bboxes = torch.cat([x[0] for x in all_b])
        bscores = torch.cat([x[1] for x in all_b])
        blabels = torch.cat([x[2] for x in all_b])

        keep_idx = batched_nms(bboxes, bscores, blabels, iou_thresh)
        results.append({
            "boxes": bboxes[keep_idx].cpu(),
            "scores": bscores[keep_idx].cpu(),
            "labels": blabels[keep_idx].cpu(),
        })

    return results


# ----------------------------
# train / val
# ----------------------------
def run_epoch(model, loader, optimizer=None, device=None, train=True, scaler=None, accum_steps=1, radius=1, label_smoothing=0.05):
    model.train() if train else model.eval()
    total_loss = 0.0

    # Get ce_weight from model (handle compiled wrapper)
    raw_model = _unwrap_compiled(model)
    ce_weight = raw_model.ce_weight

    metric = None
    if not train:
        metric = MeanAveragePrecision(box_format="xyxy", iou_type="bbox", iou_thresholds=[0.5])

    prefetcher = CUDAPrefetcher(loader, device)
    pbar = tqdm(prefetcher, desc="train" if train else "val", leave=False, total=len(loader))

    for step, (images, targets) in enumerate(pbar):

        with torch.set_grad_enabled(train):
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                all_cls, all_boxes, all_ctr = model(images)
                loss, parts = detection_loss_multiscale(
                    all_cls, all_boxes, all_ctr, targets, ce_weight,
                    radius=radius, label_smoothing=label_smoothing,
                )
                if train:
                    loss = loss / accum_steps

        if train:
            scaler.scale(loss).backward()
            if (step + 1) % accum_steps == 0 or (step + 1) == len(loader):
                scaler.unscale_(optimizer)
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                # Skip step if gradients are NaN/Inf (scaler handles this automatically)
                if torch.isfinite(grad_norm):
                    scaler.step(optimizer)
                else:
                    print(f"  [step {step}] skipping — grad_norm={grad_norm:.1f}")
                scaler.update()
                optimizer.zero_grad(set_to_none=True)

        total_loss += loss.item() * (accum_steps if train else 1)
        avg_loss = total_loss / (step + 1)

        if train:
            pbar.set_postfix(loss=f"{avg_loss:.4f}", cls=f"{parts['cls']:.3f}", ciou=f"{parts['ciou']:.3f}", ctr=f"{parts['ctr']:.3f}")
        else:
            preds = predict_from_outputs_multiscale(all_cls, all_boxes, all_ctr, score_thresh=0.05, iou_thresh=0.5)
            gts = [{"boxes": t["boxes"].cpu(), "labels": t["labels"].cpu()} for t in targets]
            metric.update(preds, gts)

    avg_loss = total_loss / max(len(loader), 1)

    if train:
        return avg_loss

    scores = metric.compute()
    return avg_loss, scores["map_50"].item()


# ----------------------------
# main
# ----------------------------
def main():
    set_seed(SEED)
    make_dirs(SAVE_DIR)

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    full_ds = CocoDetDataset(DATA_DIR, indices=None, augment=False, img_size=IMG_SIZE)

    perm = np.random.RandomState(SEED).permutation(len(full_ds))
    n_val = max(1, int(VAL_RATIO * len(full_ds)))
    val_idx = perm[:n_val].tolist()
    train_idx = perm[n_val:].tolist()

    train_ds = CocoDetDataset(DATA_DIR, indices=train_idx, augment=True, img_size=IMG_SIZE)
    val_ds = CocoDetDataset(DATA_DIR, indices=val_idx, augment=False, img_size=IMG_SIZE)

    # Wrap training set with mosaic
    train_ds_mosaic = MosaicWrapper(train_ds, p=0.5)

    loader_kwargs = dict(
        num_workers=NUM_WORKERS,
        pin_memory=(device.type == "cuda"),
        collate_fn=collate_fn,
        persistent_workers=NUM_WORKERS > 0,
        prefetch_factor=4 if NUM_WORKERS > 0 else None,
    )

    train_loader = InfiniteDataLoader(DataLoader(train_ds_mosaic, batch_size=BATCH_SIZE, shuffle=True, drop_last=True, **loader_kwargs))
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, **loader_kwargs)

    model = MambaVisionDetector(
        num_classes=full_ds.num_classes,
        model_name=MODEL_NAME,
        freeze_stages=FREEZE_BACKBONE_STAGES,
        fpn_ch=FPN_CHANNELS,
    ).to(device)

    # EMA model for evaluation
    ema = ModelEMA(model, decay=EMA_DECAY)

    # torch.compile incompatible with mamba's selective_scan_cuda kernels
    ema_compiled = ema.ema

    # Differential LR: lower for backbone, higher for head/neck
    backbone_params = []
    head_params = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if "backbone" in name:
            backbone_params.append(param)
        else:
            head_params.append(param)

    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": LR * BACKBONE_LR_MULT},
        {"params": head_params, "lr": LR},
    ], weight_decay=WEIGHT_DECAY, fused=True)

    warmup_scheduler = torch.optim.lr_scheduler.LinearLR(optimizer, start_factor=0.01, total_iters=WARMUP_EPOCHS)
    cosine_scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=1000, T_mult=2, eta_min=1e-6)
    scheduler = torch.optim.lr_scheduler.SequentialLR(optimizer, [warmup_scheduler, cosine_scheduler], milestones=[WARMUP_EPOCHS])

    best_map50 = -1.0

    total_params = sum(p.numel() for p in model.parameters())
    train_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"device={device}")
    print(f"train_images={len(train_ds)} val_images={len(val_ds)}")
    print(f"num_classes={full_ds.num_classes}")
    print(f"image_size={IMG_SIZE} backbone={MODEL_NAME}")
    print(f"params: {total_params/1e6:.1f}M total, {train_params/1e6:.1f}M trainable")
    print(f"FPN channels={FPN_CHANNELS}, multi-cell radius={MULTI_CELL_RADIUS}")
    print(f"mosaic=0.5, EMA={EMA_DECAY}, label_smooth={LABEL_SMOOTHING}")
    print(f"backbone_lr={LR*BACKBONE_LR_MULT:.1e}, head_lr={LR:.1e}")

    for epoch in range(1, EPOCHS + 1):
        train_loss = run_epoch(
            model, train_loader, optimizer=optimizer, device=device,
            train=True, scaler=scaler, accum_steps=GRAD_ACCUM_STEPS,
            radius=MULTI_CELL_RADIUS, label_smoothing=LABEL_SMOOTHING,
        )
        scheduler.step()

        # Update EMA after each epoch
        raw_model = _unwrap_compiled(model)
        ema.update(raw_model, step=epoch)

        if epoch % VAL_EVERY == 0 or epoch == 1:
            val_loss, val_map50 = run_epoch(
                ema_compiled, val_loader, device=device, train=False, scaler=scaler,
                radius=MULTI_CELL_RADIUS, label_smoothing=LABEL_SMOOTHING,
            )

            print(
                f"epoch {epoch}: "
                f"train_loss={train_loss:.4f} "
                f"val_loss={val_loss:.4f} "
                f"val_mAP50={val_map50:.4f} "
                f"lr={optimizer.param_groups[1]['lr']:.2e}"
            )

            if val_map50 > best_map50:
                best_map50 = val_map50
                ckpt = {
                    "model_state_dict": ema.ema.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "epoch": epoch,
                    "best_map50": best_map50,
                    "id2label": full_ds.id2label,
                    "label_to_cat_id": full_ds.label_to_cat_id,
                    "config": {
                        "model_name": MODEL_NAME,
                        "img_size": IMG_SIZE,
                        "num_classes": full_ds.num_classes,
                        "fpn_ch": FPN_CHANNELS,
                    },
                }
                torch.save(ckpt, str(Path(SAVE_DIR) / "best.pt"))
                print(f"  -> saved best checkpoint (mAP50={best_map50:.4f})")
        else:
            print(f"epoch {epoch}: train_loss={train_loss:.4f} lr={optimizer.param_groups[1]['lr']:.2e}")

    print(f"best val mAP@0.5 = {best_map50:.4f}")


if __name__ == "__main__":
    main()
