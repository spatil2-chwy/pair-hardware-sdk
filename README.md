# Hardware SDK

ROS 2 bringup workspace for a sensor stack with:

- Intel/RealSense depth camera
- Arducam camera through the generic V4L2 ROS 2 driver
- Slamtec RPLIDAR
- Hesai 3D LiDAR

This repo is not trying to rewrite vendor drivers. The practical SDK shape is:

1. install or build each vendor ROS 2 driver,
2. keep one repo with your robot-specific launch/config files,
3. expose predictable topics, frames, and startup commands,
4. add calibration, diagnostics, recording, and downstream perception later.

## Layout

```text
hardware-sdk/
  hardware_sdk.repos          # optional source checkout list for vendor drivers
  src/hardware_bringup/       # this repo's ROS 2 bringup package
    launch/
      all_sensors.launch.py
      arducam_v4l2.launch.py
      hesai.launch.py
      realsense.launch.py
      rplidar.launch.py
    config/
      hesai.yaml
      static_transforms.yaml
  src/argos_provider_bridge/  # Argos provider bridge over Zenoh
    config/
      puffle_go2.yaml
    launch/
      hardware_provider_bridge.launch.py
```

## Recommended Setup

Use Ubuntu 22.04 + ROS 2 Humble unless you already have a reason to use Jazzy on Ubuntu 24.04.

Install base tools:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-pip \
  python3-rosdep \
  python3-vcstool
```

Source ROS:

```bash
source /opt/ros/humble/setup.bash
```

Initialize rosdep once per machine:

```bash
sudo rosdep init
rosdep update
```

## Docker On Jetson Thor

ROS 2 Humble is built for Ubuntu 22.04, so on a Jetson Thor host running Ubuntu 24.04 use the Jammy-based Humble container in this repo.

Build the image from the repo root. The image installs `v4l2_camera`, the RealSense SDK 2.0 development/runtime packages, and builds the vendor driver repos from `hardware_sdk.repos` into `/opt/pair_vendor_ws`:

```bash
./docker/build_humble_image.sh
```

To force a clean rebuild after Dockerfile or driver changes:

```bash
docker rm -f pair-hardware-sdk-humble 2>/dev/null || true
docker rmi pair-hardware-sdk:humble 2>/dev/null || true
./docker/build_humble_image.sh
```

Run an interactive container against this local checkout. This is the right path for the local `thor-test` branch before it is pushed to GitHub:

```bash
./docker/run_humble.sh
```

Inside the container, build the mounted workspace:

```bash
rosdep install -i --from-path src --rosdistro humble --skip-keys="librealsense2 ament_python" -y
colcon build --symlink-install
source install/setup.bash
```

To clone from GitHub and build inside a container-managed workspace instead of mounting the local checkout:

```bash
PAIR_HARDWARE_SDK_MOUNT_LOCAL=0 ./docker/run_humble.sh clone-and-build-pair-hardware-sdk
```

To clone a branch after it exists on GitHub:

```bash
PAIR_HARDWARE_SDK_MOUNT_LOCAL=0 PAIR_HARDWARE_SDK_BRANCH=thor-test ./docker/run_humble.sh clone-and-build-pair-hardware-sdk
```

For local-only branch work, use the mounted checkout flow above. The run wrapper uses host networking, `/dev`, privileged mode, and the NVIDIA runtime when Docker reports one. That is intentional for ROS 2 discovery plus USB, serial, video, and LiDAR access on Thor.

The image entrypoint sources `/opt/pair_vendor_ws/install/setup.bash` before the mounted SDK workspace, so these should be discoverable in every fresh container:

```bash
ros2 pkg prefix realsense2_camera
ros2 pkg prefix rplidar_ros
ros2 pkg prefix hesai_ros_driver
ros2 pkg prefix v4l2_camera
```

The image also installs the Python Zenoh bindings used by the Argos provider bridge.

To build, source, and launch the full sensor stack plus Argos hardware provider
in one command:

```bash
./docker/run_provider.sh
```

Pass launch overrides after the script name:

```bash
./docker/run_provider.sh use_hesai:=false arducam_video_device:=/dev/video2
```

## Install Drivers

If you are using the Thor Docker image from this repo, the normal driver dependencies are already in the image. The sections below are mainly for host installs, debugging, or rebuilding a driver outside Docker.

### RealSense

First check whether your container/OS has the ROS package available:

```bash
apt search ros-$ROS_DISTRO-realsense
```

If you see `ros-$ROS_DISTRO-realsense2-camera`, install it:

```bash
sudo apt install -y ros-$ROS_DISTRO-realsense2-camera
```

If apt cannot find it, build `realsense-ros` from source using `hardware_sdk.repos` or clone it into another ROS 2 workspace and source that workspace before launching `hardware_bringup`.

Direct vendor command:

```bash
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  enable_color:=true \
  align_depth.enable:=true \
  rgb_camera.color_profile:=640,480,15 \
  depth_module.depth_profile:=640,480,15
