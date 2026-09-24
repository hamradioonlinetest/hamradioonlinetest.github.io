#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="${1:-$root/_site}"

rm -rf "$output"
mkdir -p "$output"

rsync -a --delete \
  --exclude '/.git/' \
  --exclude '/.github/' \
  --exclude '/_site/' \
  --exclude '/node_modules/' \
  --exclude '/scripts/' \
  --exclude '/README.md' \
  --exclude '/.gitignore' \
  "$root/" "$output/"

npx --yes pagefind@1.4.0 --site "$output" --output-subdir pagefind
