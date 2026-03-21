"""Overnight v2: K-fold ablation + Optuna + Final 100% data training.

Phase 1 (2h): K-fold ablation — test dataset sizes & product crop injection
Phase 2 (1h): Optuna HP search with K-fold on best config
Phase 3 (3h): Final training on ALL 248 images with best params

Key anti-overfitting measures:
- K-fold splits BEFORE augmentation (no data leakage)
- Val on original untouched images only
- Final model trains on 100% data (no wasted images)
- close_mosaic=5 (not 15)
- Stronger regularization
"""
import os, json, random, shutil, copy, time, glob
from pathlib import Path
import numpy as np, cv2, torch

os.environ['WANDB_API_KEY'] = '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'

SEED = 42
DATA_DIR = Path.home() / 'train_data' / 'train'
PRODUCT_DIR = Path.home() / 'product_images' / 'NGD Product Images'
WORK_DIR = Path.home() / 'overnight_v2'
START_TIME = time.time()
TOTAL_BUDGET = 6.5 * 3600

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)

import wandb; wandb.login()
from ultralytics import YOLO, settings
settings.update({'wandb': True})

# Fixed Optuna augmentation params
AUG = {
    'mosaic': 0.5, 'mixup': 0.134, 'copy_paste': 0.182, 'scale': 0.206,
    'degrees': 9.64, 'shear': 1.94, 'hsv_h': 0.0286, 'hsv_s': 0.689,
    'hsv_v': 0.305, 'erasing': 0.345, 'flipud': 0.0, 'bgr': 0.003,
    'close_mosaic': 5,
}

def time_left():
    return TOTAL_BUDGET - (time.time() - START_TIME)

def hours_left():
    return time_left() / 3600

# ─── Load COCO data ──────────────────────────────────────────────────────────
print('Loading annotations...')
with open(DATA_DIR / 'annotations.json') as f:
    COCO = json.load(f)

IMG_LOOKUP = {img['id']: img for img in COCO['images']}
ANNS_BY_IMAGE = {}
for ann in COCO['annotations']:
    ANNS_BY_IMAGE.setdefault(ann['image_id'], []).append(ann)
NUM_CLASSES = len(COCO['categories'])
CLASS_NAMES = {cat['id']: cat['name'] for cat in COCO['categories']}

# Category to product code mapping
CAT_TO_CODE = {}
for cat in COCO['categories']:
    CAT_TO_CODE[cat['id']] = cat.get('name', '')

# ─── Product crop preparation ────────────────────────────────────────────────
def prepare_product_crops():
    """Simple background removal for product images."""
    crop_dir = WORK_DIR / 'product_crops'
    if crop_dir.exists() and len(list(crop_dir.glob('*.png'))) > 50:
        print(f'Product crops already prepared ({len(list(crop_dir.glob("*.png")))} crops)')
        return crop_dir
    crop_dir.mkdir(parents=True, exist_ok=True)

    # Map category names to product folders
    cat_ann_counts = {}
    for ann in COCO['annotations']:
        cat_ann_counts[ann['category_id']] = cat_ann_counts.get(ann['category_id'], 0) + 1

    processed = 0
    for product_folder in sorted(PRODUCT_DIR.iterdir()):
        if not product_folder.is_dir():
            continue
        code = product_folder.name
        # Find matching category
        cat_id = None
        for cid, cname in CLASS_NAMES.items():
            if code in cname or cname in str(code):
                cat_id = cid
                break

        # Try front, main, or any image
        img_path = None
        for pref in ['front', 'main', 'left', 'right']:
            candidates = list(product_folder.glob(f'*{pref}*'))
            if candidates:
                img_path = candidates[0]
                break
        if img_path is None:
            imgs = list(product_folder.glob('*.jpg')) + list(product_folder.glob('*.png'))
            if imgs:
                img_path = imgs[0]
        if img_path is None:
            continue

        img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue

        # Simple white background removal
        if len(img.shape) == 2:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        # Create RGBA
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = mask
        # Crop to content
        coords = cv2.findNonZero(mask)
        if coords is None:
            continue
        x, y, w, h = cv2.boundingRect(coords)
        if w < 10 or h < 10:
            continue
        crop = rgba[y:y+h, x:x+w]
        out_name = f'prod_{code}.png'
        cv2.imwrite(str(crop_dir / out_name), crop)
        processed += 1

    print(f'Prepared {processed} product crops')
    return crop_dir

