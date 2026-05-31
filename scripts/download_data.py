"""Download the course PDF corpus from a Hugging Face dataset into data/raw/.

Usage:
    # Full dataset
    python scripts/download_data.py

    # Subset by explicit filenames
    python scripts/download_data.py --files Q4_oil.pdf renewables_2024.pdf

    # Subset from a newline-separated list file
    python scripts/download_data.py --files-from my_corpus.txt

    # Override the dataset
    python scripts/download_data.py --repo-id Altgan/rag-for-unstructured-data

Public datasets work anonymously. For private datasets, set HF_TOKEN in your
environment (or .env) or run `huggingface-cli login` first.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_REPO_ID = os.environ.get("HF_DATASET_REPO", "Altgan/rag-for-unstructured-data")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO_ROOT / "data" / "raw"


def _read_file_list(path: Path) -> list[str]:
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def _download_subset(repo_id: str, revision: str, files: list[str], target: Path, token: str | None) -> tuple[int, list[str]]:
    """Download a list of specific filenames. Returns (downloaded_count, missing_names)."""
    from huggingface_hub import HfApi, hf_hub_download

    available = {s.rfilename for s in HfApi().dataset_info(repo_id, revision=revision, token=token).siblings}
    missing = [f for f in files if f not in available]
    to_fetch = [f for f in files if f in available]

    for name in to_fetch:
        print(f"  fetching  {name}")
        hf_hub_download(
            repo_id=repo_id,
            filename=name,
            repo_type="dataset",
            revision=revision,
            local_dir=str(target),
            local_dir_use_symlinks=False,
            token=token,
        )
    return len(to_fetch), missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"Hugging Face dataset repo id (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"Local directory to populate (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--revision",
        default="main",
        help="Dataset branch / tag / commit to pull (default: main)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Specific filenames to download (relative to the dataset root). "
             "If omitted, the entire dataset is snapshot-downloaded.",
    )
    parser.add_argument(
        "--files-from",
        type=Path,
        default=None,
        help="Path to a text file with one filename per line. Lines starting with # are ignored.",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import snapshot_download  # noqa: F401  (import-test only)
    except ImportError:
        print(
            "ERROR: huggingface_hub is not installed.\n"
            "Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    args.target.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN") or None

    requested_files: list[str] = []
    if args.files:
        requested_files.extend(args.files)
    if args.files_from:
        if not args.files_from.exists():
            print(f"ERROR: --files-from path does not exist: {args.files_from}", file=sys.stderr)
            return 2
        requested_files.extend(_read_file_list(args.files_from))

    try:
        if requested_files:
            print(f"Downloading {len(requested_files)} file(s) from {args.repo_id}@{args.revision} -> {args.target}")
            fetched, missing = _download_subset(args.repo_id, args.revision, requested_files, args.target, token)
            print(f"Downloaded {fetched} of {len(requested_files)} requested file(s) -> {args.target}")
            if missing:
                print(f"WARNING: {len(missing)} file(s) not found in the dataset:", file=sys.stderr)
                for m in missing:
                    print(f"  - {m}", file=sys.stderr)
                return 1 if fetched == 0 else 0
        else:
            from huggingface_hub import snapshot_download

            print(f"Downloading FULL dataset {args.repo_id}@{args.revision} -> {args.target}")
            snapshot_download(
                repo_id=args.repo_id,
                repo_type="dataset",
                revision=args.revision,
                local_dir=str(args.target),
                local_dir_use_symlinks=False,
                token=token,
            )
    except Exception as exc:
        print(f"ERROR: download failed: {exc}", file=sys.stderr)
        print(
            "\nHints:\n"
            "  * Public dataset? Make sure the repo-id is correct.\n"
            "  * Private dataset? Set HF_TOKEN in your environment.\n"
            "  * Offline? Place the PDFs manually under data/raw/.\n",
            file=sys.stderr,
        )
        return 1

    pdfs = list(args.target.rglob("*.pdf"))
    print(f"Done. {len(pdfs)} PDF(s) available under {args.target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
