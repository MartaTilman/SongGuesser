"""
Migration: blockchain_storage schema v1 to v2

Schema v1 files (created before the PoW upgrade) have no nonce, difficulty,
or schema_version on individual blocks, and no consensus/difficulty fields
at the top level.

This script adds those fields with accurate values:
  - schema_version = 1  (honest -- these were NOT mined)
  - nonce = 0
  - difficulty = 0      (difficulty 0 means no PoW was required)
  - consensus = "legacy_no_pow" at the top level

Hashes are NOT recomputed -- they stay as-is so the chain remains valid.
The script is idempotent: already-migrated files are skipped.

Usage:
    python migrate_blockchain_v1_to_v2.py
"""

import json
import sys
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent / "blockchain_storage"


def needs_migration(payload):
    consensus = payload.get("consensus")
    if consensus == "legacy_no_pow":
        return False
    if consensus == "proof_of_work":
        chain = payload.get("chain", [])
        if chain and chain[0].get("schema_version", 0) >= 2:
            return False
    return True


def migrate_file(path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        print("  ERROR reading %s: %s" % (path.name, exc))
        return "error"

    if not needs_migration(payload):
        return "skipped"

    chain = payload.get("chain", [])
    for block in chain:
        if block.get("schema_version") is None:
            block["schema_version"] = 1
        if block.get("nonce") is None:
            block["nonce"] = 0
        if block.get("difficulty") is None:
            block["difficulty"] = 0

    payload["consensus"] = "legacy_no_pow"
    payload["difficulty"] = 0
    payload["block_count"] = len(chain)
    payload["chain"] = chain

    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    return "migrated"


def main():
    if not STORAGE_DIR.exists():
        print("Storage dir not found: %s" % STORAGE_DIR)
        sys.exit(1)

    files = sorted(STORAGE_DIR.glob("*.json"))
    if not files:
        print("No blockchain files found.")
        return

    migrated = skipped = errors = 0
    icons = {"migrated": "v", "skipped": "-", "error": "x"}

    for path in files:
        result = migrate_file(path)
        print("  %s %s  [%s]" % (icons[result], path.name, result))
        if result == "migrated":
            migrated += 1
        elif result == "skipped":
            skipped += 1
        else:
            errors += 1

    print("")
    print("Done: %d migrated, %d already up-to-date, %d errors." % (migrated, skipped, errors))


if __name__ == "__main__":
    main()
