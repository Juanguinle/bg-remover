import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from PIL import Image
import psutil

from ..models.factory import ModelFactory
from ..config.manager import ConfigManager
from .statistics import ProcessingStats

logger = logging.getLogger(__name__)

class BackgroundProcessor:
    """Main background removal processor"""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize processor
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.stats = ProcessingStats()
        self.model = None
        self.is_running = False
        self._shutdown_requested = False
        
        # Setup directories
        self._setup_directories()
        
    def _setup_directories(self):
        """Create required directories"""
        dirs = [
            self.config.get("processing.input_folder"),
            self.config.get("processing.output_folder"),
        ]
        
        if self.config.get("processing.preserve_original"):
            dirs.append(self.config.get("processing.processed_folder"))
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {dir_path}")
            
    def _generate_output_filename(self, input_path: Path, processing_time: float = None) -> Path:
        """Generate output filename with model, quality and timing information"""
        output_folder = Path(self.config.get("processing.output_folder"))
        model_name = self.config.get("processing.model")
        
        # Get model-specific settings
        model_config = self.config.get(f"models.{model_name}", {})
        quality = model_config.get("quality", "default")
        device = self.model.device if self.model else "unknown"
        
        # For rembg, include model variant
        if model_name == "rembg":
            model_variant = model_config.get("model_name", "u2net")
            model_info = f"{model_name}_{model_variant}"
        else:
            model_info = model_name
        
        # Create detailed filename with timing
        base_name = input_path.stem
        
        if processing_time is not None:
            time_str = f"{processing_time:.1f}s"
            output_name = f"{base_name}_{model_info}_{quality}_{device}_{time_str}.png"
        else:
            output_name = f"{base_name}_{model_info}_{quality}_{device}.png"
        
        return output_folder / output_name
    
    def _initialize_model(self):
        """Initialize the background removal model"""
        if self.model is not None:
            return
        
        model_name = self.config.get("processing.model")
        model_config = self.config.get(f"models.{model_name}", {})
        
        if not model_config.get("enabled", False):
            raise ValueError(f"Model '{model_name}' is not enabled in configuration")
        
        try:
            # Create model with configuration
            device = model_config.get("device", self.config.get("processing.device", "auto"))
            options = model_config.get("options", {})
            
            # Add quality setting if available
            if "quality" in model_config:
                options["quality"] = model_config["quality"]
            
            # Add mode setting for transparent-background
            if model_name == "transparent-background" and "mode" in model_config:
                options["mode"] = model_config["mode"]
            
            self.model = ModelFactory.create_model(model_name, device=device, **options)
            self.model.initialize()
            
            logger.info(f"Model initialized: {model_name} on {self.model.device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize model '{model_name}': {e}")
            raise
    
    def _cleanup_model(self):
        """Clean up model resources"""
        if self.model is not None:
            try:
                self.model.cleanup()
                self.model = None
                logger.debug("Model cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up model: {e}")
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported for processing
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is supported
        """
        extensions = self.config.get("processing.file_extensions", [])
        return file_path.suffix.lower() in [ext.lower() for ext in extensions]
    
    def _is_file_stable(self, file_path: Path) -> bool:
        """Check if file is stable (not being written to)
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is stable
        """
        try:
            timeout = self.config.get("processing.file_stability_timeout", 2.0)
            initial_size = file_path.stat().st_size
            time.sleep(timeout)
            
            if not file_path.exists():
                return False
            
            current_size = file_path.stat().st_size
            return initial_size == current_size
            
        except Exception as e:
            logger.warning(f"Error checking file stability for {file_path}: {e}")
            return False
    
    def _should_process_file(self, input_path: Path) -> bool:
        """Check if file should be processed with enhanced output checking
        
        Args:
            input_path: Input file path
            
        Returns:
            True if file should be processed
        """
        if not self._is_supported_file(input_path):
            return False
        
        if not input_path.exists():
            return False
        
        # Check if output already exists with current model/quality settings (without timing)
        output_path = self._generate_output_filename(input_path)
        
        if output_path.exists() and not self.config.get("processing.overwrite_existing", False):
            logger.debug(f"Output already exists, skipping: {output_path}")
            return False
        
        return True
    
    def _process_single_file(self, input_path: Path, progress_callback: Optional[Callable] = None) -> bool:
        """Process a single file with enhanced naming
        
        Args:
            input_path: Input file path
            progress_callback: Optional progress callback function
            
        Returns:
            True if processing was successful
        """
        try:
            if not self._should_process_file(input_path):
                return False
            
            # Check if file still exists before processing (important for monitoring)
            if not input_path.exists():
                logger.warning(f"File no longer exists, skipping: {input_path}")
                return False
            
            logger.info(f"Processing: {input_path}")
            start_time = time.time()
            
            # Store original file size for stats
            original_file_size = input_path.stat().st_size
            
            # Wait for file to be stable
            if not self._is_file_stable(input_path):
                logger.warning(f"File not stable, skipping: {input_path}")
                return False
            
            # Load image
            with Image.open(input_path) as image:
                # Process image
                result = self.model.process_image(image)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Generate output path with detailed naming including timing
                output_path = self._generate_output_filename(input_path, processing_time)
                
                # Save result
                result.save(output_path, "PNG")
                
                # Handle original file ONLY if it still exists
                if self.config.get("processing.preserve_original") and input_path.exists():
                    processed_folder = Path(self.config.get("processing.processed_folder"))
                    processed_path = processed_folder / input_path.name
                    shutil.move(str(input_path), str(processed_path))
                    logger.debug(f"Moved original to: {processed_path}")
                
                # Update statistics
                self.stats.add_success(processing_time, original_file_size)
                
                logger.info(f"Completed: {input_path} -> {output_path} ({processing_time:.2f}s)")
                
                if progress_callback:
                    progress_callback(input_path, output_path, True, processing_time)
                
                return True
                
        except Exception as e:
            # Use stored file size if available
            file_size = 0
            try:
                if input_path.exists():
                    file_size = input_path.stat().st_size
                else:
                    # Try to get size from locals if we stored it earlier
                    file_size = locals().get('original_file_size', 0)
            except:
                pass
                
            logger.error(f"Error processing {input_path}: {e}")
            self.stats.add_failure(file_size)
            
            if progress_callback:
                progress_callback(input_path, None, False, 0)
            
            return False
    
    def process_batch(self, input_paths: List[Path], progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Process multiple files
        
        Args:
            input_paths: List of input file paths
            progress_callback: Optional progress callback function
            
        Returns:
            Processing results summary
        """
        if not input_paths:
            return {"processed": 0, "failed": 0, "skipped": 0}
        
        # Initialize model
        self._initialize_model()
        
        try:
            self.is_running = True
            batch_size = self.config.get("processing.batch_size", 1)
            
            processed = 0
            failed = 0
            skipped = 0
            
            if batch_size == 1:
                # Sequential processing
                for input_path in input_paths:
                    if self._shutdown_requested:
                        break
                    
                    if self._should_process_file(input_path):
                        success = self._process_single_file(input_path, progress_callback)
                        if success:
                            processed += 1
                        else:
                            failed += 1
                    else:
                        skipped += 1
            else:
                # Parallel processing
                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    future_to_path = {
                        executor.submit(self._process_single_file, path, progress_callback): path
                        for path in input_paths if self._should_process_file(path)
                    }
                    
                    skipped = len(input_paths) - len(future_to_path)
                    
                    for future in as_completed(future_to_path):
                        if self._shutdown_requested:
                            # Cancel remaining futures
                            for f in future_to_path:
                                f.cancel()
                            break
                        
                        try:
                            success = future.result()
                            if success:
                                processed += 1
                            else:
                                failed += 1
                        except Exception as e:
                            logger.error(f"Batch processing error: {e}")
                            failed += 1
            
            return {
                "processed": processed,
                "failed": failed, 
                "skipped": skipped,
                "total_time": self.stats.total_processing_time,
                "avg_time": self.stats.average_processing_time
            }
            
        finally:
            self.is_running = False
            self._cleanup_model()
    
    def process_folder(self, input_folder: Optional[str] = None, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Process all supported files in a folder
        
        Args:
            input_folder: Input folder path (uses config default if None)
            progress_callback: Optional progress callback function
            
        Returns:
            Processing results summary
        """
        folder_path = Path(input_folder or self.config.get("processing.input_folder"))
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Input folder not found: {folder_path}")
        
        # Find all supported files
        extensions = self.config.get("processing.file_extensions", [])
        files = []
        
        for ext in extensions:
            files.extend(folder_path.glob(f"*{ext}"))
            files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        logger.info(f"Found {len(files)} files to process in {folder_path}")
        
        return self.process_batch(files, progress_callback)
    
    def shutdown(self):
        """Request graceful shutdown"""
        self._shutdown_requested = True
        logger.info("Shutdown requested")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics
        
        Returns:
            Statistics dictionary
        """
        return self.stats.get_summary()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage
        
        Returns:
            Memory usage information
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }