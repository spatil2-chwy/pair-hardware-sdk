from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_config = PathJoinSubstitution(
        [FindPackageShare("hardware_bringup"), "config", "hesai.yaml"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("hesai_namespace", default_value="hesai_ros_driver"),
            DeclareLaunchArgument("hesai_config_file", default_value=default_config),
            Node(
                package="hesai_ros_driver",
                executable="hesai_ros_driver_node",
                namespace=LaunchConfiguration("hesai_namespace"),
                name="hesai_ros_driver_node",
                output="screen",
                parameters=[{"config_path": LaunchConfiguration("hesai_config_file")}],
            ),
        ]
    )
