#!/usr/bin/env sh
set -eu

TF_BIN=".tools/terraform/bin/terraform"

if [ ! -x "$TF_BIN" ]; then
  echo "Terraform is not installed for this workspace yet."
  echo "Run: pnpm setup"
  exit 1
fi

if [ "${1:-}" = "--" ]; then
  shift
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: pnpm terraform <command> [subcommand] [parameters]"
  echo "Examples:"
  echo "  pnpm terraform -version"
  echo "  pnpm terraform -chdir=infra/terraform init"
  echo "  pnpm terraform -chdir=infra/terraform plan"
  echo "  pnpm terraform apply"
  exit 0
fi

exec "$TF_BIN" "$@"
