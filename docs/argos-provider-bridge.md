# Argos Provider Bridge

The Argos bridge is intentionally separate from `hardware_bringup`.

`hardware_bringup` starts vendor ROS 2 drivers and standardizes local topics.
`argos_provider_bridge` loads a provider manifest, subscribes to the configured
camera topics, caches the latest camera state, and exposes Argos
provider request/response JSON over Zenoh.

```text
ROS 2 camera topics
        |
        v
argos_provider_bridge cache
        |
        v
Zenoh request/response JSON
```

## Scaling Model

The bridge code is generic for camera RGB, RGBD, and intrinsics resources. The
robot-specific parts live in a YAML manifest:

- provider ID
- Zenoh key prefix
- resource IDs
- resource capabilities
- ROS image, depth, and CameraInfo topics
- per-depth-topic scale into meters

For one robot with multiple cameras, use one manifest with multiple resources.
For the same camera system on another robot, reuse the same ROS bringup pattern
and provide a different manifest with that robot's provider ID, key prefix,
resource IDs, and topic namespaces.

## Default Provider

- Provider ID: `puffle-go2`
- Key prefix: `argos/providers/puffle-go2`

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

## Operations

Requests use:

```text
argos/providers/puffle-go2/resources/{resource_id}/request/{request_id}
```

Responses use:

```text
argos/providers/puffle-go2/resources/{resource_id}/response/{request_id}
```

Implemented ops:

| Capability | Op |
| --- | --- |
| `camera.rgb` | `camera.latest_image` |
| `camera.rgbd` | `camera.latest_rgbd` |
| `camera.intrinsics` | `camera.intrinsics` |

The bridge responds with `ok: false` and an error object when a resource is
configured but an op is unsupported, or the requested ROS message has not been
cached yet. It only subscribes to request keys for resources in its manifest, so
unknown resources under the same provider prefix are left for another provider
process instead of receiving an error response from this bridge.

## Launch

```bash
ros2 launch argos_provider_bridge puffle_go2_provider.launch.py
```

The generic launch entry point is equivalent:

```bash
ros2 launch argos_provider_bridge camera_provider_bridge.launch.py
```

That command loads the installed default manifest:

```text
share/argos_provider_bridge/config/puffle_go2_provider.yaml
```

Or with all sensors:

```bash
ros2 launch hardware_bringup all_sensors.launch.py use_argos_provider:=true
```

Use another manifest for another robot or a larger camera set:

```bash
ros2 launch argos_provider_bridge puffle_go2_provider.launch.py \
  manifest_path:=/path/to/robot_provider.yaml
```

You can override the provider ID or key prefix at launch time without modifying
the manifest:

```bash
ros2 launch argos_provider_bridge puffle_go2_provider.launch.py \
  manifest_path:=/path/to/robot_provider.yaml \
  provider_id:=puffle-go2-lab \
  key_prefix:=argos/providers/puffle-go2-lab
```

The Python Zenoh bindings must be available in the same environment:

```bash
python3 -m pip install eclipse-zenoh
```

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

To add a second RealSense on the same robot, add another resource with its own
resource ID and ROS namespace:

```yaml
  - resource_id: realsense_rear_001
    capabilities:
      - camera.rgb
      - camera.rgbd
      - camera.intrinsics
    topics:
      rgb: /rear_camera/camera/color/image_raw
      depth: /rear_camera/camera/aligned_depth_to_color/image_raw
      camera_info: /rear_camera/camera/color/camera_info
    depth_scale: 0.001
```

Resource IDs only need to be unique within a provider. Provider IDs and key
prefixes should be unique per robot so Argos clients can address the intended
robot unambiguously.
