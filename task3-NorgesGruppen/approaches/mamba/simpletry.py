# mamba_vision_detector.py

import json
import random
from pathlib import Path

import albumentations as A
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from albumentations.pytorch import ToTensorV2
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from torchvision.ops import batched_nms, generalized_box_iou_loss
from tqdm.auto import tqdm

# ----------------------------
# config
# ----------------------------
DATA_DIR = "/home/devstar18131/task2/task2/train"  # folder with annotations.json and images/
MODEL_NAME = "mamba_vision_L"  # mamba_vision_T / _S / _B / _L
IMG_SIZE = 1120
VAL_RATIO = 0.1

BATCH_SIZE = 16
NUM_WORKERS = 26
EPOCHS = 5000
LR = 1e-4
WEIGHT_DECAY = 3e-3
SEED = 42

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
    out = []
    for x, y, bw, bh in boxes_xywh:
        x1 = x / w
        y1 = y / h
        x2 = (x + bw) / w
        y2 = (y + bh) / h
        out.append([x1, y1, x2, y2])
    return out


def make_dirs(path):
    Path(path).mkdir(parents=True, exist_ok=True)


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

        # background = 0
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

        self.train_tf = A.Compose(
            [
                A.RandomResizedCrop((img_size, img_size),scale=(0.4,1.0)),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(),
                A.RandomRotate90(),
                A.ChannelDropout(),
                A.RandomBrightnessContrast(p=0.7),
                A.ColorJitter(brightness=(0.3,1.7), contrast=(0.3,1.7),saturation=(0.3,1.7), p=0.95),
                A.GaussianBlur(),
                A.GaussNoise(p=0.8),
                A.RandomFog(),
                A.ChromaticAberration(),
                A.ToGray(p=0.25),
                A.ToSepia(p=0.1),
                A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
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
                A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
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
        image = np.array(Image.open(self.images_dir / img_info["file_name"]).convert("RGB"))

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


# ----------------------------
# model
# ----------------------------
class MambaVisionDetector(nn.Module):
    def __init__(self, num_classes, model_name="mamba_vision_L"):
        super().__init__()
        # Load MambaVision backbone with multi-scale feature extraction
        self.backbone = timm.create_model(model_name, pretrained=True, features_only=True)
        self.num_classes = num_classes

        # Get feature channels from backbone (last two stages for FPN-lite)
        feat_info = self.backbone.feature_info
        c_last = feat_info[-1]["num_chs"]
        c_prev = feat_info[-2]["num_chs"]

        hidden = c_last

        # Lateral connection from second-to-last stage
        self.lateral = nn.Conv2d(c_prev, hidden, kernel_size=1)

        self.neck = nn.Sequential(
            nn.Conv2d(hidden, hidden // 2, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv2d(hidden // 2, hidden, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv2d(hidden, hidden // 2, kernel_size=3, padding=1),
            nn.Conv2d(hidden // 2, hidden // 4, kernel_size=3, padding=1),
            nn.GELU(),
        )

        self.cls_head = nn.Conv2d(hidden // 4, num_classes, kernel_size=1)
        self.box_head = nn.Conv2d(hidden // 4, 4, kernel_size=1)  # cx, cy, w, h in [0, 1]

    def forward(self, images):
        features = self.backbone(images)
        feat_last = features[-1]   # highest-level (smallest spatial)
        feat_prev = features[-2]   # one level up (larger spatial)

        # Simple top-down fusion: upsample last + lateral from prev
        up = F.interpolate(feat_last, size=feat_prev.shape[2:], mode="bilinear", align_corners=False)
        feat = up + self.lateral(feat_prev)

        feat = self.neck(feat)

        B = images.shape[0]
        H, W = feat.shape[2], feat.shape[3]

        cls_logits = self.cls_head(feat)  # [B, K, H, W]

        box_raw = self.box_head(feat).sigmoid().permute(0, 2, 3, 1)  # [B, H, W, 4]
        cx, cy, bw, bh = box_raw.unbind(-1)

        x1 = (cx - 0.5 * bw).clamp(0, 1)
        y1 = (cy - 0.5 * bh).clamp(0, 1)
        x2 = (cx + 0.5 * bw).clamp(0, 1)
        y2 = (cy + 0.5 * bh).clamp(0, 1)

        pred_boxes = torch.stack([x1, y1, x2, y2], dim=-1)
        return cls_logits, pred_boxes


# ----------------------------
# dense target assignment
# ----------------------------
def build_dense_targets(targets, grid_h, grid_w, device):
    """
    Assign each GT box to the grid cell containing its center.
    If multiple GT boxes land in the same cell, keep only the largest one.
    """
    B = len(targets)

    cls_t = torch.zeros((B, grid_h, grid_w), dtype=torch.long, device=device)   # bg = 0
    box_t = torch.zeros((B, grid_h, grid_w, 4), dtype=torch.float32, device=device)
    obj_t = torch.zeros((B, grid_h, grid_w), dtype=torch.bool, device=device)

    for b, t in enumerate(targets):
        boxes = t["boxes"].to(device)
        labels = t["labels"].to(device)

        if boxes.numel() == 0:
            continue

        cx = 0.5 * (boxes[:, 0] + boxes[:, 2])
        cy = 0.5 * (boxes[:, 1] + boxes[:, 3])

        gx = torch.clamp((cx * grid_w).long(), 0, grid_w - 1)
        gy = torch.clamp((cy * grid_h).long(), 0, grid_h - 1)

        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        order = torch.argsort(areas, descending=True)

        for i in order.tolist():
            x = gx[i].item()
            y = gy[i].item()
            if obj_t[b, y, x]:
                continue
            cls_t[b, y, x] = labels[i]
            box_t[b, y, x] = boxes[i]
            obj_t[b, y, x] = True

    return cls_t, box_t, obj_t


# ----------------------------
# loss
# ----------------------------
def detection_loss(cls_logits, pred_boxes, targets):
    B, K, H, W = cls_logits.shape
    device = cls_logits.device

    cls_t, box_t, obj_t = build_dense_targets(targets, H, W, device)

    ce_weight = torch.tensor([0.1, 0.4348,  0.5718,  3.1751,  0.2498,  2.1646,  0.7006,  0.6891,  0.3685,  0.5140,  3.1751,  1.8879,  0.5792,
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
         1.1226,  0.1461, 12.1722,  1.0572,  1.3929,  3.6403,  7.2376,  0.1307]).to(device)
    ce_weight[0] = 0.1
    cls_loss = F.cross_entropy(cls_logits, cls_t, weight=ce_weight.pow(0.75))

    if obj_t.any():
        pred_obj = pred_boxes[obj_t]
        tgt_obj = box_t[obj_t]
        l1_loss = F.l1_loss(pred_obj, tgt_obj)
        giou_loss = generalized_box_iou_loss(pred_obj, tgt_obj, reduction="mean")
    else:
        l1_loss = cls_logits.new_tensor(0.0)
        giou_loss = cls_logits.new_tensor(0.0)

    total = cls_loss + 5.0 * l1_loss + 2.0 * giou_loss
    parts = {
        "cls": cls_loss.detach().item(),
        "l1": l1_loss.detach().item(),
        "giou": giou_loss.detach().item(),
    }
    return total, parts


# ----------------------------
# inference
# ----------------------------
@torch.no_grad()
def predict_from_outputs(cls_logits, pred_boxes, score_thresh=0.05, iou_thresh=0.5):
    B, K, H, W = cls_logits.shape

    probs = cls_logits.softmax(dim=1)      # [B, K, H, W]
    probs = probs[:, 1:, :, :]             # drop background
    probs = probs.permute(0, 2, 3, 1).reshape(B, H * W, K - 1)

    scores, labels = probs.max(dim=-1)
    labels = labels + 1                    # shift above background

    boxes = pred_boxes.reshape(B, H * W, 4)

    preds = []
    for b in range(B):
        keep = scores[b] > score_thresh
        bboxes = boxes[b][keep]
        bscores = scores[b][keep]
        blabels = labels[b][keep]

        if len(bboxes) == 0:
            preds.append(
                {
                    "boxes": torch.zeros((0, 4), dtype=torch.float32),
                    "scores": torch.zeros((0,), dtype=torch.float32),
                    "labels": torch.zeros((0,), dtype=torch.long),
                }
            )
            continue

        keep_idx = batched_nms(bboxes, bscores, blabels, iou_thresh)
        preds.append(
            {
                "boxes": bboxes[keep_idx].detach().cpu(),
                "scores": bscores[keep_idx].detach().cpu(),
                "labels": blabels[keep_idx].detach().cpu(),
            }
        )

    return preds


# ----------------------------
# train / val
# ----------------------------
def run_epoch(model, loader, optimizer=None, device=None, train=True, scaler=None):
    model.train() if train else model.eval()
    total_loss = 0.0

    metric = None
    if not train:
        metric = MeanAveragePrecision(
            box_format="xyxy",
            iou_type="bbox",
            iou_thresholds=[0.5],
        )

    pbar = tqdm(loader, desc="train" if train else "val", leave=False)

    for images, targets in pbar:
        images = images.to(device, non_blocking=True)

        if train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(train):
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                cls_logits, pred_boxes = model(images)
                loss, parts = detection_loss(cls_logits, pred_boxes, targets)

        if train:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

        total_loss += loss.item()
        avg_loss = total_loss / max(1, pbar.n + 1)

        if train:
            pbar.set_postfix(
                loss=f"{avg_loss:.4f}",
                cls=f"{parts['cls']:.4f}",
                l1=f"{parts['l1']:.4f}",
                giou=f"{parts['giou']:.4f}",
            )
        else:
            preds = predict_from_outputs(
                cls_logits,
                pred_boxes,
                score_thresh=0.1,
                iou_thresh=0.5,
            )
            gts = [{"boxes": t["boxes"].cpu(), "labels": t["labels"].cpu()} for t in targets]
            metric.update(preds, gts)
            map50 = metric.compute()["map_50"].item()
            pbar.set_postfix(loss=f"{avg_loss:.4f}", map50=f"{map50:.4f}")

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

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    full_ds = CocoDetDataset(DATA_DIR, indices=None, augment=False, img_size=IMG_SIZE)

    perm = np.random.RandomState(SEED).permutation(len(full_ds))
    n_val = max(1, int(VAL_RATIO * len(full_ds)))
    val_idx = perm[:n_val].tolist()
    train_idx = perm[n_val:].tolist()

    train_ds = CocoDetDataset(DATA_DIR, indices=train_idx, augment=True, img_size=IMG_SIZE)
    val_ds = CocoDetDataset(DATA_DIR, indices=val_idx, augment=False, img_size=IMG_SIZE)

    train_loader = DataLoader(
        train_ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        pin_memory=(device.type == "cuda"),
        collate_fn=collate_fn,
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=(device.type == "cuda"),
        collate_fn=collate_fn,
    )

    model = MambaVisionDetector(num_classes=full_ds.num_classes, model_name=MODEL_NAME).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    best_map50 = -1.0

    print(f"device={device}")
    print(f"train_images={len(train_ds)} val_images={len(val_ds)}")
    print(f"num_classes={full_ds.num_classes}")
    print(f"image_size={IMG_SIZE}")
    print(f"backbone={MODEL_NAME}")

    for epoch in range(1, EPOCHS + 1):
        train_loss = run_epoch(
            model,
            train_loader,
            optimizer=optimizer,
            device=device,
            train=True,
            scaler=scaler,
        )

        val_loss, val_map50 = run_epoch(
            model,
            val_loader,
            optimizer=None,
            device=device,
            train=False,
            scaler=scaler,
        )

        print(
            f"epoch {epoch}: "
            f"train_loss={train_loss:.4f} "
            f"val_loss={val_loss:.4f} "
            f"val_mAP50={val_map50:.4f}"
        )

        if val_map50 > best_map50:
            best_map50 = val_map50
            ckpt = {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "best_map50": best_map50,
                "id2label": full_ds.id2label,
                "label_to_cat_id": full_ds.label_to_cat_id,
                "config": {
                    "model_name": MODEL_NAME,
                    "img_size": IMG_SIZE,
                    "num_classes": full_ds.num_classes,
                },
            }
            torch.save(ckpt, str(Path(SAVE_DIR) / "best.pt"))
            print(f"saved best checkpoint to {Path(SAVE_DIR) / 'best.pt'}")

    print(f"best val mAP@0.5 = {best_map50:.4f}")


if __name__ == "__main__":
    main()
