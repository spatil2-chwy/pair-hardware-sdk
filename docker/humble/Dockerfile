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
    libusb-1.0-0-dev \
    net-tools \
    python3-colcon-common-extensions \
    python3-pip \
    python3-rosdep \
    python3-vcstool \
    sudo \
    udev \
    usbutils \
    v4l-utils \
  && (rosdep init 2>/dev/null || true) \
  && rosdep update \
  && rm -rf /var/lib/apt/lists/*

COPY docker/humble/entrypoint.sh /ros_entrypoint.sh
COPY docker/humble/clone_and_build.sh /usr/local/bin/clone-and-build-pair-hardware-sdk

RUN chmod +x /ros_entrypoint.sh /usr/local/bin/clone-and-build-pair-hardware-sdk

WORKDIR /workspaces

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
