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

MODEL_DEFAULTS = {
    "a1": {"serial_baudrate": "115200", "scan_mode": "Sensitivity"},
    "a2m7": {"serial_baudrate": "256000", "scan_mode": "Sensitivity"},
    "a2m8": {"serial_baudrate": "115200", "scan_mode": "Sensitivity"},
    "a2m12": {"serial_baudrate": "256000", "scan_mode": "Sensitivity"},
    "a3": {"serial_baudrate": "256000", "scan_mode": "Sensitivity"},
    "s1": {"serial_baudrate": "256000", "scan_mode": "Sensitivity"},
    "s1_tcp": {"serial_baudrate": "256000", "scan_mode": "Sensitivity"},
    "s2": {"serial_baudrate": "1000000", "scan_mode": "DenseBoost"},
    "s2e": {"serial_baudrate": "1000000", "scan_mode": "Sensitivity"},
    "s3": {"serial_baudrate": "1000000", "scan_mode": "DenseBoost"},
    "t1": {"serial_baudrate": "1000000", "scan_mode": "Sensitivity"},
    "c1": {"serial_baudrate": "460800", "scan_mode": "Standard"},
}


def include_rplidar(context):
    model = LaunchConfiguration("model").perform(context)
    with_rviz = LaunchConfiguration("with_rviz").perform(context).lower() == "true"
    serial_baudrate = LaunchConfiguration("serial_baudrate").perform(context)
    scan_mode = LaunchConfiguration("scan_mode").perform(context)

    if model not in SUPPORTED_MODELS:
        valid = ", ".join(sorted(SUPPORTED_MODELS))
        raise RuntimeError(f"Unsupported RPLIDAR model '{model}'. Valid values: {valid}")

    defaults = MODEL_DEFAULTS[model]
    if serial_baudrate == "auto":
        serial_baudrate = defaults["serial_baudrate"]
    if scan_mode == "auto":
        scan_mode = defaults["scan_mode"]

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
                "serial_baudrate": serial_baudrate,
                "frame_id": LaunchConfiguration("frame_id"),
                "inverted": LaunchConfiguration("inverted"),
                "angle_compensate": LaunchConfiguration("angle_compensate"),
                "scan_mode": scan_mode,
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
            DeclareLaunchArgument("serial_baudrate", default_value="auto"),
            DeclareLaunchArgument("frame_id", default_value="rplidar_link"),
            DeclareLaunchArgument("inverted", default_value="false"),
            DeclareLaunchArgument("angle_compensate", default_value="true"),
            DeclareLaunchArgument("scan_mode", default_value="auto"),
            OpaqueFunction(function=include_rplidar),
        ]
    )
