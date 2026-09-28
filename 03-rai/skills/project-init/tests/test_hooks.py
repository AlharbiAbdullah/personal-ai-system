"""project-init v3, milestone M6: the Claude Code hooks of project.py.

`project.py hook pre-bash` (PreToolUse, matcher Bash) blocks with exit 2 and one stderr line;
`project.py hook session-start` prints the derived block of design section 8, 3 KB at most.
Both read Claude Code's hook JSON on stdin, and project.py is their launcher: from another
worktree of the repo, that worktree's own scripts/project.py runs.

The pre-bash cases of design 6.P5 run in-process (`pre_bash()` on the parsed JSON) and through
the real script. The session-start and launcher tests build a small repo by hand from
tests/fixtures (tipcalc on main, the feat1 change on feat/entrypoint-hardening, the rendered
.githooks) with no network and no mise task run; `project.py selftest` repeats the P5 cases, the
3 KB cap and the launcher (test_gates.py checks its rows).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent
PROJECT_PY = SKILL / "templates" / "scripts" / "project.py"
HOOKS = SKILL / "templates" / "githooks"
SETTINGS = SKILL / "templates" / "settings.json"
FIXTURES = TESTS / "fixtures"
FEAT = "feat/entrypoint-hardening"
CHANGE = "specs/changes/2026-09-24-entrypoint-hardening"
MERGED_BY = "Merged-By: mise run merge"
GATES = "specs/README.md#gates"
MARK = "test: the worktree's own project.py ran"

# design 6.P5: pre-bash must deny these ...
DENY = (
    "mise run merge",
    'sh -c "PROJECT_MERGE=1 git merge x"',
    "bash ./x.sh",  # x.sh contains PROJECT_MERGE=1
    "git -c core.hooksPath=/dev/null commit",
    "git -c core.hookspath=/dev/null commit",
    "git -c hook.project-main-guard.enabled=false branch -f main x",
    "git send-pack origin feat/x:main",
    "gh api -X PUT repos/o/r/pulls/1/merge",
    "gh api -X DELETE repos/o/r/branches/main/protection",
    "cp /tmp/h .githooks/pre-commit",
)
# ... and allow these (the read-only exemption, and a pattern that only looks like one)
ALLOW = (
    "grep -n PROJECT_MERGE scripts/project.py",
    "git config --get core.hooksPath",
    "grep -- --no-verify specs/README.md",
    "mise run test -- -k merge",
)
# the rest of design 6.P4's pattern list, and forms an agent types
MORE_DENY = (
    "mise r merge",
    "mise approve",
    "FOO=1 mise run merge",
    "mise run -q release",
    "mise tasks run abandon",
    "uv run --script scripts/project.py merge",
    'python3 "$CLAUDE_PROJECT_DIR/scripts/project.py" approve',
    "git commit --no-verify -m x",
    "git commit --no-veri -m x",  # git takes an unambiguous prefix of a long option
    "git push --no-verify origin feat/x",
    "git commit -nm x",
    "git commit -an -m x",
    "git -c HOOK.Project-Main-Guard.Command=true commit -m x",
    "git config --unset hook.project-main-guard.command",
    "git config --remove-section hook.project-main-guard",
    "git config --rename-section 'hook.project-main-guard' old",
    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git commit",
    "GIT_CONFIG_PARAMETERS=x git commit",
    # rollout review R2: what picks, or writes, the git config whose url.<base>.insteadOf rules
    # the main guard follows when it confirms a sync from origin
    "GIT_CONFIG_GLOBAL=evil.gitconfig git pull --ff-only origin main",
    "GIT_CONFIG_SYSTEM=/tmp/x git pull --ff-only origin main",
    "git config --global url.file:///tmp/fake.insteadOf https://github.com/o/r.git",
    "git -c url.file:///tmp/fake.insteadOf=https://github.com/o/r.git pull",
    "git config --global include.path /tmp/x",
    "git -C . config --system core.pager cat",
    "cp /tmp/x ~/.gitconfig",
    "echo '[include]' >> ~/.config/git/config",
    "printf '[core]\\n' > ~/.gitconfig",
    "cat /tmp/x > ~/.gitconfig",
    # a print's or a read's words count once its output feeds a $(...), a pipe to another
    # program or a file: the name becomes a write's argument (tail-verify r1)
    'cp /tmp/x "$(echo ~/.gitconfig)"',
    "cp /tmp/x $(printf %s ~/.gitconfig)",
    "cp /tmp/x `echo ~/.gitconfig`",
    "cat /tmp/x > $(echo ~/.gitconfig)",
    "echo ~/.gitconfig | xargs -I{} cp /tmp/x {}",
    "find ~ -maxdepth 1 -name .gitconfig | xargs sed -i 's/a/b/'",
    "ls ~/.gitconfig | xargs rm",
    "grep -l core ~/.gitconfig | xargs sed -i 's/a/b/'",
    "cat ~/.gitconfig | grep -l core | xargs rm",
    "echo ~/.gitconfig > /tmp/list; xargs -a /tmp/list cp /tmp/x",
    "{ echo ~/.gitconfig; } > /tmp/list",
    "(echo ~/.gitconfig)|xargs rm",
    "echo ~/.gitconfig |& xargs rm",
    "ls ~/.gitconfig > >(xargs rm)",
    "xargs -a <(echo ~/.gitconfig) rm",
    "bash -c 'echo ~/.gitconfig' | xargs rm",
    "xargs -I{} cp /tmp/x {} <<< ~/.gitconfig",
    "HOME=/tmp/h git pull --ff-only origin main",
    "env HOME=/tmp/h git fetch origin main:main",
    "export XDG_CONFIG_HOME=/tmp/h",
    # rollout finding D: judged by command structure, so these forms still count
    "HOME=$(mktemp -d) git pull --ff-only origin main",
    "HOME=/tmp/h; git pull --ff-only origin main",
    "XDG_CONFIG_HOME=/tmp/x timeout 30 git fetch origin main:main",
    "sh -c 'HOME=/tmp/h git pull'",
    "HOME=/tmp/h bash -c 'git pull'",
    "echo $(HOME=/tmp/h git pull)",
    "declare -x HOME=/tmp/h",
    "git config url.file:///tmp/fake.insteadOf https://github.com/o/r.git",
    "git config set --global core.sshCommand /tmp/fake-ssh",
    "git config --file ~/.gitconfig user.name x",
    "git -c url.a.pushInsteadOf=b push origin feat/x",
    "git --config-env=url.a.insteadOf=URL pull",
    "git show HEAD:notes > ~/.gitconfig",
    "tee -a ~/.gitconfig.local < /tmp/x",
    "sed -i s/a/b/ /etc/gitconfig",
    "rm -r .githooks",
    "echo hi > .git/config",
    "chmod -x .git/hooks/pre-commit",
    "gh pr merge 1 --squash",
    "gh repo edit --visibility public",
    "gh repo delete o/r --yes",
    "gh ruleset list",
    "gh api repos/o/r/issues -f title=x",
    "gh api --method=PATCH repos/o/r",
    "gh api -XPOST repos/o/r/merges",
    "gh api repos/o/r/contents/x --input body.json",
    "eval 'PROJECT_MERGE=1 git merge x'",
    "echo $(mise run merge)",
    "grep PROJECT_MERGE specs/README.md > notes.txt",
    "sed -i 's/PROJECT_MERGE//' specs/README.md",
    "sed -n '1e PROJECT_MERGE=1 git merge x' specs/README.md",
    "find . -name .githooks -delete",
    "cat .githooks/pre-commit | tee copy",
    "rg --pre cat PROJECT_MERGE",
    "git diff --output=x .githooks",
    "echo 'an open quote PROJECT_MERGE",
    # a user config path reaches a write through a variable (tail-verify r2)
    'f=~/.gitconfig; cp /tmp/x "$f"',
    'f="$HOME/.gitconfig"; cp /tmp/evil "$f"',
    "F=~/.gitconfig && sed -i 's/a/b/' \"$F\"",
    '{ f=~/.gitconfig; }; cp /tmp/x "$f"',
    'f=~/.gitconfig g=1; mv /tmp/x "$f"',
    "bash -c 'f=~/.gitconfig; cp /tmp/x \"$f\"'",
    'printf -v f %s ~/.gitconfig; cp /tmp/x "$f"',
    "printf -v f '%s' \"$HOME/.gitconfig\" && cp /tmp/x \"$f\"",
)
MORE_ALLOW = (
    "ls -la",
    "mise run status",
    "mise run -q test -- -k merge",
    "uv run pytest -k merge",
    "git commit -am 'feat(cli): x'",
    "git commit --amend --no-edit",
    "git commit -m 'fix: a typo in hook.py'",
    "git log --grep commit -n 5",
    "gh api repos/o/r/pulls/1",
    "gh api -X GET search/issues -f q=merge",
    "grep PROJECT_MERGE specs/README.md 2>/dev/null | head -3",
    "grep -rn 'mise run merge' specs >/dev/null 2>&1",
    "sed -n '/PROJECT_MERGE/p' specs/README.md",
    "sed -n '10,20p' scripts/project.py",
    "cat .git/config",
    "ls .githooks && cat .githooks/pre-push",
    "git log --grep PROJECT_MERGE",
    "git -C . log -1 --format=%H -- .githooks",
    "git branch --list '*merge*'",
    "cd specs && grep -n core.hooksPath README.md",
    "find . -path ./.git -prune -o -name '*.githooks*' -print",
    "uv run --script scripts/project.py status",  # the gate script itself is not a script to read
    "git config --global --get user.name",
    "git config --show-scope --get-regexp '^url\\..*\\.insteadof$'",
    "cat ~/.gitconfig",
    'echo "$HOME"',
    # reads are not writes: a program that only prints or reads a config path writes nothing
    'echo "$HOME/.gitconfig"',
    "printf '%s\\n' ~/.config/git/config",
    "cat ~/.gitconfig && echo done",
    "grep -n sshCommand ~/.gitconfig; echo $?",
    "cat ~/.gitconfig | grep -n url && echo done",  # piped into a read: still the terminal
    "echo ~/.gitconfig | wc -c",
    "ls -la ~/.gitconfig 2>/dev/null || echo none",
    "bash -c 'cat ~/.gitconfig && echo done'",
    "export PATH=$HOME/bin:$PATH",
    "CARGO_HOME=/tmp/c cargo build",
    # rollout finding D: text inside a message, a scratch HOME for another tool, a file name
    'git commit -m "docs: explain the insteadOf rule in the README"',
    "HOME=$(mktemp -d) uv run pytest -q",
    "docker run --rm -e HOME=/root alpine true",
    "uv run pytest tests/test_gitconfig.py",
    "git log --grep insteadOf",
    "echo 'set HOME=/tmp and XDG_CONFIG_HOME=/x in the docs'",
    "git config --global core.editor",
    "git config core.sshCommand 'ssh -i deploy_key'",
    "GIT_SSH_COMMAND='ssh -v' git fetch origin",
)


def load_project() -> ModuleType:
    spec = importlib.util.spec_from_file_location("project_hooks_under_test", PROJECT_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no __pycache__ in templates/
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = keep
    return module


project = load_project()


def clean_env(trusted: Path | None) -> dict[str, str]:
    drop = ("GIT_", "PYTEST_", "GITHUB_", "PROJECT_", "MISE_TRUSTED")
    env = {k: v for k, v in os.environ.items() if not k.startswith(drop)}
    for key in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH", "CLAUDE_PROJECT_DIR"):
        env.pop(key, None)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Test Author",
        GIT_AUTHOR_EMAIL="author@example.com",
        GIT_COMMITTER_NAME="Test Author",
        GIT_COMMITTER_EMAIL="author@example.com",
    )
    if trusted is not None:
        env["MISE_TRUSTED_CONFIG_PATHS"] = str(trusted)  # never writes mise's trust store
    return env


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env or clean_env(root),
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def bash_payload(command: str, cwd: Path) -> dict[str, object]:
    return {
        "session_id": "t",
        "cwd": str(cwd),
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "test"},
    }


def run_hook(
    script: Path,
    name: str,
    stdin: str,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "hook", name],
        input=stdin,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env or clean_env(cwd),
        timeout=120,
    )


def verdict(command: str, cwd: Path, roots: list[Path] | None = None) -> str | None:
    payload = json.loads(json.dumps(bash_payload(command, cwd)))
    return project.pre_bash(payload, cwd, roots if roots is not None else [cwd])


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    """A git repo with x.sh (which sets PROJECT_MERGE) and a copy of project.py."""
    root = tmp_path / "scratch"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "x.sh").write_text("#!/bin/sh\nPROJECT_MERGE=1 git merge x\n", encoding="utf-8")
    (root / "scripts").mkdir()
    shutil.copy2(PROJECT_PY, root / "scripts" / "project.py")
    (root / "specs").mkdir()
    return root


# ---------------------------------------------------------------------------------------------
# settings.json


def test_settings_json_runs_both_hooks_through_mise() -> None:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    base = 'mise x -- uv run --script "$CLAUDE_PROJECT_DIR/scripts/project.py" hook'
    ((start,),) = [
        [h["command"] for h in entry["hooks"]] for entry in settings["hooks"]["SessionStart"]
    ]
    (bash,) = settings["hooks"]["PreToolUse"]
    assert start.startswith(f"{base} session-start || echo ")
    assert bash["matcher"] == "Bash"
    assert [h["command"] for h in bash["hooks"]] == [f"{base} pre-bash"]
    assert all(h["type"] == "command" for h in bash["hooks"])


# ---------------------------------------------------------------------------------------------
# pre-bash


@pytest.mark.parametrize("command", DENY + MORE_DENY)
def test_pre_bash_denies(scratch: Path, command: str) -> None:
    assert verdict(command, scratch) is not None


@pytest.mark.parametrize("command", ALLOW + MORE_ALLOW)
def test_pre_bash_allows(scratch: Path, command: str) -> None:
    assert verdict(command, scratch) is None


def test_the_p5_cases_through_the_script(scratch: Path) -> None:
    """The real hook: exit 2 and one stderr line that points at the gates for each deny case,
    exit 0 and silence for each allow case."""
    script = scratch / "scripts" / "project.py"
    for command in DENY:
        done = run_hook(script, "pre-bash", json.dumps(bash_payload(command, scratch)), cwd=scratch)
        assert done.returncode == 2, (command, done.stderr)
        (line,) = done.stderr.splitlines()
        assert line.startswith("pre-bash: blocked `") and line.endswith(f"(see {GATES})"), line
        assert done.stdout == ""
    for command in ALLOW:
        done = run_hook(script, "pre-bash", json.dumps(bash_payload(command, scratch)), cwd=scratch)
        assert (done.returncode, done.stdout, done.stderr) == (0, "", ""), command


@pytest.mark.parametrize(
    "stdin",
    [
        "",
        "not json",
        "[1, 2]",
        '{"tool_name": "Bash", "tool_input": 5}',
        '{"tool_name": "Bash", "tool_input": {"command": 7}}',
        '{"tool_name": "Write", "tool_input": {"file_path": ".githooks/pre-commit"}}',
        '{"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": "/no/such/dir"}',
    ],
)
def test_pre_bash_fails_open_on_malformed_input(scratch: Path, stdin: str) -> None:
    done = run_hook(scratch / "scripts" / "project.py", "pre-bash", stdin, cwd=scratch)
    assert done.returncode == 0, done.stderr


def test_pre_bash_outside_a_git_repo_still_denies(tmp_path: Path) -> None:
    """No repo at the cwd, none around the script: the patterns still hold."""
    loose = tmp_path / "loose"
    loose.mkdir()
    script = loose / "project.py"
    shutil.copy2(PROJECT_PY, script)
    payload = json.dumps(bash_payload("mise run merge", loose))
    assert run_hook(script, "pre-bash", payload, cwd=loose).returncode == 2
    payload = json.dumps(bash_payload("ls", loose))
    assert run_hook(script, "pre-bash", payload, cwd=loose).returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "sh x.sh",
        "source x.sh",
        ". ./x.sh",
        "zsh -e x.sh",
        "./x.sh",
        "env A=1 nohup bash x.sh",
        "timeout 5 bash x.sh",
        "bash -c 'bash x.sh'",
        "cd sub && bash inner.sh",
        "bash calls.sh",  # calls.sh runs x.sh
        "python3 hooks_off.py",
        "python -u hooks_off.py",
        "uv run hooks_off.py",
        "uv run --with rich python hooks_off.py",
        "uv run --script tool",
        "node guard_off.js",
        "bash link.sh",  # a symlink inside the repo, to a script outside it
    ],
)
def test_script_indirection(scratch: Path, tmp_path: Path, command: str) -> None:
    (scratch / "sub").mkdir()
    (scratch / "sub" / "inner.sh").write_text("git -c core.hooksPath=/x commit\n", "utf-8")
    (scratch / "calls.sh").write_text("#!/bin/sh\nset -e\nbash x.sh\n", "utf-8")
    (scratch / "hooks_off.py").write_text('import os\nos.system("git commit -n")\n', "utf-8")
    (scratch / "tool").write_text("import subprocess\n# send-pack origin x:main\n", "utf-8")
    (scratch / "guard_off.js").write_text("run('gh pr merge 1')\n", "utf-8")
    outside = tmp_path / "outside.sh"
    outside.write_text("mise run merge\n", "utf-8")
    (scratch / "link.sh").symlink_to(outside)
    reason = verdict(command, scratch)
    assert reason is not None and re.match(r"`[^`]+` in \S+: ", reason), reason


def test_script_indirection_reads_temp_dirs_only_besides_the_repo(
    scratch: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setenv("TMPDIR", str(temp))
    (temp / "t.sh").write_text("PROJECT_MERGE=1 git merge x\n", "utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "e.sh").write_text("PROJECT_MERGE=1 git merge x\n", "utf-8")
    assert verdict(f"bash {temp / 't.sh'}", scratch) is not None
    # a program outside the repo and the temp dirs is the design's honest limit (3.2)
    assert verdict(f"bash {elsewhere / 'e.sh'}", scratch) is None


def test_script_indirection_reads_256_kb(scratch: Path) -> None:
    filler = "# filler\n" * (256 * 1024 // 10)
    (scratch / "early.sh").write_text(filler + "PROJECT_MERGE=1 git merge x\n", "utf-8")
    (scratch / "late.sh").write_text(filler * 2 + "PROJECT_MERGE=1 git merge x\n", "utf-8")
    assert verdict("bash early.sh", scratch) is not None
    assert verdict("bash late.sh", scratch) is None


def test_git_config_rules_are_read_from_command_structure(scratch: Path) -> None:
    """Rollout finding D: what writes or picks the git config the main guard trusts is judged
    by command structure, in a script file too; the same words in a message pass."""
    (scratch / "pull.sh").write_text("#!/bin/sh\nHOME=/tmp/h git pull origin main\n", "utf-8")
    (scratch / "note.sh").write_text(
        "#!/bin/sh\ngit commit -m 'docs: HOME=/tmp and the insteadOf rule'\n", "utf-8"
    )
    reason = verdict("bash pull.sh", scratch)
    assert reason == (
        "`HOME=/tmp/h git pull origin main` in pull.sh: HOME and XDG_CONFIG_HOME pick the git "
        "config the main guard trusts"
    ), reason
    assert verdict("bash note.sh", scratch) is None
    reason = verdict("HOME=$(mktemp -d) git pull", scratch)
    assert reason is not None and reason.startswith("`HOME=$(...) git pull`: HOME and"), reason
    reason = verdict("git config --global url.x.insteadOf y", scratch)
    assert reason is not None and reason.endswith(
        "git config are a person's (the main guard trusts them)"
    ), reason
    reason = verdict("git config url.x.insteadOf y", scratch)
    assert reason is not None and "a url.<base>.insteadOf rule can point origin" in reason


def test_a_script_run_through_a_read_is_not_read(scratch: Path) -> None:
    """cat x.sh only prints it; bash runs it."""
    assert verdict("cat x.sh", scratch) is None
    assert verdict("cat x.sh | bash", scratch) is None  # piped text: the honest limit (3.2)
    assert verdict("bash x.sh", scratch) is not None


# ---------------------------------------------------------------------------------------------
# session-start

LESSONS = "# Lessons\n" + "".join(
    f"\n## 2026-09-{day:02d} | lesson {day:02d} {'long title words ' * 8}\n"
    f"Trigger: something surprised us on day {day}\n"
    f"Rule: lesson rule {day:02d} {'do the careful thing ' * 12}\n"
    for day in (3, 1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 11)  # a union merge interleaves them
)
DECISIONS = {
    "2026-09-01-first.md": ("active", "First choice"),
    "2026-09-02-second.md": ("superseded by 2026-09-05-fifth", "Second choice"),
    "2026-09-03-third.md": ("active", "Third choice"),
    "2026-09-04-fourth.md": ("active", "Fourth choice"),
    "2026-09-05-fifth.md": ("active", "Fifth choice"),
}


MISE_TOML = (
    '[tools]\ngitleaks = "8.30.1"\n'  # pre-commit's scanner, as the rendered mise.toml pins it
)


def adr(status: str, title: str) -> str:
    return (
        f"---\nstatus: {status}   # active | superseded by <date>-<slug>\n"
        "# aliases: [D-1]\n---\n<!-- decision (ADR) -->\n"
        f"# {title}\n\n## Context\nx\n\n## Decision\ny\n"
    )


def results_json(ids: list[str], files: dict[str, str]) -> str:
    nodes = {
        f"tests/test_cli.py::test_{sid.split('.')[1].replace('-', '_')}": {
            "ids": [sid],
            "outcome": "passed",
            "body": "",
        }
        for sid in ids
    }
    finished = datetime.now(UTC).isoformat(timespec="seconds")
    data = {"format": 3, "complete": True, "finished": finished, "nodes": nodes, "files": files}
    return json.dumps(data)


@pytest.fixture(scope="module")
def adopted(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """tipcalc as the gates see it: main adopted (one Merged-By commit), feat/entrypoint-hardening
    with its approved change, the rendered .githooks, `hook install` done."""
    root = tmp_path_factory.mktemp("m6") / "tipcalc"
    root.mkdir()
    env = clean_env(root)
    git(root, "init", "-q", "-b", "main", env=env)
    shutil.copytree(FIXTURES / "tipcalc" / "specs", root / "specs")
    shutil.copy2(FIXTURES / "tipcalc" / "project.toml", root / ".project.toml")
    shutil.copy2(FIXTURES / "tipcalc" / "gitignore", root / ".gitignore")
    (root / "scripts").mkdir()
    shutil.copy2(PROJECT_PY, root / "scripts" / "project.py")
    (root / ".githooks").mkdir()
    for hook in ("pre-commit", "commit-msg", "pre-push", "reference-transaction"):
        text = (HOOKS / hook).read_text(encoding="utf-8").replace("{DEFAULT_BRANCH}", "main")
        (root / ".githooks" / hook).write_text(text, encoding="utf-8")
        (root / ".githooks" / hook).chmod(0o755)
    (root / "mise.toml").write_text(MISE_TOML, encoding="utf-8")
    memory = root / "project_memory"
    (memory / "decisions").mkdir(parents=True)
    (memory / "lessons.md").write_text(LESSONS, encoding="utf-8")
    for name, (status, title) in DECISIONS.items():
        (memory / "decisions" / name).write_text(adr(status, title), encoding="utf-8")
    git(root, "add", "-A", env=env)
    git(root, "commit", "-q", "-m", f"chore(init): adopt\n\n{MERGED_BY}", env=env)
    git(root, "switch", "-q", "-c", FEAT, env=env)
    shutil.copytree(FIXTURES / "feat1" / "specs", root / "specs", dirs_exist_ok=True)
    requirements = root / CHANGE / "requirements.md"
    text = requirements.read_text(encoding="utf-8").replace("status: draft", "status: approved")
    requirements.write_text(text, encoding="utf-8")
    git(root, "add", "-A", env=env)
    git(root, "commit", "-q", "-m", "spec(entrypoint-hardening): approve", env=env)
    installed = run_hook_install(root, env)
    assert installed.returncode == 0, installed.stdout + installed.stderr
    return root


def run_hook_install(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/project.py", "hook", "install"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def repo(adopted: Path, tmp_path: Path) -> Path:
    dest = tmp_path / "tipcalc"
    shutil.copytree(adopted, dest, symlinks=True)
    installed = run_hook_install(dest, clean_env(dest))  # the pinned guard names its repo's blob
    assert installed.returncode == 0, installed.stderr
    return dest


def session_start(
    root: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {
            "session_id": "t",
            "cwd": str(root),
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
    )
    return run_hook(root / "scripts" / "project.py", "session-start", payload, cwd=root, env=env)


def test_session_start_prints_the_derived_block(repo: Path) -> None:
    g1 = ["cli.tip-default", "cli.no-args", "cli.help", "cli.bad-amount", "cli.negative-amount"]
    (repo / "notes.txt").write_text("untracked\n", encoding="utf-8")
    files = project.tree_files(repo)
    (repo / ".cache").mkdir()
    (repo / ".cache" / "spec-results.json").write_text(results_json(g1, files), encoding="utf-8")
    done = session_start(repo)
    assert done.returncode == 0, done.stderr
    out = done.stdout
    lines = out.splitlines()
    assert lines[0] == (
        f"[tipcalc] {FEAT} | change entrypoint-hardening (approved) | hooks on | mise trusted"
    ), out
    assert "WARNING" not in out, out
    assert re.fullmatch(
        r"next: G2 env knob: config\.percent-empty config\.percent-invalid "
        r"\(no passing tests; results \d\d:\d\d\) \| dirty: 1",
        lines[1],
    ), out
    assert lines[2].startswith("audit main: ok (1 commit since adoption"), out
    assert "AGENTS" not in out
    assert len(out.encode()) <= 3 * 1024


def test_session_start_keeps_the_newest_5_lessons_and_3_active_decisions(repo: Path) -> None:
    out = session_start(repo).stdout
    assert len(out.encode()) <= 3 * 1024, len(out.encode())
    lessons = [
        line for line in out.splitlines() if line.startswith("- 2026-09-") and "lesson" in line
    ]
    assert [line.split()[1] for line in lessons] == [f"2026-09-{d:02d}" for d in range(8, 13)], out
    assert "lessons (newest 5):" in out
    assert "| Rule: lesson rule 12 do the careful thing" in out
    shown = [title for _, title in DECISIONS.values() if title in out]
    assert shown == ["Third choice", "Fourth choice", "Fifth choice"], out
    assert "decisions (active, newest 3):" in out
    assert "(2026-09-05-fifth.md)" in out
    assert "aliases" not in out


def test_session_start_warns_loudly(repo: Path, tmp_path: Path) -> None:
    """hooks off, mise untrusted, gitleaks missing, and main commits the audit flags."""
    env = clean_env(repo)
    git(repo, "switch", "-q", "main", env=env)
    (repo / "README.md").write_text("# tipcalc\n", encoding="utf-8")
    git(repo, "add", "README.md", env=env)
    sneak = {**env, "PROJECT_MERGE": "1"}  # the guard lets it pass; the audit still sees it
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "docs: sneak", env=sneak)
    git(repo, "switch", "-q", FEAT, env=env)
    git(repo, "config", "--unset", "core.hooksPath", env=env)
    bin_dir = tmp_path / "bin"  # git and mise, and no gitleaks
    bin_dir.mkdir()
    for tool in ("git", "mise"):
        found = shutil.which(tool)
        assert found is not None
        (bin_dir / tool).symlink_to(found)
    bare = {**clean_env(None), "PATH": str(bin_dir)}
    done = session_start(repo, env=bare)
    assert done.returncode == 0, done.stderr
    out = done.stdout
    head = out.splitlines()[0]
    assert "| hooks OFF |" in head and head.endswith("mise UNTRUSTED"), out
    assert "WARNING: git gates off: git config core.hooksPath is unset" in out, out
    assert "WARNING: mise does not trust this repo's config" in out, out
    assert "WARNING: gitleaks is not runnable here" in out, out
    assert "WARNING: audit: " in out and '"docs: sneak" on main' in out, out
    assert "audit main: 1 of 2 commits since adoption" in out, out


def test_session_start_on_the_default_branch_names_the_roadmap(repo: Path) -> None:
    """On main, the head line says what `mise run change` would: the open feat branch first
    (I8), and the next roadmap item only once no change is open."""
    env = clean_env(repo)
    git(repo, "switch", "-q", "main", env=env)
    out = session_start(repo).stdout
    assert out.splitlines()[0].startswith(f"[tipcalc] main | change open on {FEAT} | hooks on"), out
    assert f"next: finish {FEAT} first (`git switch {FEAT}`): one change at a time (I8)" in out
    git(repo, "branch", "-D", FEAT, env=env)
    out = session_start(repo).stdout
    assert out.splitlines()[0].startswith("[tipcalc] main | no open change | hooks on"), out
    assert 'next: roadmap item entrypoint-hardening (start it: /sdd "entrypoint-hardening")' in out


def test_session_start_always_exits_0(tmp_path: Path) -> None:
    loose = tmp_path / "loose"
    loose.mkdir()
    shutil.copy2(PROJECT_PY, loose / "project.py")
    for stdin in ("", "garbage", json.dumps({"cwd": str(loose)})):
        done = run_hook(loose / "project.py", "session-start", stdin, cwd=loose)
        assert done.returncode == 0, done.stderr
        assert "not inside a git repository" in done.stdout
    broken = tmp_path / "broken"
    broken.mkdir()
    git(broken, "init", "-q", "-b", "main")
    (broken / "scripts").mkdir()
    shutil.copy2(PROJECT_PY, broken / "scripts" / "project.py")
    (broken / ".project.toml").write_text("this is [not toml\n", encoding="utf-8")
    done = session_start(broken)
    assert done.returncode == 0, done.stderr
    assert "session-start failed" in done.stdout and ".project.toml" in done.stdout


def test_render_session_is_tail_capped() -> None:
    """Over 3 KB, the oldest entries go first; each line is cut at 300 characters."""
    head = ["[x] feat/y | change y (approved) | hooks on | mise trusted", *["W" * 1000] * 4]
    lessons = [
        (f"2026-01-{d:02d}", f"- 2026-01-{d:02d} lesson {d:02d} " + "l" * 400) for d in range(1, 6)
    ]
    decisions = [
        (f"2026-01-{d:02d}", f"- 2026-01-{d:02d} adr {d:02d} " + "d" * 400) for d in (2, 4, 6)
    ]
    out = project.render_session(head, lessons, decisions)
    assert len(out.encode()) <= project.SESSION_CAP
    assert out.startswith("[x] feat/y")
    assert all(len(line) <= project.SESSION_LINE_CAP for line in out.splitlines())
    kept = [line.split()[2] + line.split()[3] for line in out.splitlines() if line.startswith("- ")]
    assert kept and "lesson05" in kept and "adr06" in kept
    assert "lesson01" not in kept and "adr02" not in kept
    small = project.render_session(["h"], lessons[:2], [])
    assert small.splitlines()[1:] == [
        "lessons (newest 2):",
        *(project.clip(l) for _, l in lessons[:2]),
    ]


# ---------------------------------------------------------------------------------------------
# the launcher


def worktree(repo: Path, tmp_path: Path, branch: str) -> Path:
    wt = tmp_path / f"wt-{branch.replace('/', '-')}"
    git(repo, "worktree", "add", "-q", "-b", branch, str(wt), "main", env=clean_env(repo))
    return wt


def test_the_launcher_runs_the_worktree_copy(repo: Path, tmp_path: Path) -> None:
    wt = worktree(repo, tmp_path, "feat/other")
    script = wt / "scripts" / "project.py"
    text = script.read_text(encoding="utf-8")
    script.write_text(text.replace("\ndef main(", f"\nprint({MARK!r})\n\n\ndef main(", 1), "utf-8")
    main_script = repo / "scripts" / "project.py"
    env = clean_env(repo)
    there = run_hook(main_script, "pre-bash", json.dumps(bash_payload("ls", wt)), cwd=repo, env=env)
    assert (there.returncode, there.stdout) == (0, MARK + "\n"), there.stderr
    deny = json.dumps(bash_payload("mise run merge", wt))
    blocked = run_hook(main_script, "pre-bash", deny, cwd=repo, env=env)
    assert blocked.returncode == 2 and MARK in blocked.stdout, blocked.stderr
    start = json.dumps(
        {"session_id": "t", "cwd": str(wt / "src"), "hook_event_name": "SessionStart"}
    )
    (wt / "src").mkdir(exist_ok=True)
    began = run_hook(main_script, "session-start", start, cwd=repo, env=env)
    assert began.returncode == 0 and began.stdout.startswith(
        MARK + "\n[wt-feat-other] feat/other |"
    )
    here = run_hook(
        main_script, "pre-bash", json.dumps(bash_payload("ls", repo)), cwd=repo, env=env
    )
    assert (here.returncode, here.stdout) == (0, "")


def test_the_launcher_skips_a_copy_without_the_hooks(repo: Path, tmp_path: Path) -> None:
    """A worktree on an old branch: its project.py predates the hooks, and argparse's exit 2
    for `hook pre-bash` would block every Bash call. The session root's copy judges instead."""
    wt = worktree(repo, tmp_path, "feat/old")
    (wt / "scripts" / "project.py").write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
    main_script = repo / "scripts" / "project.py"
    env = clean_env(repo)
    ok = run_hook(main_script, "pre-bash", json.dumps(bash_payload("ls", wt)), cwd=repo, env=env)
    assert ok.returncode == 0, ok.stderr
    deny = json.dumps(bash_payload("mise run merge", wt))
    assert run_hook(main_script, "pre-bash", deny, cwd=repo, env=env).returncode == 2
    start = json.dumps({"session_id": "t", "cwd": str(wt), "hook_event_name": "SessionStart"})
    began = run_hook(main_script, "session-start", start, cwd=repo, env=env)
    assert began.returncode == 0 and began.stdout.startswith("[wt-feat-old] feat/old |"), (
        began.stdout
    )


