#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

image="${PAIR_HARDWARE_SDK_IMAGE:-pair-hardware-sdk:humble}"

docker build \
  --file "${repo_root}/docker/humble/Dockerfile" \
  --tag "${image}" \
  "${repo_root}"
