#!/usr/bin/env bash
# Download received task files from GCS to local received_tasks/ directory
# Usage:
#   bash download_tasks.sh              # Download ALL tasks
#   bash download_tasks.sh abc12345     # Download specific req_id

set -euo pipefail

BUCKET="gs://tripletex-task-files-1813"
LOCAL_DIR="$(dirname "$0")/received_tasks"

mkdir -p "$LOCAL_DIR"

if [ $# -ge 1 ]; then
    echo "Downloading task $1..."
    gsutil -m cp -r "$BUCKET/$1/" "$LOCAL_DIR/$1/"
else
    echo "Downloading all tasks from $BUCKET..."
    gsutil -m cp -r "$BUCKET/*" "$LOCAL_DIR/"
fi

echo ""
echo "Files saved to: $LOCAL_DIR"
ls -la "$LOCAL_DIR"
