"""Detects deleted/renamed files and calls Cognee's real forget() to
surgically remove graph nodes tied to that path.

Source of "deletion" events: commits in demo-data/commits.jsonl typed
"deletion" (see ingest/git_reader.py, ingest/memory_units.py). For each
such commit, we resolve its real data_id in the live Cognee dataset
(ingest/dataset_index.py) and call forget(data_id=...), logging what was
forgotten and why — for transparency in the dashboard later.
"""

from __future__ import annotations

from dataclasses import dataclass

from ingest.dataset_index import build_commit_to_data_id, get_dataset_id
from ingest.memory_units import MemoryUnit, build_memory_units
from ingest.remember_client import DATASET_NAME, _client


@dataclass(frozen=True)
class ForgetLogEntry:
    commit: str
    files: list[str]
    reason: str
    data_id: str | None
    status: str  # forgotten | skipped
    forget_result: dict | None = None


def find_deletion_units(units: list[MemoryUnit] | None = None) -> list[MemoryUnit]:
    units = units if units is not None else build_memory_units()
    return [u for u in units if u.kind == "deletion"]


def prune_deleted_files(dataset_name: str = DATASET_NAME) -> list[ForgetLogEntry]:
    deletion_units = find_deletion_units()
    log: list[ForgetLogEntry] = []

    with _client() as client:
        client.health()
        dataset_id = get_dataset_id(client, dataset_name)
        commit_to_data_id = build_commit_to_data_id(client, dataset_id)

        for unit in deletion_units:
            data_id = commit_to_data_id.get(unit.source_commit)
            if not data_id:
                log.append(
                    ForgetLogEntry(
                        commit=unit.source_commit,
                        files=unit.files,
                        reason=unit.title,
                        data_id=None,
                        status="skipped (no data_id found — already pruned or never ingested)",
                    )
                )
                continue
            result = client.forget(dataset=dataset_name, data_id=data_id)
            entry = ForgetLogEntry(
                commit=unit.source_commit,
                files=unit.files,
                reason=unit.title,
                data_id=data_id,
                status="forgotten",
                forget_result=result,
            )
            log.append(entry)
            print(
                f"forgot {unit.source_commit} (files: {', '.join(unit.files)}) "
                f"reason={unit.title!r} -> {result}"
            )
    return log


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    out = prune_deleted_files()
    print(json.dumps([asdict(e) for e in out], indent=2, default=str))
