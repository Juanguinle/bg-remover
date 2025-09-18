"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image

from bg_remover.config.manager import ConfigManager
from bg_remover.core.processor import BackgroundProcessor

class TestBackgroundProcessor:
    def test_directory_setup(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ConfigManager()
            config.set("processing.input_folder", f"{tmp_dir}/input")
            config.set("processing.output_folder", f"{tmp_dir}/output")
            config.set("processing.processed_folder", f"{tmp_dir}/processed")
            
            processor = BackgroundProcessor(config)
            
            assert Path(f"{tmp_dir}/input").exists()
            assert Path(f"{tmp_dir}/output").exists()
            assert Path(f"{tmp_dir}/processed").exists()
    
    def test_supported_file_detection(self):
        config = ConfigManager()
        processor = BackgroundProcessor(config)
        
        assert processor._is_supported_file(Path("test.jpg"))
        assert processor._is_supported_file(Path("test.png"))
        assert not processor._is_supported_file(Path("test.txt"))
        assert not processor._is_supported_file(Path("test.pdf"))
    
    @patch('bg_remover.models.factory.ModelFactory.create_model')
    def test_model_initialization(self, mock_create_model):
        mock_model = Mock()
        mock_create_model.return_value = mock_model
        
        config = ConfigManager()
        config.set("models.transparent-background.enabled", True)
        
        processor = BackgroundProcessor(config)
        processor._initialize_model()
        
        mock_create_model.assert_called_once()
        mock_model.initialize.assert_called_once()
"""