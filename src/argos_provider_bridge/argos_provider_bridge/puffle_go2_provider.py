from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image

try:
    import zenoh
except ImportError:  # pragma: no cover - exercised only on hosts missing Zenoh.
    zenoh = None

try:
    import yaml
except ImportError:  # pragma: no cover - validated at runtime if a YAML manifest is used.
    yaml = None


DEFAULT_PROVIDER_ID = "puffle-go2"
DEFAULT_KEY_PREFIX = "argos/providers/puffle-go2"
DEFAULT_MANIFEST = {
    "provider_id": DEFAULT_PROVIDER_ID,
    "key_prefix": DEFAULT_KEY_PREFIX,
    "resources": [
        {
            "resource_id": "arducam_001",
            "capabilities": ["camera.rgb", "camera.intrinsics"],
            "topics": {
                "rgb": "/arducam/image_raw",
                "camera_info": "/arducam/camera_info",
            },
        },
        {
            "resource_id": "realsense_001",
            "capabilities": ["camera.rgb", "camera.rgbd", "camera.intrinsics"],
            "topics": {
                "rgb": "/camera/camera/color/image_raw",
                "depth": "/camera/camera/aligned_depth_to_color/image_raw",
                "camera_info": "/camera/camera/color/camera_info",
            },
            "depth_scale": 0.001,
        },
    ],
}


@dataclass(frozen=True)
class ResourceConfig:
    resource_id: str
    capabilities: Tuple[str, ...]
    rgb_topic: str
    camera_info_topic: str
    depth_topic: Optional[str] = None
    depth_scale: float = 0.001


@dataclass
class ResourceCache:
    color_image: Optional[Image] = None
    depth_image: Optional[Image] = None
    camera_info: Optional[CameraInfo] = None


