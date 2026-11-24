# Prints the directory each git commit in a Bash tool command runs in, one per line
# Input: the PreToolUse hook payload
# A commit is a `git ... commit` that starts the command,
# or follows `&&`, `||`, `;`, `|`, `&` or a newline
# Its directory comes from any `-C <dir>` options, else the last `cd <dir>` before it,
# else the session directory

# Quoted text has its whitespace and separators swapped for control characters,
# so quoted words never read as a command and a quoted directory survives the split
def hide: gsub("\\s"; "\u0001") | gsub(";"; "\u0002") | gsub("&"; "\u0003") | gsub("\\|"; "\u0004");
def unhide: gsub("\u0001"; " ") | gsub("\u0002"; ";") | gsub("\u0003"; "&") | gsub("\u0004"; "|");

def resolve($base; $dir):
  ($dir | sub("^\\$(HOME|\\{HOME\\})"; "~")) as $dir
  | if $dir | test("^(/|~|[A-Za-z]:)") then $dir else $base + "/" + $dir end;

(.cwd // ".") as $session
| .tool_input.command // ""
# Drop heredoc bodies, keeping the rest of the line that opens one
| gsub("<<-?[ \\t]*['\"]?(?<tag>\\w+)['\"]?(?<rest>[^\\n]*)\\n[\\s\\S]*?\\n[ \\t]*\\k<tag>(?=\\n|$)"; .rest)
| gsub("(?<q>\"(?:\\\\.|[^\"\\\\])*\"|'[^']*')"; .q[1:-1] | hide)
| gsub("\\\\ "; "\u0001")
| [splits("&&|\\|\\||[;|&\\n]")]
# Trim each segment, along with the brackets of a subshell or group
| reduce (.[] | gsub("^[\\s({]+|[\\s)}]+$"; "")) as $segment ({cwd: $session, commits: []};
    if $segment | test("^(cd|pushd)(\\s|$)") then
      .cwd = resolve(.cwd; first(($segment | capture("^\\w+(\\s+-\\S+)*\\s+(?<dir>\\S+)").dir), "~"))
    elif $segment | test("^(\\w+=\\S*\\s+)*git(\\s+-\\S+(\\s+\\S+)?)*?\\s+commit(\\s|$)") then
      ($segment | capture("^(\\w+=\\S*\\s+)*git(?<options>.*?)\\s+commit(\\s|$)").options) as $options
      | .commits += [reduce ($options | scan("-C\\s*(\\S+)")[0]) as $dir (.cwd; resolve(.; $dir))]
    else
      .
    end)
| .commits[]
| unhide
