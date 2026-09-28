#!/bin/sh
# Build the M4 fixture repo: make_tipcalc.sh's main, then a branch plan/project-init holding
# what project-init renders for the git gates, in one commit made before any hook is active:
# .githooks/ from templates/githooks ({DEFAULT_BRANCH} -> main), .gitleaks.toml, scripts/project.py,
# .project.toml, mise.toml and its mise.lock from the M2 fixture, the M2 specs and tests, and
# ruff + ty as dev dependencies with the standard ruff settings. core.hooksPath stays unset: the caller turns
# the hooks on (or runs `project.py selftest`, which works in its own clone).
#
# usage: make_gates.sh [<dest> [<tipcalc repo>]]   (the arguments of make_tipcalc.sh)
set -eu

here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
skill=$(dirname -- "$(dirname -- "$here")")
fixture="$here/tipcalc"
dest=${1:-$(mktemp -d)/tipcalc}

sh "$here/make_tipcalc.sh" "$dest" ${2:+"$2"} >/dev/null
cd "$dest"
git switch -q -c plan/project-init

uv add -q --dev ruff ty
cp -R "$fixture/specs" specs
cp "$fixture/tests/helpers.py" "$fixture/tests/test_cli.py" "$fixture/tests/test_config.py" tests/
cp "$fixture/src/tipcalc/__init__.py" src/tipcalc/__init__.py
cp "$fixture/project.toml" .project.toml
cp "$fixture/mise.fixture.toml" mise.toml
cp "$fixture/mise.fixture.lock" mise.lock          # P4 runs `mise lock --platform linux-x64` (network)
mkdir -p scripts .githooks
cp "$skill/templates/scripts/project.py" scripts/project.py
for hook in pre-commit commit-msg pre-push reference-transaction; do
  sed 's/{DEFAULT_BRANCH}/main/' "$skill/templates/githooks/$hook" >".githooks/$hook"
  chmod 755 ".githooks/$hook"
done
cp "$skill/templates/gitleaks.toml" .gitleaks.toml
cat >>pyproject.toml <<'EOF'

[tool.ruff]
line-length = 100
extend-exclude = ["scripts/project.py", "tests/conftest.py"]

[tool.ruff.lint]
extend-select = ["S", "ANN"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S603", "S607"]
EOF
cat "$fixture/gitignore" >>.gitignore

git add -A
git -c user.name="tipcalc fixture" -c user.email="fixture@example.invalid" \
  commit -q -m "chore(init): project-init v3 gates"
echo "make_gates: $dest on plan/project-init ($(git rev-parse --short HEAD))"
