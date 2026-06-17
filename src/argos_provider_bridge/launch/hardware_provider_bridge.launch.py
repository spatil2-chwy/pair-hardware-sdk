from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
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
                        "puffle_go2.yaml",
                    ]
                ),
            ),
            DeclareLaunchArgument("provider_id", default_value=""),
            DeclareLaunchArgument("key_prefix", default_value=""),
            DeclareLaunchArgument(
                "zenoh_connect",
                default_value=EnvironmentVariable("ARGOS_ZENOH_CONNECT", default_value=""),
            ),
            DeclareLaunchArgument(
                "zenoh_listen",
                default_value=EnvironmentVariable("ARGOS_ZENOH_LISTEN", default_value=""),
            ),
            DeclareLaunchArgument(
                "zenoh_mode",
                default_value=EnvironmentVariable("ARGOS_ZENOH_MODE", default_value=""),
            ),
            Node(
                package="argos_provider_bridge",
                executable="hardware_provider_bridge",
                name="argos_hardware_provider",
                output="screen",
                parameters=[
                    {
                        "manifest_path": LaunchConfiguration("manifest_path"),
                        "provider_id": LaunchConfiguration("provider_id"),
                        "key_prefix": LaunchConfiguration("key_prefix"),
                        "zenoh_connect": LaunchConfiguration("zenoh_connect"),
                        "zenoh_listen": LaunchConfiguration("zenoh_listen"),
                        "zenoh_mode": LaunchConfiguration("zenoh_mode"),
                    }
                ],
            ),
        ]
    )
