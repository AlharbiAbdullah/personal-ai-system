"""Code: everything outside the hooks tree that helm runs parses before the day it runs. The
hooks tree has its own load-bearing parse checks (HOOK-3, PIPE-2)."""

import subprocess

from . import core
from .core import FAIL, PASS, PRODUCER, P, check


def _rel(entry: str) -> str:
    return entry.replace(f"{P.HELM}/", "")


@check("CODE-1", "Code", role=PRODUCER)
def code_parses():
    """Every other vault .py compiles under the system python3 the scripts run on, and every .sh
    passes `bash -n`: a syntax error in a scheduled runner shows only when it next fires. The hub
    runs these scripts, so the hub's interpreter is the one that counts."""
    py = [p for p in core.vault_files("*.py", skip_top=("13-archive",)) if P.HOOKS not in p.parents]
    sh = core.vault_files("*.sh", skip_top=("13-archive",))
    bad = [_rel(b) for b in core.compile_with(core.SYSTEM_PYTHON, py)]
    for f in sh:
        r = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True, timeout=20)
        if r.returncode:
            bad.append(f"{_rel(str(f))}: {(r.stderr.strip().splitlines() or ['?'])[-1][:60]}")
    ev = f"{len(py)} .py (system python3), {len(sh)} .sh (bash -n)"
    if bad:
        return FAIL, ev + f", {len(bad)} broken: {bad[:4]}", "Fix the syntax error before its job or skill next runs it."
    return PASS, ev + ", all parse", ""
