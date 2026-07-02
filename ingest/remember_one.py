"""Ingest a single memory unit by commit hash — used when demo-data grows
incrementally (e.g. Day 2's fresh auth contradiction) rather than
re-running the full batch."""

from __future__ import annotations

import sys

from ingest.memory_units import build_memory_units
from ingest.remember_client import remember_unit, _client


def main(commit_hash: str):
    units = build_memory_units()
    unit = next(u for u in units if u.source_commit == commit_hash)
    with _client() as client:
        client.health()
        result = remember_unit(client, unit)
    return result


if __name__ == "__main__":
    import json

    out = main(sys.argv[1])
    print(json.dumps(out, indent=2, default=str))
