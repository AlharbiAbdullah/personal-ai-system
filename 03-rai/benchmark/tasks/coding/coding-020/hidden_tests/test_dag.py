import heapq
import random
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import dag
import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "pipeline.toml"

SAMPLE_GRAPH = {
    "extract_orders": [],
    "extract_customers": [],
    "clean_orders": ["extract_orders"],
    "clean_customers": ["extract_customers"],
    "join_orders_customers": ["clean_orders", "clean_customers"],
    "daily_revenue": ["join_orders_customers"],
    "customer_ltv": ["join_orders_customers", "clean_customers"],
    "publish_dashboard": ["daily_revenue", "customer_ltv"],
    "audit_log": [],
}


def ref_topo(graph):
    waiting = {t: len(set(d)) for t, d in graph.items()}
    ready = [t for t, n in waiting.items() if n == 0]
    heapq.heapify(ready)
    out = []
    while ready:
        t = heapq.heappop(ready)
        out.append(t)
        for child, deps in graph.items():
            if t in deps:
                waiting[child] -= 1
                if waiting[child] == 0:
                    heapq.heappush(ready, child)
    return out


def ref_levels(graph):
    level = {}
    for t in ref_topo(graph):
        level[t] = 1 + max((level[d] for d in graph[t]), default=-1)
    return [
        sorted(t for t, n in level.items() if n == i)
        for i in range(max(level.values(), default=-1) + 1)
    ]


def ref_longest(graph, durations):
    finish = {}
    for t in ref_topo(graph):
        finish[t] = durations[t] + max((finish[d] for d in graph[t]), default=0)
    return max(finish.values(), default=0)


def random_dag(seed, n=30):
    rng = random.Random(seed)
    names = [f"{rng.choice('abcdefghij')}{i:02d}" for i in range(n)]
    rng.shuffle(names)  # hidden topological order differs from name order
    graph = {name: [] for name in names}
    for i, name in enumerate(names):
        k = rng.randrange(0, min(i, 4) + 1)
        graph[name] = rng.sample(names[:i], k)
    durations = {name: rng.randrange(0, 20) for name in names}
    return graph, durations


def write(tmp_path, text):
    path = tmp_path / "p.toml"
    path.write_text(text)
    return path


def test_load_sample():
    graph, durations = dag.load_pipeline(SAMPLE)
    assert {k: sorted(v) for k, v in graph.items()} == {
        k: sorted(v) for k, v in SAMPLE_GRAPH.items()
    }
    assert durations["extract_orders"] == 5
    assert durations["audit_log"] == 1
    assert dag.load_pipeline(str(SAMPLE))[1] == durations


@pytest.mark.parametrize(
    "text",
    [
        "[tasks.a]\ndeps = ['ghost']\n",
        "[tasks.a]\ndeps = 'b'\n[tasks.b]\n",
        "[tasks.a]\ndeps = [1]\n",
        "[tasks.a]\nduration = -1\n",
        "[tasks.a]\nduration = 'long'\n",
        "[tasks.a]\nduration = true\n",
        "[jobs.a]\n",
        "this is not toml = = =",
    ],
)
def test_load_errors(tmp_path, text):
    with pytest.raises(dag.PipelineError):
        dag.load_pipeline(write(tmp_path, text))


def test_unknown_dependency_message_names_both_tasks(tmp_path):
    with pytest.raises(dag.PipelineError) as err:
        dag.load_pipeline(write(tmp_path, "[tasks.report]\ndeps = ['ghost']\n"))
    assert "report" in str(err.value) and "ghost" in str(err.value)


def test_topo_order_sample_is_deterministic():
    assert dag.topo_order(SAMPLE_GRAPH) == [
        "audit_log",
        "extract_customers",
        "clean_customers",
        "extract_orders",
        "clean_orders",
        "join_orders_customers",
        "customer_ltv",
        "daily_revenue",
        "publish_dashboard",
    ]


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_topo_order_random(seed):
    graph, _ = random_dag(seed)
    order = dag.topo_order(graph)
    assert order == ref_topo(graph)
    position = {t: i for i, t in enumerate(order)}
    assert all(position[d] < position[t] for t, deps in graph.items() for d in deps)


def assert_valid_cycle(graph, cycle):
    assert len(cycle) >= 2
    assert cycle[0] == cycle[-1]
    for x, y in pairwise(cycle):
        assert y in graph[x], (x, y)


