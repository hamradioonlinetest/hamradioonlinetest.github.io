#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Build and validate exactly as production does, including Pagefind.
bash "$root/scripts/build-site.sh"

# Then make the staged copy self-contained for the preview host.
python3 "$root/scripts/prepare-preview-site.py" "$root/_site"

echo "Prepared preview site in $root/_site"
