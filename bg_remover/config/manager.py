import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration with YAML/JSON support"""
    
    DEFAULT_CONFIG = {
        "processing": {
            "input_folder": "./input",
            "output_folder": "./output",
            "processed_folder": "./processed",
            "model": "transparent-background",
            "device": "auto",  # auto, cpu, cuda
            "batch_size": 1,
            "quality": "high",
            "file_extensions": [".jpg", ".jpeg", ".png", ".bmp", ".tiff"],
            "file_stability_timeout": 2.0,
            "preserve_original": True,
            "overwrite_existing": False
        },
        "models": {
            "transparent-background": {
                "enabled": True,
                "device": "auto",
                "quality": "high",
                "options": {}
            },
            "rembg": {
                "enabled": True,
                "model_name": "u2net",
                "device": "auto",
                "options": {}
            }
        },
        "monitoring": {
            "enabled": True,
            "recursive": False,
            "debounce_seconds": 1.0
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "bg_remover.log",
            "max_size": "10MB",
            "backup_count": 5
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _get_default_config_path(self) -> Path:
        """Get default configuration file path"""
        # Check for config in current directory first
        local_config = Path("config.yaml")
        if local_config.exists():
            return local_config
        
        # Check user's home directory
        home_config = Path.home() / ".bg_remover" / "config.yaml"
        if home_config.exists():
            return home_config
        
        # Use package default
        package_dir = Path(__file__).parent
        return package_dir / "default.yaml"
    
    def _load_config(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, using defaults")
            self._save_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.suffix.lower() == '.json':
                    user_config = json.load(f)
                else:
                    user_config = yaml.safe_load(f)
            
            # Deep merge with defaults
            self._config = self._deep_merge(self.DEFAULT_CONFIG, user_config)
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            logger.info("Using default configuration")
    
    def _save_default_config(self):
        """Save default configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False, indent=2)
            logger.info(f"Default configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving default config: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key
        
        Args:
            key: Configuration key (e.g., 'processing.model')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot notation key
        
        Args:
            key: Configuration key (e.g., 'processing.model')
            value: Value to set
        """
        keys = key.split('.')
        target = self._config
        
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    def save(self):
        """Save current configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.suffix.lower() == '.json':
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                else:
                    yaml.dump(self._config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration dictionary"""
        return self._config.copy()