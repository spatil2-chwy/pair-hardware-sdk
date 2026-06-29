cmake_minimum_required(VERSION 3.8)
project(hardware_bringup)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS
    scripts/arducam_fisheye_rectifier.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
