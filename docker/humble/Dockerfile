FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=humble \
    RMW_IMPLEMENTATION=rmw_fastrtps_cpp

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    ca-certificates \
    curl \
    git \
    gnupg \
    iproute2 \
    less \
    libboost-system-dev \
    libboost-thread-dev \
    libusb-1.0-0-dev \
    net-tools \
    python3-colcon-common-extensions \
    python3-numpy \
    python3-pip \
    python3-rosdep \
    python3-vcstool \
    python3-yaml \
    ros-humble-rqt \
    ros-humble-rqt-common-plugins \
    ros-humble-rqt-image-view \
    ros-humble-rviz2 \
    ros-humble-v4l2-camera \
    sudo \
    udev \
    usbutils \
    v4l-utils \
  && install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://librealsense.realsenseai.com/Debian/librealsenseai.asc \
    | gpg --dearmor -o /etc/apt/keyrings/librealsenseai.gpg \
  && . /etc/os-release \
  && echo "deb [signed-by=/etc/apt/keyrings/librealsenseai.gpg] https://librealsense.realsenseai.com/Debian/apt-repo ${VERSION_CODENAME} main" \
    > /etc/apt/sources.list.d/librealsense.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    librealsense2-dev \
    librealsense2-utils \
  && (rosdep init 2>/dev/null || true) \
  && rosdep update \
  && python3 -m pip install --no-cache-dir eclipse-zenoh \
  && rm -rf /var/lib/apt/lists/*

COPY hardware_sdk.repos /tmp/hardware_sdk.repos

RUN mkdir -p /opt/pair_vendor_ws/src \
  && vcs import /opt/pair_vendor_ws/src < /tmp/hardware_sdk.repos \
  && git -C /opt/pair_vendor_ws/src/vendor/HesaiLidar_ROS_2.0 submodule update --init --recursive \
  && apt-get update \
  && source /opt/ros/${ROS_DISTRO}/setup.bash \
  && rosdep install -i --from-paths /opt/pair_vendor_ws/src --rosdistro ${ROS_DISTRO} --skip-keys=librealsense2 -y \
  && cd /opt/pair_vendor_ws \
  && colcon build --merge-install --symlink-install \
  && rm -rf /var/lib/apt/lists/*

COPY docker/humble/entrypoint.sh /ros_entrypoint.sh
COPY docker/humble/clone_and_build.sh /usr/local/bin/clone-and-build-pair-hardware-sdk

RUN chmod +x /ros_entrypoint.sh /usr/local/bin/clone-and-build-pair-hardware-sdk

WORKDIR /workspaces

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
