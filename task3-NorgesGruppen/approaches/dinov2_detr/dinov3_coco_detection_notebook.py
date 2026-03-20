import json
import os
import random
from pathlib import Path
from tqdm.auto import tqdm
import torchmetrics
import albumentations as A
import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import AutoBackbone, AutoConfig, AutoImageProcessor, DetrConfig, DetrForObjectDetection

DATA_DIR = "./data/raw/train"
OUTPUT_DIR = "./outputs_dinov2_detr"
VAL_RATIO = 0.1
EPOCHS = 200
BATCH_SIZE = 32
NUM_WORKERS = 16
LR_1 = 1e-4
LR_BACKBONE = 1e-5
MAX_SIZE = 512
SEED = 42

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

set_seed(SEED)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
device

from pathlib import Path
import json

import albumentations as A
import numpy as np
from PIL import Image
from torch.utils.data import Dataset


class CocoDetDataset(Dataset):
    def __init__(
        self,
        root,
        image_processor=None,
        indices=None,
        augment=False,
        max_size=MAX_SIZE,
        sliding_window=False,
        window_size=MAX_SIZE,
        stride=256,
    ):
        self.root = Path(root)
        self.image_processor = image_processor
        self.augment = augment
        self.sliding_window = sliding_window
        self.window_size = window_size
        self.stride = stride

        with open(self.root / "annotations.json", "r", encoding="utf-8") as f:
            coco = json.load(f)

        self.images_dir = self.root / "images"
        self.images = coco["images"]
        self.categories = coco["categories"]

        self.cat_ids = sorted(c["id"] for c in self.categories)
        self.cat_id_to_label = {cid: i for i, cid in enumerate(self.cat_ids)}
        self.id2label = {
            i: next(c["name"] for c in self.categories if c["id"] == cid)
            for i, cid in enumerate(self.cat_ids)
        }
        self.label2id = {v: k for k, v in self.id2label.items()}

        anns_by_image = {}
        for ann in coco["annotations"]:
            if ann.get("iscrowd", 0) == 0:
                anns_by_image.setdefault(ann["image_id"], []).append(ann)

        if indices is None:
            indices = list(range(len(self.images)))

        base = [(self.images[i], anns_by_image.get(self.images[i]["id"], [])) for i in indices]

        self.train_tf = A.Compose(
            [
                A.RandomResizedCrop(
                    size=(max_size, max_size),
                    scale=(0.5, 1),
                    p=1,
                ),
                A.HorizontalFlip(p=0.5),
                A.RandomRotate90(),
                A.Affine(
                    scale=(0.95, 1.05),
                    translate_percent=(0, 0.05),
                    rotate=(-5, 5),
                    p=0.4,
                ),
                A.RandomBrightnessContrast(p=0.7),
                A.ElasticTransform(),
                A.GaussianBlur(),
                A.ColorJitter(),
                A.ToGray(p=0.25),
                A.ToSepia(p=0.1),
            ],
            bbox_params=A.BboxParams(format="coco", label_fields=["class_labels"]),
        )

        self.val_tf = A.Compose(
            [A.Resize(height=MAX_SIZE, width=MAX_SIZE)],
            bbox_params=A.BboxParams(format="coco", label_fields=["class_labels"]),
        )

        self.samples = self._make_windows(base) if sliding_window else base

    def _positions(self, size):
        if size <= self.window_size:
            return [0]
        pos = list(range(0, size - self.window_size + 1, self.stride))
        last = size - self.window_size
        if pos[-1] != last:
            pos.append(last)
        return pos

    def _make_windows(self, base):
        out = []
        for img_info, anns in base:
            W, H = img_info["width"], img_info["height"]
            for x0 in self._positions(W):
                for y0 in self._positions(H):
                    out.append((img_info, anns, x0, y0))
        return out

    def __len__(self):
        return len(self.samples)

    def _crop_boxes(self, anns, x0, y0, w, h):
        boxes, labels = [], []
        for ann in anns:
            x, y, bw, bh = ann["bbox"]
            x1, y1 = x + bw, y + bh
            ix0, iy0 = max(x, x0), max(y, y0)
            ix1, iy1 = min(x1, x0 + w), min(y1, y0 + h)
            iw, ih = ix1 - ix0, iy1 - iy0
            if iw > 1 and ih > 1:
                boxes.append([ix0 - x0, iy0 - y0, iw, ih])
                labels.append(self.cat_id_to_label[ann["category_id"]])
        return boxes, labels

    def __getitem__(self, idx):
        if self.sliding_window:
            img_info, anns, x0, y0 = self.samples[idx]
        else:
            img_info, anns = self.samples[idx]
            x0 = y0 = 0

        image = np.array(Image.open(self.images_dir / img_info["file_name"]).convert("RGB"))

        if self.sliding_window:
            H, W = image.shape[:2]
            x1, y1 = min(x0 + self.window_size, W), min(y0 + self.window_size, H)
            image = image[y0:y1, x0:x1]
            boxes, labels = self._crop_boxes(anns, x0, y0, x1 - x0, y1 - y0)
            out = self.val_tf(image=image, bboxes=boxes, class_labels=labels)
        else:
            boxes, labels = [], []
            for ann in anns:
                x, y, w, h = ann["bbox"]
                if w > 1 and h > 1:
                    boxes.append([x, y, w, h])
                    labels.append(self.cat_id_to_label[ann["category_id"]])

            tf = self.train_tf if self.augment else self.val_tf
            out = tf(image=image, bboxes=boxes, class_labels=labels)

        annotations = [
            {
                "image_id": int(img_info["id"]),
                "category_id": int(label),
                "bbox": [float(x), float(y), float(w), float(h)],
                "area": float(w * h),
                "iscrowd": 0,
            }
            for (x, y, w, h), label in zip(out["bboxes"], out["class_labels"])
        ]

        return {
            "image": Image.fromarray(out["image"]),
            "image_id": int(img_info["id"]),
            "annotations": annotations,
        }

