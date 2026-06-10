# Bringup Notes

## What ROS 2 Gives You

Each hardware driver is a ROS 2 node. When the node starts, it opens the physical device, converts hardware packets or frames into ROS messages, and publishes topics. It may also expose services/actions for calibration, reset, lifecycle, or diagnostics.

For this stack:

- RealSense publishes RGB images, depth images, camera info, aligned depth, optional IMU, optional point clouds, and device services.
- Arducam through V4L2 publishes an image stream and camera info.
- RPLIDAR publishes `sensor_msgs/LaserScan` on `/scan`.
- Hesai publishes `sensor_msgs/PointCloud2` on `/lidar_points`, optional IMU, packets, and packet-loss telemetry.

## Bringup Order

1. Verify the OS can see the device.
2. Verify the vendor driver can run by itself.
3. Wrap the vendor launch/node in this repo.
4. Standardize frame IDs and topics.
5. Add measured static transforms.
6. Record a short rosbag and inspect it.

## Useful Commands

```bash
lsusb
ip addr
v4l2-ctl --list-devices
ros2 node list
ros2 topic list
ros2 topic info /scan
ros2 topic echo --once /lidar_points
ros2 run tf2_tools view_frames
```

## Network Notes For Hesai

Most Hesai units send UDP packets to the host. Put the host NIC on the same subnet as the LiDAR, then update `config/hesai.yaml`.

Example:

```bash
sudo ip addr add 192.168.1.100/24 dev eth0
sudo ip link set eth0 up
```

Use the actual interface name from `ip addr`.

## Serial Notes For RPLIDAR

RPLIDAR commonly appears as `/dev/ttyUSB0`. If multiple USB serial devices are connected, create udev rules and use stable symlinks such as `/dev/rplidar`.
