from typing import Dict, Type, Any
import logging

from .base import BaseModel
from .transparent_bg import TransparentBackgroundModel
from .rembg_model import RembgModel
from .sam_model import SAMModel


logger = logging.getLogger(__name__)

class ModelFactory:
    _models: Dict[str, Type[BaseModel]] = {
        "transparent-background": TransparentBackgroundModel,
        "rembg": RembgModel,
        "sam": SAMModel,
    }
    
    @classmethod
    def register_model(cls, name: str, model_class: Type[BaseModel]):
        """Register a new model class
        
        Args:
            name: Model name
            model_class: Model class
        """
        cls._models[name] = model_class
        logger.info(f"Registered model: {name}")
    
    @classmethod
    def get_available_models(cls) -> list:
        """Get list of available model names"""
        return list(cls._models.keys())
    
    @classmethod
    def create_model(cls, name: str, **kwargs) -> BaseModel:
        """Create a model instance
        
        Args:
            name: Model name
            **kwargs: Model-specific arguments
            
        Returns:
            Model instance
        """
        if name not in cls._models:
            available = ", ".join(cls.get_available_models())
            raise ValueError(f"Unknown model: {name}. Available models: {available}")
        
        model_class = cls._models[name]
        logger.info(f"Creating model: {name}")
        
        return model_class(**kwargs)
    
    @classmethod
    def is_model_available(cls, name: str) -> bool:
        """Check if a model is available
        
        Args:
            name: Model name
            
        Returns:
            True if model is available
        """
        return name in cls._models