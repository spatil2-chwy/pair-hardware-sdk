from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare


SUPPORTED_MODELS = {
    "a1",
    "a2m7",
    "a2m8",
    "a2m12",
    "a3",
    "s1",
    "s1_tcp",
    "s2",
    "s2e",
    "s3",
    "t1",
    "c1",
}


def include_rplidar(context):
    model = LaunchConfiguration("model").perform(context)
    with_rviz = LaunchConfiguration("with_rviz").perform(context).lower() == "true"

    if model not in SUPPORTED_MODELS:
        valid = ", ".join(sorted(SUPPORTED_MODELS))
        raise RuntimeError(f"Unsupported RPLIDAR model '{model}'. Valid values: {valid}")

    prefix = "view_" if with_rviz else ""
    launch_file = f"{prefix}rplidar_{model}_launch.py"

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [FindPackageShare("rplidar_ros"), "/launch/", launch_file]
            ),
            launch_arguments={
                "channel_type": LaunchConfiguration("channel_type"),
                "serial_port": LaunchConfiguration("serial_port"),
                "serial_baudrate": LaunchConfiguration("serial_baudrate"),
                "frame_id": LaunchConfiguration("frame_id"),
                "inverted": LaunchConfiguration("inverted"),
                "angle_compensate": LaunchConfiguration("angle_compensate"),
                "scan_mode": LaunchConfiguration("scan_mode"),
            }.items(),
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("model", default_value="a1"),
            DeclareLaunchArgument("with_rviz", default_value="false"),
            DeclareLaunchArgument("channel_type", default_value="serial"),
            DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("serial_baudrate", default_value="115200"),
            DeclareLaunchArgument("frame_id", default_value="rplidar_link"),
            DeclareLaunchArgument("inverted", default_value="false"),
            DeclareLaunchArgument("angle_compensate", default_value="true"),
            DeclareLaunchArgument("scan_mode", default_value="Sensitivity"),
            OpaqueFunction(function=include_rplidar),
        ]
    )
