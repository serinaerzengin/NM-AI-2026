"""NorgesGruppen submission API — build zip and upload to competition."""

import os
import json
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).parent / ".env")

BASE = "https://api.ainm.no/norgesgruppen-data"
TASK_DIR = Path(__file__).parent

# Allowed file extensions in submission zip
ALLOWED_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".cfg", ".pt", ".pth", ".onnx", ".safetensors", ".npy"}
WEIGHT_EXTENSIONS = {".pt", ".pth", ".onnx", ".safetensors", ".npy"}
MAX_ZIP_SIZE = 420 * 1024 * 1024  # 420 MB uncompressed
MAX_WEIGHT_SIZE = 420 * 1024 * 1024  # 420 MB total weight files
MAX_FILES = 1000
MAX_PYTHON_FILES = 10
MAX_WEIGHT_FILES = 3


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def _session() -> requests.Session:
    token = os.environ.get("AINM_TOKEN", "")
    if not token:
        raise RuntimeError("Set AINM_TOKEN in .env or env var")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


SESSION: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global SESSION
    if SESSION is None:
        SESSION = _session()
    return SESSION


# ---------------------------------------------------------------------------
# Zip builder
# ---------------------------------------------------------------------------

def validate_submission(files: list[Path]) -> list[str]:
    """Validate files against submission constraints. Returns list of errors."""
    errors = []

    if not any(f.name == "run.py" for f in files):
        errors.append("run.py must be included at the zip root")

    py_files = [f for f in files if f.suffix == ".py"]
    weight_files = [f for f in files if f.suffix in WEIGHT_EXTENSIONS]

    if len(files) > MAX_FILES:
        errors.append(f"Too many files: {len(files)} > {MAX_FILES}")
    if len(py_files) > MAX_PYTHON_FILES:
        errors.append(f"Too many Python files: {len(py_files)} > {MAX_PYTHON_FILES}")
    if len(weight_files) > MAX_WEIGHT_FILES:
        errors.append(f"Too many weight files: {len(weight_files)} > {MAX_WEIGHT_FILES}")

    total_size = sum(f.stat().st_size for f in files)
    weight_size = sum(f.stat().st_size for f in weight_files)

    if total_size > MAX_ZIP_SIZE:
        errors.append(f"Total size {total_size / 1e6:.1f} MB > {MAX_ZIP_SIZE / 1e6:.0f} MB")
    if weight_size > MAX_WEIGHT_SIZE:
        errors.append(f"Weight size {weight_size / 1e6:.1f} MB > {MAX_WEIGHT_SIZE / 1e6:.0f} MB")

    for f in files:
        if f.suffix not in ALLOWED_EXTENSIONS:
            errors.append(f"Disallowed file type: {f.name}")

    return errors


def build_zip(
    model_path: Optional[str] = None,
    output_path: Optional[str] = None,
    extra_files: Optional[list[str]] = None,
) -> Path:
    """Build a submission zip with run.py + model weights.

    Args:
        model_path: Path to model weights (best.pt, model.onnx, etc.).
                    Defaults to best.pt or yolov8n.pt in task dir.
        output_path: Where to write the zip. Defaults to task_dir/submission.zip.
        extra_files: Additional .py/.json/.yaml files to include.

    Returns:
        Path to the created zip file.
    """
    run_py = TASK_DIR / "run.py"
    if not run_py.exists():
        raise FileNotFoundError(f"run.py not found at {run_py}")

    # Resolve model path
    models_dir = TASK_DIR / "models"
    if model_path:
        model = Path(model_path)
    else:
        model = models_dir / "best.pt"
        if not model.exists():
            model = models_dir / "yolov8n.pt"
    if not model.exists():
        raise FileNotFoundError(
            f"Model weights not found: {model}\n"
            "Place best.pt or yolov8n.pt in task3-NorgesGruppen/models/"
        )

    # Collect all files
    files = [run_py, model]
    if extra_files:
        for f in extra_files:
            p = Path(f)
            if p.exists():
                files.append(p)
            else:
                print(f"Warning: extra file not found: {f}")

    # Validate
    errors = validate_submission(files)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        raise ValueError(f"Submission validation failed with {len(errors)} error(s)")

    # Build zip
    if output_path is None:
        output_path = TASK_DIR / "submission.zip"
    output_path = Path(output_path)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            # Preserve models/ subfolder for weight files, flat for everything else
            if f.parent.name == "models":
                arcname = f"models/{f.name}"
            else:
                arcname = f.name
            zf.write(f, arcname)
            print(f"  Added: {arcname} ({f.stat().st_size / 1e6:.2f} MB)")

    print(f"\nCreated {output_path} ({output_path.stat().st_size / 1e6:.2f} MB)")
    return output_path