class ArgosProviderBridge(Node):
    def __init__(self) -> None:
        super().__init__("puffle_go2_argos_provider")
        if zenoh is None:
            raise RuntimeError(
                "The Python Zenoh bindings are required. Install with "
                "`python3 -m pip install eclipse-zenoh` inside the ROS 2 environment."
            )

        manifest_path = str(self.declare_parameter("manifest_path", "").value or "")
        provider_id_override = str(
            self.declare_parameter("provider_id", "").value or ""
        )
        key_prefix_override = str(self.declare_parameter("key_prefix", "").value or "")

        manifest = load_manifest(manifest_path)
        self.provider_id = provider_id_override or str(
            manifest.get("provider_id") or DEFAULT_PROVIDER_ID
        )
        self.key_prefix = (
            key_prefix_override
            or str(manifest.get("key_prefix") or f"argos/providers/{self.provider_id}")
        ).strip("/")

        self.resources = resources_from_manifest(manifest)
        self._lock = threading.RLock()
        self._cache: Dict[str, ResourceCache] = {
            resource_id: ResourceCache() for resource_id in self.resources
        }

        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        self._subscriptions = []
        for resource_id, config in self.resources.items():
            self._subscriptions.append(
                self.create_subscription(
                    Image,
                    config.rgb_topic,
                    lambda msg, rid=resource_id: self._cache_color_image(rid, msg),
                    sensor_qos,
                )
            )
            self._subscriptions.append(
                self.create_subscription(
                    CameraInfo,
                    config.camera_info_topic,
                    lambda msg, rid=resource_id: self._cache_camera_info(rid, msg),
                    sensor_qos,
                )
            )
            if config.depth_topic:
                self._subscriptions.append(
                    self.create_subscription(
                        Image,
                        config.depth_topic,
                        lambda msg, rid=resource_id: self._cache_depth_image(rid, msg),
                        sensor_qos,
                    )
                )

        self._zenoh_session = zenoh.open(zenoh.Config())
        self._request_key_expr = f"{self.key_prefix}/resources/*/request/*"
        self._zenoh_subscriber = self._zenoh_session.declare_subscriber(
            self._request_key_expr, self._on_zenoh_request
        )

        resource_summary = ", ".join(
            f"{rid}: {cfg.capabilities}" for rid, cfg in self.resources.items()
        )
        self.get_logger().info(
            f"Argos provider {self.provider_id} listening on {self._request_key_expr}"
        )
        if manifest_path:
            self.get_logger().info(f"Loaded Argos provider manifest: {manifest_path}")
        self.get_logger().info(f"Configured resources: {resource_summary}")

    def _cache_color_image(self, resource_id: str, msg: Image) -> None:
        with self._lock:
            self._cache[resource_id].color_image = msg

    def _cache_depth_image(self, resource_id: str, msg: Image) -> None:
        with self._lock:
            self._cache[resource_id].depth_image = msg

    def _cache_camera_info(self, resource_id: str, msg: CameraInfo) -> None:
        with self._lock:
            self._cache[resource_id].camera_info = msg

    def _on_zenoh_request(self, sample: Any) -> None:
        key = self._sample_key(sample)
        parsed = self._parse_request_key(key)
        if parsed is None:
            self.get_logger().warning(f"Ignoring unexpected Argos request key: {key}")
            return

        resource_id, request_id = parsed
        try:
            request = json.loads(self._sample_payload(sample).decode("utf-8"))
            response = self._handle_request(resource_id, request_id, request)
        except Exception as exc:  # Keep malformed requests from killing the subscriber.
            self.get_logger().warning(f"Failed Argos request {request_id}: {exc}")
            response = self._error_response(
                request_id,
                "bad_request",
                f"Could not decode or handle request: {exc}",
            )

        self._send_response(resource_id, request_id, response)

    def _handle_request(
        self, resource_id: str, request_id: str, request: Dict[str, Any]
    ) -> Dict[str, Any]:
        if resource_id not in self.resources:
            return self._error_response(
                request_id, "unknown_resource", f"Unknown resource_id {resource_id}"
            )

        op = request.get("op")
        if op == "camera.latest_image":
            return self._latest_image_response(resource_id, request_id)
        if op == "camera.latest_rgbd":
            return self._latest_rgbd_response(resource_id, request_id)
        if op == "camera.intrinsics":
            return self._intrinsics_response(resource_id, request_id)

        return self._error_response(request_id, "unsupported_op", f"Unsupported op {op}")

    def _latest_image_response(self, resource_id: str, request_id: str) -> Dict[str, Any]:
        if "camera.rgb" not in self.resources[resource_id].capabilities:
            return self._error_response(
                request_id, "unsupported_op", f"{resource_id} does not support camera.rgb"
            )

        color_image = self._latest_cached(resource_id).color_image
        if color_image is None:
            return self._error_response(
                request_id, "not_ready", f"{resource_id} has no cached RGB image yet"
            )

        stamp_s = stamp_to_seconds(color_image)
        return self._ok_response(
            request_id,
            {
                "resource_id": resource_id,
                "captured_at": stamp_s,
                "stamp_s": stamp_s,
                "image": image_to_color_payload(color_image),
            },
        )

    def _latest_rgbd_response(self, resource_id: str, request_id: str) -> Dict[str, Any]:
        config = self.resources[resource_id]
        if "camera.rgbd" not in config.capabilities:
            return self._error_response(
                request_id, "unsupported_op", f"{resource_id} does not support camera.rgbd"
            )

        cached = self._latest_cached(resource_id)
        if cached.color_image is None:
            return self._error_response(
                request_id, "not_ready", f"{resource_id} has no cached color image yet"
            )
        if cached.depth_image is None:
            return self._error_response(
                request_id, "not_ready", f"{resource_id} has no cached depth image yet"
            )

        return self._ok_response(
            request_id,
            {
                "color_image": image_to_color_payload(cached.color_image),
                "depth_m": image_to_depth_m_payload(
                    cached.depth_image, config.depth_scale
                ),
                "color_stamp_s": stamp_to_seconds(cached.color_image),
                "depth_stamp_s": stamp_to_seconds(cached.depth_image),
            },
        )

    def _intrinsics_response(self, resource_id: str, request_id: str) -> Dict[str, Any]:
        if "camera.intrinsics" not in self.resources[resource_id].capabilities:
            return self._error_response(
                request_id,
                "unsupported_op",
                f"{resource_id} does not support camera.intrinsics",
            )

        camera_info = self._latest_cached(resource_id).camera_info
        if camera_info is None:
            return self._error_response(
                request_id, "not_ready", f"{resource_id} has no cached CameraInfo yet"
            )

        return self._ok_response(
            request_id,
            {
                "fx": float(camera_info.k[0]),
                "fy": float(camera_info.k[4]),
                "cx": float(camera_info.k[2]),
                "cy": float(camera_info.k[5]),
                "width": int(camera_info.width),
                "height": int(camera_info.height),
                "stamp_s": stamp_to_seconds(camera_info),
            },
        )

    def _latest_cached(self, resource_id: str) -> ResourceCache:
        with self._lock:
            cached = self._cache[resource_id]
            return ResourceCache(
                color_image=cached.color_image,
                depth_image=cached.depth_image,
                camera_info=cached.camera_info,
            )

    def _ok_response(self, request_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": request_id,
            "type": "response",
            "ok": True,
            "result": result,
            "error": None,
            "ts": time.time(),
        }

    def _error_response(
        self, request_id: str, code: str, message: str
    ) -> Dict[str, Any]:
        return {
            "id": request_id,
            "type": "response",
            "ok": False,
            "result": None,
            "error": {"code": code, "message": message},
            "ts": time.time(),
        }

    def _send_response(
        self, resource_id: str, request_id: str, response: Dict[str, Any]
    ) -> None:
        response_key = (
            f"{self.key_prefix}/resources/{resource_id}/response/{request_id}"
        )
        payload = json.dumps(response, separators=(",", ":")).encode("utf-8")
        self._zenoh_session.put(response_key, payload)

    def _parse_request_key(self, key: str) -> Optional[Tuple[str, str]]:
        prefix = f"{self.key_prefix}/resources/"
        if not key.startswith(prefix):
            return None
        parts = key[len(prefix) :].split("/")
        if len(parts) != 3 or parts[1] != "request" or not parts[0] or not parts[2]:
            return None
        return parts[0], parts[2]

    @staticmethod
    def _sample_key(sample: Any) -> str:
        key_expr = getattr(sample, "key_expr", None)
        if key_expr is None:
            key_expr = getattr(sample, "keyexpr", None)
        return str(key_expr)

    @staticmethod
    def _sample_payload(sample: Any) -> bytes:
        payload = sample.payload
        if hasattr(payload, "to_bytes"):
            return bytes(payload.to_bytes())
        if hasattr(payload, "deserialize"):
            return payload.deserialize(bytes)
        return bytes(payload)

    def destroy_node(self) -> bool:
        close_or_undeclare(self._zenoh_subscriber)
        close_or_undeclare(self._zenoh_session)
        return super().destroy_node()