```

This repo wraps the same driver with:

```bash
ros2 launch hardware_bringup realsense.launch.py
```

The RealSense wrapper has changed profile argument names across releases. This repo exposes `color_profile` and `depth_profile` and translates them to the installed driver style.

### Arducam

There are multiple Arducam product families. If your camera appears as `/dev/video0`, the simplest ROS 2 path is usually the generic V4L2 driver:

```bash
sudo apt install -y ros-$ROS_DISTRO-v4l2-camera
```

Then:

```bash
ros2 launch hardware_bringup arducam_v4l2.launch.py video_device:=/dev/video0
```

Check devices with:

```bash
v4l2-ctl --list-devices
```

For a model-specific Arducam SDK, install the vendor package and add a new launch wrapper next to `arducam_v4l2.launch.py`.

### RPLIDAR

Slamtec's ROS 2 package is usually built from source:

```bash
mkdir -p ~/rplidar_ros2_ws/src
cd ~/rplidar_ros2_ws/src
git clone -b ros2 https://github.com/Slamtec/rplidar_ros.git
cd ~/rplidar_ros2_ws
rosdep install -i --from-path src --rosdistro $ROS_DISTRO -y
colcon build --symlink-install
source install/setup.bash
```

Give your user access to the serial device. A quick test is:

```bash
sudo chmod 666 /dev/ttyUSB0
```

For a persistent setup, use Slamtec's udev rule script from the driver repo.

Run through this repo:

```bash
ros2 launch hardware_bringup rplidar.launch.py model:=a1 serial_port:=/dev/ttyUSB0
```

Supported model values are `a1`, `a2m7`, `a2m8`, `a2m12`, `a3`, `s1`, `s1_tcp`, `s2`, `s2e`, `s3`, `t1`, and `c1`.

The bringup wrapper accepts `serial_baudrate:=auto` and `scan_mode:=auto`, which choose model-specific defaults:

| Model | Baud | Scan mode |
| --- | ---: | --- |
| `a1` | 115200 | `Sensitivity` |
| `a2m8` | 115200 | `Sensitivity` |
| `a2m7`, `a2m12`, `a3`, `s1` | 256000 | `Sensitivity` |
| `s2`, `s3` | 1000000 | `DenseBoost` |
| `s2e`, `t1` | 1000000 | `Sensitivity` |
| `c1` | 460800 | `Standard` |

If the node times out, confirm the exact model printed on the sensor, that the motor is spinning, and that the selected serial port is the RPLIDAR adapter.

### Hesai

Build the Hesai ROS 2 driver from source:

```bash
mkdir -p ~/hesai_ros2_ws/src
cd ~/hesai_ros2_ws/src
git clone --recurse-submodules https://github.com/HesaiTechnology/HesaiLidar_ROS_2.0.git
cd ~/hesai_ros2_ws
rosdep install -i --from-path src --rosdistro $ROS_DISTRO -y
colcon build --symlink-install
source install/setup.bash
```

Direct vendor command:

```bash
ros2 launch hesai_ros_driver start.py
```

This repo uses `src/hardware_bringup/config/hesai.yaml` so you can keep IPs, ports, topic names, and frame IDs in your own source tree:

```bash
ros2 launch hardware_bringup hesai.launch.py
```

Edit `src/hardware_bringup/config/hesai.yaml` for your LiDAR IP, host network, correction/firetime files, and desired topics.

## Build This Workspace

From the repo root:

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
python3 -m pip install eclipse-zenoh
rosdep install -i --from-path src --rosdistro $ROS_DISTRO --skip-keys="librealsense2 ament_python" -y
colcon build --symlink-install
source install/setup.bash
```

If you are using the Thor Docker image from this repo, `eclipse-zenoh` is already
installed in the image.

