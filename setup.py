#!/usr/bin/env python3
"""Setup script for now-playing package."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="now-playing",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AirPlay metadata display for shairport-sync",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/now-playing",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pygame>=2.0.0",
        "mcp>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "nowplaying-display=nowplaying.display:main",
            "nowplaying-test=nowplaying.test:main",
            "nowplaying-mcp=nowplaying.cli:mcp_main",
        ],
    },
    include_package_data=True,
)