# ─── Augmentation functions ──────────────────────────────────────────────────
def apply_hsv(img, h, s, v):
    r = np.random.uniform(-1, 1, 3) * [h, s, v] + 1
    hue, sat, val = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HSV))
    x = np.arange(0, 256, dtype=r.dtype)
    im_hsv = cv2.merge((cv2.LUT(hue, ((x*r[0])%180).astype(np.uint8)),
                         cv2.LUT(sat, np.clip(x*r[1],0,255).astype(np.uint8)),
                         cv2.LUT(val, np.clip(x*r[2],0,255).astype(np.uint8))))
    return cv2.cvtColor(im_hsv, cv2.COLOR_HSV2BGR)

def augment_image(img, anns, w, h):
    a = img.copy(); aa = copy.deepcopy(anns)
    a = apply_hsv(a, 0.0286, 0.689, 0.305)
    angle = random.uniform(-9.64, 9.64)
    s = random.uniform(0.794, 1.206)
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, s)
    a = cv2.warpAffine(a, M, (w, h), borderValue=(114, 114, 114))
    new_anns = []
    for ann in aa:
        bx,by,bw,bh = ann['bbox']
        corners = np.array([[bx,by,1],[bx+bw,by,1],[bx+bw,by+bh,1],[bx,by+bh,1]], dtype=np.float64)
        t = (M @ corners.T).T
        nx,ny = max(0,float(t[:,0].min())), max(0,float(t[:,1].min()))
        nx2,ny2 = min(w,float(t[:,0].max())), min(h,float(t[:,1].max()))
        if nx2-nx>5 and ny2-ny>5:
            na = copy.deepcopy(ann); na['bbox']=[nx,ny,nx2-nx,ny2-ny]; new_anns.append(na)
    if random.random()<0.5:
        a=np.fliplr(a).copy()
        for ann in new_anns: ann['bbox'][0]=w-ann['bbox'][0]-ann['bbox'][2]
    if random.random()<0.345:
        eh=int(np.sqrt(random.uniform(0.02,0.2)*h*w*random.uniform(0.5,2)))
        ew=int(np.sqrt(random.uniform(0.02,0.2)*h*w/random.uniform(0.5,2)))
        if 0<eh<h and 0<ew<w:
            y0,x0=random.randint(0,h-eh),random.randint(0,w-ew)
            a[y0:y0+eh,x0:x0+ew]=np.random.randint(0,255,(eh,ew,3),dtype=np.uint8)
    return a, new_anns

def inject_crops(img, anns, crop_dir, w, h, n_inject=3):
    """Paste product crops onto shelf image."""
    crops = list(crop_dir.glob('*.png'))
    if not crops:
        return img, anns
    a = img.copy(); aa = copy.deepcopy(anns)
    for _ in range(n_inject):
        crop_path = random.choice(crops)
        crop = cv2.imread(str(crop_path), cv2.IMREAD_UNCHANGED)
        if crop is None or crop.shape[2] < 4:
            continue
        # Scale to realistic shelf size (30-200px height)
        target_h = random.randint(30, 200)
        scale = target_h / crop.shape[0]
        target_w = int(crop.shape[1] * scale)
        if target_w < 10:
            continue
        crop = cv2.resize(crop, (target_w, target_h))
        # Random position
        if w - target_w <= 0 or h - target_h <= 0:
            continue
        x0 = random.randint(0, w - target_w)
        y0 = random.randint(0, h - target_h)
        # Alpha blend
        alpha = crop[:, :, 3:4].astype(np.float32) / 255.0
        rgb = crop[:, :, :3].astype(np.float32)
        bg = a[y0:y0+target_h, x0:x0+target_w].astype(np.float32)
        a[y0:y0+target_h, x0:x0+target_w] = (rgb * alpha + bg * (1 - alpha)).astype(np.uint8)
        # Add annotation (use category 0 as fallback — detection still helps)
        aa.append({
            'id': 999999 + random.randint(0, 999999),
            'image_id': -1,
            'category_id': random.randint(0, NUM_CLASSES - 1),
            'bbox': [x0, y0, target_w, target_h],
            'area': target_w * target_h,
            'iscrowd': 0,
        })
    return a, aa

# ─── K-fold split ────────────────────────────────────────────────────────────
def create_kfold_splits(n_folds=3):
    image_ids = sorted(IMG_LOOKUP.keys())
    rng = random.Random(SEED)
    rng.shuffle(image_ids)
    folds = [[] for _ in range(n_folds)]
    for i, iid in enumerate(image_ids):
        folds[i % n_folds].append(iid)
    return folds

