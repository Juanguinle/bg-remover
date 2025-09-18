"""
#!/usr/bin/env python3

Development environment setup script

This script sets up a complete development environment for bg-remover
including all dependencies, pre-commit hooks, and development tools.
"""

import subprocess
import sys
import platform
from pathlib import Path

def run_command(cmd, shell=False):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        print(f"✓ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        print(f"  Error: {e.stderr}")
        return False

def main():
    """Setup development environment"""
    print("Setting up BG Remover development environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Install development dependencies
    print("\nInstalling development dependencies...")
    dev_packages = [
        "pytest>=6.0.0",
        "pytest-cov>=2.12.0",
        "black>=21.0.0",
        "flake8>=3.9.0",
        "pre-commit>=2.15.0",
        "sphinx>=4.0.0",
        "sphinx-rtd-theme>=0.5.0",
    ]
    
    for package in dev_packages:
        if not run_command([sys.executable, "-m", "pip", "install", package]):
            print(f"Failed to install {package}")
            sys.exit(1)
    
    # Install PyTorch
    print("\nInstalling PyTorch...")
    if platform.system() == "Windows":
        pytorch_cmd = [
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", 
            "--index-url", "https://download.pytorch.org/whl/cu121"
        ]
    else:
        pytorch_cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision"]
    
    if not run_command(pytorch_cmd):
        print("Failed to install PyTorch")
        sys.exit(1)
    
    # Install model dependencies
    print("\nInstalling model dependencies...")
    model_packages = [
        "transparent-background==1.2.5 --no-deps",
        "easydict", "kornia", "opencv-python", "pyvirtualcam",
        "rembg>=2.0.0"
    ]
    
    for package in model_packages:
        cmd = [sys.executable, "-m", "pip", "install"] + package.split()
        if not run_command(cmd):
            print(f"Warning: Failed to install {package}")
    
    # Install package in development mode
    print("\nInstalling bg-remover in development mode...")
    if not run_command([sys.executable, "-m", "pip", "install", "-e", "."]):
        print("Failed to install bg-remover")
        sys.exit(1)
    
    # Setup pre-commit hooks
    print("\nSetting up pre-commit hooks...")
    if not run_command(["pre-commit", "install"]):
        print("Failed to setup pre-commit hooks")
    
    # Create development directories
    print("\nCreating development directories...")
    dirs = ["test_images", "test_output", "docs/build", "logs"]
    for dir_name in dirs:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {dir_name}/")
    
    # Test installation
    print("\nTesting installation...")
    if not run_command(["bg-remover", "info"]):
        print("Installation test failed")
        sys.exit(1)
    
    print("\n🎉 Development environment setup completed successfully!")
    print("\nNext steps:")
    print("1. Run tests: pytest tests/")
    print("2. Format code: black bg_remover/")
    print("3. Lint code: flake8 bg_remover/")
    print("4. Build docs: cd docs && make html")

if __name__ == "__main__":
    main()