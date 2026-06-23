from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.substitutions import FindPackageShare


def local_launch(filename):
    return PythonLaunchDescriptionSource(
        [FindPackageShare("hardware_bringup"), "/launch/", filename]
    )


def generate_launch_description():
    args = [
        DeclareLaunchArgument("use_realsense", default_value="true"),
        DeclareLaunchArgument("use_realsense_001", default_value="true"),
        DeclareLaunchArgument("use_realsense_002", default_value="false"),
        DeclareLaunchArgument("use_arducam", default_value="true"),
        DeclareLaunchArgument("use_rplidar", default_value="true"),
        DeclareLaunchArgument("use_hesai", default_value="true"),
        DeclareLaunchArgument("use_argos_provider", default_value="false"),
        DeclareLaunchArgument("realsense_camera_namespace", default_value="camera"),
        DeclareLaunchArgument("realsense_camera_name", default_value="realsense_001"),
        DeclareLaunchArgument(
            "realsense_001_camera_namespace",
            default_value=LaunchConfiguration("realsense_camera_namespace"),
        ),
        DeclareLaunchArgument(
            "realsense_001_camera_name",
            default_value=LaunchConfiguration("realsense_camera_name"),
        ),
        DeclareLaunchArgument("realsense_001_serial_no", default_value="''"),
        DeclareLaunchArgument("realsense_002_camera_namespace", default_value="camera"),
        DeclareLaunchArgument("realsense_002_camera_name", default_value="realsense_002"),
        DeclareLaunchArgument("realsense_002_serial_no", default_value="''"),
        DeclareLaunchArgument("realsense_color_profile", default_value="1280,720,15"),
        DeclareLaunchArgument("realsense_depth_profile", default_value="1280,720,15"),
        DeclareLaunchArgument("arducam_video_device", default_value="/dev/video0"),
        DeclareLaunchArgument("arducam_namespace", default_value="arducam"),
        DeclareLaunchArgument("arducam_image_width", default_value="1280"),
        DeclareLaunchArgument("arducam_image_height", default_value="720"),
        DeclareLaunchArgument("arducam_fps", default_value="15"),
        DeclareLaunchArgument("arducam_camera_info_url", default_value=""),
        DeclareLaunchArgument(
            "argos_manifest_path",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("argos_provider_bridge"),
                    "config",
                    "puffle_go2.yaml",
                ]
            ),
        ),
        DeclareLaunchArgument("argos_provider_id", default_value=""),
        DeclareLaunchArgument("argos_key_prefix", default_value=""),
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

    realsense_001 = IncludeLaunchDescription(
        local_launch("realsense.launch.py"),
        condition=IfCondition(
            PythonExpression(
                [
                    "'",
                    LaunchConfiguration("use_realsense"),
                    "'.lower() == 'true' and '",
                    LaunchConfiguration("use_realsense_001"),
                    "'.lower() == 'true'",
                ]
            )
        ),
        launch_arguments={
            "camera_namespace": LaunchConfiguration("realsense_001_camera_namespace"),
            "camera_name": LaunchConfiguration("realsense_001_camera_name"),
            "serial_no": LaunchConfiguration("realsense_001_serial_no"),
            "color_profile": LaunchConfiguration("realsense_color_profile"),
            "depth_profile": LaunchConfiguration("realsense_depth_profile"),
        }.items(),
    )

    realsense_002 = IncludeLaunchDescription(
        local_launch("realsense.launch.py"),
        condition=IfCondition(
            PythonExpression(
                [
                    "'",
                    LaunchConfiguration("use_realsense"),
                    "'.lower() == 'true' and '",
                    LaunchConfiguration("use_realsense_002"),
                    "'.lower() == 'true'",
                ]
            )
        ),
        launch_arguments={
            "camera_namespace": LaunchConfiguration("realsense_002_camera_namespace"),
            "camera_name": LaunchConfiguration("realsense_002_camera_name"),
            "serial_no": LaunchConfiguration("realsense_002_serial_no"),
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
            "image_width": LaunchConfiguration("arducam_image_width"),
            "image_height": LaunchConfiguration("arducam_image_height"),
            "fps": LaunchConfiguration("arducam_fps"),
            "camera_info_url": LaunchConfiguration("arducam_camera_info_url"),
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

    argos_provider = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                FindPackageShare("argos_provider_bridge"),
                "/launch/hardware_provider_bridge.launch.py",
            ]
        ),
        condition=IfCondition(LaunchConfiguration("use_argos_provider")),
        launch_arguments={
            "manifest_path": LaunchConfiguration("argos_manifest_path"),
            "provider_id": LaunchConfiguration("argos_provider_id"),
            "key_prefix": LaunchConfiguration("argos_key_prefix"),
        }.items(),
    )

    return LaunchDescription(
        args + [realsense_001, realsense_002, arducam, rplidar, hesai, argos_provider]
    )
