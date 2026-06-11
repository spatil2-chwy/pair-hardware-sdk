from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def local_launch(filename):
    return PythonLaunchDescriptionSource(
        [FindPackageShare("hardware_bringup"), "/launch/", filename]
    )


def generate_launch_description():
    args = [
        DeclareLaunchArgument("use_realsense", default_value="true"),
        DeclareLaunchArgument("use_arducam", default_value="true"),
        DeclareLaunchArgument("use_rplidar", default_value="true"),
        DeclareLaunchArgument("use_hesai", default_value="true"),
        DeclareLaunchArgument("realsense_camera_namespace", default_value="camera"),
        DeclareLaunchArgument("realsense_camera_name", default_value="camera"),
        DeclareLaunchArgument("realsense_color_profile", default_value="640,480,15"),
        DeclareLaunchArgument("realsense_depth_profile", default_value="640,480,15"),
        DeclareLaunchArgument("arducam_video_device", default_value="/dev/video0"),
        DeclareLaunchArgument("arducam_namespace", default_value="arducam"),
        DeclareLaunchArgument("rplidar_model", default_value="a1"),
        DeclareLaunchArgument("rplidar_serial_port", default_value="/dev/ttyUSB0"),
        DeclareLaunchArgument("rplidar_serial_baudrate", default_value="auto"),
        DeclareLaunchArgument("rplidar_scan_mode", default_value="auto"),
        DeclareLaunchArgument(
            "hesai_config_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("hardware_bringup"), "config", "hesai.yaml"]
            ),
        ),
    ]

    realsense = IncludeLaunchDescription(
        local_launch("realsense.launch.py"),
        condition=IfCondition(LaunchConfiguration("use_realsense")),
        launch_arguments={
            "camera_namespace": LaunchConfiguration("realsense_camera_namespace"),
            "camera_name": LaunchConfiguration("realsense_camera_name"),
            "color_profile": LaunchConfiguration("realsense_color_profile"),
            "depth_profile": LaunchConfiguration("realsense_depth_profile"),
        }.items(),
    )

    arducam = IncludeLaunchDescription(
        local_launch("arducam_v4l2.launch.py"),
        condition=IfCondition(LaunchConfiguration("use_arducam")),
        launch_arguments={
            "arducam_namespace": LaunchConfiguration("arducam_namespace"),
            "video_device": LaunchConfiguration("arducam_video_device"),
        }.items(),
    )

    rplidar = IncludeLaunchDescription(
        local_launch("rplidar.launch.py"),
        condition=IfCondition(LaunchConfiguration("use_rplidar")),
        launch_arguments={
            "model": LaunchConfiguration("rplidar_model"),
            "serial_port": LaunchConfiguration("rplidar_serial_port"),
            "serial_baudrate": LaunchConfiguration("rplidar_serial_baudrate"),
            "scan_mode": LaunchConfiguration("rplidar_scan_mode"),
        }.items(),
    )

    hesai = IncludeLaunchDescription(
        local_launch("hesai.launch.py"),
        condition=IfCondition(LaunchConfiguration("use_hesai")),
        launch_arguments={
            "hesai_config_file": LaunchConfiguration("hesai_config_file")
        }.items(),
    )

    return LaunchDescription(args + [realsense, arducam, rplidar, hesai])
