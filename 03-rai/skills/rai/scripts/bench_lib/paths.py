"""Where the bench reads and writes. Every path resolves at call time from the environment, so
tests point the engine at a throwaway tree with RAI_BENCH_DIR, RAI_BENCH_CACHE and RAI_BENCH_HELM."""

import os
from pathlib import Path


def home() -> Path:
    return Path.home()


def helm() -> Path:
    """The live vault the snapshot is taken from. Never written by a run."""
    return Path(os.environ.get("RAI_BENCH_HELM", home() / "helm"))


def bench_dir() -> Path:
    """Tasks, targets.toml, results/ and leaderboard.md (tracked in the vault)."""
    return Path(os.environ.get("RAI_BENCH_DIR", helm() / "03-rai" / "benchmark"))


def cache_dir() -> Path:
    """Snapshots, attempt sandboxes and raw harness output. On disk, never under /tmp."""
    return Path(os.environ.get("RAI_BENCH_CACHE", home() / ".cache" / "rai-bench"))


def results_dir() -> Path:
    return bench_dir() / "results"


def run_dir(run_id: str) -> Path:
    return results_dir() / run_id


def run_cache(run_id: str) -> Path:
    return cache_dir() / "runs" / run_id