def test_the_launcher_never_runs_another_repos_script(repo: Path, tmp_path: Path) -> None:
    """A repo that is not a worktree of this one, with a project.py that allows everything."""
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    (other / "scripts").mkdir()
    fake = '"session-start", "pre-bash"\nimport sys\nprint("fake")\nsys.exit(0)\n'
    (other / "scripts" / "project.py").write_text(fake, encoding="utf-8")
    main_script = repo / "scripts" / "project.py"
    deny = json.dumps(bash_payload("mise run merge", other))
    done = run_hook(main_script, "pre-bash", deny, cwd=repo, env=clean_env(repo))
    assert done.returncode == 2 and "fake" not in done.stdout


def test_a_launched_copy_never_launches_again(repo: Path, tmp_path: Path) -> None:
    wt = worktree(repo, tmp_path, "feat/loop")
    script = wt / "scripts" / "project.py"
    text = script.read_text(encoding="utf-8")
    script.write_text(text.replace("\ndef main(", f"\nprint({MARK!r})\n\n\ndef main(", 1), "utf-8")
    env = {**clean_env(repo), "PROJECT_PY_LAUNCHED": "1"}
    main_script = repo / "scripts" / "project.py"
    done = run_hook(main_script, "pre-bash", json.dumps(bash_payload("ls", wt)), cwd=repo, env=env)
    assert (done.returncode, done.stdout) == (0, "")


def test_hook_args_after_the_name_still_route(scratch: Path) -> None:
    """`hook pre-bash <extra>` goes through argparse to the same hook, never to exit 2."""
    payload = json.dumps(bash_payload("ls", scratch))
    done = subprocess.run(
        [sys.executable, str(scratch / "scripts" / "project.py"), "hook", "pre-bash", "extra"],
        input=payload,
        cwd=scratch,
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(scratch),
    )
    assert done.returncode == 0, done.stderr


def test_the_template_is_executable_and_stdlib_only() -> None:
    assert PROJECT_PY.stat().st_mode & stat.S_IXUSR
    text = PROJECT_PY.read_text(encoding="utf-8")
    assert "# dependencies = []" in text
    assert '"session-start"' in text and '"pre-bash"' in text  # what the launcher looks for