class Collate:
    def __init__(self, image_processor):
        self.image_processor = image_processor

    def __call__(self, batch):
        images = [x["image"] for x in batch]
        annotations = [{"image_id": x["image_id"], "annotations": x["annotations"]} for x in batch]
        return self.image_processor(images=images, annotations=annotations, return_tensors="pt")

def make_split_indices(n, val_ratio=0.1, seed=42):
    ids = list(range(n))
    rnd = random.Random(seed)
    rnd.shuffle(ids)
    n_val = max(1, int(n * val_ratio))
    val_ids = ids[:n_val]
    train_ids = ids[n_val:]
    return train_ids, val_ids

image_processor = AutoImageProcessor.from_pretrained("facebook/detr-resnet-50")

full_ds = CocoDetDataset(DATA_DIR, augment=False, max_size=MAX_SIZE)
train_ids, val_ids = make_split_indices(len(full_ds), VAL_RATIO, SEED)

train_ds = CocoDetDataset(DATA_DIR, indices=train_ids, augment=True, max_size=MAX_SIZE)
val_ds = CocoDetDataset(DATA_DIR, indices=val_ids, augment=False, max_size=MAX_SIZE, sliding_window=True)

train_loader = DataLoader(
    train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS, collate_fn=Collate(image_processor)
)
val_loader = DataLoader(
    val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, collate_fn=Collate(image_processor)
)

print("train:", len(train_ds), "val:", len(val_ds))
print(train_ds.id2label)

BACKBONE_NAME = "facebook/dinov2-base"

def build_model(id2label, label2id):
    config = DetrConfig(
        num_labels=len(id2label),
        id2label=id2label,
        label2id=label2id,
        backbone=BACKBONE_NAME,
        use_pretrained_backbone=True,
        use_timm_backbone=False,
        backbone_kwargs={
            "out_indices": [11],          # last DINOv2 block
            "reshape_hidden_states": True
        },
    )
    model = DetrForObjectDetection(config)
    return model

model = build_model(train_ds.id2label, train_ds.label2id).to(device)

backbone_params, other_params = [], []
for name, param in model.named_parameters():
    (backbone_params if "backbone" in name else other_params).append(param)

optimizer = torch.optim.AdamW(
    [
        {"params": backbone_params, "lr": LR_BACKBONE, "wd": 1/len(train_ds)},
        {"params": other_params, "lr": LR_1, "wd": 1/len(train_ds)},
    ]
)




class Collate:
    def __init__(self, image_processor):
        self.image_processor = image_processor

    def __call__(self, batch):
        images = [x["image"] for x in batch]
        annotations = [{"image_id": x["image_id"], "annotations": x["annotations"]} for x in batch]

        encoded = self.image_processor(
            images=images,
            annotations=annotations,
            return_tensors="pt",
        )

        # for mAP@0.5 on validation
        target_sizes = torch.tensor(
            [[img.size[1], img.size[0]] for img in images],  # (H, W)
            dtype=torch.long,
        )

        raw_targets = []
        for x in batch:
            boxes = []
            labels = []
            for ann in x["annotations"]:
                bx, by, bw, bh = ann["bbox"]
                boxes.append([bx, by, bx + bw, by + bh])  # xyxy
                labels.append(ann["category_id"])

            raw_targets.append(
                {
                    "boxes": torch.tensor(boxes, dtype=torch.float32) if boxes else torch.zeros((0, 4), dtype=torch.float32),
                    "labels": torch.tensor(labels, dtype=torch.int64) if labels else torch.zeros((0,), dtype=torch.int64),
                }
            )

        encoded["target_sizes"] = target_sizes
        encoded["raw_targets"] = raw_targets
        return encoded


