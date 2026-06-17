# Argos Hardware Provider Bridge

The Argos bridge is intentionally separate from `hardware_bringup`.

`hardware_bringup` starts vendor ROS 2 drivers and standardizes local topics.
`argos_provider_bridge` loads a robot manifest, subscribes to configured sensor
topics, caches the latest camera state, and exposes Argos request/response JSON
over Zenoh.

```text
ROS 2 sensor topics
        |
        v
hardware_provider_bridge cache
        |
        v
Zenoh request/response JSON
```

## Naming Model

Use one manifest per robot/sensor configuration. Name manifests as
`<robot_name_or_id>_<robot_type>.yaml`.

Examples:

```text
puffle_go2.yaml
noodle_go2.yaml
haze_spot.yaml
001_spot.yaml
```

The default provider uses:

```text
robot_id=puffle
robot_type=go2
provider_id=puffle-go2
key_prefix=argos/providers/puffle-go2
```

Requests use:

```text
argos/providers/puffle-go2/resources/{resource_id}/request/{request_id}
```

Responses use:

```text
argos/providers/puffle-go2/resources/{resource_id}/response/{request_id}
```

The provider also publishes its manifest and heartbeat:

```text
argos/providers/puffle-go2/manifest
argos/providers/puffle-go2/heartbeat
```

## Default Resources

`arducam_001`

- Capabilities: `camera.rgb`, `camera.intrinsics`
- Default image topic: `/arducam/image_raw`
- Default CameraInfo topic: `/arducam/camera_info`

`realsense_001`

- Capabilities: `camera.rgb`, `camera.rgbd`, `camera.intrinsics`
- Default color topic: `/camera/camera/color/image_raw`
- Default aligned depth topic: `/camera/camera/aligned_depth_to_color/image_raw`
- Default color CameraInfo topic: `/camera/camera/color/camera_info`

The bridge expects RealSense depth to be aligned to color. If your driver only
publishes unaligned depth, enable `align_depth.enable:=true` in the RealSense
launch or point the manifest's `topics.depth` at a suitable aligned topic.

## Launch

Run only the provider bridge after camera drivers are publishing:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py
```

Or start it with all sensors:

```bash
ros2 launch hardware_bringup all_sensors.launch.py use_argos_provider:=true
```

Use another robot or camera set:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py \
  manifest_path:=/path/to/noodle_go2.yaml
```

Override the provider key at launch time:

```bash
ros2 launch argos_provider_bridge hardware_provider_bridge.launch.py \
  manifest_path:=/path/to/noodle_go2.yaml \
  provider_id:=noodle_go2_lab
```

Configure Zenoh routing through environment or launch args:

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

The Python Zenoh bindings must be available in the same environment:

```bash
python3 -m pip install eclipse-zenoh
```

## Manifest Shape

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
      rgb: /camera/camera/color/image_raw
      depth: /camera/camera/aligned_depth_to_color/image_raw
      camera_info: /camera/camera/color/camera_info
    depth_scale: 0.001
```

For an unnamed robot:

```yaml
robot_id: "001"
robot_type: spot
provider_id: 001_spot
provider_key_root: argos
```

## Operations

| Capability | Op |
| --- | --- |
| `camera.rgb` | `camera.latest_image` |
| `camera.rgbd` | `camera.latest_rgbd` |
| `camera.intrinsics` | `camera.intrinsics` |

The bridge responds with `ok: false` and a structured error object when a
configured resource does not support an op or the requested ROS message has not
been cached yet. It subscribes only to request keys for resources in its
manifest, so unknown resources under the same provider prefix can be owned by
another provider process.
