#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Personal AI System's README diagrams: architecture (the solution) and tech stack (where
each tool lives), on one layout. Run it to regenerate both .excalidraw.svg files here.
The kit is Rai's /media → diagram; RAI_DIAGRAM_KIT points elsewhere if needed.
"""

import os
import sys
from collections.abc import Callable
from pathlib import Path

DEFAULT_KIT = Path.home() / "helm/03-rai/skills/media/scripts/diagram"
KIT = Path(os.environ.get("RAI_DIAGRAM_KIT", DEFAULT_KIT))
sys.path.insert(0, str(KIT))
from lib import MUTED, VIOLET, Scene, render  # ty: ignore[unresolved-import]

HERE = Path(__file__).parent
USER = "url:https://cdn.jsdelivr.net/npm/lucide-static/icons/user.svg"
CHROMA = ("url:https://raw.githubusercontent.com/chroma-core/chroma/main/"
          "docs/mintlify/images/favicon.svg")
VALE = "url:https://vale.sh/brand/vale-mark.svg"
# zone: (x, y, w, h, title)
Z = {
    "you": (0, 350, 170, 710, "YOU"),
    "model": (640, 0, 620, 150, "MODEL"),
    "session": (330, 350, 530, 300, "SESSION"),
    "batch": (1000, 350, 370, 300, "BATCH"),
    "vault": (330, 760, 300, 300, "VAULT"),
    "memory": (770, 760, 600, 300, "MEMORY"),
    "checks": (280, 1180, 1140, 190, "CHECKS"),
}
MID = 500


def frame(s: Scene, header: Callable[[Scene], None]) -> None:
    """Zones, the project box and the labelled arrows: the same in both diagrams."""
    s.zone(280, 200, 1140, 910, None, dotted=True)
    header(s)
    for x, y, w, h, title in Z.values():
        s.zone(x, y, w, h, title)
    s.arrow([(172, MID), (328, MID)], label="send\neach turn", at=(172, MID - 60, 108))
    s.arrow([(172, 839), (328, 839)], color=VIOLET, dashed=True,
            label="fill in\nidentity", at=(172, 779, 108))
    s.arrow([(480, 758), (480, 652)], color=VIOLET, dashed=True,
            label="load\nidentity, skills", at=(490, 680, 140))
    s.arrow([(820, 758), (820, 652)], label="inject\nsnapshot, pointers",
            at=(830, 680, 190))
    s.arrow([(862, MID), (998, MID)], label="scan\npast sessions", at=(862, MID - 60, 136))
    s.arrow([(1290, 652), (1290, 758)], label="store\nfacts, sessions",
            at=(1130, 680, 150))
    s.arrow([(768, 899), (632, 899)], color=VIOLET, dashed=True,
            label="render\nlearned rules", at=(630, 839, 140))
    s.arrow([(800, 348), (800, 152)], label="call\nthe model", at=(810, 250, 100))
    s.arrow([(1100, 348), (1100, 152)], label="distill\nsessions", at=(1110, 250, 90))
    s.arrow([(380, 1178), (380, 1112)], color=MUTED, dashed=True,
            label="check\nthe project", at=(390, 1122, 130))


def row(
    s: Scene, zone: str, items: list[tuple[str, str]], top: int | None = None
) -> None:
    """Logos with names, spread evenly across a zone."""
    x, y, w, _, _ = Z[zone]
    slot = w / len(items)
    top = y + 90 if top is None else top
    for j, (key, name) in enumerate(items):
        s.tool(x + slot * j + slot / 2, top, key, name, w=slot)


def tech_stack() -> None:
    s = Scene()

    def header(s: Scene) -> None:
        s.tool(356, 214, "si:git", "git", w=110)

    frame(s, header)
    row(s, "you", [(USER, "you")], top=655)
    row(s, "model", [("si:claude", "Claude")], top=30)
    row(s, "session", [("si:claudecode", "Claude Code")], top=440)
    row(s, "batch", [("si:uv", "uv")], top=440)
    row(s, "vault", [("si:markdown", "Markdown"), ("si:obsidian", "Obsidian")], top=850)
    row(s, "memory", [(CHROMA, "ChromaDB"), ("si:json", "JSON Lines")], top=850)
    row(s, "checks", [("si:pytest", "pytest"), (VALE, "Vale")], top=1230)
    s.save("tech-stack")


def architecture() -> None:
    s = Scene()

    frame(s, lambda s: None)

    def stack(zone: str, labels: list[str], top: int, h: int = 48, gap: int = 12) -> None:
        x, _, w, _, _ = Z[zone]
        for label in labels:
            s.part(x + 20, top, w - 40, h, label)
            top += h + gap

    def grid(zone: str, labels: list[str], top: int, h: int = 80, gap: int = 20) -> None:
        x, _, w, _, _ = Z[zone]
        cw = (w - 60) / 2
        for j, label in enumerate(labels):
            s.part(x + 20 + (j % 2) * (cw + 20), top + (j // 2) * (h + gap), cw, h, label)

    s.part(20, MID - 26, 130, 52, "prompts")
    s.part(20, 813, 130, 52, "your notes")
    s.part(800, 60, 300, 56, "Claude models")
    grid("session", ["note each turn", "daily notes,\ntranscripts", "load at start",
                     "recall per prompt"], top=405, h=80, gap=30)
    stack("batch", ["scan, classify", "distill sessions", "store, archive",
                    "curate weekly"], top=405)
    stack("vault", ["your identity", "Rai's rules", "skills, agents", "notes, workflows"],
          top=815)
    grid("memory", ["vector store", "session archive", "frozen snapshot",
                    "committed index"], top=830)
    x, y, w, _, _ = Z["checks"]
    checks = ["brain sanity", "tests, nothing live", "wiring check", "prose gate"]
    slot = (w - 40) / len(checks)
    for j, label in enumerate(checks):
        s.part(x + 20 + slot * j + 8, y + 70, slot - 16, 64, label)
    s.save("architecture")


tech_stack()
architecture()
render(HERE, "architecture", "tech-stack")
