"""Full pipeline: Data ablation → K-fold ensemble → Full data model.

Phase 1 (2-3h): Ablation on data/augmentation strategies with 3-fold CV
  - Test: 1x, 4x, 8x, 16x augmentation multipliers
  - Test: with/without product crop injection
  - Test: with/without horizontal flip in offline aug
  - Fixed model HPs throughout (already proven)

Phase 2 (3-4h): K-fold ensemble + full data with winning data recipe
  - 5-fold ensemble: train 5 models on different folds
  - 1 full-data model: all 248 images + augmented
  - Export all to ONNX

All logged to wandb.
"""
import os, json, random, shutil, copy, time, glob
from pathlib import Path
import numpy as np, cv2, torch

os.environ['WANDB_API_KEY'] = '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'

SEED = 42
DATA_DIR = Path.home() / 'train_data' / 'train'
WORK_DIR = Path.home() / 'pipeline_v3'
CROP_DIR = Path.home() / 'overnight_v2' / 'product_crops'  # already prepared
START_TIME = time.time()
TOTAL_BUDGET = 7 * 3600  # 7 hours

# Proven model HPs — DO NOT CHANGE
MODEL_HP = {
    'lr0': 0.0003920379472728676,
    'lrf': 0.013604651830782358,
    'weight_decay': 0.003063462210622081,
    'warmup_epochs': 2.105,
    'cls': 0.9866,
    'box': 8.3416,
    'optimizer': 'AdamW',
    'dropout': 0.212,
    'imgsz': 800,
}

# Fixed augmentation params for YOLO online aug
ONLINE_AUG = {
    'mosaic': 0.5, 'mixup': 0.134, 'copy_paste': 0.182, 'scale': 0.206,
    'degrees': 9.64, 'shear': 1.94, 'hsv_h': 0.0286, 'hsv_s': 0.689,
    'hsv_v': 0.305, 'erasing': 0.345, 'flipud': 0.0, 'bgr': 0.003,
    'close_mosaic': 5,
}

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
import wandb; wandb.login()
from ultralytics import YOLO, settings
settings.update({'wandb': True})

# Load COCO
with open(DATA_DIR / 'annotations.json') as f:
    COCO = json.load(f)
IMG_LOOKUP = {img['id']: img for img in COCO['images']}
ANNS_BY_IMAGE = {}
for ann in COCO['annotations']:
    ANNS_BY_IMAGE.setdefault(ann['image_id'], []).append(ann)
NUM_CLASSES = len(COCO['categories'])
CLASS_NAMES = {cat['id']: cat['name'] for cat in COCO['categories']}

def time_left(): return TOTAL_BUDGET - (time.time() - START_TIME)
def hours_left(): return time_left() / 3600

# ─── Augmentation functions ──────────────────────────────────────────────────
def apply_hsv(img, h=0.0286, s=0.689, v=0.305):
    r = np.random.uniform(-1, 1, 3) * [h, s, v] + 1
    hue, sat, val = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HSV))
    x = np.arange(0, 256, dtype=r.dtype)
    return cv2.cvtColor(cv2.merge((
        cv2.LUT(hue, ((x*r[0])%180).astype(np.uint8)),
        cv2.LUT(sat, np.clip(x*r[1],0,255).astype(np.uint8)),
        cv2.LUT(val, np.clip(x*r[2],0,255).astype(np.uint8))
    )), cv2.COLOR_HSV2BGR)

def augment_image(img, anns, w, h, do_flip=True):
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
    if do_flip and random.random()<0.5:
        a=np.fliplr(a).copy()
        for ann in new_anns: ann['bbox'][0]=w-ann['bbox'][0]-ann['bbox'][2]
    if random.random()<0.345:
        area = random.uniform(0.02,0.2)*h*w
        eh=int(np.sqrt(area*random.uniform(0.5,2))); ew=int(np.sqrt(area/random.uniform(0.5,2)))
        if 0<eh<h and 0<ew<w:
            y0,x0=random.randint(0,h-eh),random.randint(0,w-ew)
            a[y0:y0+eh,x0:x0+ew]=np.random.randint(0,255,(eh,ew,3),dtype=np.uint8)
    return a, new_anns

