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
  --exclude '/.pagefind-cache/' \
  --exclude '/scripts/' \
  --exclude '/netlify.toml' \
  --exclude '/README.md' \
  --exclude '/.gitignore' \
  "$root/" "$output/"

python3 "$root/scripts/test-validate-site.py"
python3 "$root/scripts/validate-site.py" "$output"

npx --yes pagefind@1.5.2 --site "$output" --output-subdir pagefind

for asset in pagefind-component-ui.css pagefind-component-ui.js pagefind.js; do
  test -s "$output/pagefind/$asset" || {
    echo "Missing required Pagefind asset: $output/pagefind/$asset" >&2
    exit 1
  }
done

test -s "$output/pagefind/pagefind-entry.json" || {
  echo "Missing required Pagefind entry file: $output/pagefind/pagefind-entry.json" >&2
  exit 1
}

index_files=("$output"/pagefind/index/*.pf_index)
if [[ ! -e "${index_files[0]}" ]]; then
  echo "Missing Pagefind index files in $output/pagefind/index" >&2
  exit 1
fi

fragment_files=("$output"/pagefind/fragment/*.pf_fragment)
if [[ ! -e "${fragment_files[0]}" ]]; then
  echo "Missing Pagefind fragment files in $output/pagefind/fragment" >&2
  exit 1
fi

echo "Verified Pagefind browser assets and search index in $output/pagefind"
