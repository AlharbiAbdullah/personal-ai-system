"""The catalog in 03-rai/benchmark/targets.toml: harness routes, models, harness-mode pairs and
judges. A target is one model in one harness; every score belongs to a target."""

from dataclasses import dataclass
from pathlib import Path

import tomllib


class TargetError(ValueError):
    pass


# The effort levels each harness's CLI takes (`--effort`).
EFFORTS = {"claude-code": ("low", "medium", "high", "xhigh", "max"),
           "agy": ("low", "medium", "high", "max")}


@dataclass(frozen=True)
class Target:
    key: str          # catalog key, e.g. opus-5.5
    harness: str      # claude-code | agy | pi | opencode
    model: str        # the id the harness CLI takes
    label: str
    effort: str | None = None   # None = the harness default

    @property
    def name(self) -> str:
        return f"{self.label} @ {self.harness}"

    def at(self, effort: str) -> "Target":
        """This model at one effort level: its own target, key and leaderboard row."""
        if effort not in EFFORTS.get(self.harness, ()):
            raise TargetError(f"{self.harness} has no effort '{effort}': "
                              f"{', '.join(EFFORTS.get(self.harness, ())) or 'no --effort flag'}")
        return Target(f"{self.key}@{effort}", self.harness, self.model, f"{self.label} ({effort})", effort)


@dataclass
class Catalog:
    harnesses: dict   # name -> {enabled, account, route, reason}
    models: dict      # key -> Target
    defaults: list    # keys
    harness_mode: dict  # harness -> model key
    judges: dict      # name -> {harness, id, effort}

    def account(self, harness: str) -> str:
        return self.harnesses.get(harness, {}).get("account", harness)

    def enabled(self, harness: str) -> bool:
        return bool(self.harnesses.get(harness, {}).get("enabled"))


def load(bench: Path) -> Catalog:
    raw = tomllib.loads((bench / "targets.toml").read_text())
    harnesses = raw.get("harness", {})
    models, defaults = {}, []
    for key, m in raw.get("model", {}).items():
        if m.get("harness") not in harnesses:
            raise TargetError(f"model {key}: unknown harness {m.get('harness')}")
        models[key] = Target(key, m["harness"], m["id"], m.get("label", m["id"]))
        if m.get("default"):
            defaults.append(key)
    hm = raw.get("harness_mode", {})
    for h, key in hm.items():
        if key not in models or models[key].harness != h:
            raise TargetError(f"harness_mode.{h}: {key} is not a {h} model")
    return Catalog(harnesses, models, defaults, hm, raw.get("judge", {}))


def resolve(cat: Catalog, mode: str, keys: list | None = None, harnesses: list | None = None,
            efforts: list | None = None) -> list:
    """The targets a run covers. Model mode: the picked keys, else the defaults. Harness mode:
    the harness_mode pair of each picked harness, else of every enabled one. `efforts` runs each
    of them once per effort level. A disabled harness is refused with its reason, never run."""
    if mode == "model":
        picked = keys or cat.defaults
        unknown = [k for k in picked if k not in cat.models]
        if unknown:
            raise TargetError(f"unknown model key(s): {', '.join(unknown)}. See: bench.py models")
        out = [cat.models[k] for k in picked]
    elif mode == "harness":
        hs = harnesses or [h for h in cat.harness_mode if cat.enabled(h)]
        missing = [h for h in hs if h not in cat.harness_mode]
        if missing:
            raise TargetError(f"no harness_mode model for: {', '.join(missing)}")
        out = [cat.models[cat.harness_mode[h]] for h in hs]
    else:
        raise TargetError(f"unknown mode {mode}: model or harness")
    if efforts:
        out = [t.at(e) for t in out for e in efforts]
    off = [t for t in out if not cat.enabled(t.harness)]
    if off:
        why = "; ".join(f"{t.harness}: {cat.harnesses[t.harness].get('reason', 'disabled')}" for t in off)
        raise TargetError(f"disabled harness: {why}")
    return out
