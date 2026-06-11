#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

image="${PAIR_HARDWARE_SDK_IMAGE:-pair-hardware-sdk:humble}"
container_name="${PAIR_HARDWARE_SDK_CONTAINER_NAME:-pair-hardware-sdk-humble}"
mount_local="${PAIR_HARDWARE_SDK_MOUNT_LOCAL:-1}"

nvidia_args=()
if docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q '"nvidia"'; then
  nvidia_args+=(--runtime nvidia)
elif docker run --help 2>/dev/null | grep -q -- '--gpus'; then
  nvidia_args+=(--gpus all)
fi

x11_args=()
if [[ -n "${DISPLAY:-}" ]]; then
  x11_args+=(-e DISPLAY="${DISPLAY}")

  if [[ -d /tmp/.X11-unix ]]; then
    x11_args+=(-v /tmp/.X11-unix:/tmp/.X11-unix:rw)
  fi

  xauth_source="${XAUTHORITY:-}"
  if [[ -z "${xauth_source}" && -n "${SUDO_USER:-}" ]]; then
    sudo_home="$(getent passwd "${SUDO_USER}" | cut -d: -f6 || true)"
    if [[ -n "${sudo_home}" && -f "${sudo_home}/.Xauthority" ]]; then
      xauth_source="${sudo_home}/.Xauthority"
    fi
  fi

  if command -v xauth >/dev/null 2>&1 && [[ -f "${xauth_source}" ]]; then
    xauth_file=/tmp/pair-hardware-sdk-docker.xauth
    touch "${xauth_file}"
    chmod 600 "${xauth_file}"
    xauth -f "${xauth_source}" nlist "${DISPLAY}" 2>/dev/null \
      | sed -e 's/^..../ffff/' \
      | xauth -f "${xauth_file}" nmerge - 2>/dev/null || true
    x11_args+=(-e XAUTHORITY=/tmp/.docker.xauth -v "${xauth_file}:/tmp/.docker.xauth:ro")
  fi
fi

volume_args=()
workdir=/workspaces
if [[ "${mount_local}" == "1" ]]; then
  volume_args+=(-v "${repo_root}:/workspaces/pair-hardware-sdk")
  workdir=/workspaces/pair-hardware-sdk
else
  host_ws="${PAIR_HARDWARE_SDK_HOST_WS:-${HOME}/pair-hardware-sdk-docker}"
  mkdir -p "${host_ws}"
  volume_args+=(-v "${host_ws}:/workspaces")
fi

exec docker run --rm -it \
  --name "${container_name}" \
  --network host \
  --ipc host \
  --privileged \
  "${nvidia_args[@]}" \
  "${x11_args[@]}" \
  "${volume_args[@]}" \
  -v /dev:/dev \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
  -e RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}" \
  -e PAIR_HARDWARE_SDK_REPO="${PAIR_HARDWARE_SDK_REPO:-https://github.com/spatil2-chwy/pair-hardware-sdk.git}" \
  -e PAIR_HARDWARE_SDK_BRANCH="${PAIR_HARDWARE_SDK_BRANCH:-main}" \
  -e PAIR_HARDWARE_SDK_IMPORT_VENDOR_DRIVERS="${PAIR_HARDWARE_SDK_IMPORT_VENDOR_DRIVERS:-0}" \
  -w "${workdir}" \
  "${image}" \
  "$@"