from tqdm.auto import tqdm
import torch

USE_AMP = device.type == "cuda"
scaler = torch.amp.GradScaler("cuda", enabled=USE_AMP)
def run_epoch(model, loader, optimizer=None, device=None, train=True):
    model.train() if train else model.eval()
    total_loss = 0.0

    metric = None
    if not train:
        from torchmetrics.detection.mean_ap import MeanAveragePrecision
        metric = MeanAveragePrecision(box_format="xyxy", iou_type="bbox", iou_thresholds=[0.5])

    pbar = tqdm(loader, desc="train" if train else "val", leave=False)

    for batch in pbar:
        pixel_values = batch["pixel_values"].to(device)
        pixel_mask = batch.get("pixel_mask")
        if pixel_mask is not None:
            pixel_mask = pixel_mask.to(device)

        labels = [{k: v.to(device) for k, v in x.items()} for x in batch["labels"]]

        if train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(train):
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                outputs = model(
                    pixel_values=pixel_values,
                    pixel_mask=pixel_mask,
                    labels=labels,
                )
                loss = outputs.loss

        if train:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

        total_loss += loss.item()
        avg_loss = total_loss / max(1, pbar.n + 1)

        if train:
            pbar.set_postfix(loss=f"{avg_loss:.4f}")
        else:
            target_sizes = torch.stack([
                torch.tensor([img.shape[-2], img.shape[-1]], device=device)
                for img in batch["pixel_values"]
            ])

            preds = image_processor.post_process_object_detection(
                outputs,
                threshold=0.0,
                target_sizes=target_sizes,
            )

            preds = [
                {
                    "boxes": p["boxes"].detach().cpu(),
                    "scores": p["scores"].detach().cpu(),
                    "labels": p["labels"].detach().cpu(),
                }
                for p in preds
            ]

            targets = []
            for lbl in batch["labels"]:
                boxes = lbl["boxes"].detach().cpu()
                labels_ = (
                    lbl["class_labels"].detach().cpu()
                    if "class_labels" in lbl
                    else lbl["labels"].detach().cpu()
                )

                # HF DETR labels are usually normalized cxcywh -> convert to xyxy pixels
                h, w = lbl["orig_size"].tolist()
                scale = torch.tensor([w, h, w, h], dtype=boxes.dtype)

                boxes = boxes * scale
                cx, cy, bw, bh = boxes.unbind(-1)
                x1 = cx - 0.5 * bw
                y1 = cy - 0.5 * bh
                x2 = cx + 0.5 * bw
                y2 = cy + 0.5 * bh
                boxes = torch.stack([x1, y1, x2, y2], dim=-1)

                targets.append({"boxes": boxes, "labels": labels_})

            metric.update(preds, targets)
            map50 = metric.compute()["map_50"].item()
            pbar.set_postfix(loss=f"{avg_loss:.4f}", map50=f"{map50:.4f}")

    avg_loss = total_loss / max(len(loader), 1)

    if train:
        return avg_loss

    scores = metric.compute()
    return avg_loss, scores["map_50"].item()

os.makedirs(OUTPUT_DIR, exist_ok=True)
best_val = float("inf")


for epoch in range(1, EPOCHS + 1):
    train_loss = run_epoch(model, train_loader, optimizer=optimizer, device=device, train=True)
    if epoch % 5 != 0:
      print(
        f"epoch {epoch}: "
        f"train_loss={train_loss:.4f} "
      )
      continue

    with torch.no_grad():
      val_loss, val_map50 = run_epoch(model, val_loader, optimizer=None, device=device, train=False)

    print(
        f"epoch {epoch}: "
        f"train_loss={train_loss:.4f} "
        f"val_loss={val_loss:.4f} "
        f"val_mAP50={val_map50:.4f}"
    )

    if val_loss < best_val:
        best_val = val_loss
        save_dir = os.path.join(OUTPUT_DIR, "best")
        os.makedirs(save_dir, exist_ok=True)
        model.save_pretrained(save_dir)
        image_processor.save_pretrained(save_dir)

print("best val loss:", best_val)
print("saved to:", os.path.join(OUTPUT_DIR, "best"))