from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("camera_namespace", default_value="camera"),
            DeclareLaunchArgument("camera_name", default_value="camera"),
            DeclareLaunchArgument("serial_no", default_value="''"),
            DeclareLaunchArgument("enable_depth", default_value="true"),
            DeclareLaunchArgument("enable_color", default_value="true"),
            DeclareLaunchArgument("enable_infra", default_value="false"),
            DeclareLaunchArgument("enable_infra1", default_value="false"),
            DeclareLaunchArgument("enable_infra2", default_value="false"),
            DeclareLaunchArgument("align_depth.enable", default_value="true"),
            DeclareLaunchArgument("enable_sync", default_value="true"),
            DeclareLaunchArgument("enable_rgbd", default_value="false"),
            DeclareLaunchArgument("pointcloud.enable", default_value="false"),
            DeclareLaunchArgument("color_profile", default_value="640,480,15"),
            DeclareLaunchArgument("depth_profile", default_value="640,480,15"),
            DeclareLaunchArgument("log_level", default_value="info"),
            Node(
                package="realsense2_camera",
                executable="realsense2_camera_node",
                namespace=LaunchConfiguration("camera_namespace"),
                name=LaunchConfiguration("camera_name"),
                output="screen",
                emulate_tty=True,
                arguments=[
                    "--ros-args",
                    "--log-level",
                    LaunchConfiguration("log_level"),
                ],
                parameters=[
                    {
                        "camera_namespace": LaunchConfiguration("camera_namespace"),
                        "camera_name": LaunchConfiguration("camera_name"),
                        "serial_no": ParameterValue(
                            LaunchConfiguration("serial_no"),
                            value_type=str,
                        ),
                        "enable_depth": LaunchConfiguration("enable_depth"),
                        "enable_color": LaunchConfiguration("enable_color"),
                        "enable_infra": LaunchConfiguration("enable_infra"),
                        "enable_infra1": LaunchConfiguration("enable_infra1"),
                        "enable_infra2": LaunchConfiguration("enable_infra2"),
                        "align_depth.enable": LaunchConfiguration("align_depth.enable"),
                        "enable_sync": LaunchConfiguration("enable_sync"),
                        "enable_rgbd": LaunchConfiguration("enable_rgbd"),
                        "pointcloud.enable": LaunchConfiguration("pointcloud.enable"),
                        "rgb_camera.color_profile": LaunchConfiguration(
                            "color_profile"
                        ),
                        "depth_module.depth_profile": LaunchConfiguration(
                            "depth_profile"
                        ),
                    }
                ],
            ),
        ]
    )
