#!/bin/sh
# PreToolUse hook on Bash: denies a git commit whose target repository is on main
# commit-guard.jq finds the commits and the directory each one runs in

# Exit 1 is a non-blocking hook error: the command still runs and the error is shown to the user
if ! command -v jq >/dev/null 2>&1; then
    echo "Commit guard skipped: jq is not on PATH (see docs/agents/hooks.md)" >&2
    exit 1
fi
dirs=$(jq -r -f "$(dirname "$0")/commit-guard.jq") || exit 1

IFS='
'
for dir in $dirs; do
    case $dir in
        "~" | "~/"*) dir="$HOME${dir#"~"}" ;;
    esac
    if [ "$(git -C "$dir" branch --show-current 2>/dev/null)" = "main" ]; then
        printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Never commit directly to main. Fetch latest main, create a branch from it, then commit there."}}'
        exit 0
    fi
done
