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

npx --yes pagefind@1.5.2 --site "$output" --output-subdir pagefind --base-url /

for asset in pagefind-component-ui.css pagefind-component-ui.js pagefind.js; do
  test -s "$output/pagefind/$asset" || {
    echo "Missing required Pagefind asset: $output/pagefind/$asset" >&2
    exit 1
  }
done

echo "Verified Pagefind browser assets in $output/pagefind"
