#!/usr/bin/env bash
# Layer 1 protocol tests for Arena (docs/specs/arena.md, Verification).
# Usage: tests/run.sh <scenario>   runs scenarios/<scenario> and scenarios/<scenario>-*
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
skill=$(cd "$here/../skills/arena" && pwd)
name=${1:?usage: run.sh <scenario>}
failures=0
ran=0

check() { # $1 = scenario dir, $2 = work dir
  local sc=$1 work=$2 key value calls
  calls=$(grep -c '^exec' "$work/calls.log" || true)
  while IFS=' ' read -r key value; do
    [ -z "$key" ] && continue
    case $key in
      exec_calls)
        [ "$calls" = "$value" ] || { echo "  expected $value exec calls, got $calls"; return 1; } ;;
      args)
        if grep '^exec' "$work/calls.log" | grep -Evq -- "$value"; then
          echo "  an exec call does not match: $value"; return 1
        fi ;;
      no_args)
        if grep '^exec' "$work/calls.log" | grep -Eq -- "$value"; then
          echo "  an exec call matches forbidden: $value"; return 1
        fi ;;
      output)
        grep -Eiq -- "$value" "$work/out.txt" || { echo "  output lacks: $value"; return 1; } ;;
      *) echo "  unknown expect key: $key"; return 1 ;;
    esac
  done <"$sc/expect"
}

for sc in "$here/scenarios/$name" "$here/scenarios/$name"-*; do
  [ -d "$sc" ] || continue
  ran=$((ran + 1))
  work=$(mktemp -d)
  : >"$work/calls.log"
  proj="$work/proj"
  mkdir -p "$proj/.claude/skills"
  ln -s "$skill" "$proj/.claude/skills/arena"
  cp "$here/fixtures/doc.md" "$proj/doc.md"
  if [ ! -f "$sc/nogit" ]; then
    git -C "$proj" init -q
    git -C "$proj" add -A
    git -C "$proj" -c user.name=t -c user.email=t@example.com commit -qm fixture
  fi
  args=$(cat "$sc/args" 2>/dev/null || echo "doc.md --rubric text")
  (
    cd "$proj"
    ARENA_STUB_DIR="$sc" ARENA_STUB_LOG="$work/calls.log" PATH="$here/bin:$PATH" \
      timeout 1500 claude -p "/arena $args" --permission-mode bypassPermissions \
      </dev/null >"$work/out.txt" 2>&1
  ) || true
  if check "$sc" "$work"; then
    echo "PASS $(basename "$sc")"
    rm -rf "$work"
  else
    echo "FAIL $(basename "$sc") (kept $work)"
    failures=$((failures + 1))
  fi
done

[ "$ran" -gt 0 ] || { echo "no scenario named $name"; exit 2; }
[ "$failures" -eq 0 ]
