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
    iproute2 \
    less \
    libboost-system-dev \
    libboost-thread-dev \
    libusb-1.0-0-dev \
    net-tools \
    python3-colcon-common-extensions \
    python3-pip \
    python3-rosdep \
    python3-vcstool \
    ros-humble-v4l2-camera \
    sudo \
    udev \
    usbutils \
    v4l-utils \
  && (rosdep init 2>/dev/null || true) \
  && rosdep update \
  && rm -rf /var/lib/apt/lists/*

COPY hardware_sdk.repos /tmp/hardware_sdk.repos

RUN mkdir -p /opt/pair_vendor_ws/src \
  && vcs import /opt/pair_vendor_ws/src < /tmp/hardware_sdk.repos \
  && git -C /opt/pair_vendor_ws/src/vendor/HesaiLidar_ROS_2.0 submodule update --init --recursive \
  && apt-get update \
  && source /opt/ros/${ROS_DISTRO}/setup.bash \
  && rosdep install -i --from-paths /opt/pair_vendor_ws/src --rosdistro ${ROS_DISTRO} -y \
  && cd /opt/pair_vendor_ws \
  && colcon build --merge-install --symlink-install \
  && rm -rf /var/lib/apt/lists/*

COPY docker/humble/entrypoint.sh /ros_entrypoint.sh
COPY docker/humble/clone_and_build.sh /usr/local/bin/clone-and-build-pair-hardware-sdk

RUN chmod +x /ros_entrypoint.sh /usr/local/bin/clone-and-build-pair-hardware-sdk

WORKDIR /workspaces

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
