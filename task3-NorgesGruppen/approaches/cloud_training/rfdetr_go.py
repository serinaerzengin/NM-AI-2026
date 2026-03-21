import os
os.environ['WANDB_API_KEY'] = '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'

import json
from pathlib import Path
from rfdetr import RFDETRLarge

WORK_DIR = Path.home() / 'rfdetr_run'
with open(Path.home() / 'train_data' / 'train' / 'annotations.json') as f:
    coco = json.load(f)
class_names = [cat['name'] for cat in coco['categories']]

print(f'RF-DETR Large — {len(class_names)} classes')

model = RFDETRLarge(num_classes=len(class_names))
model.train(
    dataset_dir=str(WORK_DIR / 'dataset'),
    epochs=300,
    batch_size='auto',
    grad_accum_steps=4,
    lr=1e-4,
    lr_encoder=1.5e-4,
    weight_decay=1e-4,
    warmup_epochs=3.0,
    multi_scale=True,
    use_ema=True,
    seed=42,
    output_dir=str(WORK_DIR / 'output'),
    checkpoint_interval=10,
    eval_interval=5,
    early_stopping=True,
    early_stopping_patience=50,
    early_stopping_min_delta=0.001,
    wandb=True,
    project='NM i ai',
    run='rfdetr-large-v2',
    class_names=class_names,
    log_per_class_metrics=False,
)

print('Exporting ONNX...')
model.export(str(WORK_DIR / 'rfdetr_best.onnx'))
print('DONE!')
