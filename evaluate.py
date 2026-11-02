import tempfile
import time
from contextlib import closing
from pathlib import Path

from brain import connect, sync, search as keyword_search
from semantic import search as semantic_search

NOTES = {
    "Harbor.md": (
        "Harbor creates a daily backup of PostgreSQL databases. "
        "Copies are retained for thirty days."
    ),
    "Beacon.md": (
        "Beacon masks patient names and medical record numbers "
        "before healthcare data reaches analytics."
    ),
    "Summit.md": (
        "Summit detects fraudulent card purchases. "
        "Suspicious transactions trigger an alert for investigation."
    ),
    "Orchard.md": (
        "Orchard predicts warehouse inventory shortages "
        "and recommends replenishment quantities."
    ),
    "Atlas.md": (
        "Atlas transcribes recorded meetings and extracts "
        "decisions and assigned action items."
    )
}

QUESTIONS = [
    ("Which system keeps spare copies of the database?", "Harbor.md"),
    ("Which system removes identifying details from clinical records?", "Beacon.md"),
    ("Which system flags potentially dishonest payments?", "Summit.md"),
    ("Which system helps prevent products from running out?", "Orchard.md"),
    ("Which system turns team discussions into tasks?", "Atlas.md")
]


def evaluate(db, label, finder):
    first_hits = 0
    top_three_hits = 0
    started = time.perf_counter()

    print(f"\n--- {label} ---")
    for question, expected in QUESTIONS:
        results = finder(db, question, limit=3)
        paths = [item["path"] for item in results]
        first_hits += bool(paths and paths[0] == expected)
        top_three_hits += expected in paths

        print(f"\nQuestion: {question}")
        print(f"Expected: {expected}")
        print(f"Retrieved: {', '.join(paths) or '(none)'}")

    count = len(QUESTIONS)
    print(f"\nCorrect first result: {first_hits}/{count}")
    print(f"Expected source in top 3: {top_three_hits}/{count}")
    print(f"Total time: {time.perf_counter() - started:.2f} seconds")


def main():
    with tempfile.TemporaryDirectory(prefix="brain-eval-") as folder:
        root = Path(folder)
        vault = root / "demo-vault"
        vault.mkdir()

        for name, content in NOTES.items():
            (vault / name).write_text(content, encoding="utf-8")

        with closing(connect(root / "evaluation.sqlite", vault)) as db:
            sync(db, vault)
            evaluate(db, "Keyword search", keyword_search)
            evaluate(db, "Semantic search", semantic_search)

    print("\nEvaluation finished. Temporary demo files removed.")


if __name__ == "__main__":
    main()
