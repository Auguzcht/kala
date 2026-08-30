#!/usr/bin/env sh
# Append a workspace-local tool's bin dir to the shell rc PATH block.
# Generalizes the old setup-aws-path.sh to any vendored tool.
# Idempotent: guarded by START/END marks, re-running never duplicates lines.
#
# Usage: sh scripts/setup-tool-paths.sh <label> <bin-dir-relative-to-root> <mark>
#   sh scripts/setup-tool-paths.sh "aws cli" .tools/aws-cli/bin "kala aws cli"
#   sh scripts/setup-tool-paths.sh terraform .tools/terraform/bin "kala terraform"
set -eu

LABEL="${1:?usage: setup-tool-paths.sh <label> <bin-dir> <mark>}"
BIN_DIR="${2:?usage: setup-tool-paths.sh <label> <bin-dir> <mark>}"
MARK="${3:?usage: setup-tool-paths.sh <label> <bin-dir> <mark>}"

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ABS_BIN_DIR="$REPO_ROOT/$BIN_DIR"
SHELL_NAME=$(basename "${SHELL:-}")

if [ "$SHELL_NAME" = "bash" ]; then
  RC_FILE="$HOME/.bashrc"
else
  RC_FILE="$HOME/.zshrc"
fi

START_MARK="# >>> $MARK >>>"
END_MARK="# <<< $MARK <<<"
PATH_LINE="export PATH=\"$ABS_BIN_DIR:\$PATH\""

touch "$RC_FILE"

if grep -Fq "$START_MARK" "$RC_FILE"; then
  echo "$LABEL PATH block already exists in $RC_FILE"
else
  {
    printf "\n%s\n" "$START_MARK"
    printf "%s\n" "$PATH_LINE"
    printf "%s\n" "$END_MARK"
  } >> "$RC_FILE"
  echo "Added $LABEL PATH block to $RC_FILE"
fi

echo "Run: source $RC_FILE"
