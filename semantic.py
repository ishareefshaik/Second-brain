import hashlib
import json
import math
import sys
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen

from brain import connect, sync, context

MODEL = "nomic-embed-text"


def embed(texts):
    payload = {
        "model": MODEL,
        "input": texts,
        "truncate": False,
        "keep_alive": "0"
    }
    request = Request(
        "http://127.0.0.1:11434/api/embed",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urlopen(request, timeout=180) as response:
        return json.load(response)["embeddings"]


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError("Embedding dimensions differ. Rebuild the vector cache.")
    denominator = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / denominator if denominator else 0


def search(db, question, limit=3):
    rows = [
        dict(row)
        for row in db.execute("SELECT path, line, body FROM chunks")
    ]
    if not rows:
        return []

    db.execute("""
        CREATE TABLE IF NOT EXISTS vectors (
            model TEXT,
            digest TEXT,
            vector TEXT,
            PRIMARY KEY (model, digest)
        )
    """)

    documents = {
        hashlib.sha256(row["body"].encode()).hexdigest(): row["body"]
        for row in rows
    }
    cached = {
        row["digest"]: json.loads(row["vector"])
        for row in db.execute(
            "SELECT digest, vector FROM vectors WHERE model=?", (MODEL,)
        )
    }

    missing = [key for key in documents if key not in cached]
    for start in range(0, len(missing), 16):
        keys = missing[start:start + 16]
        texts = ["search_document: " + documents[key] for key in keys]
        generated = embed(texts)
        if len(generated) != len(keys):
            raise ValueError("Incomplete embedding response.")
        for key, vector in zip(keys, generated):
            cached[key] = vector
            db.execute(
                "INSERT OR REPLACE INTO vectors VALUES (?, ?, ?)",
                (MODEL, key, json.dumps(vector))
            )

    for key in cached.keys() - documents.keys():
        db.execute(
            "DELETE FROM vectors WHERE model=? AND digest=?", (MODEL, key)
        )
    db.commit()

    query = embed(["search_query: " + question])[0]
    for row in rows:
        key = hashlib.sha256(row["body"].encode()).hexdigest()
        row["score"] = cosine(query, cached[key])

    return sorted(rows, key=lambda row: row["score"], reverse=True)[:limit]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        raise SystemExit('Usage: python3 semantic.py "your question"')

    vault = Path("my-vault")
    if not vault.is_dir():
        raise SystemExit("Run this inside your second-brain folder.")

    try:
        with closing(connect(Path("my-brain.sqlite"), vault)) as db:
            sync(db, vault)
            results = search(db, question)
        print(context(results, budget=4000))
    except Exception as error:
        raise SystemExit(f"Semantic search failed: {error}")
