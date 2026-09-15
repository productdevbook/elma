#!/usr/bin/env bash
# Builds a self-contained Python environment for the bundled app.
#
# The bridge needs pymobiledevice3, and a released app can't assume the user
# has Python at all, let alone that dependency. This vendors an interpreter
# plus site-packages next to the bridge so the app runs on a clean machine.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/python/.runtime"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null; then
  echo "error: $PYTHON not found; set PYTHON=/path/to/python3" >&2
  exit 1
fi

echo "==> building runtime with $("$PYTHON" --version)"
rm -rf "$OUT"
"$PYTHON" -m venv --copies "$OUT"
"$OUT/bin/pip" install --quiet --upgrade pip
"$OUT/bin/pip" install --quiet "pymobiledevice3>=11.12.5"

# pymobiledevice3 imports a surprising amount of its CLI stack at module load
# (pygments, prompt_toolkit, questionary, xonsh), so those have to stay. What
# it never reaches from the bridge is the editor/notebook tier — jedi alone is
# 29 MB — and the image stack.
#
# The import check below is the guard: if this list ever over-trims, the build
# fails here rather than at the user's first click.
SP=("$OUT"/lib/python*/site-packages)
rm -rf "${SP[@]}"/{jedi,IPython,PIL,Pillow*,parso,matplotlib_inline,pexpect,ptyprocess,stack_data,executing,asttokens,pure_eval,pickleshare,backcall} 2>/dev/null || true
rm -rf "${SP[@]}"/{pip,setuptools,pkg_resources} 2>/dev/null || true
find "$OUT" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT" -type d -name "tests" -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT" -name "*.pyc" -delete 2>/dev/null || true

PYTHONPATH="$ROOT/python" "$OUT/bin/python" -c "import elma_bridge.handlers" \
  || { echo 'error: trimming removed something the bridge imports' >&2; exit 1; }
echo "   bridge imports cleanly"

echo "==> runtime ready: $(du -sh "$OUT" | cut -f1)"
