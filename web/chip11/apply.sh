#!/usr/bin/env bash
set -euo pipefail
chip_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
checkout="$(git -C "${1:?Pass the path of the Sites source checkout}" rev-parse --show-toplevel)"
git -C "$checkout" apply --check "$chip_dir/site-integration.patch"
assets=(optical-logic.css optical-logic.js optical-logic-model.mjs)
for asset in "${assets[@]}"; do
  if [[ -e "$checkout/dist/$asset" ]]; then
    printf 'Refusing to overwrite %s\n' "$checkout/dist/$asset" >&2
    exit 1
  fi
done
git -C "$checkout" apply "$chip_dir/site-integration.patch"
for asset in "${assets[@]}"; do
  cp -- "$chip_dir/$asset" "$checkout/dist/$asset"
done
