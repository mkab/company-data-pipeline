# Claude Code hooks

`.claude/settings.json` defines two project hooks that enforce the conventions in `CLAUDE.md`:

- `PostToolUse` on `Edit|Write` fails the write when the touched file contains an em dash.
- `PreToolUse` on `Bash` runs `.claude/hooks/commit-guard.sh`, which denies a commit into a repository whose branch is `main`.

## The commit guard

`commit-guard.jq` reads the Bash command and lists each commit in it, with the directory it runs in.

- A commit is a `git ... commit` at the start of the command, or right after `&&`, `||`, `;`, `|`, `&` or a newline.
  Git options before `commit` (`-C <dir>`, `-c key=val`, `--no-pager`), `VAR=x` prefixes and subshell brackets are allowed.
- Quoted text and heredoc bodies are ignored, so a `gh issue create --body "..."` that mentions a commit is not one.
- The directory comes from the `-C <dir>` options, else the last `cd` or `pushd` earlier in the command, else the session directory.
  A relative directory resolves against the one before it, so a commit in a worktree is judged by the worktree's branch.

`commit-guard.sh` runs `git -C <dir> branch --show-current` for each commit and denies the command when any of them is on `main`.
It does not parse shell fully: git aliases, `$(...)` command substitutions and `eval` are not recognised as commits, and a variable in a directory other than `$HOME` is not expanded.

A hook too long for a readable one-liner lives in `.claude/hooks/` like this one, with a test script beside it.
Run the tests after changing either file:

```sh
sh .claude/hooks/commit-guard.test.sh
```

## Prerequisite: `jq` must be on `PATH`

Both hooks parse the hook payload with it.

| Platform | Install |
| --- | --- |
| macOS | `brew install jq` |
| Debian/Ubuntu | `apt install jq` |
| Windows | `winget install jqlang.jq`, or `pacman -S jq` under MSYS2 |

Git for Windows does not bundle it, so a fresh Git Bash install needs this step. Without `jq` the hooks fail on every edit and every Bash call: the commit guard reports a non-blocking error and lets the command run.

`jq` was chosen over a Python equivalent because it is roughly 2.4x faster per call (about 18ms versus 43ms), and these hooks run on every tool call.

## Windows contributors need Git Bash

Claude Code routes command hooks to PowerShell when it is absent, and these hooks are POSIX shell.
