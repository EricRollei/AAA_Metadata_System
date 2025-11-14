"""
ComfyUI Nodes - Custom Nodes Collection for ComfyUI
Author: Eric Hiss (GitHub: EricRollei)
Version: 0.1.0
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="comfyui-nodes",
    version="0.1.0",
    author="Eric Hiss",
    author_email="your.email@example.com",  # Replace with your email
    description="A collection of custom nodes for ComfyUI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/EricRollei/comfyui-nodes",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Creative Commons Attribution-NonCommercial 4.0 International License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Graphics",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            # Add any command line scripts here
            # "example=package.module:function",
        ],
    },
)
