from glob import glob

from setuptools import find_packages, setup

package_name = "argos_provider_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml", "README.md"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Hardware SDK Maintainer",
    maintainer_email="you@example.com",
    description="Argos provider bridge for ROS 2 camera resources over Zenoh.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "hardware_provider_bridge = argos_provider_bridge.hardware_provider_bridge:main",
        ],
    },
)
