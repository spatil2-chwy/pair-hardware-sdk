#!/usr/bin/env bash
set -euo pipefail

echo "ROS_DISTRO=${ROS_DISTRO:-unset}"
echo
echo "Nodes:"
ros2 node list || true
echo
echo "Topics:"
ros2 topic list || true
echo
echo "Key topic rates:"
for topic in /scan /lidar_points /camera/camera/color/image_raw /arducam/image_raw; do
  if ros2 topic list | grep -qx "$topic"; then
    echo "$topic"
    timeout 6 ros2 topic hz "$topic" || true
  else
    echo "$topic: not present"
  fi
done
