import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def make_pdf(path, text):
    """Create a minimal one-page PDF containing known test text."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        (
            f"<< /Length {len(stream)} >>\nstream\n".encode()
            + stream + b"\nendstream"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode())
        data.extend(body + b"\nendobj\n")

    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(data)


class PdfRefreshTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = Path(__file__).resolve().parent

        for name in ("brain.py", "import_pdf.py", "refresh_pdf.py"):
            shutil.copy2(source / name, self.root / name)

        (self.root / "my-vault").mkdir()
        (self.root / "pdf-inbox").mkdir()
        self.pdf = self.root / "pdf-inbox/Demo.pdf"
        make_pdf(self.pdf, "Original demo evidence.")

    def tearDown(self):
        self.temp.cleanup()

    def refresh(self, expected_success=True):
        result = subprocess.run(
            [
                sys.executable,
                str(self.root / "refresh_pdf.py"),
                str(self.pdf)
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=60
        )
        if expected_success:
            self.assertEqual(
                result.returncode, 0, result.stdout + result.stderr
            )
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def active(self):
        return list(
            (self.root / "my-vault/pdf-imports").glob("*/manifest.json")
        )

    def archived(self):
        return list(
            (self.root / "pdf-archive").glob("*/*/manifest.json")
        )

    def test_unchanged_pdf_does_not_duplicate(self):
        self.refresh()
        self.refresh()
        self.assertEqual(len(self.active()), 1)
        self.assertEqual(len(self.archived()), 0)

    def test_changed_text_replaces_index_and_archives_previous(self):
        self.refresh()
        old_hash = hashlib.sha256(self.pdf.read_bytes()).hexdigest()

        make_pdf(self.pdf, "Updated replacement evidence.")
        new_hash = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.refresh()

        self.assertEqual(len(self.active()), 1)
        self.assertEqual(len(self.archived()), 1)

        active = json.loads(self.active()[0].read_text())
        archived = json.loads(self.archived()[0].read_text())
        self.assertEqual(active["sha256"], new_hash)
        self.assertEqual(archived["sha256"], old_hash)

        with sqlite3.connect(self.root / "my-brain.sqlite") as db:
            bodies = "\n".join(
                row[0] for row in db.execute("SELECT body FROM chunks")
            )
            paths = [
                row[0] for row in db.execute("SELECT path FROM files")
            ]

        self.assertIn("Updated replacement evidence.", bodies)
        self.assertNotIn("Original demo evidence.", bodies)
        self.assertTrue(paths)
        self.assertTrue(all(old_hash[:12] not in path for path in paths))

        self.refresh()
        self.assertEqual(len(self.archived()), 1)

    def test_missing_pdf_preserves_existing_import(self):
        self.refresh()
        before = self.active()[0].read_bytes()
        self.pdf.unlink()

        self.refresh(expected_success=False)

        self.assertEqual(len(self.active()), 1)
        self.assertEqual(self.active()[0].read_bytes(), before)
        self.assertEqual(len(self.archived()), 0)


if __name__ == "__main__":
    unittest.main()