def inject_crops(img, anns, w, h, n_inject=3):
    crops = list(CROP_DIR.glob('*.png'))
    if not crops: return img, anns
    a = img.copy(); aa = copy.deepcopy(anns)
    for _ in range(n_inject):
        crop = cv2.imread(str(random.choice(crops)), cv2.IMREAD_UNCHANGED)
        if crop is None or len(crop.shape)<3 or crop.shape[2]<4: continue
        th = random.randint(30,200); sc=th/crop.shape[0]; tw=int(crop.shape[1]*sc)
        if tw<10 or w-tw<=0 or h-th<=0: continue
        crop = cv2.resize(crop, (tw, th))
        x0,y0 = random.randint(0,w-tw), random.randint(0,h-th)
        alpha = crop[:,:,3:4].astype(np.float32)/255.0
        a[y0:y0+th,x0:x0+tw] = (crop[:,:,:3].astype(np.float32)*alpha + a[y0:y0+th,x0:x0+tw].astype(np.float32)*(1-alpha)).astype(np.uint8)
        aa.append({'id':random.randint(100000,999999),'image_id':-1,'category_id':random.randint(0,NUM_CLASSES-1),'bbox':[x0,y0,tw,th],'area':tw*th,'iscrowd':0})
    return a, aa

# ─── Dataset creation ────────────────────────────────────────────────────────
def create_dataset(train_ids, val_ids, out_dir, aug_mult=1, use_crops=False):
    if out_dir.exists(): shutil.rmtree(out_dir)
    for sp in ('train','val'):
        (out_dir/'images'/sp).mkdir(parents=True, exist_ok=True)
        (out_dir/'labels'/sp).mkdir(parents=True, exist_ok=True)

    def write_labels(info, anns, sp, fname=None):
        w, h = info['width'], info['height']
        if fname is None: fname = info['file_name']
        lines = []
        for ann in anns:
            if ann.get('iscrowd',0): continue
            bx,by,bw,bh = ann['bbox']
            lines.append(f"{ann['category_id']} {max(0,min(1,(bx+bw/2)/w)):.6f} {max(0,min(1,(by+bh/2)/h)):.6f} {max(0,min(1,bw/w)):.6f} {max(0,min(1,bh/h)):.6f}")
        (out_dir/'labels'/sp/f'{Path(fname).stem}.txt').write_text('\n'.join(lines))

    for iid in val_ids:
        info = IMG_LOOKUP[iid]
        dst = out_dir/'images'/'val'/info['file_name']
        if not dst.exists(): shutil.copy2(DATA_DIR/'images'/info['file_name'], dst)
        write_labels(info, ANNS_BY_IMAGE.get(iid,[]), 'val')

    for iid in train_ids:
        info = IMG_LOOKUP[iid]; w,h = info['width'],info['height']; fname = info['file_name']
        dst = out_dir/'images'/'train'/fname
        if not dst.exists(): shutil.copy2(DATA_DIR/'images'/fname, dst)
        write_labels(info, ANNS_BY_IMAGE.get(iid,[]), 'train')
        if aug_mult <= 1: continue
        img = cv2.imread(str(DATA_DIR/'images'/fname))
        if img is None: continue
        anns = ANNS_BY_IMAGE.get(iid,[])
        for ai in range(aug_mult - 1):
            aug_img, aug_anns = augment_image(img, anns, w, h)
            if use_crops:
                aug_img, aug_anns = inject_crops(aug_img, aug_anns, w, h)
            af = f'{Path(fname).stem}_aug{ai}.jpg'
            cv2.imwrite(str(out_dir/'images'/'train'/af), aug_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            write_labels(info, aug_anns, 'train', af)

    yc = f'path: {out_dir.resolve()}\ntrain: images/train\nval: images/val\nnc: {NUM_CLASSES}\nnames:\n'
    for i in range(NUM_CLASSES): yc += f'  {i}: "{CLASS_NAMES.get(i, f"class_{i}")}"\n'
    (out_dir/'dataset.yaml').write_text(yc)
    t = len(list((out_dir/'images'/'train').iterdir()))
    v = len(list((out_dir/'images'/'val').iterdir()))
    return str(out_dir/'dataset.yaml'), t, v

def train_model(yaml_path, name, epochs=30, patience=15, save=False):
    model = YOLO('yolo26x.pt')
    r = model.train(
        data=yaml_path, epochs=epochs, imgsz=MODEL_HP['imgsz'],
        batch=16, device='0',
        project='NM i ai', name=name, exist_ok=True, seed=SEED,
        **ONLINE_AUG,
        lr0=MODEL_HP['lr0'], lrf=MODEL_HP['lrf'],
        weight_decay=MODEL_HP['weight_decay'],
        warmup_epochs=MODEL_HP['warmup_epochs'],
        cls=MODEL_HP['cls'], box=MODEL_HP['box'],
        optimizer=MODEL_HP['optimizer'], dropout=MODEL_HP['dropout'],
        save=save, val=True, patience=patience, verbose=False,
        cos_lr=True,
    )
    return r

# ─── K-fold split ────────────────────────────────────────────────────────────
def make_folds(n_folds=3):
    ids = sorted(IMG_LOOKUP.keys())
    rng = random.Random(SEED); rng.shuffle(ids)
    folds = [[] for _ in range(n_folds)]
    for i, iid in enumerate(ids):
        folds[i % n_folds].append(iid)
    return folds

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: DATA ABLATION
# ═══════════════════════════════════════════════════════════════════════════════
def phase1():
    print(f'\n{"=" * 60}')
    print(f'PHASE 1: DATA/AUGMENTATION ABLATION ({hours_left():.1f}h left)')
    print(f'{"=" * 60}')

    folds = make_folds(n_folds=3)

    configs = [
        {'name': '1x_nocrop',   'aug': 1,  'crops': False},   # 248 images (baseline)
        {'name': '4x_nocrop',   'aug': 4,  'crops': False},   # ~990 images
        {'name': '4x_crop',     'aug': 4,  'crops': True},    # ~990 + product crops
        {'name': '8x_nocrop',   'aug': 8,  'crops': False},   # ~1980 images
        {'name': '8x_crop',     'aug': 8,  'crops': True},    # ~1980 + product crops
        {'name': '16x_nocrop',  'aug': 16, 'crops': False},   # ~3960 images
        {'name': '16x_crop',    'aug': 16, 'crops': True},    # ~3960 + product crops
    ]

    results = {}
    for cfg in configs:
        if time_left() < 4 * 3600:  # Save 4h for Phase 2
            print(f'Time limit: skipping remaining configs')
            break

        fold_scores = []
        for fi in range(len(folds)):
            val_ids = folds[fi]
            train_ids = [iid for fj, f in enumerate(folds) for iid in f if fj != fi]
            ds_dir = WORK_DIR / 'ablation' / f'{cfg["name"]}_f{fi}'
            yaml_path, nt, nv = create_dataset(train_ids, val_ids, ds_dir, cfg['aug'], cfg['crops'])
            print(f'  {cfg["name"]} fold{fi}: {nt} train, {nv} val')
            r = train_model(yaml_path, f'abl-{cfg["name"]}-f{fi}', epochs=30, patience=15)
            score = float(r.results_dict.get('metrics/mAP50(B)', 0))
            fold_scores.append(score)
            print(f'  -> fold{fi} mAP50={score:.4f}')
            shutil.rmtree(ds_dir, ignore_errors=True)  # cleanup disk

        avg = np.mean(fold_scores); std = np.std(fold_scores)
        results[cfg['name']] = {'avg': avg, 'std': std, 'scores': fold_scores,
                                 'aug': cfg['aug'], 'crops': cfg['crops']}
        print(f'>>> {cfg["name"]}: avg={avg:.4f} ± {std:.4f}  (images per fold: ~{cfg["aug"]*165})')

    best_name = max(results, key=lambda k: results[k]['avg'])
    print(f'\nBEST DATA CONFIG: {best_name} (avg mAP50={results[best_name]["avg"]:.4f})')
    with open(WORK_DIR / 'ablation_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    return results[best_name]

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: K-FOLD ENSEMBLE + FULL DATA
# ═══════════════════════════════════════════════════════════════════════════════
def phase2(best_data):
    N_FOLDS = 5
    aug_mult = best_data['aug']
    use_crops = best_data['crops']

    remaining_h = hours_left()
    # Budget: ~35min per fold model (80 epochs) + ~50min for full data = ~4.5h total
    epochs_per_fold = min(80, int(remaining_h * 60 / (N_FOLDS + 2)))
    full_epochs = min(120, epochs_per_fold * 2)

    print(f'\n{"=" * 60}')
    print(f'PHASE 2: K-FOLD ENSEMBLE + FULL DATA ({remaining_h:.1f}h left)')
    print(f'Config: aug={aug_mult}x, crops={use_crops}')
    print(f'Epochs: {epochs_per_fold}/fold, {full_epochs}/full')
    print(f'{"=" * 60}')

    all_ids = sorted(IMG_LOOKUP.keys())
    rng = random.Random(SEED); rng.shuffle(all_ids)
    folds = [[] for _ in range(N_FOLDS)]
    for i, iid in enumerate(all_ids):
        folds[i % N_FOLDS].append(iid)

    fold_models = []

    # Train 5 fold models
    for fi in range(N_FOLDS):
        if time_left() < 3600:
            print(f'Time limit: skipping remaining folds')
            break
        print(f'\n--- FOLD {fi+1}/{N_FOLDS} ---')
        val_ids = folds[fi]
        train_ids = [iid for fj, f in enumerate(folds) for iid in f if fj != fi]
        ds_dir = WORK_DIR / f'ensemble_f{fi}'
        yaml_path, nt, nv = create_dataset(train_ids, val_ids, ds_dir, aug_mult, use_crops)
        print(f'  {nt} train, {nv} val')

        model = YOLO('yolo26x.pt')
        model.train(
            data=yaml_path, epochs=epochs_per_fold, imgsz=MODEL_HP['imgsz'],
            batch=16, device='0',
            project='NM i ai', name=f'ensemble-f{fi}', exist_ok=True,
            seed=SEED + fi, **ONLINE_AUG,
            lr0=MODEL_HP['lr0'], lrf=MODEL_HP['lrf'],
            weight_decay=MODEL_HP['weight_decay'],
            warmup_epochs=MODEL_HP['warmup_epochs'],
            cls=MODEL_HP['cls'], box=MODEL_HP['box'],
            optimizer=MODEL_HP['optimizer'], dropout=MODEL_HP['dropout'],
            save=True, val=True, patience=25, cos_lr=True, multi_scale=0.3,
        )
        best_pt = glob.glob(str(Path.home() / f'runs/detect/NM i ai/ensemble-f{fi}*/weights/best.pt'))
        if best_pt:
            dst = WORK_DIR / f'fold{fi}.pt'
            shutil.copy2(best_pt[-1], dst)
            YOLO(str(dst)).export(format='onnx', imgsz=MODEL_HP['imgsz'], opset=17, simplify=True)
            fold_models.append(str(WORK_DIR / f'fold{fi}.onnx'))
            print(f'  Exported: fold{fi}.onnx')

    # Full data model (ALL 248 images + augmented)
    if time_left() > 1800:
        print(f'\n--- FULL DATA MODEL ---')
        monitor = random.Random(SEED).sample(all_ids, 10)
        ds_dir = WORK_DIR / 'full_data'
        yaml_path, nt, nv = create_dataset(all_ids, monitor, ds_dir, aug_mult, use_crops)
        print(f'  {nt} train (ALL data + augmented), {nv} monitor')

        model = YOLO('yolo26x.pt')
        model.train(
            data=yaml_path, epochs=full_epochs, imgsz=MODEL_HP['imgsz'],
            batch=16, device='0',
            project='NM i ai', name='full-data', exist_ok=True,
            seed=SEED, **ONLINE_AUG,
            lr0=MODEL_HP['lr0'], lrf=MODEL_HP['lrf'],
            weight_decay=MODEL_HP['weight_decay'],
            warmup_epochs=MODEL_HP['warmup_epochs'],
            cls=MODEL_HP['cls'], box=MODEL_HP['box'],
            optimizer=MODEL_HP['optimizer'], dropout=MODEL_HP['dropout'],
            save=True, save_period=20, val=True, patience=50,
            cos_lr=True, multi_scale=0.3,
        )
        best_pt = glob.glob(str(Path.home() / 'runs/detect/NM i ai/full-data*/weights/best.pt'))
        if best_pt:
            dst = WORK_DIR / 'full.pt'
            shutil.copy2(best_pt[-1], dst)
            YOLO(str(dst)).export(format='onnx', imgsz=MODEL_HP['imgsz'], opset=17, simplify=True)
            fold_models.append(str(WORK_DIR / 'full.onnx'))
            print(f'  Exported: full.onnx')

    with open(WORK_DIR / 'ensemble_models.json', 'w') as f:
        json.dump({'models': fold_models, 'imgsz': MODEL_HP['imgsz'],
                   'aug_mult': aug_mult, 'use_crops': use_crops}, f, indent=2)

    print(f'\n{"=" * 60}')
    print(f'ENSEMBLE READY: {len(fold_models)} models')
    for m in fold_models: print(f'  {m}')
    print(f'{"=" * 60}')

if __name__ == '__main__':
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    print(f'FULL PIPELINE — {TOTAL_BUDGET/3600:.0f}h budget')
    print(f'Phase 1: Data ablation (1x/4x/8x/16x × crop/nocrop)')
    print(f'Phase 2: K-fold ensemble + full data with best recipe')
    print()
    best_data = phase1()
    phase2(best_data)
    print(f'\nTotal time: {(time.time()-START_TIME)/3600:.1f}h')