@pytest.mark.parametrize(
    "graph",
    [
        {"a": ["a"]},
        {"a": ["b"], "b": ["a"]},
        {"start": [], "a": ["start", "c"], "b": ["a"], "c": ["b"], "z": ["a"]},
        {"x1": ["x2"], "x2": ["x3"], "x3": ["x4"], "x4": ["x2"], "free": []},
    ],
)
def test_cycles_are_reported_with_a_real_cycle(graph):
    with pytest.raises(dag.CycleError) as err:
        dag.topo_order(graph)
    assert isinstance(err.value, dag.PipelineError)
    assert_valid_cycle(graph, err.value.cycle)
    with pytest.raises(dag.CycleError):
        dag.levels(graph)


def test_self_dependency_cycle():
    with pytest.raises(dag.CycleError) as err:
        dag.topo_order({"a": ["a"], "b": []})
    assert err.value.cycle == ["a", "a"]


def test_unknown_dependency_in_graph_is_not_a_cycle():
    with pytest.raises(dag.PipelineError) as err:
        dag.topo_order({"a": ["missing"]})
    assert not isinstance(err.value, dag.CycleError)


def test_levels_sample():
    assert dag.levels(SAMPLE_GRAPH) == [
        ["audit_log", "extract_customers", "extract_orders"],
        ["clean_customers", "clean_orders"],
        ["join_orders_customers"],
        ["customer_ltv", "daily_revenue"],
        ["publish_dashboard"],
    ]
    assert dag.levels({}) == []


@pytest.mark.parametrize("seed", [6, 7, 8])
def test_levels_random(seed):
    graph, _ = random_dag(seed)
    assert dag.levels(graph) == ref_levels(graph)


def test_downstream():
    assert dag.downstream(SAMPLE_GRAPH, "extract_customers") == [
        "clean_customers",
        "customer_ltv",
        "daily_revenue",
        "join_orders_customers",
        "publish_dashboard",
    ]
    assert dag.downstream(SAMPLE_GRAPH, "daily_revenue") == ["publish_dashboard"]
    assert dag.downstream(SAMPLE_GRAPH, "audit_log") == []
    with pytest.raises(KeyError):
        dag.downstream(SAMPLE_GRAPH, "nope")


@pytest.mark.parametrize("seed", [9, 10])
def test_downstream_random(seed):
    graph, _ = random_dag(seed)
    for task in graph:
        expected = sorted(
            t for t in graph if t != task and task in _ancestors(graph, t)
        )
        assert dag.downstream(graph, task) == expected


def _ancestors(graph, task):
    seen, stack = set(), list(graph[task])
    while stack:
        d = stack.pop()
        if d not in seen:
            seen.add(d)
            stack.extend(graph[d])
    return seen


def test_critical_path_sample():
    graph, durations = dag.load_pipeline(SAMPLE)
    assert dag.critical_path(graph, durations) == (
        23,
        [
            "extract_orders",
            "clean_orders",
            "join_orders_customers",
            "customer_ltv",
            "publish_dashboard",
        ],
    )
    assert dag.critical_path({}, {}) == (0, [])


@pytest.mark.parametrize("seed", [11, 12, 13, 14])
def test_critical_path_random(seed):
    graph, durations = random_dag(seed)
    total, path = dag.critical_path(graph, durations)
    assert total == ref_longest(graph, durations)
    assert sum(durations[t] for t in path) == total
    assert graph[path[0]] == []
    for before, after in pairwise(path):
        assert before in graph[after]


def cli(*args):
    return subprocess.run(
        [sys.executable, "dag.py", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


def test_cli_modes():
    proc = cli(SAMPLE)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == dag.topo_order(SAMPLE_GRAPH)
    proc = cli(SAMPLE, "--levels")
    assert proc.stdout.splitlines() == [
        "0: audit_log extract_customers extract_orders",
        "1: clean_customers clean_orders",
        "2: join_orders_customers",
        "3: customer_ltv daily_revenue",
        "4: publish_dashboard",
    ]
    proc = cli(SAMPLE, "--critical")
    assert (
        proc.stdout.strip()
        == "23 extract_orders -> clean_orders -> join_orders_customers -> customer_ltv -> publish_dashboard"
    )


def test_cli_errors(tmp_path):
    proc = cli(write(tmp_path, "[tasks.a]\ndeps = ['b']\n[tasks.b]\ndeps = ['a']\n"))
    assert proc.returncode == 1
    assert proc.stderr.startswith("error:")
    proc = cli(write(tmp_path, "[tasks.a]\ndeps = ['ghost']\n"), "--levels")
    assert proc.returncode == 1
    assert "ghost" in proc.stderr
