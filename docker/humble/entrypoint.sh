#!/usr/bin/env bash
set -e

ros_distro="${ROS_DISTRO:-humble}"
source "/opt/ros/${ros_distro}/setup.bash"

if [[ -f /opt/pair_vendor_ws/install/setup.bash ]]; then
  source /opt/pair_vendor_ws/install/setup.bash
fi

if [[ -f /workspaces/pair-hardware-sdk/install/setup.bash ]]; then
  source /workspaces/pair-hardware-sdk/install/setup.bash
fi

exec "$@"
