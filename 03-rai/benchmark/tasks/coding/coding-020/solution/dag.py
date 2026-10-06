"""Plan a pipeline of dependent tasks declared in TOML."""

from __future__ import annotations

import argparse
import heapq
import sys
from collections import deque
from pathlib import Path

import tomllib

Graph = dict[str, list[str]]


class PipelineError(Exception):
    pass


class CycleError(PipelineError):
    def __init__(self, cycle: list[str]) -> None:
        super().__init__("dependency cycle: " + " -> ".join(cycle))
        self.cycle = cycle


def _check_known(graph: Graph) -> None:
    for task, deps in graph.items():
        for dep in deps:
            if dep not in graph:
                raise PipelineError(f"unknown dependency: {task} -> {dep}")


def load_pipeline(path: str | Path) -> tuple[Graph, dict[str, int]]:
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PipelineError(f"cannot read pipeline: {exc}") from exc
    tasks = data.get("tasks")
    if not isinstance(tasks, dict):
        raise PipelineError("missing [tasks] table")
    graph: Graph = {}
    durations: dict[str, int] = {}
    for name, spec in tasks.items():
        if not isinstance(spec, dict):
            raise PipelineError(f"{name}: task must be a table")
        deps = spec.get("deps", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise PipelineError(f"{name}: deps must be a list of task names")
        duration = spec.get("duration", 1)
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise PipelineError(f"{name}: duration must be a non-negative integer")
        graph[name] = list(dict.fromkeys(deps))
        durations[name] = duration
    _check_known(graph)
    return graph, durations


def _find_cycle(graph: Graph, remaining: set[str]) -> list[str]:
    # Every remaining task still waits on another remaining task, so walking deps must loop.
    path: list[str] = []
    seen: dict[str, int] = {}
    node = min(remaining)
    while node not in seen:
        seen[node] = len(path)
        path.append(node)
        node = min(d for d in graph[node] if d in remaining)
    return path[seen[node] :] + [node]


def topo_order(graph: Graph) -> list[str]:
    _check_known(graph)
    waiting = {task: len(set(deps)) for task, deps in graph.items()}
    dependents: dict[str, list[str]] = {task: [] for task in graph}
    for task, deps in graph.items():
        for dep in set(deps):
            dependents[dep].append(task)
    ready = [task for task, n in waiting.items() if n == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        task = heapq.heappop(ready)
        order.append(task)
        for child in dependents[task]:
            waiting[child] -= 1
            if waiting[child] == 0:
                heapq.heappush(ready, child)
    if len(order) < len(graph):
        raise CycleError(_find_cycle(graph, set(graph) - set(order)))
    return order


def levels(graph: Graph) -> list[list[str]]:
    level: dict[str, int] = {}
    for task in topo_order(graph):
        level[task] = 1 + max((level[d] for d in graph[task]), default=-1)
    out: list[list[str]] = [[] for _ in range(max(level.values(), default=-1) + 1)]
    for task, n in level.items():
        out[n].append(task)
    return [sorted(group) for group in out]


def downstream(graph: Graph, task: str) -> list[str]:
    if task not in graph:
        raise KeyError(task)
    dependents: dict[str, list[str]] = {t: [] for t in graph}
    for t, deps in graph.items():
        for dep in deps:
            dependents.setdefault(dep, []).append(t)
    found: set[str] = set()
    queue = deque([task])
    while queue:
        for child in dependents[queue.popleft()]:
            if child not in found:
                found.add(child)
                queue.append(child)
    found.discard(task)
    return sorted(found)


def critical_path(graph: Graph, durations: dict[str, int]) -> tuple[int, list[str]]:
    finish: dict[str, int] = {}
    via: dict[str, str | None] = {}
    for task in topo_order(graph):
        best = max(graph[task], key=lambda d: finish[d], default=None)
        via[task] = best
        finish[task] = durations.get(task, 1) + (
            finish[best] if best is not None else 0
        )
    if not finish:
        return 0, []
    end = max(finish, key=lambda t: finish[t])
    path = [end]
    while via[path[-1]] is not None:
        path.append(via[path[-1]])
    return finish[end], path[::-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pipeline")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--levels", action="store_true")
    mode.add_argument("--critical", action="store_true")
    args = parser.parse_args(argv)
    try:
        graph, durations = load_pipeline(args.pipeline)
        if args.levels:
            for i, group in enumerate(levels(graph)):
                print(f"{i}: {' '.join(group)}")
        elif args.critical:
            total, path = critical_path(graph, durations)
            print(f"{total} {' -> '.join(path)}".rstrip())
        else:
            for task in topo_order(graph):
                print(task)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
