#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
image="${PAIR_HARDWARE_SDK_IMAGE:-pair-hardware-sdk:humble}"

if ! docker image inspect "${image}" >/dev/null 2>&1; then
  "${repo_root}/docker/build_humble_image.sh"
fi

exec "${repo_root}/docker/run_humble.sh" bash -lc '
set -eo pipefail
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
set -u
rosdep install -i --from-path src --rosdistro ${ROS_DISTRO:-humble} --skip-keys=librealsense2 -y
colcon build --symlink-install
set +u
source install/setup.bash
set -u
exec ros2 launch hardware_bringup all_sensors.launch.py use_argos_provider:=true "$@"
' bash "$@"
