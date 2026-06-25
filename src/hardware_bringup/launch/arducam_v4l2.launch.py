from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def start_camera(context):
    width = int(LaunchConfiguration("image_width").perform(context))
    height = int(LaunchConfiguration("image_height").perform(context))
    fps = int(LaunchConfiguration("fps").perform(context))

    namespace = LaunchConfiguration("arducam_namespace").perform(context)

    return [
        Node(
            package="v4l2_camera",
            executable="v4l2_camera_node",
            namespace=namespace,
            name="camera",
            output="screen",
            parameters=[
                {
                    "video_device": LaunchConfiguration("video_device").perform(context),
                    "camera_frame_id": LaunchConfiguration("frame_id").perform(context),
                    "pixel_format": LaunchConfiguration("pixel_format").perform(context),
                    "output_encoding": LaunchConfiguration("output_encoding").perform(context),
                    "image_size": [width, height],
                    "time_per_frame": [1, fps],
                    "camera_info_url": LaunchConfiguration("camera_info_url").perform(context),
                }
            ],
        ),
        Node(
            package="hardware_bringup",
            executable="arducam_fisheye_rectifier.py",
            namespace=namespace,
            name="fisheye_rectifier",
            output="screen",
            condition=IfCondition(LaunchConfiguration("publish_rect")),
            parameters=[
                {
                    "image_topic": "image_raw",
                    "camera_info_topic": "camera_info",
                    "rect_image_topic": "image_rect",
                    "rect_camera_info_topic": "camera_info_rect",
                    "balance": ParameterValue(LaunchConfiguration("rect_balance"), value_type=float),
                    "fov_scale": ParameterValue(
                        LaunchConfiguration("rect_fov_scale"),
                        value_type=float,
                    ),
                    "interpolation": LaunchConfiguration("rect_interpolation").perform(context),
                }
            ],
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("arducam_namespace", default_value="arducam"),
            DeclareLaunchArgument("video_device", default_value="/dev/video0"),
            DeclareLaunchArgument("frame_id", default_value="arducam_color_optical_frame"),
            DeclareLaunchArgument("pixel_format", default_value="YUYV"),
            DeclareLaunchArgument("output_encoding", default_value="rgb8"),
            DeclareLaunchArgument("image_width", default_value="1280"),
            DeclareLaunchArgument("image_height", default_value="720"),
            DeclareLaunchArgument("fps", default_value="15"),
            DeclareLaunchArgument(
                "camera_info_url",
                default_value=[
                    "file://",
                    PathJoinSubstitution(
                        [
                            FindPackageShare("hardware_bringup"),
                            "config",
                            "arducam_b0202_1280x720.yaml",
                        ]
                    ),
                ],
            ),
            DeclareLaunchArgument("publish_rect", default_value="true"),
            DeclareLaunchArgument("rect_balance", default_value="0.0"),
            DeclareLaunchArgument("rect_fov_scale", default_value="1.0"),
            DeclareLaunchArgument("rect_interpolation", default_value="linear"),
            OpaqueFunction(function=start_camera),
        ]
    )
