from typing import Union
import numpy as np
from PIL import Image
import logging

from .base import BaseModel

logger = logging.getLogger(__name__)

class RembgModel(BaseModel):
    """Rembg model implementation"""
    
    def __init__(self, device: str = "auto", model_name: str = "u2net", **kwargs):
        """Initialize Rembg model
        
        Args:
            device: Device to use
            model_name: Model name ('u2net', 'silueta', etc.)
            **kwargs: Additional options
        """
        super().__init__(device, **kwargs)
        self.model_name = model_name
        self.session = None
        
    def initialize(self):
        """Initialize the model"""
        if self._initialized:
            return
            
        try:
            # Import here to avoid issues if package not installed
            import rembg
            
            logger.info(f"Initializing Rembg model ({self.model_name}) on {self.device}")
            
            # Create session
            self.session = rembg.new_session(self.model_name)
            
            self._initialized = True
            logger.info(f"Rembg model ({self.model_name}) initialized successfully")
            
        except ImportError:
            logger.error("rembg package not installed. Install with: pip install rembg")
            raise
        except Exception as e:
            logger.error(f"Error initializing Rembg model: {e}")
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
            import rembg
            
            # Convert to PIL Image if needed
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            # Ensure RGB mode for processing
            if image.mode not in ['RGB', 'RGBA']:
                image = image.convert('RGB')
            
            # Process with rembg
            result = rembg.remove(image, session=self.session)
            
            # Ensure RGBA mode
            if result.mode != 'RGBA':
                result = result.convert('RGBA')
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image with Rembg: {e}")
            raise
    
    def cleanup(self):
        """Clean up model resources"""
        if self.session is not None:
            try:
                # Rembg sessions don't have explicit cleanup
                pass
            except:
                pass
        self.session = None
        self._initialized = False
        logger.debug("Rembg model cleaned up")