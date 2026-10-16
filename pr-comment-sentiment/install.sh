#!/usr/bin/env bash
# Install the pr-tone skill for Claude Code and GitHub Copilot.
#
#   From a clone of this repo:   ./pr-comment-sentiment/install.sh
#   Without cloning:             curl -fsSL https://raw.githubusercontent.com/albybarber/ai-play-projects/main/pr-comment-sentiment/install.sh | bash
#
# Options:
#   --target DIR   install into DIR instead of the defaults (repeatable)
#   --copy         copy the skill instead of symlinking it
#   --uninstall    remove the skill (reports in ~/pr-tone-reports are kept)
#   -h, --help     show this help
#
# Installs into ~/.claude/skills (Claude Code) and ~/.copilot/skills (GitHub
# Copilot CLI and VS Code). Both are links to the same files. Re-run to update.

set -euo pipefail

SKILL=pr-tone
REPO_URL="${PR_TONE_REPO_URL:-https://github.com/albybarber/ai-play-projects.git}"
REF="${PR_TONE_REF:-main}"
SRC_HOME="${PR_TONE_SRC:-$HOME/.local/share/pr-tone}"

targets=()
mode=link
action=install

usage() {
  if [ -f "${BASH_SOURCE[0]:-}" ]; then sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  else say "Options: --target DIR (repeatable), --copy, --uninstall, -h/--help. See pr-comment-sentiment/README.md."; fi
}
say() { printf '%s\n' "$*"; }
if [ -t 1 ]; then G=$'\033[32m' Y=$'\033[33m' R=$'\033[31m' N=$'\033[0m'; else G='' Y='' R='' N=''; fi
ok() { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
die() { printf '%serror:%s %s\n' "$R" "$N" "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target) [ $# -ge 2 ] || die "--target needs a directory"; targets+=("${2/#\~/$HOME}"); shift 2 ;;
    --copy) mode=copy; shift ;;
    --uninstall) action=uninstall; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done
[ ${#targets[@]} -gt 0 ] || targets=("$HOME/.claude/skills" "$HOME/.copilot/skills")

# Is this folder one of our installs (a link to a pr-tone skill, or a copy of one)?
is_ours() {
  [ -f "$1/SKILL.md" ] && grep -q '^name: pr-tone$' "$1/SKILL.md"
}

# Is $SRC_HOME a download this installer made (or nothing at all)? It may come from PR_TONE_SRC,
# so never delete a folder that holds anything else.
src_home_is_ours() {
  [ ! -e "$SRC_HOME" ] || is_ours "$SRC_HOME/pr-comment-sentiment/skills/$SKILL" \
    || [ -z "$(ls -A "$SRC_HOME" 2>/dev/null)" ]
}

if [ "$action" = uninstall ]; then
  say "Uninstalling $SKILL"
  for t in "${targets[@]}"; do
    dest="$t/$SKILL"
    if [ -L "$dest" ] || is_ours "$dest"; then
      rm -rf "$dest"; ok "removed $dest"
    elif [ -e "$dest" ]; then
      warn "left $dest alone: it isn't a pr-tone skill"
    else
      ok "nothing at $dest"
    fi
  done
  if [ -d "$SRC_HOME" ]; then
    if src_home_is_ours; then rm -rf "$SRC_HOME"; ok "removed downloaded copy $SRC_HOME"
    else warn "left $SRC_HOME alone: it isn't a pr-tone download"; fi
  fi
  say "Reports were kept in ${PR_TONE_HOME:-$HOME/pr-tone-reports}. Delete that folder yourself if you no longer need them."
  exit 0
fi

say "Installing $SKILL"

# 1. Find the skill: next to this script if run from a clone, otherwise download it.
script_dir=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$script_dir" ] && [ -f "$script_dir/skills/$SKILL/SKILL.md" ]; then
  src="$script_dir/skills/$SKILL"
  ok "using this checkout: $src"
else
  command -v git >/dev/null || die "git is required to download the skill"
  src_home_is_ours || die "$SRC_HOME exists and isn't a pr-tone download; move it or set PR_TONE_SRC"
  if [ -d "$SRC_HOME/.git" ]; then
    git -C "$SRC_HOME" fetch -q --depth 1 origin "$REF"
    git -C "$SRC_HOME" checkout -q --detach FETCH_HEAD
    ok "updated $SRC_HOME to the latest $REF"
  else
    rm -rf "$SRC_HOME"
    mkdir -p "$(dirname "$SRC_HOME")"
    # a partial clone needs server support; if it fails, clear what it left and clone normally
    git clone -q --depth 1 --filter=blob:none --sparse --branch "$REF" "$REPO_URL" "$SRC_HOME" 2>/dev/null \
      || { rm -rf "$SRC_HOME"; git clone -q --depth 1 --branch "$REF" "$REPO_URL" "$SRC_HOME"; }
    git -C "$SRC_HOME" sparse-checkout set pr-comment-sentiment 2>/dev/null || true
    ok "downloaded to $SRC_HOME"
  fi
  src="$SRC_HOME/pr-comment-sentiment/skills/$SKILL"
  [ -f "$src/SKILL.md" ] || die "download did not contain skills/$SKILL (ref: $REF)"
fi
chmod +x "$src/scripts/prtone.py"

# 2. Link or copy it into each skills folder.
for t in "${targets[@]}"; do
  dest="$t/$SKILL"
  mkdir -p "$t"
  if [ -L "$dest" ] || is_ours "$dest"; then
    rm -rf "$dest"
  elif [ -e "$dest" ]; then
    die "$dest already exists and isn't a pr-tone skill; move it and run again"
  fi
  if [ "$mode" = copy ]; then
    cp -R "$src" "$dest"; ok "copied to $dest"
  else
    ln -s "$src" "$dest"; ok "linked $dest -> $src"
  fi
done

# 3. Check what the skill needs at run time (warnings only).
say "Checking requirements"
py=""
for c in python3 python; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then py=$c; break; fi
done
if [ -n "$py" ]; then ok "$("$py" --version 2>&1)"; else warn "Python 3.10+ not found: install it before using the skill"; fi
if command -v gh >/dev/null; then
  ok "gh $(gh --version | head -1 | awk '{print $3}')"
  if gh auth status >/dev/null 2>&1; then ok "gh is signed in"; else warn "gh is not signed in: run 'gh auth login'"; fi
else
  warn "GitHub CLI (gh) not found: install it from https://cli.github.com and run 'gh auth login'"
fi
if [ -n "$py" ]; then
  if "$py" "$src/scripts/prtone.py" --help >/dev/null; then ok "helper script runs"
  else warn "the helper script failed to start: try '$py $src/scripts/prtone.py --help'"; fi
fi

cat <<EOF

Done. Start a new session (or run /skills reload in Copilot CLI), then try it:
  Claude Code:  /pr-tone owner/repo some-login last 2 weeks
  Copilot:      "Use the pr-tone skill to check some-login in owner/repo over the last 2 weeks"
                (check it's listed with /skills in Copilot CLI or VS Code chat)
Reports are saved to ${PR_TONE_HOME:-$HOME/pr-tone-reports} (never inside a git repo).
Run this installer again to update, or with --uninstall to remove.
EOF
