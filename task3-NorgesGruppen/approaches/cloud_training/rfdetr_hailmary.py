"""RF-DETR Large hail mary: proven augmented data + tuned-equivalent HPs.

Uses 8x augmented dataset (~1980 images) with product crop injection.
RF-DETR Large with early stopping (patience=50 epochs).
"""
import os, json, random, shutil, copy
from pathlib import Path
import numpy as np, cv2, torch

os.environ['WANDB_API_KEY'] = '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'

SEED = 42
DATA_DIR = Path.home() / 'train_data' / 'train'
CROP_DIR = Path.home() / 'overnight_v2' / 'product_crops'
WORK_DIR = Path.home() / 'rfdetr_run'
AUG_MULT = 8

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

# Load COCO
with open(DATA_DIR / 'annotations.json') as f:
    COCO = json.load(f)
IMG_LOOKUP = {img['id']: img for img in COCO['images']}
ANNS_BY_IMAGE = {}
for ann in COCO['annotations']:
    ANNS_BY_IMAGE.setdefault(ann['image_id'], []).append(ann)
NUM_CLASSES = len(COCO['categories'])
CLASS_NAMES = {cat['id']: cat['name'] for cat in COCO['categories']}

# ─── Augmentation ─────────────────────────────────────────────────────────────
def apply_hsv(img):
    r = np.random.uniform(-1, 1, 3) * [0.0286, 0.689, 0.305] + 1
    hue, sat, val = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HSV))
    x = np.arange(0, 256, dtype=r.dtype)
    return cv2.cvtColor(cv2.merge((
        cv2.LUT(hue, ((x*r[0])%180).astype(np.uint8)),
        cv2.LUT(sat, np.clip(x*r[1],0,255).astype(np.uint8)),
        cv2.LUT(val, np.clip(x*r[2],0,255).astype(np.uint8))
    )), cv2.COLOR_HSV2BGR)

def augment_image(img, anns, w, h):
    a = apply_hsv(img.copy())
    angle = random.uniform(-9.64, 9.64); s = random.uniform(0.794, 1.206)
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, s)
    a = cv2.warpAffine(a, M, (w, h), borderValue=(114, 114, 114))
    new_anns = []
    for ann in copy.deepcopy(anns):
        bx,by,bw,bh = ann['bbox']
        corners = np.array([[bx,by,1],[bx+bw,by,1],[bx+bw,by+bh,1],[bx,by+bh,1]], dtype=np.float64)
        t = (M @ corners.T).T
        nx,ny = max(0,float(t[:,0].min())), max(0,float(t[:,1].min()))
        nx2,ny2 = min(w,float(t[:,0].max())), min(h,float(t[:,1].max()))
        if nx2-nx>5 and ny2-ny>5:
            ann['bbox']=[nx,ny,nx2-nx,ny2-ny]; new_anns.append(ann)
    if random.random()<0.5:
        a=np.fliplr(a).copy()
        for ann in new_anns: ann['bbox'][0]=w-ann['bbox'][0]-ann['bbox'][2]
    if random.random()<0.345:
        area = random.uniform(0.02,0.2)*h*w
        eh=int(np.sqrt(area*random.uniform(0.5,2))); ew=int(np.sqrt(area/random.uniform(0.5,2)))
        if 0<eh<h and 0<ew<w:
            y0,x0=random.randint(0,h-eh),random.randint(0,w-ew)
            a[y0:y0+eh,x0:x0+ew]=np.random.randint(0,255,(eh,ew,3),dtype=np.uint8)
    return a, new_anns

def inject_crops(img, anns, w, h, n=3):
    crops = list(CROP_DIR.glob('*.png'))
    if not crops: return img, anns
    a = img.copy(); aa = copy.deepcopy(anns)
    for _ in range(n):
        crop = cv2.imread(str(random.choice(crops)), cv2.IMREAD_UNCHANGED)
        if crop is None or len(crop.shape)<3 or crop.shape[2]<4: continue
        th=random.randint(30,200); sc=th/crop.shape[0]; tw=int(crop.shape[1]*sc)
        if tw<10 or w-tw<=0 or h-th<=0: continue
        crop = cv2.resize(crop, (tw, th))
        x0,y0 = random.randint(0,w-tw), random.randint(0,h-th)
        alpha = crop[:,:,3:4].astype(np.float32)/255.0
        a[y0:y0+th,x0:x0+tw] = (crop[:,:,:3].astype(np.float32)*alpha + a[y0:y0+th,x0:x0+tw].astype(np.float32)*(1-alpha)).astype(np.uint8)
        aa.append({'id':random.randint(100000,999999),'image_id':-1,'category_id':random.randint(0,NUM_CLASSES-1),'bbox':[x0,y0,tw,th],'area':tw*th,'iscrowd':0})
    return a, aa

