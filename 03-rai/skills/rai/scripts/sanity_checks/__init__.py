"""The sanity check registry. Importing this package registers every check (see core.check)."""

from . import (code, config, data, drift, harness, hooks, identity, jobs, memory,  # noqa: F401
               meta, pipeline, stores, vault)
from .core import CHECKS  # noqa: F401
