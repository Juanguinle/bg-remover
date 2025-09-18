from abc import ABC, abstractmethod
from typing import Union, Any, Dict
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class BaseModel(ABC):
    """Abstract base class for background removal models"""
    
    def __init__(self, device: str = "auto", **kwargs):
        """Initialize the model
        
        Args:
            device: Device to use ('auto', 'cpu', 'cuda')
            **kwargs: Model-specific options
        """
        self.device = self._resolve_device(device)
        self.options = kwargs
        self._initialized = False
        
    def _resolve_device(self, device: str) -> str:
        """Resolve device setting to actual device"""
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device
    
    @abstractmethod
    def initialize(self):
        """Initialize the model (load weights, etc.)"""
        pass
    
    @abstractmethod
    def process_image(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """Process a single image to remove background
        
        Args:
            image: Input image as PIL Image or numpy array
            
        Returns:
            Processed image with transparent background
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up model resources"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        if not self._initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
    
    @property
    def name(self) -> str:
        """Get model name"""
        return self.__class__.__name__
    
    @property
    def is_initialized(self) -> bool:
        """Check if model is initialized"""
        return self._initialized