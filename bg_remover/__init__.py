"""
BG Remover - Professional Background Removal Application
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.processor import BackgroundProcessor
from .core.monitor import FolderMonitor
from .config.manager import ConfigManager

__all__ = ["BackgroundProcessor", "FolderMonitor", "ConfigManager"]
