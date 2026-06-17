#!/usr/bin/env bash
set -euo pipefail

ros_distro="${ROS_DISTRO:-humble}"
repo_url="${PAIR_HARDWARE_SDK_REPO:-https://github.com/spatil2-chwy/pair-hardware-sdk.git}"
branch="${PAIR_HARDWARE_SDK_BRANCH:-main}"
workspace="${PAIR_HARDWARE_SDK_WORKSPACE:-/workspaces/pair-hardware-sdk}"
import_vendor_drivers="${PAIR_HARDWARE_SDK_IMPORT_VENDOR_DRIVERS:-0}"

set +u
source "/opt/ros/${ros_distro}/setup.bash"
set -u

mkdir -p "$(dirname "${workspace}")"

if [[ ! -d "${workspace}/.git" ]]; then
  git clone --branch "${branch}" "${repo_url}" "${workspace}"
else
  git -C "${workspace}" fetch origin "${branch}"
  git -C "${workspace}" switch "${branch}"
  git -C "${workspace}" pull --ff-only origin "${branch}"
fi

cd "${workspace}"

if [[ "${import_vendor_drivers}" == "1" ]]; then
  vcs import src < hardware_sdk.repos
fi

rosdep install -i --from-path src --rosdistro "${ros_distro}" --skip-keys="librealsense2 ament_python" -y
colcon build --symlink-install "$@"

set +u
source install/setup.bash
set -u
