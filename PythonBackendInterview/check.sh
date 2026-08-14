#!/usr/bin/env bash
# Full verification: lint, format, tests, and a smoke-run of every runnable exercise.
#
#   ./check.sh
#
# Every solution file has an `if __name__ == "__main__":` demo block, so running them all is a
# cheap end-to-end check that nothing in the tree is broken -- including the files whose output
# is prose rather than assertions.

set -uo pipefail
cd "$(dirname "$0")"

fail=0
step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

step "ruff check"
uv run ruff check . || fail=1

step "ruff format --check"
uv run ruff format --check . || fail=1

step "pytest (practice stubs excluded)"
uv run pytest || fail=1

step "smoke-run every exercise"
# Only the numbered section folders; skip tests, stubs, shared case modules and the deliberately
# broken `_naive` files.
while IFS= read -r f; do
  case "$(basename "$f")" in
    test_*|practice_*|*_cases.py|*_naive.py|conftest.py|__init__.py) continue ;;
  esac
  if ! out=$(uv run python "$f" 2>&1); then
    printf '  \033[31mFAIL\033[0m %s\n' "$f"
    printf '%s\n' "$out" | tail -5 | sed 's/^/       /'
    fail=1
  else
    printf '  ok   %s\n' "$f"
  fi
done < <(find ./[0-9]*-* -name '*.py' | sort)

step "result"
if [ "$fail" -eq 0 ]; then
  printf '\033[32mall checks passed\033[0m\n'
else
  printf '\033[31msomething failed (see above)\033[0m\n'
fi
exit "$fail"
