import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PENDING = ROOT / "memory-inbox"
APPROVED = ROOT / "my-vault" / "memories"


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    propose = sub.add_parser("propose")
    propose.add_argument("name")
    propose.add_argument("text")

    sub.add_parser("list")

    approve = sub.add_parser("approve")
    approve.add_argument("name")

    args = parser.parse_args()

    if args.command == "list":
        files = sorted(PENDING.glob("*.json"))
        if not files:
            print("No pending memories.")
        for file in files:
            item = json.loads(file.read_text(encoding="utf-8"))
            print(f'\n{file.stem}\n{item["text"]}')
        return

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", args.name):
        parser.error("Use a short name containing lowercase letters, numbers, and hyphens.")

    pending = PENDING / f"{args.name}.json"
    approved = APPROVED / f"{args.name}.md"

    if args.command == "propose":
        text = args.text.strip()
        if not text or len(text) > 4000:
            parser.error("Memory text must contain 1–4000 characters.")
        if approved.exists():
            raise SystemExit("An approved memory already uses this name.")

        PENDING.mkdir(exist_ok=True)
        item = {
            "text": text,
            "source": "User-entered proposal",
            "proposed_at": datetime.now(timezone.utc).isoformat()
        }
        with pending.open("x", encoding="utf-8") as file:
            json.dump(item, file, indent=2)

        print("Proposal saved outside the searchable vault:")
        print(text)
        print(f"\nReview with: python memory.py list")
        print(f"Approve with: python memory.py approve {args.name}")
        return

    item = json.loads(pending.read_text(encoding="utf-8"))
    APPROVED.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    with approved.open("x", encoding="utf-8") as file:
        file.write(
            f"# Reviewed memory: {args.name}\n\n"
            f'{item["text"]}\n\n'
            f'## Provenance\nSource: {item["source"]}\n'
            f'Proposed at: {item["proposed_at"]}\n'
            f"Approved through the local CLI at: {timestamp}\n"
        )

    pending.unlink()
    print(f"Approved: memories/{approved.name}")
    print("It will be indexed on the next search.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Memory operation failed: {error}")
