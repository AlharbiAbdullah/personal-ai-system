"""The two judges: Opus through Claude Code and Gemini through agy, each on John's
subscriptions. Each rules PASS or FAIL on one criterion, apart from the other, so the report
can show where they disagree. Opus judging Claude answers leans toward Claude; Gemini is the
cross-family check. Neither judge sees which model or harness wrote the answer."""

import json
import sys
from pathlib import Path

from . import adapters

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "hooks"))

PROMPT = """You are a strict grader in a benchmark of an AI assistant. Rule PASS or FAIL on ONE criterion.

Criterion: {rubric}
{reference}
The request the assistant received:
<request>
{request}
</request>

The assistant's final answer:
<answer>
{answer}
</answer>

Judge only the criterion. Do not reward length or polish the criterion does not ask for.
Reply with ONLY this JSON, nothing else: {{"pass": true or false, "reason": "one sentence"}}"""


def build_prompt(check: dict, request: str, answer: str) -> str:
    ref = f"\nReference answer or facts:\n<reference>\n{check['reference']}\n</reference>\n" if check.get("reference") else ""
    return PROMPT.format(rubric=check["rubric"], reference=ref, request=request, answer=answer or "(empty)")


def parse_verdict(text: str) -> tuple:
    """(pass bool, reason) from the judge's reply; ValueError when it holds no verdict."""
    start, end = text.find("{"), text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("no JSON object")
    obj = json.loads(text[start:end])
    if not isinstance(obj.get("pass"), bool):
        raise ValueError("no boolean pass")
    return obj["pass"], str(obj.get("reason", ""))[:300]


def judge_argv(cfg: dict, prompt: str) -> tuple:
    """(harness, argv, stdin) for one judge call."""
    if cfg["harness"] == "claude-code":
        try:
            from lib.claude_cli import effort_args
            effort = effort_args(cfg["effort"]) if cfg.get("effort") else []
        except Exception:
            effort = []
        argv = ["claude", "-p", "--model", cfg["id"], *effort, "--output-format", "stream-json",
                "--verbose", "--max-turns", "3"]
        return "claude-code", argv, prompt
    if cfg["harness"] == "agy":
        argv = ["agy", "-p", prompt, "--model", cfg["id"], "--output-format", "stream-json",
                "--dangerously-skip-permissions", "--print-timeout", "0s"]
        return "agy", argv, None
    raise ValueError(f"no judge route for harness {cfg['harness']}")


def judge_one(name: str, cfg: dict, prompt: str, run) -> dict:
    """One judge's verdict: {verdict: bool|None, reason, infra, resets_at}. `run(harness, argv,
    stdin)` executes inside a sandbox and returns (stdout, stderr, code). One retry on a reply
    that holds no verdict; a rate limit is returned to the runner, never retried here."""
    harness, argv, stdin = judge_argv(cfg, prompt)
    last = ""
    for _ in range(2):
        out, err, code = run(harness, argv, stdin)
        o = adapters.parse(harness, out, err, code)
        if o.infra == "rate_limit":
            return {"verdict": None, "reason": o.detail, "infra": "rate_limit", "resets_at": o.resets_at}
        if o.infra:
            last = o.detail
            continue
        try:
            verdict, reason = parse_verdict(o.text)
            return {"verdict": verdict, "reason": reason, "infra": None, "resets_at": None}
        except (ValueError, json.JSONDecodeError) as e:
            last = f"unparseable: {e}: {o.text[:120]}"
    return {"verdict": None, "reason": last, "infra": "error", "resets_at": None}
