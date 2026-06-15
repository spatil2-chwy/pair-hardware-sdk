# Argos Provider Bridge

`argos_provider_bridge` adapts local ROS 2 camera topics into Argos provider
request/response JSON over Zenoh. Argos clients never subscribe to raw ROS
topics directly; this bridge owns the ROS 2 and camera-driver side of the
integration.

## Provider

- `provider_id`: `puffle-go2`
- `key_prefix`: `argos/providers/puffle-go2`

The default manifest is `config/puffle_go2_provider.yaml`.

Resources in the default manifest:

| Resource | Capabilities | Default ROS 2 sources |
| --- | --- | --- |
| `arducam_001` | `camera.rgb`, `camera.intrinsics` | `/arducam/image_raw`, `/arducam/camera_info` |
| `realsense_001` | `camera.rgb`, `camera.rgbd`, `camera.intrinsics` | `/camera/camera/color/image_raw`, `/camera/camera/aligned_depth_to_color/image_raw`, `/camera/camera/color/camera_info` |

The RealSense depth topic defaults to aligned depth-to-color so returned depth
pixels share the color image coordinate space.

## Zenoh Protocol

Requests arrive on:

```text
argos/providers/puffle-go2/resources/{resource_id}/request/{request_id}
```

Responses are published on:

```text
argos/providers/puffle-go2/resources/{resource_id}/response/{request_id}
```

Supported request bodies:

```json
{"op":"camera.latest_image"}
{"op":"camera.latest_rgbd"}
{"op":"camera.intrinsics"}
```

The response `id` is always taken from `{request_id}` in the key.

## Run

Install runtime dependencies in the ROS 2 environment:

```bash
python3 -m pip install eclipse-zenoh
```

Build the workspace:

```bash
colcon build --symlink-install
source install/setup.bash
```

Run the provider bridge:

```bash
ros2 launch argos_provider_bridge puffle_go2_provider.launch.py
```

The generic launch name is equivalent and is better for non-puffle robots:

```bash
ros2 launch argos_provider_bridge camera_provider_bridge.launch.py
```

Or start it with the aggregate sensor launch:

```bash
ros2 launch hardware_bringup all_sensors.launch.py use_argos_provider:=true
```

For another robot or a different camera set, pass a different manifest:

```bash
ros2 launch argos_provider_bridge puffle_go2_provider.launch.py \
  manifest_path:=/path/to/robot_provider.yaml
```

For `16UC1`, `mono16`, or `z16` RealSense depth images, the bridge multiplies
raw depth by `realsense_depth_scale` before returning float32 meters. The
default is `0.001`.

## Manifest Shape

```yaml
provider_id: puffle-go2
key_prefix: argos/providers/puffle-go2

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

Use one provider manifest per robot. Add more resources for more cameras on the
same robot. Reuse the same camera bringup packages and change only topic
namespaces, resource IDs, provider ID, and key prefix.

## Response Notes

`camera.latest_image` returns raw contiguous `uint8` image bytes with shape
`[height, width, 3]` and a `format` field such as `rgb8` or `bgr8`.

`camera.latest_rgbd` returns the latest color image plus aligned depth as
contiguous `float32` meters with shape `[height, width]`.

`camera.intrinsics` maps ROS `CameraInfo.K` as:

- `fx = K[0]`
- `fy = K[4]`
- `cx = K[2]`
- `cy = K[5]`
