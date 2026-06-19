# Argos Hardware Provider Bridge

`argos_provider_bridge` adapts local ROS 2 sensor topics into Argos provider
request/response JSON over Zenoh. The bridge is generic hardware-provider code;
robot-specific identity and ROS topic mappings live in YAML manifests.

## Default Provider

The default manifest is `config/puffle_go2.yaml`.

```text
robot_id=puffle
robot_type=go2
provider_id=puffle-go2
key_prefix=argos/providers/puffle-go2
```

Requests and responses use resource-scoped keys:

```text
argos/providers/puffle-go2/resources/{resource_id}/request/{request_id}
argos/providers/puffle-go2/resources/{resource_id}/response/{request_id}
```

The provider also publishes:

```text
argos/providers/puffle-go2/manifest
argos/providers/puffle-go2/heartbeat
```

## Resources

The default `puffle_go2.yaml` resources are:

| Resource | Capabilities | Default ROS 2 sources |
| --- | --- | --- |
| `arducam_001` | `camera.rgb`, `camera.intrinsics` | `/arducam/image_raw`, `/arducam/camera_info` |
| `realsense_001` | `camera.rgb`, `camera.rgbd`, `camera.intrinsics` | `/camera/realsense_001/color/image_raw`, `/camera/realsense_001/aligned_depth_to_color/image_raw`, `/camera/realsense_001/color/camera_info` |
| `realsense_002` | `camera.rgb`, `camera.rgbd`, `camera.intrinsics` | `/camera/realsense_002/color/image_raw`, `/camera/realsense_002/aligned_depth_to_color/image_raw`, `/camera/realsense_002/color/camera_info` |

The RealSense depth topic defaults to aligned depth-to-color so returned depth
pixels share the color image coordinate space.

## Build And Run

Install runtime dependencies in the ROS 2 environment:

```bash
python3 -m pip install eclipse-zenoh
```

Build the workspace:

```bash
colcon build --symlink-install
source install/setup.bash
```

Run only the hardware provider bridge after sensor drivers are already
publishing:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py
```

Start sensors and the provider together:

```bash
ros2 launch hardware_bringup all_sensors.launch.py use_argos_provider:=true
```

Use another robot manifest:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py \
  manifest_path:=/path/to/noodle_go2.yaml
```

Configure Zenoh routing through launch args or environment:

```bash
ARGOS_ZENOH_CONNECT=tcp/127.0.0.1:7447 \
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py
```

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py \
  zenoh_connect:=tcp/127.0.0.1:7447 \
  zenoh_listen:=tcp/0.0.0.0:7447 \
  zenoh_mode:=peer
```

## Manifest Naming

Name manifests as `<robot_name_or_id>_<robot_type>.yaml`.

Examples:

```text
puffle_go2.yaml
noodle_go2.yaml
haze_spot.yaml
001_spot.yaml
```

Manifest shape:

```yaml
robot_id: puffle
robot_type: go2
provider_id: puffle-go2
provider_key_root: argos

resources:
  - resource_id: arducam_001
    capabilities:
      - camera.rgb
      - camera.intrinsics
    topics:
      rgb: /arducam/image_raw
      camera_info: /arducam/camera_info

  - resource_id: realsense_001
    capabilities:
      - camera.rgb
      - camera.rgbd
      - camera.intrinsics
    topics:
      rgb: /camera/realsense_001/color/image_raw
      depth: /camera/realsense_001/aligned_depth_to_color/image_raw
      camera_info: /camera/realsense_001/color/camera_info
    depth_scale: 0.001

  - resource_id: realsense_002
    capabilities:
      - camera.rgb
      - camera.rgbd
      - camera.intrinsics
    topics:
      rgb: /camera/realsense_002/color/image_raw
      depth: /camera/realsense_002/aligned_depth_to_color/image_raw
      camera_info: /camera/realsense_002/color/camera_info
    depth_scale: 0.001
```

For an unnamed Spot robot, use a numeric ID:

```yaml
robot_id: "001"
robot_type: spot
provider_id: 001_spot
provider_key_root: argos
```

## Operations

Supported request bodies:

```json
{"op":"camera.latest_image"}
{"op":"camera.latest_rgbd"}
{"op":"camera.intrinsics"}
```

`camera.latest_image` returns raw contiguous `uint8` image bytes with shape
`[height, width, 3]` and a `format` field such as `rgb8` or `bgr8`.

`camera.latest_rgbd` returns the latest color image plus aligned depth as
contiguous `float32` meters with shape `[height, width]`.

`camera.intrinsics` maps ROS `CameraInfo.K` as:

- `fx = K[0]`
- `fy = K[4]`
- `cx = K[2]`
- `cy = K[5]`
