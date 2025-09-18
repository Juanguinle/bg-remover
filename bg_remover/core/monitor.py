import time
from pathlib import Path
from typing import Callable, Optional, Set
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """Handle file system events for folder monitoring"""
    
    def __init__(self, processor_callback: Callable, config: ConfigManager):
        """Initialize event handler
        
        Args:
            processor_callback: Callback function for processing files
            config: Configuration manager
        """
        super().__init__()
        self.processor_callback = processor_callback
        self.config = config
        self.debounce_seconds = config.get("monitoring.debounce_seconds", 1.0)
        self.pending_files: Set[Path] = set()
        self.last_event_time = {}
        
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported"""
        extensions = self.config.get("processing.file_extensions", [])
        return file_path.suffix.lower() in [ext.lower() for ext in extensions]
    
    def _should_process_event(self, file_path: Path) -> bool:
        """Check if event should trigger processing"""
        current_time = time.time()
        
        # Check debounce
        if file_path in self.last_event_time:
            if current_time - self.last_event_time[file_path] < self.debounce_seconds:
                return False
        
        self.last_event_time[file_path] = current_time
        return True
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if not self._is_supported_file(file_path):
            return
        
        if not self._should_process_event(file_path):
            return
        
        logger.debug(f"File created: {file_path}")
        self.processor_callback(file_path)
    
    def on_moved(self, event):
        """Handle file move events (e.g., from temp to final location)"""
        if event.is_directory:
            return
        
        dest_path = Path(event.dest_path)
        
        if not self._is_supported_file(dest_path):
            return
        
        if not self._should_process_event(dest_path):
            return
        
        logger.debug(f"File moved: {dest_path}")
        self.processor_callback(dest_path)

class FolderMonitor:
    """Monitor folder for new files and trigger processing"""
    
    def __init__(self, config_manager: ConfigManager, processor_callback: Callable):
        """Initialize folder monitor
        
        Args:
            config_manager: Configuration manager
            processor_callback: Callback function for processing files
        """
        self.config = config_manager
        self.processor_callback = processor_callback
        self.observer = None
        self.is_monitoring = False
        
    def start_monitoring(self, folder_path: Optional[str] = None):
        """Start monitoring folder
        
        Args:
            folder_path: Folder to monitor (uses config default if None)
        """
        if self.is_monitoring:
            logger.warning("Monitoring is already active")
            return
        
        if not self.config.get("monitoring.enabled", True):
            logger.info("Folder monitoring is disabled in configuration")
            return
        
        watch_path = Path(folder_path or self.config.get("processing.input_folder"))
        
        if not watch_path.exists():
            raise FileNotFoundError(f"Monitor folder not found: {watch_path}")
        
        # Create event handler
        event_handler = FileEventHandler(self.processor_callback, self.config)
        
        # Setup observer
        self.observer = Observer()
        recursive = self.config.get("monitoring.recursive", False)
        self.observer.schedule(event_handler, str(watch_path), recursive=recursive)
        
        # Start monitoring
        self.observer.start()
        self.is_monitoring = True
        
        logger.info(f"Started monitoring folder: {watch_path} (recursive: {recursive})")
    
    def stop_monitoring(self):
        """Stop monitoring folder"""
        if not self.is_monitoring or self.observer is None:
            return
        
        self.observer.stop()
        self.observer.join()
        self.observer = None
        self.is_monitoring = False
        
        logger.info("Stopped folder monitoring")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()