If you want to build vendor drivers from source in this same workspace, import the optional repo manifest first:

```bash
vcs import src < hardware_sdk.repos
rosdep install -i --from-path src --rosdistro $ROS_DISTRO --skip-keys="librealsense2 ament_python" -y
colcon build --symlink-install
source install/setup.bash
```

## Run Bringup

Launch everything enabled by default:

```bash
ros2 launch hardware_bringup all_sensors.launch.py
```

Start the Argos provider bridge with the sensors:

```bash
ros2 launch hardware_bringup all_sensors.launch.py use_argos_provider:=true
```

Or run the bridge separately after the camera drivers are publishing:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py
```

The default bridge launch loads
`src/argos_provider_bridge/config/puffle_go2.yaml`, which declares
provider `puffle-go2`, resources `arducam_001` and `realsense_001`, and their
ROS topic mappings. For another robot or another camera set, provide a different
manifest:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py \
  manifest_path:=/path/to/noodle_go2.yaml
```

The bridge exposes provider `puffle-go2` at
`argos/providers/puffle-go2/resources/{resource_id}/request/{request_id}` and
responds on the matching `.../response/{request_id}` key. See
`docs/argos-provider-bridge.md` for the JSON response shapes.

Robot manifests use `<robot_name_or_id>_<robot_type>.yaml`, for example
`puffle_go2.yaml`, `noodle_go2.yaml`, `haze_spot.yaml`, or `001_spot.yaml`.
They set `robot_id`, `robot_type`, `provider_id`, `provider_key_root`, resource
IDs, and ROS topic mappings.

Zenoh routing can be configured with environment variables:

```bash
ARGOS_ZENOH_CONNECT=tcp/127.0.0.1:7447 \
ARGOS_ZENOH_LISTEN= \
ARGOS_ZENOH_MODE= \
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py
```

Launch a subset:

```bash
ros2 launch hardware_bringup all_sensors.launch.py \
  use_realsense:=true \
  use_arducam:=false \
  use_rplidar:=true \
  use_hesai:=false
```

Override common device settings:

```bash
ros2 launch hardware_bringup all_sensors.launch.py \
  arducam_video_device:=/dev/video2 \
  arducam_namespace:=arducam \
  rplidar_model:=a2m8 \
  rplidar_serial_port:=/dev/ttyUSB1 \
  realsense_color_profile:=640,480,15 \
  hesai_config_file:=$(pwd)/src/hardware_bringup/config/hesai.yaml
```

## Verify

In another terminal:

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
source install/setup.bash
ros2 node list
ros2 topic list
ros2 topic hz /scan
ros2 topic hz /lidar_points
ros2 topic hz /camera/camera/color/image_raw
ros2 topic hz /arducam/image_raw
```

If you have GUI/X forwarding set up later, `rqt_image_view` and `rviz2` are useful optional tools, but they are not required for headless bringup.

Or run the helper:

```bash
./scripts/check_bringup.sh
```

Expected topic families:

- RealSense: `/camera/camera/color/image_raw`, `/camera/camera/depth/image_rect_raw`, `/camera/camera/aligned_depth_to_color/image_raw`
- Arducam V4L2: `/arducam/image_raw`, `/arducam/camera_info`
- RPLIDAR: `/scan`
- Hesai: `/lidar_points`, `/lidar_imu`, `/lidar_packets_loss`

## Frames And Calibration

The drivers can publish sensor frames, but the robot still needs extrinsics: where each sensor is mounted relative to `base_link`.

Start with `src/hardware_bringup/config/static_transforms.yaml` as the source of truth, then add static transform publishers or a URDF once the physical mounts are measured. Do not guess these if you plan to fuse data.

## When To Write A Custom SDK

Do not write custom drivers unless a vendor driver cannot do what you need. Use ROS 2 packages for hardware IO, then put your own SDK value in:

- bringup launch files,
- config and calibration,
- topic naming conventions,
- health checks,
- bag recording profiles,
- perception/fusion nodes,
- Docker/systemd deployment later.

## Sources Checked

- RealSense ROS wrapper: https://github.com/realsenseai/realsense-ros
- Hesai ROS 2 driver: https://github.com/HesaiTechnology/HesaiLidar_ROS_2.0
- Slamtec RPLIDAR ROS 2 branch: https://github.com/Slamtec/rplidar_ros/tree/ros2
