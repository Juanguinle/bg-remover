from setuptools import setup, find_packages
import os
import sys

# Read README for long description
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "Professional background removal application with automatic folder monitoring"

# Read requirements with special handling for problematic packages
def read_requirements():
    requirements = []
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Handle special cases for problematic packages
                    if "transparent-background" in line:
                        requirements.append("transparent-background>=1.2.5")
                    else:
                        requirements.append(line)
    except FileNotFoundError:
        # Fallback requirements if file not found
        requirements = [
            "torch>=1.9.0",
            "torchvision>=0.10.0",
            "opencv-python>=4.5.0",
            "Pillow>=8.0.0",
            "numpy>=1.21.0",
            "watchdog>=2.1.0",
            "pyyaml>=6.0",
            "click>=8.0.0",
            "tqdm>=4.62.0",
            "psutil>=5.8.0",
            "easydict>=1.9",
            "kornia>=0.6.0",
            "pyvirtualcam>=0.6.0",
            "rembg>=2.0.0",
            "onnxruntime>=1.12.0",
            "transparent-background>=1.2.5",
        ]
    return requirements

setup(
    name="bg-remover",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Professional background removal application with automatic folder monitoring",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/bg-remover",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "bg-remover=bg_remover.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "bg_remover": ["config/*.yaml", "config/*.json"],
    },
    zip_safe=False,
    keywords="background-removal image-processing ai computer-vision machine-learning",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/bg-remover/issues",
        "Source": "https://github.com/yourusername/bg-remover",
        "Documentation": "https://github.com/yourusername/bg-remover/blob/main/README.md",
    },
)