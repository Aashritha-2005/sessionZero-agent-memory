"""Wraps Cognee's remember() to ingest memory units.

Each MemoryUnit becomes one remember() call, tagged with a dataset name
so it can be recalled/consolidated/pruned as a coherent set later. We
call the real Cognee SDK — no mocking (see PROJECT_PLAN.md §7).
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from ingest.memory_units import MemoryUnit, build_memory_units

load_dotenv()

DATASET_NAME = "shiftlog_demo"


def _require_env() -> None:
    if not os.getenv("COGNEE_API_KEY") and not os.getenv("LLM_API_KEY"):
        raise RuntimeError(
            "No Cognee/LLM credentials found. Copy .env.example to .env and fill in "
            "COGNEE_API_KEY (Cognee Cloud) or LLM_API_KEY (self-hosted), then re-run."
        )


async def remember_unit(unit: MemoryUnit, dataset_name: str = DATASET_NAME):
    import cognee

    result = await cognee.remember(
        data=unit.body,
        dataset_name=dataset_name,
    )
    print(f"remembered {unit.id} ({unit.kind}) -> {result}")
    return result


async def remember_all(units: list[MemoryUnit] | None = None, dataset_name: str = DATASET_NAME):
    _require_env()
    units = units if units is not None else build_memory_units()
    results = []
    for unit in units:
        results.append(await remember_unit(unit, dataset_name=dataset_name))
    return results


if __name__ == "__main__":
    asyncio.run(remember_all())
