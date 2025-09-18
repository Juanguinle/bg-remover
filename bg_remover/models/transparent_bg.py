from typing import Union
import numpy as np
from PIL import Image
import logging

from .base import BaseModel

logger = logging.getLogger(__name__)

class TransparentBackgroundModel(BaseModel):
    """Transparent Background model implementation"""
    
    def __init__(self, device: str = "auto", quality: str = "high", mode: str = "base", **kwargs):
        """Initialize Transparent Background model
        
        Args:
            device: Device to use
            quality: Quality setting ('high', 'medium', 'low')
            mode: Model mode ('base', 'base-nightly')
            **kwargs: Additional options
        """
        super().__init__(device, **kwargs)
        self.quality = quality
        self.mode = mode
        self.model = None
        
    def initialize(self):
        """Initialize the model"""
        if self._initialized:
            return
            
        try:
            import transparent_background
            import torch
            
            logger.info(f"Initializing Transparent Background model (mode: {self.mode}) on {self.device}")
            
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Initialize model with mode parameter
            self.model = transparent_background.Remover(
                device=self.device,
                mode=self.mode,
                **self.options
            )
            
            self._initialized = True
            logger.info(f"Transparent Background model ({self.mode}) initialized successfully")
            
        except ImportError as e:
            logger.error("transparent-background package not installed. Install with: pip install transparent-background==1.2.5 --no-deps")
            raise
        except Exception as e:
            logger.error(f"Error initializing Transparent Background model: {e}")
            raise
    
    def process_image(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """Process image to remove background
        
        Args:
            image: Input image
            
        Returns:
            Image with transparent background
        """
        if not self._initialized:
            self.initialize()
            
        try:
            # Convert to PIL Image if needed
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            # Ensure RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Process with transparent-background
            result = self.model.process(image)
            
            # Convert result to RGBA if needed
            if isinstance(result, np.ndarray):
                if result.shape[2] == 3:
                    # Add alpha channel
                    alpha = np.ones((result.shape[0], result.shape[1], 1), dtype=result.dtype) * 255
                    result = np.concatenate([result, alpha], axis=2)
                result = Image.fromarray(result, 'RGBA')
            elif result.mode != 'RGBA':
                result = result.convert('RGBA')
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image with Transparent Background: {e}")
            raise
    
    def cleanup(self):
        """Clean up model resources"""
        if self.model is not None:
            try:
                import torch
                if self.device == "cuda" and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
        self.model = None
        self._initialized = False
        logger.debug("Transparent Background model cleaned up")