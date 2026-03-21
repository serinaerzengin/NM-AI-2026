"""Overnight Optuna + Hail Mary: 6-hour budget to find the perfect model.

Strategy:
1. Phase 1 (3h): Optuna searches hyperparams — each trial trains 40 epochs on 1826 images
   ~20 trials, each ~8-10 min
2. Phase 2 (3h): Best params → full 200-epoch hail mary run

All runs logged to wandb with native ultralytics integration.
"""
import os, random, shutil, time
from pathlib import Path
import numpy as np, torch, wandb, optuna

os.environ['WANDB_API_KEY'] = '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'

SEED = 42
YOLO_DIR = Path.home() / 'hailmary_yolo'
YAML_PATH = str(YOLO_DIR / 'dataset.yaml')
START_TIME = time.time()
TOTAL_BUDGET = 6 * 3600  # 6 hours
OPTUNA_BUDGET = 3 * 3600  # 3 hours for search
BASE_MODEL = Path.home() / 'best_final.pt'

# Fixed augmentation params (already optimized)
AUG = {
    'mosaic': 0.5, 'mixup': 0.134, 'copy_paste': 0.182, 'scale': 0.206,
    'degrees': 9.64, 'shear': 1.94, 'hsv_h': 0.0286, 'hsv_s': 0.689,
    'hsv_v': 0.305, 'erasing': 0.345, 'flipud': 0.0, 'bgr': 0.003, 'close_mosaic': 15,
}

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)

wandb.login()

from ultralytics import YOLO, settings
settings.update({'wandb': True})


def time_left():
    return TOTAL_BUDGET - (time.time() - START_TIME)


def optuna_time_left():
    return OPTUNA_BUDGET - (time.time() - START_TIME)


def objective(trial):
    if optuna_time_left() < 300:  # less than 5 min left for optuna
        raise optuna.exceptions.OptunaError('Time budget exhausted')

    # Hyperparameter search space
    lr0 = trial.suggest_float('lr0', 5e-5, 0.01, log=True)
    lrf = trial.suggest_float('lrf', 0.005, 0.2, log=True)
    weight_decay = trial.suggest_float('weight_decay', 1e-5, 0.01, log=True)
    warmup_epochs = trial.suggest_float('warmup_epochs', 0.5, 5.0)
    cls_gain = trial.suggest_float('cls', 0.2, 3.0)
    box_gain = trial.suggest_float('box', 4.0, 12.0)
    batch = trial.suggest_categorical('batch', [8, 16])
    cos_lr = trial.suggest_categorical('cos_lr', [True, False])
    optimizer = trial.suggest_categorical('optimizer', ['AdamW', 'SGD'])
    imgsz = trial.suggest_categorical('imgsz', [640, 800])
    dropout = trial.suggest_float('dropout', 0.0, 0.3)

    model = YOLO(str(BASE_MODEL)) if BASE_MODEL.exists() else YOLO('yolo26x.pt')

    try:
        results = model.train(
            data=YAML_PATH,
            epochs=40, imgsz=imgsz, batch=batch, device='0',
            project='NM i ai', name=f'optuna-trial-{trial.number}',
            exist_ok=True, seed=SEED,
            lr0=lr0, lrf=lrf, weight_decay=weight_decay,
            warmup_epochs=warmup_epochs, cls=cls_gain, box=box_gain,
            optimizer=optimizer, cos_lr=cos_lr, dropout=dropout,
            **AUG,
            save=False, val=True, patience=15, verbose=True,
        )

        metrics = results.results_dict
        det_map = metrics.get('metrics/mAP50(B)', 0)
        # Competition score: 0.7 * detection + 0.3 * classification
        # For us mAP50 already combines both since model predicts classes
        score = float(det_map)

        print(f'Trial {trial.number}: mAP50={score:.4f} lr0={lr0:.6f} batch={batch} opt={optimizer} imgsz={imgsz}')
        return score

    except Exception as e:
        print(f'Trial {trial.number} failed: {e}')
        return 0.0


def phase1_optuna():
    print('=' * 60)
    print('PHASE 1: OPTUNA HYPERPARAMETER SEARCH (3h budget)')
    print('=' * 60)

    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=SEED),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10),
    )

    try:
        study.optimize(objective, timeout=OPTUNA_BUDGET, n_trials=50)
    except Exception as e:
        print(f'Optuna stopped: {e}')

    print(f'\nOptuna completed: {len(study.trials)} trials')
    print(f'Best trial: {study.best_trial.number}')
    print(f'Best mAP50: {study.best_value:.4f}')
    print(f'Best params: {study.best_params}')

    # Save best params
    import json
    with open(Path.home() / 'best_optuna_params.json', 'w') as f:
        json.dump({'best_value': study.best_value, 'best_params': study.best_params}, f, indent=2)

    return study.best_params


def phase2_hailmary(best_params):
    remaining = time_left()
    if remaining < 600:
        print('Not enough time for hail mary, skipping')
        return

    # Estimate epochs based on remaining time (~45s per epoch)
    max_epochs = min(300, int(remaining / 50))
    print(f'\n{"=" * 60}')
    print(f'PHASE 2: HAIL MARY with best params ({max_epochs} epochs, {remaining/3600:.1f}h left)')
    print(f'Best params: {best_params}')
    print(f'{"=" * 60}')

    model = YOLO(str(BASE_MODEL)) if BASE_MODEL.exists() else YOLO('yolo26x.pt')

    model.train(
        data=YAML_PATH,
        epochs=max_epochs,
        imgsz=best_params.get('imgsz', 640),
        batch=best_params.get('batch', 16),
        device='0',
        project='NM i ai', name='hail-mary-best-params',
        exist_ok=True, seed=SEED,
        lr0=best_params['lr0'],
        lrf=best_params['lrf'],
        weight_decay=best_params['weight_decay'],
        warmup_epochs=best_params['warmup_epochs'],
        cls=best_params['cls'],
        box=best_params['box'],
        optimizer=best_params.get('optimizer', 'AdamW'),
        cos_lr=best_params.get('cos_lr', True),
        dropout=best_params.get('dropout', 0.0),
        **AUG,
        save=True, save_period=20, val=True, patience=50,
        multi_scale=0.5,
    )

    best_pt = Path('NM i ai') / 'hail-mary-best-params' / 'weights' / 'best.pt'
    if best_pt.exists():
        dst = Path.home() / 'overnight_best.pt'
        shutil.copy2(best_pt, dst)
        print(f'\nFINAL BEST MODEL: {dst}')
        YOLO(str(dst)).export(format='onnx', imgsz=best_params.get('imgsz', 640), opset=17, simplify=True)
        print('ONNX exported as overnight_best.onnx!')
    else:
        # Try alternate path
        import glob
        pts = glob.glob(str(Path.home() / 'runs/detect/NM i ai/hail-mary-best-params*/weights/best.pt'))
        if pts:
            dst = Path.home() / 'overnight_best.pt'
            shutil.copy2(pts[-1], dst)
            print(f'FINAL BEST MODEL: {dst}')
            YOLO(str(dst)).export(format='onnx', imgsz=best_params.get('imgsz', 640), opset=17, simplify=True)


if __name__ == '__main__':
    print(f'Starting overnight run. Budget: 6 hours.')
    print(f'Phase 1: Optuna search (~3h)')
    print(f'Phase 2: Hail mary with best params (~3h)')
    print()

    best_params = phase1_optuna()
    phase2_hailmary(best_params)

    elapsed = (time.time() - START_TIME) / 3600
    print(f'\nDone! Total time: {elapsed:.1f}h')
