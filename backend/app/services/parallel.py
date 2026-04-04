"""Parallel execution helpers for CPU-bound sweep/optimization workloads.

Each worker thread gets its own asyncio event loop (via ``asyncio.run``) and
its own database session, so there is no contention on the main event loop.
The GIL is released during IO waits and numpy/scipy C extensions, giving
real speedup on multi-core machines for mixed IO/CPU workloads.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# Cap at physical cores or 4, whichever is smaller
MAX_SWEEP_WORKERS = min(os.cpu_count() or 2, 4)


def run_parallel_sweeps(
    tasks: list[Callable[[], Any]],
    max_workers: int | None = None,
) -> list[Any]:
    """Execute a list of callables in parallel threads, preserving order.

    Each callable should be self-contained (create its own event loop and DB
    session).  Results are returned in the same order as ``tasks``.
    """
    workers = min(max_workers or MAX_SWEEP_WORKERS, len(tasks))
    if workers <= 1:
        return [task() for task in tasks]

    results: list[Any] = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {pool.submit(task): i for i, task in enumerate(tasks)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
    return results


async def run_in_thread_pool(
    fn: Callable[[], Any],
    max_workers: int = 1,
) -> Any:
    """Run a synchronous function in a thread pool from an async context."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return await loop.run_in_executor(pool, fn)
