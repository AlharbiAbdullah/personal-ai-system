"""One adapter per harness: the headless command, and a parser that turns its output into an
Outcome (final answer, tool calls, usage, and whether the failure was the infrastructure's).

A rate-limited or crashed attempt is infrastructure: the runner re-runs it and never scores it.
`claude -p` can exit 0 with is_error true on a rate limit, so the result event decides, not the
exit code. The pi and OpenCode parsers follow their docs and stay unproven while their harness
is disabled in targets.toml.
"""

import json
import re
from dataclasses import dataclass, field

LIMIT_RE = re.compile(r"rate.?limit|usage limit|session limit|weekly limit|limit reached|hit your (?:\w+ )?limit|quota|resource.?exhausted"
                      r"|too many requests|\b429\b|overloaded", re.I)
EPOCH_RE = re.compile(r"\|(\d{10})\b")
MAX_TURNS = 40


@dataclass
class Outcome:
    text: str = ""
    tool_calls: list = field(default_factory=list)   # [{"name": str, "input": dict}]
    usage: dict = field(default_factory=dict)
    infra: str | None = None      # None | rate_limit | timeout | error
    detail: str = ""
    resets_at: float | None = None
    num_turns: int | None = None


def _lines(stdout: str):
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict):
            yield ev


def _classify_error(o: Outcome, message) -> Outcome:
    message = message if isinstance(message, str) else json.dumps(message, default=str)
    o.detail = message.strip()[:400]
    o.infra = "rate_limit" if LIMIT_RE.search(message) else "error"
    m = EPOCH_RE.search(message)
    if m:
        o.resets_at = float(m.group(1))
    return o


# ---------------------------------------------------------------- Claude Code

def claude_cmd(model: str, effort: str | None = None) -> list:
    """Prompt goes on stdin. Permissions are bypassed because the sandbox is the boundary."""
    return ["claude", "-p", "--model", model, *(["--effort", effort] if effort else []),
            "--output-format", "stream-json", "--verbose",
            "--permission-mode", "bypassPermissions", "--max-turns", str(MAX_TURNS)]


def parse_claude(stdout: str, stderr: str, code: int) -> Outcome:
    o, result = Outcome(), None
    for ev in _lines(stdout):
        t = ev.get("type")
        if t == "assistant":
            for item in (ev.get("message") or {}).get("content") or []:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    o.tool_calls.append({"name": item.get("name", ""), "input": item.get("input") or {}})
        elif t == "result":
            result = ev
    if result is None:
        return _classify_error(o, stderr or f"no result event, exit {code}")
    o.text = result.get("result") or ""
    o.usage = result.get("usage") or {}
    o.num_turns = result.get("num_turns")
    if result.get("is_error") or result.get("subtype", "success") != "success":
        msg = o.text or stderr or str(result.get("subtype") or "error")
        if result.get("subtype") == "error_max_turns":
            o.detail = "max turns reached"     # the agent's own failure: scored, not re-run
            return o
        return _classify_error(o, msg)
    return o


# ---------------------------------------------------------------- agy (Google Antigravity CLI)

def agy_cmd(model: str, prompt: str, effort: str | None = None) -> list:
    return ["agy", "-p", prompt, "--model", model, *(["--effort", effort] if effort else []),
            "--output-format", "stream-json", "--dangerously-skip-permissions", "--print-timeout", "0s"]


def parse_agy(stdout: str, stderr: str, code: int) -> Outcome:
    o, result, seen, text = Outcome(), None, set(), []
    for ev in _lines(stdout):
        t = ev.get("type")
        if t == "step_update":
            info = ev.get("tool_info") or {}
            name = info.get("name") or ev.get("tool_name")
            key = (ev.get("step_index"), name)
            if name and key not in seen:
                seen.add(key)
                o.tool_calls.append({"name": name, "input": info.get("parameters") or {}})
            if ev.get("text_delta"):
                text.append(ev["text_delta"])
        elif t == "result":
            result = ev
    if result is None:
        return _classify_error(o, stderr or f"no result event, exit {code}")
    o.text = result.get("response") or "".join(text)
    o.usage = result.get("usage") or {}
    o.num_turns = result.get("num_turns")
    if result.get("status") != "SUCCESS" or result.get("error"):
        return _classify_error(o, result.get("error") or stderr or str(result.get("status")))
    return o


# ---------------------------------------------------------------- pi (disabled until a compliant route)

def pi_cmd(model: str, prompt: str) -> list:
    return ["pi", "-p", "--mode", "json", "--model", model, "--no-session", prompt]


def parse_pi(stdout: str, stderr: str, code: int) -> Outcome:
    o, last = Outcome(), None
    for ev in _lines(stdout):
        t = ev.get("type")
        if t == "tool_execution_start":
            o.tool_calls.append({"name": ev.get("toolName", ""), "input": ev.get("args") or {}})
        elif t == "message_end" and (ev.get("message") or {}).get("role") == "assistant":
            last = ev["message"]
    if last is None:
        return _classify_error(o, stderr or f"no assistant message, exit {code}")
    content = last.get("content") or []
    o.text = "".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    o.usage = last.get("usage") or {}
    if last.get("stopReason") == "error":
        return _classify_error(o, last.get("errorMessage") or stderr or "error")
    return o


# ---------------------------------------------------------------- OpenCode (disabled until a compliant route)

def opencode_cmd(model: str, prompt: str) -> list:
    return ["opencode", "run", "--format", "json", "--model", model, "--auto", prompt]


def parse_opencode(stdout: str, stderr: str, code: int) -> Outcome:
    o, text, errors = Outcome(), [], []
    for ev in _lines(stdout):
        t = ev.get("type")
        part = ev.get("part") or {}
        if t == "text":
            text.append(part.get("text", ""))
        elif t == "tool_use":
            o.tool_calls.append({"name": part.get("tool", ""), "input": (part.get("state") or {}).get("input") or {}})
        elif t == "step_finish":
            for k, v in (part.get("tokens") or {}).items():
                if isinstance(v, (int, float)):
                    o.usage[k] = o.usage.get(k, 0) + v
        elif t == "error":
            errors.append(json.dumps(ev.get("error") or ev))
    o.text = "".join(text)
    if errors or (code != 0 and not o.text):
        return _classify_error(o, " ".join(errors) or stderr or f"exit {code}")
    return o


# ---------------------------------------------------------------- registry

def command(harness: str, model: str, prompt: str, effort: str | None = None) -> tuple:
    """(argv, stdin text or None) for one attempt."""
    if harness == "claude-code":
        return claude_cmd(model, effort), prompt
    if harness == "agy":
        return agy_cmd(model, prompt, effort), None
    if harness == "pi":
        return pi_cmd(model, prompt), None
    if harness == "opencode":
        return opencode_cmd(model, prompt), None
    raise ValueError(f"no adapter for harness {harness}")


PARSERS = {"claude-code": parse_claude, "agy": parse_agy, "pi": parse_pi, "opencode": parse_opencode}


def parse(harness: str, stdout: str, stderr: str, code: int) -> Outcome:
    return PARSERS[harness](stdout, stderr, code)
