#!/usr/bin/env python3
"""Capture and calibrate an OpenCV fisheye camera with a ChArUco board."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable, Optional

import cv2
import numpy as np


ARUCO_DICTIONARIES = {
    "4x4_50": "DICT_4X4_50",
    "4x4_100": "DICT_4X4_100",
    "4x4_250": "DICT_4X4_250",
    "4x4_1000": "DICT_4X4_1000",
    "5x5_50": "DICT_5X5_50",
    "5x5_100": "DICT_5X5_100",
    "5x5_250": "DICT_5X5_250",
    "5x5_1000": "DICT_5X5_1000",
    "6x6_50": "DICT_6X6_50",
    "6x6_100": "DICT_6X6_100",
    "6x6_250": "DICT_6X6_250",
    "6x6_1000": "DICT_6X6_1000",
    "7x7_50": "DICT_7X7_50",
    "7x7_100": "DICT_7X7_100",
    "7x7_250": "DICT_7X7_250",
    "7x7_1000": "DICT_7X7_1000",
    "aruco_original": "DICT_ARUCO_ORIGINAL",
}


class CharucoFisheyeCalibrator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.dictionary = self._dictionary(args.aruco_dict)
        self.board = self._charuco_board(
            args.squares_x,
            args.squares_y,
            args.square_length,
            args.marker_length,
            self.dictionary,
        )
        self.detector_params = self._detector_params()
        self.chessboard_corners = self._board_chessboard_corners(self.board)

    def detect(self, image_bgr: np.ndarray) -> tuple[Optional[np.ndarray], Optional[np.ndarray], np.ndarray]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray,
            self.dictionary,
            parameters=self.detector_params,
        )
        overlay = image_bgr.copy()
        if ids is None or len(ids) == 0:
            return None, None, overlay

        cv2.aruco.drawDetectedMarkers(overlay, corners, ids)
        try:
            cv2.aruco.refineDetectedMarkers(gray, self.board, corners, ids, rejected)
        except cv2.error:
            pass

        count, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
            corners,
            ids,
            gray,
            self.board,
        )
        if count is None or count < self.args.min_corners or charuco_ids is None:
            return None, None, overlay

        cv2.aruco.drawDetectedCornersCharuco(overlay, charuco_corners, charuco_ids)
        return charuco_corners, charuco_ids, overlay

    def calibrate_from_paths(self, image_paths: Iterable[Path]) -> tuple[float, np.ndarray, np.ndarray]:
        object_points = []
        image_points = []
        corner_counts = []
        all_image_points = []
        image_size = None

        for path in image_paths:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                print(f"Skipping unreadable image: {path}", file=sys.stderr)
                continue
            h, w = image.shape[:2]
            if image_size is None:
                image_size = (w, h)
            elif image_size != (w, h):
                raise ValueError(f"{path} has size {(w, h)}, expected {image_size}")

            charuco_corners, charuco_ids, _ = self.detect(image)
            if charuco_corners is None or charuco_ids is None:
                print(f"Skipping image with too few ChArUco corners: {path}", file=sys.stderr)
                continue

            ids = charuco_ids.flatten().astype(np.int32)
            obj = self.chessboard_corners[ids].reshape(-1, 1, 3).astype(np.float64)
            img = charuco_corners.reshape(-1, 1, 2).astype(np.float64)
            object_points.append(obj)
            image_points.append(img)
            corner_counts.append(len(ids))
            all_image_points.append(img.reshape(-1, 2))

        if image_size is None:
            raise ValueError("No readable calibration images found")
        if len(object_points) < self.args.min_images:
            raise ValueError(
                f"Need at least {self.args.min_images} usable images, found {len(object_points)}"
            )

        self._print_dataset_summary(corner_counts, all_image_points, image_size)
        return self._calibrate(object_points, image_points, image_size)

    def _calibrate(
        self,
        object_points: list[np.ndarray],
        image_points: list[np.ndarray],
        image_size: tuple[int, int],
    ) -> tuple[float, np.ndarray, np.ndarray]:
        w, h = image_size
        diagonal = math.hypot(w, h)
        f_guess = diagonal / math.radians(self.args.diagonal_fov_deg)
        k = np.array(
            [
                [f_guess, 0.0, (w - 1) / 2.0],
                [0.0, f_guess, (h - 1) / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        d = np.zeros((4, 1), dtype=np.float64)
        rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _ in object_points]
        tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _ in object_points]

        flags = 0
        if self.args.use_intrinsic_guess:
            flags |= cv2.fisheye.CALIB_USE_INTRINSIC_GUESS
        if self.args.fix_skew:
            flags |= cv2.fisheye.CALIB_FIX_SKEW
        if self.args.fix_principal_point:
            flags |= cv2.fisheye.CALIB_FIX_PRINCIPAL_POINT
        if self.args.recompute_extrinsics:
            flags |= cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
        if self.args.check_conditions:
            flags |= cv2.fisheye.CALIB_CHECK_COND

        rms, k, d, _, _ = cv2.fisheye.calibrate(
            object_points,
            image_points,
            image_size,
            k,
            d,
            rvecs,
            tvecs,
            flags=flags,
            criteria=(
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                self.args.max_iterations,
                self.args.epsilon,
            ),
        )
        print(f"Used {len(object_points)} images at {w}x{h}")
        print(f"RMS reprojection error: {rms:.6f}")
        print("K:")
        print(k)
        print("D:")
        print(d.reshape(-1))
        return rms, k, d

    @staticmethod
    def _print_dataset_summary(
        corner_counts: list[int],
        image_points: list[np.ndarray],
        image_size: tuple[int, int],
    ) -> None:
        counts = np.asarray(corner_counts, dtype=np.int32)
        points = np.concatenate(image_points, axis=0)
        mins = points.min(axis=0)
        maxs = points.max(axis=0)
        w, h = image_size
        coverage = (maxs - mins) / np.asarray([w, h], dtype=np.float64)
        print(f"Usable images: {len(corner_counts)}")
        print(
            "ChArUco corners/image: "
            f"min={counts.min()}, median={np.median(counts):.1f}, max={counts.max()}"
        )
        print(
            "Detected-corner coverage: "
            f"x={coverage[0] * 100.0:.1f}% y={coverage[1] * 100.0:.1f}% "
            f"bbox=({mins[0]:.1f},{mins[1]:.1f})-({maxs[0]:.1f},{maxs[1]:.1f})"
        )

    @staticmethod
    def _dictionary(name: str):
        normalized = name.lower().replace("dict_", "")
        constant_name = ARUCO_DICTIONARIES.get(normalized)
        if constant_name is None:
            choices = ", ".join(sorted(ARUCO_DICTIONARIES))
            raise ValueError(f"Unknown ArUco dictionary {name!r}. Choices: {choices}")
        constant = getattr(cv2.aruco, constant_name)
        return cv2.aruco.getPredefinedDictionary(constant)

    @staticmethod
    def _charuco_board(squares_x: int, squares_y: int, square: float, marker: float, dictionary):
        if hasattr(cv2.aruco, "CharucoBoard_create"):
            return cv2.aruco.CharucoBoard_create(squares_x, squares_y, square, marker, dictionary)
        return cv2.aruco.CharucoBoard((squares_x, squares_y), square, marker, dictionary)

    @staticmethod
    def _detector_params():
        if hasattr(cv2.aruco, "DetectorParameters_create"):
            return cv2.aruco.DetectorParameters_create()
        return cv2.aruco.DetectorParameters()

    @staticmethod
    def _board_chessboard_corners(board) -> np.ndarray:
        if hasattr(board, "getChessboardCorners"):
            return np.asarray(board.getChessboardCorners(), dtype=np.float64)
        return np.asarray(board.chessboardCorners, dtype=np.float64)


def ros_image_to_bgr(msg) -> np.ndarray:
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
        if encoding == "rgb8":
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image.copy()

    if encoding in ("mono8", "8uc1"):
        rows = raw[: height * step].reshape(height, step)
        gray = rows[:, :width].reshape(height, width)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    if encoding in ("yuyv", "yuy2", "yuv422"):
        row_bytes = width * 2
        rows = raw[: height * step].reshape(height, step)
        yuyv = rows[:, :row_bytes].reshape(height, width, 2)
        return cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2)

    raise ValueError(f"Unsupported image encoding {msg.encoding!r}")


def capture_from_ros(args: argparse.Namespace, calibrator: CharucoFisheyeCalibrator) -> list[Path]:
    try:
        import rclpy
        from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
        from sensor_msgs.msg import Image
    except ImportError as exc:
        raise RuntimeError("ROS capture requires rclpy and sensor_msgs in the current environment") from exc

    capture_dir = Path(args.capture_dir)
    capture_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(capture_dir.glob("*.png"))
    latest = {"frame": None}

    def callback(msg):
        latest["frame"] = ros_image_to_bgr(msg)

    rclpy.init()
    node = rclpy.create_node("charuco_fisheye_capture")
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=2,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )
    node.create_subscription(Image, args.topic, callback, qos)
    print(f"Listening on {args.topic}")
    print("Press SPACE to save a detected sample, c to calibrate saved samples, q to quit.")

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.02)
            frame = latest["frame"]
            if frame is None:
                continue

            charuco_corners, charuco_ids, overlay = calibrator.detect(frame)
            usable = charuco_corners is not None and charuco_ids is not None
            count = int(len(charuco_ids)) if usable else 0
            status = f"samples={len(image_paths)} corners={count} {'OK' if usable else 'MOVE BOARD'}"
            cv2.putText(
                overlay,
                status,
                (16, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0) if usable else (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow("charuco fisheye capture", overlay)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("c")):
                break
            if key == 32:
                if not usable:
                    print("Not saving: too few detected ChArUco corners")
                    continue
                path = capture_dir / f"sample_{len(image_paths):04d}.png"
                cv2.imwrite(str(path), frame)
                image_paths.append(path)
                print(f"Saved {path}")
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

    return image_paths


def write_ros_yaml(
    path: Path,
    camera_name: str,
    image_size: tuple[int, int],
    k: np.ndarray,
    d: np.ndarray,
) -> None:
    width, height = image_size
    k_values = [float(value) for value in k.reshape(-1)]
    d_values = [float(value) for value in d.reshape(-1)]
    r_values = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    p_values = [
        k_values[0],
        k_values[1],
        k_values[2],
        0.0,
        k_values[3],
        k_values[4],
        k_values[5],
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"image_width: {width}",
                f"image_height: {height}",
                f"camera_name: {camera_name}",
                "camera_matrix:",
                "  rows: 3",
                "  cols: 3",
                f"  data: {format_float_list(k_values)}",
                "distortion_model: equidistant",
                "distortion_coefficients:",
                "  rows: 1",
                "  cols: 4",
                f"  data: {format_float_list(d_values)}",
                "rectification_matrix:",
                "  rows: 3",
                "  cols: 3",
                f"  data: {format_float_list(r_values)}",
                "projection_matrix:",
                "  rows: 3",
                "  cols: 4",
                f"  data: {format_float_list(p_values)}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def format_float_list(values: Iterable[float]) -> str:
    return "[" + ", ".join(f"{value:.10g}" for value in values) + "]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate a fisheye camera from a ChArUco board and write ROS CameraInfo YAML.",
    )
    parser.add_argument("--topic", default="/arducam/image_raw", help="ROS image topic for capture")
    parser.add_argument("--from-dir", default="", help="Calibrate from existing PNG images instead of ROS")
    parser.add_argument("--capture-dir", default="calibration/arducam_b0202_1280x720/images")
    parser.add_argument("--output", default="src/hardware_bringup/config/arducam_b0202_1280x720.yaml")
    parser.add_argument("--camera-name", default="arducam_b0202_imx291")
    parser.add_argument("--squares-x", type=int, default=9, help="ChArUco squares across")
    parser.add_argument("--squares-y", type=int, default=12, help="ChArUco squares down")
    parser.add_argument("--square-length", type=float, default=0.030, help="Square size in meters")
    parser.add_argument("--marker-length", type=float, default=0.022, help="Marker size in meters")
    parser.add_argument("--aruco-dict", default="5x5_100", help="Example: 5x5_50, 5x5_100, 5x5_250")
    parser.add_argument("--min-corners", type=int, default=18)
    parser.add_argument("--min-images", type=int, default=25)
    parser.add_argument("--diagonal-fov-deg", type=float, default=160.0)
    parser.add_argument("--max-rms", type=float, default=5.0)
    parser.add_argument("--max-iterations", type=int, default=200)
    parser.add_argument("--epsilon", type=float, default=1e-7)
    parser.add_argument("--use-intrinsic-guess", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fix-skew", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fix-principal-point", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--recompute-extrinsics", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--check-conditions", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--allow-bad-result", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.marker_length >= args.square_length:
        raise ValueError("--marker-length must be smaller than --square-length")

    calibrator = CharucoFisheyeCalibrator(args)
    if args.from_dir:
        image_paths = sorted(Path(args.from_dir).glob("*.png"))
    else:
        image_paths = capture_from_ros(args, calibrator)

    rms, k, d = calibrator.calibrate_from_paths(image_paths)
    validate_calibration_result(args, rms, k, d)
    first_image = cv2.imread(str(image_paths[0]), cv2.IMREAD_COLOR)
    if first_image is None:
        raise ValueError(f"Could not read first calibration image {image_paths[0]}")
    height, width = first_image.shape[:2]
    output = Path(args.output)
    write_ros_yaml(output, args.camera_name, (width, height), k, d)
    print(f"Wrote {output}")
    print(f"camera_info_url: file://{output.resolve()}")
    print(f"RMS reprojection error: {rms:.6f}")
    return 0


def validate_calibration_result(
    args: argparse.Namespace,
    rms: float,
    k: np.ndarray,
    d: np.ndarray,
) -> None:
    problems = []
    if not np.isfinite(rms) or rms > args.max_rms:
        problems.append(f"RMS reprojection error {rms:.3f} is above --max-rms {args.max_rms:.3f}")
    if np.allclose(d, 0.0, atol=1e-12):
        problems.append("fisheye distortion coefficients are all zero")
    if not np.all(np.isfinite(k)) or not np.all(np.isfinite(d)):
        problems.append("calibration returned non-finite K or D values")
    fx = float(k[0, 0])
    fy = float(k[1, 1])
    if fx <= 0.0 or fy <= 0.0:
        problems.append(f"focal lengths must be positive, got fx={fx:.3f}, fy={fy:.3f}")
    elif max(fx, fy) / min(fx, fy) > 1.5:
        problems.append(f"fx/fy ratio looks suspicious: fx={fx:.3f}, fy={fy:.3f}")

    if problems and not args.allow_bad_result:
        detail = "\n  - ".join(problems)
        raise ValueError(
            "Refusing to write camera_info_url YAML because calibration looks bad:\n"
            f"  - {detail}\n"
            "Try rerunning from saved images with --no-fix-principal-point, "
            "--no-use-intrinsic-guess, or fewer/better-distributed samples. "
            "Pass --allow-bad-result only if you intentionally want this YAML."
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
