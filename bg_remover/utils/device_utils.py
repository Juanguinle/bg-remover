import platform
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def detect_device() -> str:
    """Detect best available device for processing
    
    Returns:
        Device string ('cuda', 'cpu')
    """
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            logger.info(f"CUDA available: {device_count} device(s), Primary: {device_name}")
            return "cuda"
        else:
            logger.info("CUDA not available, using CPU")
            return "cpu"
    except ImportError:
        logger.info("PyTorch not available, using CPU")
        return "cpu"

def get_system_info() -> Dict[str, Any]:
    """Get system information
    
    Returns:
        System information dictionary
    """
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        info.update({
            "total_memory_gb": round(memory.total / 1024 / 1024 / 1024, 2),
            "available_memory_gb": round(memory.available / 1024 / 1024 / 1024, 2),
            "cpu_count": psutil.cpu_count(),
        })
    except ImportError:
        pass
    
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["torch_cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["torch_cuda_version"] = torch.version.cuda
            info["torch_cuda_device_count"] = torch.cuda.device_count()
    except ImportError:
        pass
    
    return info