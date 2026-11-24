#!/bin/sh
# Tests for commit-guard.sh: sh .claude/hooks/commit-guard.test.sh
# Builds a throwaway repo whose main checkout is on main, with a worktree on a feature branch

hook="$(cd "$(dirname "$0")" && pwd)/commit-guard.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

on_main="$tmp/on main"
on_feature="$tmp/feature"
git init -q -b main "$on_main"
git -C "$on_main" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
git -C "$on_main" worktree add -q -b feature "$on_feature"

failures=0

# check <expected allow|deny> <session cwd> <command>
check() {
    out=$(jq -n --arg cwd "$2" --arg c "$3" '{cwd: $cwd, tool_input: {command: $c}}' | sh "$hook")
    case $out in
        *'"deny"'*) got=deny ;;
        '') got=allow ;;
        *) got="unexpected output: $out" ;;
    esac
    if [ "$got" != "$1" ]; then
        failures=$((failures + 1))
        printf 'FAIL: expected %s, got %s\n  cwd: %s\n  command: %s\n' "$1" "$got" "$2" "$3"
    fi
}

# Plain commit in the session directory behaves as before
check deny "$on_main" 'git commit -m x'
check allow "$on_feature" 'git commit -m x'
check deny "$on_main" 'git add . && git commit -m x'
check deny "$on_main" 'git status; git commit -m x'

# A cd earlier in the command decides the target repository
check allow "$on_main" "cd '$on_feature' && git commit -m x"
check deny "$on_feature" "cd \"$on_main\" && git commit -m x"
check allow "$on_feature" "cd \"$on_main\" && cd ../feature && git commit -m x"

# git -C decides the target repository, whatever the session branch
check deny "$on_feature" "git -C \"$on_main\" commit -m x"
check allow "$on_main" "git -C '$on_feature' commit -m x"
check allow "$on_feature" "cd \"$on_main\" && git -C ../feature commit -m x"

# The words only appearing in quoted text or a heredoc body are not a commit
check allow "$on_main" 'gh issue create --body "mentions git commit here"'
check allow "$on_main" "gh issue comment 1 --body 'a; git commit -m x'"
check allow "$on_main" 'gh pr create --body "$(cat <<'"'"'EOF'"'"'
run git commit -m x
EOF
)"'
check allow "$on_main" 'echo git commit'

# A commit whose message comes from a heredoc is still a commit
check deny "$on_main" 'git commit -F - <<'"'"'EOF'"'"'
fix: message
EOF'

# Less common ways to write the same commit
check deny "$on_feature" "cd -P \"$on_main\" && git commit -m x"
check deny "$on_feature" "cd -- \"$on_main\" && git commit -m x"
check deny "$on_feature" "pushd \"$on_main\" && git commit -m x"
check deny "$on_feature" "cd $tmp/on\\ main && git commit -m x"
check deny "$on_main" 'GIT_AUTHOR_NAME=x git commit -m x'
check deny "$on_main" 'git --no-pager commit -m x'
check deny "$on_main" 'git -c user.name=x commit -m x'
check deny "$on_feature" "git -C\"$on_main\" commit -m x"
check deny "$on_feature" "git -C \"$tmp\" -C 'on main' commit -m x"
check deny "$on_main" '( git commit -m x )'

# Not a commit at all
check allow "$on_main" 'git status'
check allow "$on_main" 'git log --grep commit'

if [ "$failures" -eq 0 ]; then
    echo "All commit-guard checks passed"
else
    echo "$failures commit-guard check(s) failed"
    exit 1
fi
