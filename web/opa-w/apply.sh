#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
site="$(git -C "${1:?Pass the path to the Sites source checkout}" rev-parse --show-toplevel)"
patch="$source_dir/site-integration.patch"

git -C "$site" apply --check "$patch"

directories=(opa-w chip13 chip14 chip15)
for directory in "${directories[@]}"; do
  if [[ -e "$site/dist/$directory" ]]; then
    printf 'Integration destination already exists: %s\n' "$site/dist/$directory" >&2
    exit 1
  fi
done

git -C "$site" apply "$patch"
mkdir -p "$site/dist/"{opa-w,chip13,chip14,chip15}
cp -- "$source_dir/"{model.mjs,ui.mjs,lab.css} "$site/dist/opa-w/"
for chip in chip13 chip14 chip15; do
  cp -- "$source_dir/../$chip/"{index.html,experiment.mjs} "$site/dist/$chip/"
done
