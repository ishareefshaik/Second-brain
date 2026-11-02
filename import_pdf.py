import argparse
import hashlib
import io
import json
import re
import shutil
import tempfile
import textwrap
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()

    source = args.pdf.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("Choose an existing PDF file.")

    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", source.stem).strip("-")
    slug = (slug or "document")[:60]

    destination = ROOT / "my-vault/pdf-imports" / f"{slug}-{digest[:12]}"

    if destination.exists():
        manifest = json.loads(
            (destination / "manifest.json").read_text(encoding="utf-8")
        )
        if manifest["sha256"] != digest:
            raise ValueError("Import identifier conflict. No changes made.")
        print("This PDF snapshot is already imported.")
        return

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("This first importer does not support encrypted PDFs.")

    staging_root = ROOT / "pdf-import-staging"
    staging_root.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=staging_root))

    count = 0
    empty_pages = []

    try:
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()

            if not text:
                empty_pages.append(page_number)
                continue

            parts = textwrap.wrap(
                text,
                width=1400,
                break_long_words=True,
                break_on_hyphens=False
            )

            for part_number, part in enumerate(parts, start=1):
                name = f"page-{page_number:04d}-part-{part_number:03d}.md"
                body = (
                    f"# {source.name} - PDF page {page_number}\n\n"
                    f"Source PDF: {source.name}\n"
                    f"PDF page: {page_number}\n"
                    f"Part: {part_number}\n\n"
                    "## Extracted text\n\n"
                    + textwrap.fill(part, width=90)
                    + "\n"
                )
                (staging / name).write_text(body, encoding="utf-8")
                count += 1

        if not count:
            raise ValueError("No text extracted. This PDF may need OCR.")

        manifest = {
            "source_file": source.name,
            "sha256": digest,
            "pdf_pages": len(reader.pages),
            "notes_created": count,
            "pages_without_text": empty_pages
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        destination.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(destination)

        print(f"PDF pages: {len(reader.pages)}")
        print(f"Searchable notes created: {count}")
        print(f"Saved under: {destination.relative_to(ROOT)}")
        if empty_pages:
            print(f"Pages without extracted text: {empty_pages}")
        print("Original PDF unchanged. Review extraction before relying on it.")
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Import failed: {error}")
