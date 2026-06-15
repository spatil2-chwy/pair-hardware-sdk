from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "manifest_path",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("argos_provider_bridge"),
                        "config",
                        "puffle_go2_provider.yaml",
                    ]
                ),
            ),
            DeclareLaunchArgument("provider_id", default_value=""),
            DeclareLaunchArgument("key_prefix", default_value=""),
            Node(
                package="argos_provider_bridge",
                executable="camera_provider_bridge",
                name="argos_camera_provider_bridge",
                output="screen",
                parameters=[
                    {
                        "manifest_path": LaunchConfiguration("manifest_path"),
                        "provider_id": LaunchConfiguration("provider_id"),
                        "key_prefix": LaunchConfiguration("key_prefix"),
                    }
                ],
            ),
        ]
    )
