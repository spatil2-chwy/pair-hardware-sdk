from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_camera(context):
    width = int(LaunchConfiguration("image_width").perform(context))
    height = int(LaunchConfiguration("image_height").perform(context))
    fps = int(LaunchConfiguration("fps").perform(context))

    return [
        Node(
            package="v4l2_camera",
            executable="v4l2_camera_node",
            namespace=LaunchConfiguration("arducam_namespace").perform(context),
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
                }
            ],
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("arducam_namespace", default_value="arducam"),
            DeclareLaunchArgument("video_device", default_value="/dev/video0"),
            DeclareLaunchArgument("frame_id", default_value="arducam_color_optical_frame"),
            DeclareLaunchArgument("pixel_format", default_value="YUYV"),
            DeclareLaunchArgument("output_encoding", default_value="rgb8"),
            DeclareLaunchArgument("image_width", default_value="640"),
            DeclareLaunchArgument("image_height", default_value="480"),
            DeclareLaunchArgument("fps", default_value="30"),
            OpaqueFunction(function=start_camera),
        ]
    )
