"""
import pytest
from unittest.mock import Mock, patch
import numpy as np
from PIL import Image

from bg_remover.models.factory import ModelFactory
from bg_remover.models.base import BaseModel

class TestModelFactory:
    def test_get_available_models(self):
        models = ModelFactory.get_available_models()
        assert "transparent-background" in models
        assert "rembg" in models
    
    def test_register_custom_model(self):
        class TestModel(BaseModel):
            def initialize(self):
                pass
            def process_image(self, image):
                return image
            def cleanup(self):
                pass
        
        ModelFactory.register_model("test", TestModel)
        assert "test" in ModelFactory.get_available_models()
        
        model = ModelFactory.create_model("test")
        assert isinstance(model, TestModel)
    
    def test_unknown_model_error(self):
        with pytest.raises(ValueError):
            ModelFactory.create_model("nonexistent-model")

class TestBaseModel:
    def test_device_resolution(self):
        # Mock torch availability
        with patch('torch.cuda.is_available', return_value=True):
            model = BaseModel()
            assert model._resolve_device("auto") == "cuda"
        
        with patch('torch.cuda.is_available', return_value=False):
            model = BaseModel()
            assert model._resolve_device("auto") == "cpu"
        
        model = BaseModel()
        assert model._resolve_device("cpu") == "cpu"
        assert model._resolve_device("cuda") == "cuda"
"""