# ─── Create COCO dataset for RF-DETR ─────────────────────────────────────────
def create_coco_dataset(train_ids, val_ids, out_dir):
    """RF-DETR uses COCO format natively (not YOLO format)."""
    if out_dir.exists(): shutil.rmtree(out_dir)
    for sp in ('train', 'valid'):
        (out_dir / sp).mkdir(parents=True, exist_ok=True)

    # Val: only originals
    val_images = []
    val_anns = []
    ann_id = 1
    for iid in val_ids:
        info = IMG_LOOKUP[iid]
        shutil.copy2(DATA_DIR / 'images' / info['file_name'], out_dir / 'valid' / info['file_name'])
        val_images.append({'id': iid, 'file_name': info['file_name'], 'width': info['width'], 'height': info['height']})
        for ann in ANNS_BY_IMAGE.get(iid, []):
            va = copy.deepcopy(ann); va['id'] = ann_id; ann_id += 1
            val_anns.append(va)

    # Train: originals + augmented with crop injection
    train_images = []
    train_anns = []
    next_img_id = max(IMG_LOOKUP.keys()) + 1
    for iid in train_ids:
        info = IMG_LOOKUP[iid]; w,h = info['width'],info['height']
        fname = info['file_name']
        shutil.copy2(DATA_DIR / 'images' / fname, out_dir / 'train' / fname)
        train_images.append({'id': iid, 'file_name': fname, 'width': w, 'height': h})
        for ann in ANNS_BY_IMAGE.get(iid, []):
            ta = copy.deepcopy(ann); ta['id'] = ann_id; ann_id += 1
            train_anns.append(ta)

        # Augment
        img = cv2.imread(str(DATA_DIR / 'images' / fname))
        if img is None: continue
        anns = ANNS_BY_IMAGE.get(iid, [])
        for ai in range(AUG_MULT - 1):
            aug_img, aug_anns = augment_image(img, anns, w, h)
            aug_img, aug_anns = inject_crops(aug_img, aug_anns, w, h)
            af = f'{Path(fname).stem}_aug{ai}.jpg'
            cv2.imwrite(str(out_dir / 'train' / af), aug_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            train_images.append({'id': next_img_id, 'file_name': af, 'width': w, 'height': h})
            for ann in aug_anns:
                ta = copy.deepcopy(ann); ta['id'] = ann_id; ta['image_id'] = next_img_id
                ann_id += 1; train_anns.append(ta)
            next_img_id += 1

    # Write COCO JSON annotations
    cats = COCO['categories']
    with open(out_dir / 'train' / '_annotations.coco.json', 'w') as f:
        json.dump({'images': train_images, 'annotations': train_anns, 'categories': cats}, f)
    with open(out_dir / 'valid' / '_annotations.coco.json', 'w') as f:
        json.dump({'images': val_images, 'annotations': val_anns, 'categories': cats}, f)

    print(f'  Train: {len(train_images)} images, {len(train_anns)} annotations')
    print(f'  Val: {len(val_images)} images, {len(val_anns)} annotations')
    return str(out_dir)

def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Use ALL 248 images for training, small monitor set for val
    all_ids = sorted(IMG_LOOKUP.keys())
    rng = random.Random(SEED); rng.shuffle(all_ids)
    val_ids = all_ids[:20]  # 20 images for monitoring
    train_ids = all_ids  # ALL images for training (including val ones — maximize data)

    print('=== RF-DETR Large Hail Mary ===')
    print(f'Creating augmented COCO dataset (ALL {len(train_ids)} images × {AUG_MULT}x aug + product crops)...')
    dataset_dir = create_coco_dataset(train_ids, val_ids, WORK_DIR / 'dataset')

    print('\nStarting RF-DETR Large training...')
    from rfdetr import RFDETRLarge

    model = RFDETRLarge()
    model.train(
        dataset_dir=dataset_dir,
        epochs=300,
        batch_size='auto',
        grad_accum_steps=4,
        lr=1e-4,
        lr_encoder=1.5e-4,
        weight_decay=1e-4,
        warmup_epochs=3.0,
        multi_scale=True,
        expanded_scales=True,
        use_ema=True,
        seed=SEED,
        output_dir=str(WORK_DIR / 'output'),
        checkpoint_interval=10,
        # Early stopping
        early_stopping=True,
        early_stopping_patience=50,
        early_stopping_min_delta=0.001,
        # Logging
        wandb=True,
        project='NM i ai',
        run='rfdetr-large-hailmary',
        # Class names for wandb
        class_names=[CLASS_NAMES.get(i, f'class_{i}') for i in range(NUM_CLASSES)],
    )

    # Export to ONNX
    print('\nExporting to ONNX...')
    # Load best checkpoint
    import glob
    ckpts = sorted(glob.glob(str(WORK_DIR / 'output' / 'checkpoint_best*.pth')))
    if ckpts:
        print(f'Best checkpoint: {ckpts[-1]}')

    model.export(str(WORK_DIR / 'rfdetr_best.onnx'))
    print(f'Exported: {WORK_DIR / "rfdetr_best.onnx"}')
    print('\nDONE!')

if __name__ == '__main__':
    main()
