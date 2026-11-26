#!/usr/bin/env bash
set -euo pipefail
chip_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
checkout="$(git -C "${1:?Pass the path of the Sites source checkout}" rev-parse --show-toplevel)"
git -C "$checkout" apply --check "$chip_dir/site-integration.patch"

root_assets=(opa-graphics-xr.css opvr-headset.webp)
chip_assets=(model.js experiment.js experiment.css)
for asset in "${root_assets[@]}"; do
  if [[ -e "$checkout/dist/$asset" ]]; then
    printf 'Refusing to overwrite %s\n' "$checkout/dist/$asset" >&2
    exit 1
  fi
done
for asset in "${chip_assets[@]}"; do
  if [[ -e "$checkout/dist/chip16/$asset" ]]; then
    printf 'Refusing to overwrite %s\n' "$checkout/dist/chip16/$asset" >&2
    exit 1
  fi
done

git -C "$checkout" apply "$chip_dir/site-integration.patch"
mkdir -p "$checkout/dist/chip16"
for asset in "${root_assets[@]}"; do
  cp -- "$chip_dir/$asset" "$checkout/dist/$asset"
done
for asset in "${chip_assets[@]}"; do
  cp -- "$chip_dir/$asset" "$checkout/dist/chip16/$asset"
done
