#!/usr/bin/env sh
# Vendor Terraform into .tools/terraform/bin the same way the AWS CLI is
# vendored: self-contained in the workspace, no brew/global install, pinned
# version, SHA256-verified against HashiCorp's published checksums.
# Idempotent: if the pinned binary already exists, this is a no-op.
set -eu

TERRAFORM_VERSION="1.9.8"  # matches infra/terraform/versions.tf (>= 1.6); bump deliberately, never float
TF_BIN=".tools/terraform/bin/terraform"

if [ -x "$TF_BIN" ] && "$TF_BIN" version 2>/dev/null | grep -Eq "^Terraform v${TERRAFORM_VERSION}([^0-9]|$)"; then
  echo "Terraform $TERRAFORM_VERSION already installed at .tools/terraform/bin/terraform"
  exit 0
fi

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$OS" in
  darwin|linux) ;;
  *) echo "unsupported OS: $OS (darwin/linux only)"; exit 1 ;;
esac

case "$ARCH" in
  x86_64) TF_ARCH="amd64" ;;
  arm64|aarch64) TF_ARCH="arm64" ;;
  *) echo "unsupported arch: $ARCH (amd64/arm64 only)"; exit 1 ;;
esac

BASE_URL="https://releases.hashicorp.com/terraform/$TERRAFORM_VERSION"
ZIP="terraform_${TERRAFORM_VERSION}_${OS}_${TF_ARCH}.zip"
CHECKSUMS="terraform_${TERRAFORM_VERSION}_SHA256SUMS"

echo "Downloading Terraform $TERRAFORM_VERSION ($OS/$TF_ARCH) from $BASE_URL"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL -o "$TMP_DIR/$ZIP" "$BASE_URL/$ZIP"
curl -fsSL -o "$TMP_DIR/$CHECKSUMS" "$BASE_URL/$CHECKSUMS"

# Verify against HashiCorp's published checksum before touching anything.
expected=$(awk -v z="$ZIP" '$2 == z { print $1 }' "$TMP_DIR/$CHECKSUMS")
if [ -z "$expected" ]; then
  echo "error: no checksum entry for $ZIP in $CHECKSUMS"
  exit 1
fi
if command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 "$TMP_DIR/$ZIP" | awk '{ print $1 }')
else
  actual=$(sha256sum "$TMP_DIR/$ZIP" | awk '{ print $1 }')
fi
if [ "$actual" != "$expected" ]; then
  echo "error: SHA256 mismatch for $ZIP"
  echo "  expected: $expected"
  echo "  actual:   $actual"
  exit 1
fi
echo "SHA256 verified"

mkdir -p .tools/terraform/bin
unzip -oq "$TMP_DIR/$ZIP" -d "$TMP_DIR/unpack"
cp "$TMP_DIR/unpack/terraform" "$TF_BIN"
chmod +x "$TF_BIN"

"$TF_BIN" version
echo "Terraform $TERRAFORM_VERSION installed to .tools/terraform/bin/terraform"