def image_to_color_payload(msg: Image) -> Dict[str, Any]:
    array, normalized_encoding = image_to_array(msg)
    if array.dtype != np.uint8:
        raise ValueError(f"Color image encoding {msg.encoding} is not uint8")
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError(f"Color image encoding {msg.encoding} is not RGB-like")

    if array.shape[2] > 3:
        array = array[:, :, :3]
        if normalized_encoding == "rgba8":
            normalized_encoding = "rgb8"
        elif normalized_encoding == "bgra8":
            normalized_encoding = "bgr8"

    array = np.ascontiguousarray(array)
    return {
        "encoding": "raw",
        "dtype": "uint8",
        "shape": [int(array.shape[0]), int(array.shape[1]), int(array.shape[2])],
        "format": normalized_encoding,
        "data_b64": base64.b64encode(array.tobytes(order="C")).decode("ascii"),
    }


def load_manifest(manifest_path: str) -> Dict[str, Any]:
    if not manifest_path:
        return dict(DEFAULT_MANIFEST)

    if yaml is None:
        raise RuntimeError(
            "YAML manifests require python3-yaml. Install it in the ROS 2 environment."
        )

    path = Path(manifest_path).expanduser()
    with path.open("r", encoding="utf-8") as manifest_file:
        manifest = yaml.safe_load(manifest_file)
    if not isinstance(manifest, dict):
        raise ValueError(f"Manifest {path} must contain a mapping at the top level")
    return manifest


