#!/usr/bin/env sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AWS_BIN_DIR="$REPO_ROOT/.tools/aws-cli/bin"
SHELL_NAME=$(basename "${SHELL:-}")

if [ "$SHELL_NAME" = "bash" ]; then
  RC_FILE="$HOME/.bashrc"
else
  RC_FILE="$HOME/.zshrc"
fi

START_MARK="# >>> kala aws cli >>>"
END_MARK="# <<< kala aws cli <<<"
PATH_LINE="export PATH=\"$AWS_BIN_DIR:\$PATH\""

touch "$RC_FILE"

if grep -Fq "$START_MARK" "$RC_FILE"; then
  echo "AWS PATH block already exists in $RC_FILE"
else
  {
    printf "\n%s\n" "$START_MARK"
    printf "%s\n" "$PATH_LINE"
    printf "%s\n" "$END_MARK"
  } >> "$RC_FILE"
  echo "Added AWS PATH block to $RC_FILE"
fi

echo "Run: source $RC_FILE"