# ---------------------------------------------------------------------------
# Submission endpoints
# ---------------------------------------------------------------------------

def submit(zip_path: Optional[str] = None) -> dict:
    """Upload a submission zip to the competition.

    Args:
        zip_path: Path to the zip file. Defaults to task_dir/submission.zip.

    Returns:
        Response JSON from the server.
    """
    if zip_path is None:
        zip_path = TASK_DIR / "submission.zip"
    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise FileNotFoundError(
            f"Zip not found: {zip_path}\nRun build_zip() first."
        )

    print(f"Uploading {zip_path.name} ({zip_path.stat().st_size / 1e6:.2f} MB)...")

    with open(zip_path, "rb") as f:
        r = get_session().post(
            f"{BASE}/submit",
            files={"file": (zip_path.name, f, "application/zip")},
        )
    r.raise_for_status()
    result = r.json()
    print(f"Submission response: {json.dumps(result, indent=2)}")
    return result


def get_submissions() -> list[dict]:
    """GET /submissions — List your submission history."""
    r = get_session().get(f"{BASE}/submissions")
    r.raise_for_status()
    return r.json()


def get_submission(submission_id: str) -> dict:
    """GET /submissions/{id} — Get status/score for a submission."""
    r = get_session().get(f"{BASE}/submissions/{submission_id}")
    r.raise_for_status()
    return r.json()


def get_leaderboard() -> list[dict]:
    """GET /leaderboard — Public leaderboard."""
    r = get_session().get(f"{BASE}/leaderboard")
    r.raise_for_status()
    return r.json()


def select_for_final(submission_id: str) -> dict:
    """POST /submissions/{id}/select — Select a submission for final evaluation."""
    r = get_session().post(f"{BASE}/submissions/{submission_id}/select")
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Convenience: build + submit in one call
# ---------------------------------------------------------------------------

def build_and_submit(
    model_path: Optional[str] = None,
    extra_files: Optional[list[str]] = None,
) -> dict:
    """Build the submission zip and upload it.

    Args:
        model_path: Path to model weights.
        extra_files: Additional files to include.

    Returns:
        Submission response from server.
    """
    zip_path = build_zip(model_path=model_path, extra_files=extra_files)
    return submit(str(zip_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NorgesGruppen submission tool")
    sub = parser.add_subparsers(dest="command")

    # build
    build_p = sub.add_parser("build", help="Build submission zip")
    build_p.add_argument("--model", help="Path to model weights")
    build_p.add_argument("--output", help="Output zip path")
    build_p.add_argument("--extra", nargs="*", help="Extra files to include")

    # submit
    submit_p = sub.add_parser("submit", help="Upload submission zip")
    submit_p.add_argument("--zip", help="Path to zip file")

    # build+submit
    bs_p = sub.add_parser("go", help="Build and submit in one step")
    bs_p.add_argument("--model", help="Path to model weights")
    bs_p.add_argument("--extra", nargs="*", help="Extra files to include")

    # status
    sub.add_parser("status", help="List submissions")
    sub.add_parser("leaderboard", help="Show leaderboard")

    args = parser.parse_args()

    if args.command == "build":
        build_zip(model_path=args.model, output_path=args.output, extra_files=args.extra)
    elif args.command == "submit":
        submit(zip_path=args.zip)
    elif args.command == "go":
        build_and_submit(model_path=args.model, extra_files=args.extra)
    elif args.command == "status":
        subs = get_submissions()
        for s in subs:
            print(json.dumps(s, indent=2))
    elif args.command == "leaderboard":
        lb = get_leaderboard()
        for entry in lb:
            print(json.dumps(entry, indent=2))
    else:
        parser.print_help()
