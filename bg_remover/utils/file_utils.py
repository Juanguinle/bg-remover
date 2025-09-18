import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

def ensure_directory(path: str) -> Path:
    """Ensure directory exists
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes
    
    Args:
        file_path: File path
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = file_path.stat().st_size
        return size_bytes / 1024 / 1024
    except Exception:
        return 0.0

def is_image_file(file_path: Path, extensions: List[str] = None) -> bool:
    """Check if file is an image
    
    Args:
        file_path: File path
        extensions: List of valid extensions
        
    Returns:
        True if file is an image
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    return file_path.suffix.lower() in [ext.lower() for ext in extensions]