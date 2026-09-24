#!/usr/bin/env sh
set -eu

AWS_BIN=".tools/aws-cli/bin/aws"

if [ ! -x "$AWS_BIN" ]; then
  echo "AWS CLI is not installed for this workspace yet."
  echo "Run: pnpm setup"
  exit 1
fi

if [ "${1:-}" = "--" ]; then
  shift
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: pnpm aws <command> [subcommand] [parameters]"
  echo "Examples:"
  echo "  pnpm aws --version"
  echo "  pnpm aws sts get-caller-identity"
  exit 0
fi

exec "$AWS_BIN" "$@"
