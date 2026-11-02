import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from brain import connect, sync

ROOT = Path(__file__).resolve().parent
IMPORTS = ROOT / "my-vault/pdf-imports"


def snapshots(filename):
    found = []
    for folder in sorted(IMPORTS.iterdir()) if IMPORTS.exists() else []:
        if not folder.is_dir() or folder.is_symlink():
            continue
        manifest = folder / "manifest.json"
        if not manifest.is_file() or manifest.is_symlink():
            continue
        item = json.loads(manifest.read_text(encoding="utf-8"))
        if item.get("source_file") == filename:
            found.append((folder, item))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()

    source = args.pdf.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("Choose an existing PDF.")

    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    # Validate existing manifests before making any changes.
    snapshots(source.name)

    subprocess.run(
        [sys.executable, str(ROOT / "import_pdf.py"), str(source)],
        cwd=ROOT,
        check=True
    )

    versions = snapshots(source.name)
    current = [
        folder for folder, item in versions
        if item.get("sha256") == digest
    ]
    if len(current) != 1:
        raise ValueError(
            "Could not identify one current snapshot. Nothing archived."
        )

    # Stop if the original changed during import.
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError("PDF changed during import. Rerun the command.")

    older = [
        folder for folder, item in versions
        if item.get("sha256") != digest
    ]

    if older:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = ROOT / "pdf-archive" / f"{stamp}-{uuid4().hex[:8]}"
        archive.mkdir(parents=True)

        for folder in older:
            shutil.move(str(folder), str(archive / folder.name))
            print(f"Archived older snapshot: {folder.name}")

        print(f"Archive location: {archive.relative_to(ROOT)}")

    with closing(connect(ROOT / "my-brain.sqlite", ROOT / "my-vault")) as db:
        status = sync(db, ROOT / "my-vault")

    print(f"\nOlder snapshots archived: {len(older)}")
    print(f"Current snapshot: {current[0].relative_to(ROOT)}")
    print(f"Index refresh: {json.dumps(status)}")
    print("Semantic embeddings will refresh on the next semantic search.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(
            f"Refresh stopped: {error}\n"
            "Review the output above; earlier steps may have completed."
        )
