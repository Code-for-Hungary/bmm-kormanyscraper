#!/usr/bin/env python3
"""Generate options_schema.json from sources.json and document_types.json."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_names(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    return [item["name"] for item in payload["data"]]


def main() -> None:
    sources = load_names(BASE_DIR / "sources.json")
    document_types = load_names(BASE_DIR / "document_types.json")

    schema = [
        {
            "id": 1,
            "title": "Forrás",
            "type": "select",
            "options": sources,
        },
        {
            "id": 2,
            "title": "Dokumentum típus",
            "type": "select",
            "options": document_types,
        },
    ]

    out_path = BASE_DIR / "options_schema.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=4)
        f.write("\n")


if __name__ == "__main__":
    main()