# ─── Create YOLO dataset from image IDs ──────────────────────────────────────
def create_yolo_dataset(train_ids, val_ids, out_dir, aug_multiplier=1, use_crops=False, crop_dir=None):
    for split in ('train', 'val'):
        (out_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
        (out_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)

    def write_labels(img_id, img_info, anns, split, fname=None):
        w, h = img_info['width'], img_info['height']
        if fname is None:
            fname = img_info['file_name']
        stem = Path(fname).stem
        label_path = out_dir / 'labels' / split / f'{stem}.txt'
        lines = []
        for ann in anns:
            if ann.get('iscrowd', 0):
                continue
            bx, by, bw, bh = ann['bbox']
            cx = max(0, min(1, (bx + bw/2) / w))
            cy = max(0, min(1, (by + bh/2) / h))
            nw = max(0, min(1, bw / w))
            nh = max(0, min(1, bh / h))
            lines.append(f"{ann['category_id']} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
        label_path.write_text('\n'.join(lines))

    # Val: ONLY original images (no augmentation!)
    for iid in val_ids:
        info = IMG_LOOKUP[iid]
        src = DATA_DIR / 'images' / info['file_name']
        dst = out_dir / 'images' / 'val' / info['file_name']
        if not dst.exists():
            shutil.copy2(src, dst)
        write_labels(iid, info, ANNS_BY_IMAGE.get(iid, []), 'val')

    # Train: original + augmented
    for iid in train_ids:
        info = IMG_LOOKUP[iid]
        w, h = info['width'], info['height']
        fname = info['file_name']
        src = DATA_DIR / 'images' / fname
        dst = out_dir / 'images' / 'train' / fname
        if not dst.exists():
            shutil.copy2(src, dst)
        write_labels(iid, info, ANNS_BY_IMAGE.get(iid, []), 'train')

        if aug_multiplier <= 1:
            continue

        img = cv2.imread(str(src))
        if img is None:
            continue
        anns = ANNS_BY_IMAGE.get(iid, [])
        for ai in range(aug_multiplier - 1):
            aug_img, aug_anns = augment_image(img, anns, w, h)
            if use_crops and crop_dir:
                aug_img, aug_anns = inject_crops(aug_img, aug_anns, crop_dir, w, h)
            aug_fname = f'{Path(fname).stem}_aug{ai}.jpg'
            cv2.imwrite(str(out_dir / 'images' / 'train' / aug_fname), aug_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            write_labels(iid, info, aug_anns, 'train', aug_fname)

    # Write dataset.yaml
    yc = f'path: {out_dir.resolve()}\ntrain: images/train\nval: images/val\nnc: {NUM_CLASSES}\nnames:\n'
    for i in range(NUM_CLASSES):
        yc += f'  {i}: "{CLASS_NAMES.get(i, f"class_{i}")}"\n'
    (out_dir / 'dataset.yaml').write_text(yc)
    t = len(list((out_dir / 'images' / 'train').iterdir()))
    v = len(list((out_dir / 'images' / 'val').iterdir()))
    return str(out_dir / 'dataset.yaml'), t, v

# ─── Phase 1: K-fold ablation ────────────────────────────────────────────────
def phase1_ablation(crop_dir):
    print(f'\n{"=" * 60}')
    print(f'PHASE 1: K-FOLD ABLATION ({hours_left():.1f}h left)')
    print(f'{"=" * 60}')

    folds = create_kfold_splits(n_folds=3)
    configs = [
        {'name': 'aug4x_nocrop',  'aug_mult': 4,  'crops': False},
        {'name': 'aug8x_nocrop',  'aug_mult': 8,  'crops': False},
        {'name': 'aug4x_crop',    'aug_mult': 4,  'crops': True},
        {'name': 'aug8x_crop',    'aug_mult': 8,  'crops': True},
        {'name': 'aug16x_nocrop', 'aug_mult': 16, 'crops': False},
        {'name': 'aug16x_crop',   'aug_mult': 16, 'crops': True},
    ]

    results = {}
    for cfg in configs:
        if time_left() < 1800:
            print(f'Time limit approaching, skipping remaining configs')
            break

        fold_scores = []
        for fold_idx in range(len(folds)):
            val_ids = folds[fold_idx]
            train_ids = [iid for f_idx, f in enumerate(folds) for iid in f if f_idx != fold_idx]

            ds_dir = WORK_DIR / 'ablation' / f'{cfg["name"]}_fold{fold_idx}'
            if ds_dir.exists():
                shutil.rmtree(ds_dir)

            yaml_path, n_train, n_val = create_yolo_dataset(
                train_ids, val_ids, ds_dir,
                aug_multiplier=cfg['aug_mult'],
                use_crops=cfg['crops'],
                crop_dir=crop_dir if cfg['crops'] else None,
            )
            print(f'  {cfg["name"]} fold{fold_idx}: {n_train} train, {n_val} val')

            model = YOLO('yolo26x.pt')
            r = model.train(
                data=yaml_path, epochs=30, imgsz=640, batch=16, device='0',
                project='NM i ai', name=f'ablation-{cfg["name"]}-f{fold_idx}',
                exist_ok=True, seed=SEED, **AUG,
                lr0=0.000392, lrf=0.0136, weight_decay=0.00306,
                warmup_epochs=2.1, cls=0.987, box=8.34,
                optimizer='AdamW', dropout=0.21,
                save=False, val=True, patience=15, verbose=False,
            )
            score = float(r.results_dict.get('metrics/mAP50(B)', 0))
            fold_scores.append(score)
            print(f'  -> fold{fold_idx} mAP50={score:.4f}')

            # Cleanup to save disk
            shutil.rmtree(ds_dir, ignore_errors=True)

        avg = np.mean(fold_scores)
        std = np.std(fold_scores)
        results[cfg['name']] = {'avg': avg, 'std': std, 'scores': fold_scores}
        print(f'{cfg["name"]}: avg_mAP50={avg:.4f} ± {std:.4f}')

    # Find best config
    best_name = max(results, key=lambda k: results[k]['avg'])
    best_cfg = [c for c in configs if c['name'] == best_name][0]
    print(f'\nBest config: {best_name} (avg mAP50={results[best_name]["avg"]:.4f})')

    with open(WORK_DIR / 'ablation_results.json', 'w') as f:
        json.dump({k: {'avg': v['avg'], 'std': v['std']} for k, v in results.items()}, f, indent=2)

    return best_cfg, results

# ─── Phase 2: Optuna HP search ───────────────────────────────────────────────
def phase2_optuna(best_cfg, crop_dir):
    print(f'\n{"=" * 60}')
    print(f'PHASE 2: OPTUNA HP SEARCH ({hours_left():.1f}h left)')
    print(f'{"=" * 60}')

    import optuna
    folds = create_kfold_splits(n_folds=3)
    optuna_budget = min(3600, time_left() - 3 * 3600)  # Save 3h for phase 3
    if optuna_budget < 600:
        print('Not enough time for Optuna, using previous best params')
        return {'lr0': 0.000392, 'lrf': 0.0136, 'weight_decay': 0.00306,
                'warmup_epochs': 2.1, 'cls': 0.987, 'box': 8.34,
                'optimizer': 'AdamW', 'dropout': 0.21, 'imgsz': 800}

    def objective(trial):
        lr0 = trial.suggest_float('lr0', 1e-4, 0.005, log=True)
        lrf = trial.suggest_float('lrf', 0.005, 0.1, log=True)
        weight_decay = trial.suggest_float('weight_decay', 1e-5, 0.01, log=True)
        cls_gain = trial.suggest_float('cls', 0.3, 2.0)
        box_gain = trial.suggest_float('box', 5.0, 12.0)
        dropout = trial.suggest_float('dropout', 0.0, 0.35)
        imgsz = trial.suggest_categorical('imgsz', [640, 800])

        fold_scores = []
        for fold_idx in range(2):  # Only 2 folds for speed
            val_ids = folds[fold_idx]
            train_ids = [iid for fi, f in enumerate(folds) for iid in f if fi != fold_idx]
            ds_dir = WORK_DIR / 'optuna' / f'trial{trial.number}_f{fold_idx}'
            if ds_dir.exists(): shutil.rmtree(ds_dir)
            yaml_path, _, _ = create_yolo_dataset(
                train_ids, val_ids, ds_dir,
                aug_multiplier=best_cfg['aug_mult'],
                use_crops=best_cfg['crops'],
                crop_dir=crop_dir if best_cfg['crops'] else None,
            )
            model = YOLO('yolo26x.pt')
            r = model.train(
                data=yaml_path, epochs=25, imgsz=imgsz, batch=16, device='0',
                project='NM i ai', name=f'optuna-t{trial.number}-f{fold_idx}',
                exist_ok=True, seed=SEED, **AUG,
                lr0=lr0, lrf=lrf, weight_decay=weight_decay,
                warmup_epochs=2.1, cls=cls_gain, box=box_gain,
                optimizer='AdamW', dropout=dropout,
                save=False, val=True, patience=12, verbose=False,
            )
            fold_scores.append(float(r.results_dict.get('metrics/mAP50(B)', 0)))
            shutil.rmtree(ds_dir, ignore_errors=True)

        avg = np.mean(fold_scores)
        print(f'Trial {trial.number}: mAP50={avg:.4f} lr0={lr0:.6f} cls={cls_gain:.2f} box={box_gain:.2f} dropout={dropout:.2f} imgsz={imgsz}')
        return avg

    study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, timeout=optuna_budget, n_trials=30)

    print(f'Best trial: {study.best_trial.number}, mAP50={study.best_value:.4f}')
    print(f'Best params: {study.best_params}')

    with open(WORK_DIR / 'optuna_results.json', 'w') as f:
        json.dump({'best_value': study.best_value, 'best_params': study.best_params}, f, indent=2)

    bp = study.best_params
    bp.setdefault('optimizer', 'AdamW')
    bp.setdefault('warmup_epochs', 2.1)
    return bp

# ─── Phase 3: Final training on ALL data ─────────────────────────────────────
def phase3_final(best_hp, best_cfg, crop_dir):
    remaining = time_left()
    max_epochs = min(200, int(remaining / 60))  # ~60s per epoch estimate
    print(f'\n{"=" * 60}')
    print(f'PHASE 3: FINAL TRAINING ON ALL DATA ({max_epochs} epochs, {hours_left():.1f}h left)')
    print(f'Best HP: {best_hp}')
    print(f'Best aug config: {best_cfg["name"]}')
    print(f'{"=" * 60}')

    # ALL 248 images for training, NO validation holdout
    all_ids = sorted(IMG_LOOKUP.keys())
    # Small val set just for monitoring (10 images) — not for early stopping decisions
    rng = random.Random(SEED)
    monitor_ids = rng.sample(all_ids, 10)

    final_dir = WORK_DIR / 'final_dataset'
    if final_dir.exists(): shutil.rmtree(final_dir)
    yaml_path, n_train, n_val = create_yolo_dataset(
        all_ids, monitor_ids, final_dir,
        aug_multiplier=best_cfg['aug_mult'],
        use_crops=best_cfg['crops'],
        crop_dir=crop_dir if best_cfg['crops'] else None,
    )
    print(f'Final dataset: {n_train} train images, {n_val} monitor images')

    imgsz = best_hp.get('imgsz', 800)
    model = YOLO('yolo26x.pt')
    model.train(
        data=yaml_path, epochs=max_epochs, imgsz=imgsz, batch=16, device='0',
        project='NM i ai', name='FINAL-all-data',
        exist_ok=True, seed=SEED, **AUG,
        lr0=best_hp['lr0'], lrf=best_hp['lrf'],
        weight_decay=best_hp['weight_decay'],
        warmup_epochs=best_hp.get('warmup_epochs', 2.1),
        cls=best_hp['cls'], box=best_hp['box'],
        optimizer=best_hp.get('optimizer', 'AdamW'),
        dropout=best_hp.get('dropout', 0.21),
        save=True, save_period=20, val=True,
        patience=60,  # Very patient — we trust K-fold metrics
        multi_scale=0.5, cos_lr=True,
    )

    # Save and export
    best_pt_candidates = glob.glob(str(Path.home() / 'runs/detect/NM i ai/FINAL-all-data*/weights/best.pt'))
    if best_pt_candidates:
        dst = Path.home() / 'final_best.pt'
        shutil.copy2(best_pt_candidates[-1], dst)
        print(f'\nFINAL MODEL: {dst}')
        YOLO(str(dst)).export(format='onnx', imgsz=imgsz, opset=17, simplify=True)
        print(f'ONNX exported as final_best.onnx')

if __name__ == '__main__':
    print(f'OVERNIGHT V2 — 6.5h budget')
    print(f'Phase 1: K-fold ablation (aug sizes + product crops)')
    print(f'Phase 2: Optuna HP search with K-fold')
    print(f'Phase 3: Final training on ALL 248 images')
    print()

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    crop_dir = prepare_product_crops()
    best_cfg, ablation_results = phase1_ablation(crop_dir)
    best_hp = phase2_optuna(best_cfg, crop_dir)
    phase3_final(best_hp, best_cfg, crop_dir)

    print(f'\nDone! Total time: {(time.time()-START_TIME)/3600:.1f}h')
