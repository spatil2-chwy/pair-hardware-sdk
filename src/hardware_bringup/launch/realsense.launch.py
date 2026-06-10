import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def normalize_profile(profile, separator):
    return profile.replace("x", separator).replace(",", separator)


def start_realsense(context):
    realsense_share = get_package_share_directory("realsense2_camera")
    launch_file = os.path.join(realsense_share, "launch", "rs_launch.py")

    with open(launch_file, "r", encoding="utf-8") as launch_source:
        source = launch_source.read()

    color_profile = LaunchConfiguration("color_profile").perform(context)
    depth_profile = LaunchConfiguration("depth_profile").perform(context)

    launch_arguments = {
        "camera_namespace": LaunchConfiguration("camera_namespace"),
        "camera_name": LaunchConfiguration("camera_name"),
        "enable_depth": LaunchConfiguration("enable_depth"),
        "enable_color": LaunchConfiguration("enable_color"),
        "align_depth.enable": LaunchConfiguration("align_depth.enable"),
        "enable_sync": LaunchConfiguration("enable_sync"),
        "enable_rgbd": LaunchConfiguration("enable_rgbd"),
        "pointcloud.enable": LaunchConfiguration("pointcloud.enable"),
    }

    if "rgb_camera.color_profile" in source:
        launch_arguments["rgb_camera.color_profile"] = normalize_profile(
            color_profile, ","
        )
        launch_arguments["depth_module.depth_profile"] = normalize_profile(
            depth_profile, ","
        )
    else:
        launch_arguments["rgb_camera.profile"] = normalize_profile(color_profile, "x")
        launch_arguments["depth_module.profile"] = normalize_profile(depth_profile, "x")

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_file),
            launch_arguments=launch_arguments.items(),
        )
    ]


def generate_launch_description():
    args = [
        DeclareLaunchArgument("camera_namespace", default_value="camera"),
        DeclareLaunchArgument("camera_name", default_value="camera"),
        DeclareLaunchArgument("enable_depth", default_value="true"),
        DeclareLaunchArgument("enable_color", default_value="true"),
        DeclareLaunchArgument("align_depth.enable", default_value="true"),
        DeclareLaunchArgument("enable_sync", default_value="true"),
        DeclareLaunchArgument("enable_rgbd", default_value="false"),
        DeclareLaunchArgument("pointcloud.enable", default_value="false"),
        DeclareLaunchArgument("color_profile", default_value="640,480,15"),
        DeclareLaunchArgument("depth_profile", default_value="640,480,15"),
    ]

    return LaunchDescription(args + [OpaqueFunction(function=start_realsense)])
