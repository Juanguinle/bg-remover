"""
import pytest
import tempfile
import yaml
from pathlib import Path

from bg_remover.config.manager import ConfigManager

class TestConfigManager:
    def test_default_config_creation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test_config.yaml"
            config = ConfigManager(str(config_path))
            
            assert config.get("processing.model") == "transparent-background"
            assert config.get("processing.device") == "auto"
            assert config_path.exists()
    
    def test_config_loading(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test_config.yaml"
            
            # Create test config
            test_config = {
                "processing": {
                    "model": "rembg",
                    "device": "cpu"
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(test_config, f)
            
            config = ConfigManager(str(config_path))
            assert config.get("processing.model") == "rembg"
            assert config.get("processing.device") == "cpu"
    
    def test_config_get_set(self):
        config = ConfigManager()
        
        # Test getting nested values
        assert config.get("processing.model") is not None
        assert config.get("nonexistent.key", "default") == "default"
        
        # Test setting values
        config.set("processing.model", "test-model")
        assert config.get("processing.model") == "test-model"
        
        config.set("new.nested.key", "value")
        assert config.get("new.nested.key") == "value"
"""