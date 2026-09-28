"""Centralized path resolution for Rai hooks."""

import os
from pathlib import Path


def get_pai_dir() -> Path:
    """The Rai directory in the vault."""
    return Path.home() / "helm" / "03-rai"


def get_memory_dir() -> Path:
    return get_pai_dir() / "memory"


def get_hooks_dir() -> Path:
    return get_pai_dir() / "hooks"


def get_skills_dir() -> Path:
    return get_pai_dir() / "skills"


def get_settings_path() -> Path:
    return get_pai_dir() / "config" / "settings.json"


def get_state_dir() -> Path:
    """Tracked state in the vault: memory-block.md and README.md."""
    return get_memory_dir() / "state"


def get_runtime_dir() -> Path:
    """Per-session hook runtime state, outside the vault. Callers create it on write."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "rai" / "runtime"


def get_telemetry_dir() -> Path:
    """Hook telemetry (hook-perf.jsonl, counts-history.jsonl), outside the vault. Callers create it on write."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "rai" / "telemetry"


def get_work_dir() -> Path:
    return get_memory_dir() / "work"


def get_learning_dir() -> Path:
    return get_memory_dir() / "learning"
