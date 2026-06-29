#!/usr/bin/env python3
"""Publish a rectilinear image from a calibrated OpenCV fisheye camera."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


@dataclass
class RectificationMap:
    map1: np.ndarray
    map2: np.ndarray
    new_k: np.ndarray
    width: int
    height: int


class ArducamFisheyeRectifier(Node):
    def __init__(self) -> None:
        super().__init__("arducam_fisheye_rectifier")

        self.declare_parameter("image_topic", "image_raw")
        self.declare_parameter("camera_info_topic", "camera_info")
        self.declare_parameter("rect_image_topic", "image_rect")
        self.declare_parameter("rect_camera_info_topic", "camera_info_rect")
        self.declare_parameter("balance", 1.0)
        self.declare_parameter("fov_scale", 1.0)
        self.declare_parameter("interpolation", "linear")

        self._rectification_map: RectificationMap | None = None
        self._rect_camera_info: CameraInfo | None = None
        self._shown_warnings: set[str] = set()

        image_topic = self.get_parameter("image_topic").get_parameter_value().string_value
        camera_info_topic = self.get_parameter("camera_info_topic").get_parameter_value().string_value
        rect_image_topic = self.get_parameter("rect_image_topic").get_parameter_value().string_value
        rect_camera_info_topic = (
            self.get_parameter("rect_camera_info_topic").get_parameter_value().string_value
        )

        self._image_pub = self.create_publisher(Image, rect_image_topic, qos_profile_sensor_data)
        self._camera_info_pub = self.create_publisher(
            CameraInfo, rect_camera_info_topic, qos_profile_sensor_data
        )
        self.create_subscription(
            CameraInfo,
            camera_info_topic,
            self._camera_info_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(Image, image_topic, self._image_callback, qos_profile_sensor_data)

        self.get_logger().info(
            f"Rectifying {image_topic} + {camera_info_topic} to {rect_image_topic}"
        )

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        if msg.distortion_model not in ("equidistant", "fisheye"):
            self._warn_once(
                "distortion_model",
                "Expected fisheye/equidistant CameraInfo distortion_model, "
                f"got {msg.distortion_model!r}"
            )
            return

        if len(msg.d) < 4:
            self._warn_once("short_d", "CameraInfo has fewer than 4 fisheye coefficients")
            return

        width = int(msg.width)
        height = int(msg.height)
        if width <= 0 or height <= 0:
            self._warn_once("bad_size", "CameraInfo width/height must be positive")
            return

        k = np.asarray(msg.k, dtype=np.float64).reshape(3, 3)
        d = np.asarray(msg.d[:4], dtype=np.float64).reshape(4, 1)
        if not np.all(np.isfinite(k)) or not np.all(np.isfinite(d)):
            self._warn_once("nonfinite_calibration", "CameraInfo has non-finite K or D values")
            return

        balance = float(self.get_parameter("balance").value)
        fov_scale = float(self.get_parameter("fov_scale").value)
        balance = min(max(balance, 0.0), 1.0)
        fov_scale = max(fov_scale, 0.01)

        new_k = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
            k,
            d,
            (width, height),
            np.eye(3),
            balance=balance,
            fov_scale=fov_scale,
        )
        map1, map2 = cv2.fisheye.initUndistortRectifyMap(
            k,
            d,
            np.eye(3),
            new_k,
            (width, height),
            cv2.CV_16SC2,
        )

        rect_info = CameraInfo()
        rect_info.header = msg.header
        rect_info.width = msg.width
        rect_info.height = msg.height
        rect_info.distortion_model = "plumb_bob"
        rect_info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        rect_info.k = [
            float(new_k[0, 0]),
            float(new_k[0, 1]),
            float(new_k[0, 2]),
            float(new_k[1, 0]),
            float(new_k[1, 1]),
            float(new_k[1, 2]),
            float(new_k[2, 0]),
            float(new_k[2, 1]),
            float(new_k[2, 2]),
        ]
        rect_info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        rect_info.p = [
            float(new_k[0, 0]),
            float(new_k[0, 1]),
            float(new_k[0, 2]),
            0.0,
            float(new_k[1, 0]),
            float(new_k[1, 1]),
            float(new_k[1, 2]),
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
        ]

        self._rectification_map = RectificationMap(map1, map2, new_k, width, height)
        self._rect_camera_info = rect_info

    def _image_callback(self, msg: Image) -> None:
        if self._rectification_map is None or self._rect_camera_info is None:
            self._warn_once("waiting_camera_info", "Waiting for calibrated fisheye CameraInfo")
            return

        try:
            image, output_encoding = image_msg_to_cv(msg)
        except ValueError as exc:
            self._warn_once("unsupported_encoding", str(exc))
            return

        if (
            image.shape[1] != self._rectification_map.width
            or image.shape[0] != self._rectification_map.height
        ):
            self._warn_once(
                "mismatched_image_size",
                "Image size does not match CameraInfo; waiting for matching frames"
            )
            return

        rectified = cv2.remap(
            image,
            self._rectification_map.map1,
            self._rectification_map.map2,
            interpolation=self._interpolation(),
            borderMode=cv2.BORDER_CONSTANT,
        )

        rect_msg = cv_to_image_msg(rectified, output_encoding, msg.header)
        rect_info = CameraInfo()
        rect_info.header = msg.header
        rect_info.width = self._rect_camera_info.width
        rect_info.height = self._rect_camera_info.height
        rect_info.distortion_model = self._rect_camera_info.distortion_model
        rect_info.d = list(self._rect_camera_info.d)
        rect_info.k = list(self._rect_camera_info.k)
        rect_info.r = list(self._rect_camera_info.r)
        rect_info.p = list(self._rect_camera_info.p)

        self._image_pub.publish(rect_msg)
        self._camera_info_pub.publish(rect_info)

    def _interpolation(self) -> int:
        name = self.get_parameter("interpolation").get_parameter_value().string_value.lower()
        if name == "nearest":
            return cv2.INTER_NEAREST
        if name == "cubic":
            return cv2.INTER_CUBIC
        return cv2.INTER_LINEAR

    def _warn_once(self, key: str, message: str) -> None:
        if key in self._shown_warnings:
            return
        self._shown_warnings.add(key)
        self.get_logger().warn(message)


def image_msg_to_cv(msg: Image) -> tuple[np.ndarray, str]:
    encoding = msg.encoding.lower()
    height = int(msg.height)
    width = int(msg.width)
    step = int(msg.step)
    raw = np.frombuffer(msg.data, dtype=np.uint8)

    if encoding in ("rgb8", "bgr8"):
        channels = 3
        row_bytes = width * channels
        rows = raw[: height * step].reshape(height, step)
        image = rows[:, :row_bytes].reshape(height, width, channels)
        return image.copy(), encoding

    if encoding in ("mono8", "8uc1"):
        rows = raw[: height * step].reshape(height, step)
        image = rows[:, :width].reshape(height, width)
        return image.copy(), "mono8"

    if encoding in ("yuyv", "yuy2", "yuv422"):
        row_bytes = width * 2
        rows = raw[: height * step].reshape(height, step)
        yuyv = rows[:, :row_bytes].reshape(height, width, 2)
        return cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2), "bgr8"

    raise ValueError(f"Unsupported image encoding {msg.encoding!r}")


def cv_to_image_msg(image: np.ndarray, encoding: str, header) -> Image:
    contiguous = np.ascontiguousarray(image)
    msg = Image()
    msg.header = header
    msg.height = int(contiguous.shape[0])
    msg.width = int(contiguous.shape[1])
    msg.encoding = encoding
    msg.is_bigendian = 0
    msg.step = int(contiguous.strides[0])
    msg.data = contiguous.tobytes()
    return msg


def main() -> None:
    rclpy.init()
    node = ArducamFisheyeRectifier()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
