from typing import Union
import os
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
import logging

from .base import BaseModel

logger = logging.getLogger(__name__)

class SAMModel(BaseModel):
    """Segment Anything Model implementation"""
    
    def __init__(self, device: str = "auto", model_type: str = "vit_b", **kwargs):
        """Initialize SAM model
        
        Args:
            device: Device to use
            model_type: Model type ('vit_b', 'vit_l', 'vit_h')
            **kwargs: Additional options
        """
        super().__init__(device, **kwargs)
        self.model_type = model_type
        self.predictor = None
        
    def _download_checkpoint(self, url: str, checkpoint_path: Path) -> str:
        """Download SAM checkpoint if not exists"""
        if checkpoint_path.exists():
            logger.info(f"Using existing checkpoint: {checkpoint_path}")
            return str(checkpoint_path)
            
        logger.info(f"Downloading SAM checkpoint: {url}")
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            urllib.request.urlretrieve(url, checkpoint_path)
            logger.info(f"Downloaded checkpoint to: {checkpoint_path}")
            return str(checkpoint_path)
        except Exception as e:
            logger.error(f"Failed to download checkpoint: {e}")
            raise
        
    def initialize(self):
        """Initialize the model"""
        if self._initialized:
            return
            
        try:
            from segment_anything import sam_model_registry, SamPredictor
            
            logger.info(f"Initializing SAM model ({self.model_type}) on {self.device}")
            
            # Checkpoint URLs and local paths
            checkpoint_info = {
                "vit_b": ("https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth", "sam_vit_b_01ec64.pth"),
                "vit_l": ("https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth", "sam_vit_l_0b3195.pth"), 
                "vit_h": ("https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth", "sam_vit_h_4b8939.pth")
            }
            
            if self.model_type not in checkpoint_info:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            url, filename = checkpoint_info[self.model_type]
            checkpoint_path = Path.home() / ".cache" / "sam" / filename
            
            # Download checkpoint
            local_checkpoint = self._download_checkpoint(url, checkpoint_path)
            
            # Load model
            sam = sam_model_registry[self.model_type](checkpoint=local_checkpoint)
            sam.to(device=self.device)
            
            self.predictor = SamPredictor(sam)
            self._initialized = True
            
            logger.info(f"SAM model ({self.model_type}) initialized successfully")
            
        except ImportError:
            logger.error("segment-anything package not installed. Install with: pip install segment-anything")
            raise
        except Exception as e:
            logger.error(f"Error initializing SAM model: {e}")
            raise
    
    def process_image(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """Process image with SAM
        
        Args:
            image: Input image
            
        Returns:
            Image with transparent background
        """
        if not self._initialized:
            self.initialize()
            
        try:
            import cv2
            
            # Convert to numpy array
            if isinstance(image, Image.Image):
                image_array = np.array(image)
            else:
                image_array = image
                
            # SAM expects RGB
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_rgb = image_array
            else:
                image_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            
            # Set image for SAM
            self.predictor.set_image(image_rgb)
            
            # Use center point as prompt for automatic segmentation
            h, w = image_rgb.shape[:2]
            center_point = np.array([[w//2, h//2]])
            point_labels = np.array([1])  # foreground point
            
            # Predict mask
            masks, scores, logits = self.predictor.predict(
                point_coords=center_point,
                point_labels=point_labels,
                multimask_output=True,
            )
            
            # Use the best mask (highest score)
            best_mask_idx = np.argmax(scores)
            best_mask = masks[best_mask_idx]
            
            # Create RGBA output
            result = np.zeros((image_array.shape[0], image_array.shape[1], 4), dtype=np.uint8)
            result[:, :, :3] = image_array[:, :, :3]  # RGB channels
            result[:, :, 3] = (best_mask * 255).astype(np.uint8)  # Alpha channel
            
            return Image.fromarray(result, 'RGBA')
            
        except Exception as e:
            logger.error(f"Error processing image with SAM: {e}")
            raise
    
    def cleanup(self):
        """Clean up model resources"""
        if self.predictor is not None:
            try:
                # Clear CUDA cache if using GPU
                if self.device == "cuda":
                    import torch
                    torch.cuda.empty_cache()
            except:
                pass
            self.predictor = None
        self._initialized = False
        logger.debug("SAM model cleaned up")