def resources_from_manifest(manifest: Dict[str, Any]) -> Dict[str, ResourceConfig]:
    resources = manifest.get("resources")
    if not isinstance(resources, list) or not resources:
        raise ValueError("Argos provider manifest must define a non-empty resources list")

    configs: Dict[str, ResourceConfig] = {}
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            raise ValueError(f"resources[{index}] must be a mapping")

        resource_id = require_string(resource, "resource_id", f"resources[{index}]")
        if resource_id in configs:
            raise ValueError(f"Duplicate resource_id {resource_id}")

        capabilities_value = resource.get("capabilities")
        if not isinstance(capabilities_value, list) or not capabilities_value:
            raise ValueError(f"{resource_id} must define a non-empty capabilities list")
        capabilities = tuple(str(capability) for capability in capabilities_value)

        topics = resource.get("topics")
        if not isinstance(topics, dict):
            raise ValueError(f"{resource_id} must define topics")

        rgb_topic = require_string(topics, "rgb", f"{resource_id}.topics")
        camera_info_topic = require_string(
            topics, "camera_info", f"{resource_id}.topics"
        )
        depth_topic = optional_string(topics, "depth")
        depth_scale = float(resource.get("depth_scale", 0.001))

        if "camera.rgbd" in capabilities and not depth_topic:
            raise ValueError(f"{resource_id} has camera.rgbd but no topics.depth")

        configs[resource_id] = ResourceConfig(
            resource_id=resource_id,
            capabilities=capabilities,
            rgb_topic=rgb_topic,
            camera_info_topic=camera_info_topic,
            depth_topic=depth_topic,
            depth_scale=depth_scale,
        )

    return configs


def require_string(mapping: Dict[str, Any], key: str, path: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}.{key} must be a non-empty string")
    return value


def optional_string(mapping: Dict[str, Any], key: str) -> Optional[str]:
    value = mapping.get(key)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string when set")
    return value


def image_to_depth_m_payload(msg: Image, depth_scale: float) -> Dict[str, Any]:
    array, normalized_encoding = image_to_array(msg)
    if array.ndim != 2:
        raise ValueError(f"Depth image encoding {msg.encoding} is not single-channel")

    if normalized_encoding in ("16uc1", "z16", "mono16"):
        depth_m = array.astype(np.float32) * np.float32(depth_scale)
    elif normalized_encoding == "32fc1":
        depth_m = array.astype(np.float32, copy=False)
    else:
        raise ValueError(f"Unsupported depth image encoding {msg.encoding}")

    depth_m = np.ascontiguousarray(depth_m)
    return {
        "dtype": "float32",
        "shape": [int(depth_m.shape[0]), int(depth_m.shape[1])],
        "data_b64": base64.b64encode(depth_m.tobytes(order="C")).decode("ascii"),
    }


def image_to_array(msg: Image) -> Tuple[np.ndarray, str]:
    encoding = msg.encoding.lower()
    dtype, channels, normalized_encoding = encoding_layout(encoding)
    itemsize = np.dtype(dtype).itemsize
    expected_row_bytes = int(msg.width) * channels * itemsize
    if int(msg.step) < expected_row_bytes:
        raise ValueError(
            f"Image step {msg.step} is smaller than expected row width "
            f"{expected_row_bytes} for {msg.encoding}"
        )

    raw = np.frombuffer(msg.data, dtype=np.uint8)
    needed_bytes = int(msg.height) * int(msg.step)
    if raw.size < needed_bytes:
        raise ValueError(
            f"Image data has {raw.size} bytes, expected at least {needed_bytes}"
        )

    rows = raw[:needed_bytes].reshape((int(msg.height), int(msg.step)))
    tight_rows = np.ascontiguousarray(rows[:, :expected_row_bytes])
    array = tight_rows.view(dtype)
    if channels == 1:
        array = array.reshape((int(msg.height), int(msg.width)))
    else:
        array = array.reshape((int(msg.height), int(msg.width), channels))

    if bool(msg.is_bigendian) and itemsize > 1:
        array = array.byteswap()
    return array, normalized_encoding


def encoding_layout(encoding: str) -> Tuple[Any, int, str]:
    normalized = encoding.lower()
    aliases = {
        "8uc1": "mono8",
        "16uc1": "16uc1",
        "32fc1": "32fc1",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in ("rgb8", "bgr8"):
        return np.uint8, 3, normalized
    if normalized in ("rgba8", "bgra8"):
        return np.uint8, 4, normalized
    if normalized == "mono8":
        return np.uint8, 1, normalized
    if normalized in ("mono16", "16uc1", "z16"):
        return np.uint16, 1, normalized
    if normalized == "32fc1":
        return np.float32, 1, normalized
    raise ValueError(f"Unsupported image encoding {encoding}")


def stamp_to_seconds(msg: Any) -> float:
    stamp = msg.header.stamp
    seconds = float(stamp.sec) + float(stamp.nanosec) * 1e-9
    return seconds if seconds > 0.0 else time.time()


def close_or_undeclare(obj: Any) -> None:
    for method_name in ("undeclare", "close"):
        method = getattr(obj, method_name, None)
        if callable(method):
            method()
            return


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = ArgosProviderBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
