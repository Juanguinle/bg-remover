import sys
import signal
import time
from pathlib import Path
from typing import Optional
import click
import logging
from tqdm import tqdm

from ..config.manager import ConfigManager
from ..core.processor import BackgroundProcessor
from ..core.monitor import FolderMonitor
from ..models.factory import ModelFactory
from ..utils.logging_setup import setup_logging
from ..utils.device_utils import get_system_info, detect_device

logger = logging.getLogger(__name__)

# Global variables for graceful shutdown
processor = None
monitor = None
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_requested, processor, monitor
    
    shutdown_requested = True
    click.echo("\nShutdown requested...")
    
    if processor:
        processor.shutdown()
    
    if monitor:
        monitor.stop_monitoring()
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']))
@click.option('--log-file', help='Log file path')
@click.pass_context
def cli(ctx, config, log_level, log_file):
    """Professional background removal application with automatic folder monitoring"""
    
    # Initialize configuration
    config_manager = ConfigManager(config)
    
    # Setup logging
    log_config = config_manager.get('logging', {})
    setup_logging(
        level=log_level or log_config.get('level', 'INFO'),
        log_file=log_file or log_config.get('file'),
        format_string=log_config.get('format'),
        max_size=log_config.get('max_size', '10MB'),
        backup_count=log_config.get('backup_count', 5)
    )
    
    # Store in context
    ctx.ensure_object(dict)
    ctx.obj['config'] = config_manager

@cli.command()
@click.option('--input', '-i', help='Input folder path')
@click.option('--output', '-o', help='Output folder path')
@click.option('--model', '-m', help='Model to use', type=click.Choice(ModelFactory.get_available_models()))
@click.option('--device', type=click.Choice(['auto', 'cpu', 'cuda']), help='Device to use')
@click.option('--batch-size', type=int, help='Batch size for parallel processing')
@click.option('--quality', type=click.Choice(['low', 'medium', 'high']), help='Processing quality')
@click.option('--overwrite', is_flag=True, help='Overwrite existing output files')
@click.pass_context
def process(ctx, input, output, model, device, batch_size, quality, overwrite):
    """Process all images in a folder"""
    
    config = ctx.obj['config']
    
    # Update config with CLI arguments
    if input:
        config.set('processing.input_folder', input)
    if output:
        config.set('processing.output_folder', output)
    if model:
        config.set('processing.model', model)
    if device:
        config.set('processing.device', device)
    if batch_size:
        config.set('processing.batch_size', batch_size)
    if quality:
        config.set(f'models.{config.get("processing.model")}.quality', quality)
    if overwrite:
        config.set('processing.overwrite_existing', True)
    
    # Initialize processor
    global processor
    processor = BackgroundProcessor(config)
    
    # Progress tracking
    progress_bar = None
    processed_files = []
    
    def progress_callback(input_path, output_path, success, processing_time):
        nonlocal progress_bar, processed_files
        
        processed_files.append({
            'input': input_path,
            'output': output_path,
            'success': success,
            'time': processing_time
        })
        
        if progress_bar:
            progress_bar.update(1)
            if success:
                progress_bar.set_postfix({
                    'current': input_path.name,
                    'time': f'{processing_time:.2f}s'
                })
    
    try:
        # Get input folder
        input_folder = config.get('processing.input_folder')
        click.echo(f"Processing folder: {input_folder}")
        click.echo(f"Model: {config.get('processing.model')}")
        click.echo(f"Device: {detect_device()}")
        
        # Count files first
        folder_path = Path(input_folder)
        extensions = config.get('processing.file_extensions', [])
        total_files = 0
        for ext in extensions:
            total_files += len(list(folder_path.glob(f"*{ext}")))
            total_files += len(list(folder_path.glob(f"*{ext.upper()}")))
        
        if total_files == 0:
            click.echo("No supported image files found.")
            return
        
        # Setup progress bar
        progress_bar = tqdm(total=total_files, desc="Processing", unit="files")
        
        # Process folder
        start_time = time.time()
        results = processor.process_folder(input_folder, progress_callback)
        end_time = time.time()
        
        # Close progress bar
        progress_bar.close()
        
        # Show results
        click.echo(f"\nProcessing completed in {end_time - start_time:.2f} seconds")
        click.echo(f"Processed: {results['processed']}")
        click.echo(f"Failed: {results['failed']}")
        click.echo(f"Skipped: {results['skipped']}")
        
        if results['processed'] > 0:
            click.echo(f"Average time per file: {results['avg_time']:.2f}s")
        
        # Show statistics
        stats = processor.get_statistics()
        click.echo(f"Success rate: {stats['success_rate']:.1f}%")
        
    except KeyboardInterrupt:
        click.echo("\nProcessing interrupted by user")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error(f"Processing error: {e}", exc_info=True)
        sys.exit(1)

@cli.command()
@click.option('--input', '-i', help='Input folder to monitor')
@click.option('--model', '-m', help='Model to use', type=click.Choice(ModelFactory.get_available_models()))
@click.option('--device', type=click.Choice(['auto', 'cpu', 'cuda']), help='Device to use')
@click.option('--recursive', is_flag=True, help='Monitor subdirectories recursively')
@click.option('--process-existing', is_flag=True, help='Process existing files before monitoring')
@click.option('--new-only', is_flag=True, help='Only monitor for new files, skip existing')
@click.pass_context
def monitor(ctx, input, model, device, recursive, process_existing, new_only):
    """Monitor folder for new images and process them automatically"""
    
    config = ctx.obj['config']
    
    # Update config with CLI arguments
    if input:
        config.set('processing.input_folder', input)
    if model:
        config.set('processing.model', model)
    if device:
        config.set('processing.device', device)
    if recursive:
        config.set('monitoring.recursive', True)
    
    # Initialize components
    global processor, monitor
    processor = BackgroundProcessor(config)
    
    input_folder = config.get('processing.input_folder')
    
    # Process existing files first if requested (default behavior)
    if not new_only:
        if process_existing or not new_only:
            click.echo(f"Processing existing files in: {input_folder}")
            
            def progress_callback(input_path, output_path, success, processing_time):
                if success:
                    click.echo(f"  ✓ {input_path.name} -> {output_path.name} ({processing_time:.2f}s)")
                else:
                    click.echo(f"  ✗ Failed: {input_path.name}")
            
            results = processor.process_folder(input_folder, progress_callback)
            click.echo(f"Initial processing: {results['processed']} processed, {results['failed']} failed\n")
    
    def process_file_callback(file_path):
        """Callback for processing new files"""
        try:
            if not file_path.exists():
                return
                
            click.echo(f"New file detected: {file_path}")
            results = processor.process_batch([file_path])
            
            if results['processed'] > 0:
                click.echo(f"Successfully processed: {file_path}")
            else:
                click.echo(f"Failed to process: {file_path}")
                
        except Exception as e:
            click.echo(f"Error processing {file_path}: {e}")
            logger.error(f"Monitor processing error: {e}", exc_info=True)

    monitor = FolderMonitor(config, process_file_callback)
    
    try:
        click.echo(f"Starting folder monitoring: {input_folder}")
        click.echo(f"Model: {config.get('processing.model')}")
        click.echo(f"Device: {detect_device()}")
        click.echo(f"Recursive: {config.get('monitoring.recursive', False)}")
        click.echo("Press Ctrl+C to stop monitoring\n")
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Keep running until interrupted
        while not shutdown_requested:
            time.sleep(1)
            
            # Show periodic statistics
            if processor.stats.total_files > 0:
                stats = processor.get_statistics()
                click.echo(f"\rProcessed: {stats['total_processed']}, "
                          f"Failed: {stats['total_failed']}, "
                          f"Success Rate: {stats['success_rate']:.1f}%", nl=False)
    
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error(f"Monitoring error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if monitor:
            monitor.stop_monitoring()

@cli.command()
@click.pass_context
def info(ctx):
    """Show system and configuration information"""
    
    config = ctx.obj['config']
    
    click.echo("=== BG Remover System Information ===")
    
    # System info
    sys_info = get_system_info()
    click.echo(f"\nSystem:")
    click.echo(f"  Platform: {sys_info.get('platform', 'Unknown')}")
    click.echo(f"  Python: {sys_info.get('python_version', 'Unknown')}")
    click.echo(f"  CPU Count: {sys_info.get('cpu_count', 'Unknown')}")
    click.echo(f"  Total Memory: {sys_info.get('total_memory_gb', 'Unknown')} GB")
    click.echo(f"  Available Memory: {sys_info.get('available_memory_gb', 'Unknown')} GB")
    
    # PyTorch info
    if 'torch_version' in sys_info:
        click.echo(f"\nPyTorch:")
        click.echo(f"  Version: {sys_info['torch_version']}")
        click.echo(f"  CUDA Available: {sys_info['torch_cuda_available']}")
        if sys_info['torch_cuda_available']:
            click.echo(f"  CUDA Version: {sys_info.get('torch_cuda_version', 'Unknown')}")
            click.echo(f"  CUDA Devices: {sys_info.get('torch_cuda_device_count', 0)}")
    
    # Available models
    click.echo(f"\nAvailable Models:")
    for model_name in ModelFactory.get_available_models():
        enabled = config.get(f'models.{model_name}.enabled', False)
        status = "✓" if enabled else "✗"
        click.echo(f"  {status} {model_name}")
    
    # Configuration
    click.echo(f"\nConfiguration:")
    click.echo(f"  Config File: {config.config_path}")
    click.echo(f"  Input Folder: {config.get('processing.input_folder')}")
    click.echo(f"  Output Folder: {config.get('processing.output_folder')}")
    click.echo(f"  Current Model: {config.get('processing.model')}")
    click.echo(f"  Device: {config.get('processing.device')}")
    click.echo(f"  Monitoring Enabled: {config.get('monitoring.enabled')}")

@cli.command()
@click.option('--model', '-m', help='Model to test', type=click.Choice(ModelFactory.get_available_models()))
@click.option('--device', type=click.Choice(['auto', 'cpu', 'cuda']), help='Device to use')
@click.pass_context
def test(ctx, model, device):
    """Test model functionality"""
    
    config = ctx.obj['config']
    
    # Update config with CLI arguments
    if model:
        config.set('processing.model', model)
    if device:
        config.set('processing.device', device)
    
    model_name = config.get('processing.model')
    click.echo(f"Testing model: {model_name}")
    
    try:
        # Create a test processor
        processor = BackgroundProcessor(config)
        
        # Try to initialize the model
        click.echo("Initializing model...")
        processor._initialize_model()
        
        click.echo(f"✓ Model '{model_name}' initialized successfully on {processor.model.device}")
        
        # Get memory usage
        memory = processor.get_memory_usage()
        click.echo(f"Memory usage: {memory['rss_mb']:.1f} MB ({memory['percent']:.1f}%)")
        
        # Clean up
        processor._cleanup_model()
        click.echo("✓ Model cleaned up successfully")
        
    except Exception as e:
        click.echo(f"✗ Error testing model '{model_name}': {e}", err=True)
        logger.error(f"Model test error: {e}", exc_info=True)
        sys.exit(1)

@cli.command()
@click.option('--input', '-i', help='Input folder path')
@click.option('--output', '-o', help='Output folder path')
@click.option('--models', help='Comma-separated list of models to compare', default='rembg,transparent-background')
@click.option('--qualities', help='Comma-separated list of qualities to test', default='low,medium,high')
@click.pass_context
def compare(ctx, input, output, models, qualities):
    """Compare different models and quality settings on the same images"""
    
    config = ctx.obj['config']
    
    # Update config with CLI arguments
    if input:
        config.set('processing.input_folder', input)
    if output:
        config.set('processing.output_folder', output)
    
    # Parse models and qualities
    model_list = [m.strip() for m in models.split(',')]
    quality_list = [q.strip() for q in qualities.split(',')]
    
    # Get input folder
    input_folder = config.get('processing.input_folder')
    click.echo(f"Comparing models on images in: {input_folder}")
    click.echo(f"Models: {', '.join(model_list)}")
    click.echo(f"Qualities: {', '.join(quality_list)}")
    
    # Store original settings
    original_model = config.get('processing.model')
    original_quality = config.get(f'models.{original_model}.quality', 'high')
    
    try:
        total_combinations = len(model_list) * len(quality_list)
        current_combo = 0
        
        for model in model_list:
            if model not in ModelFactory.get_available_models():
                click.echo(f"Warning: Model '{model}' not available, skipping")
                continue
                
            for quality in quality_list:
                current_combo += 1
                click.echo(f"\n[{current_combo}/{total_combinations}] Testing {model} with {quality} quality...")
                
                # Update configuration
                config.set('processing.model', model)
                config.set(f'models.{model}.quality', quality)
                
                # Initialize processor
                processor = BackgroundProcessor(config)
                
                # Progress tracking
                def progress_callback(input_path, output_path, success, processing_time):
                    if success:
                        click.echo(f"  ✓ {input_path.name} -> {output_path.name} ({processing_time:.2f}s)")
                    else:
                        click.echo(f"  ✗ Failed: {input_path.name}")
                
                # Process folder
                results = processor.process_folder(input_folder, progress_callback)
                
                click.echo(f"  Results: {results['processed']} processed, {results['failed']} failed, {results['skipped']} skipped")
                
    except KeyboardInterrupt:
        click.echo("\nComparison interrupted by user")
    except Exception as e:
        click.echo(f"Error during comparison: {e}", err=True)
    finally:
        # Restore original settings
        config.set('processing.model', original_model)
        config.set(f'models.{original_model}.quality', original_quality)

@cli.command()
@click.option('--output', '-o', help='Output folder to analyze')
@click.pass_context
def analyze_results(ctx, output):
    """Analyze and report on processed images with different models/qualities"""
    
    config = ctx.obj['config']
    output_folder = Path(output or config.get('processing.output_folder'))
    
    if not output_folder.exists():
        click.echo(f"Output folder not found: {output_folder}")
        return
    
    # Group files by original image
    results = {}
    
    for file_path in output_folder.glob("*.png"):
        # Parse filename: originalname_model_quality_device_time.png
        parts = file_path.stem.split('_')
        if len(parts) >= 4:
            original_name = '_'.join(parts[:-3])  # Handle original names with underscores
            model = parts[-3]
            quality = parts[-2]
            device = parts[-1]
            
            if original_name not in results:
                results[original_name] = []
            
            file_size = file_path.stat().st_size / 1024 / 1024  # MB
            results[original_name].append({
                'model': model,
                'quality': quality,
                'device': device,
                'file_size_mb': file_size,
                'file_path': file_path
            })
    
    # Display results
    click.echo("=== Processing Results Analysis ===\n")
    
    for original_name, variants in results.items():
        click.echo(f"Original: {original_name}")
        
        # Sort by model and quality
        variants.sort(key=lambda x: (x['model'], x['quality']))
        
        for variant in variants:
            click.echo(f"  {variant['model']:20} {variant['quality']:8} {variant['device']:8} {variant['file_size_mb']:6.2f}MB")
        
        click.echo()
    
    # Summary statistics
    click.echo("=== Summary ===")
    models = set()
    qualities = set()
    total_files = 0
    
    for variants in results.values():
        for variant in variants:
            models.add(variant['model'])
            qualities.add(variant['quality'])
            total_files += 1
    
    click.echo(f"Total processed files: {total_files}")
    click.echo(f"Models tested: {', '.join(sorted(models))}")
    click.echo(f"Qualities tested: {', '.join(sorted(qualities))}")

@cli.command()
@click.pass_context
def config_show(ctx):
    """Show current configuration"""
    
    config = ctx.obj['config']
    
    click.echo("=== Current Configuration ===")
    click.echo(f"Config file: {config.config_path}")
    click.echo()
    
    import yaml
    click.echo(yaml.dump(config.config, default_flow_style=False, indent=2))

@cli.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key, value):
    """Set configuration value"""
    
    config = ctx.obj['config']
    
    # Try to parse value as appropriate type
    try:
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        elif '.' in value and value.replace('.', '').isdigit():
            value = float(value)
    except:
        pass
    
    config.set(key, value)
    config.save()
    
    click.echo(f"Set {key} = {value}")

@cli.command()
@click.option('--folders', help='Folders to clean (input,output,processed)', default='output,processed')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def clean(ctx, folders, confirm):
    """Clean output and processed folders"""
    
    config = ctx.obj['config']
    
    folder_map = {
        'input': config.get('processing.input_folder'),
        'output': config.get('processing.output_folder'), 
        'processed': config.get('processing.processed_folder')
    }
    
    folders_to_clean = [f.strip() for f in folders.split(',')]
    
    click.echo("Folders to clean:")
    total_files = 0
    for folder_name in folders_to_clean:
        if folder_name not in folder_map:
            click.echo(f"Unknown folder: {folder_name}")
            continue
            
        folder_path = Path(folder_map[folder_name])
        if folder_path.exists():
            files = list(folder_path.glob('*'))
            total_files += len(files)
            click.echo(f"  {folder_name}: {len(files)} files in {folder_path}")
        else:
            click.echo(f"  {folder_name}: folder doesn't exist")
    
    if total_files == 0:
        click.echo("No files to clean")
        return
    
    if not confirm:
        if not click.confirm(f"Delete {total_files} files?"):
            click.echo("Cancelled")
            return
    
    deleted = 0
    for folder_name in folders_to_clean:
        if folder_name not in folder_map:
            continue
            
        folder_path = Path(folder_map[folder_name])
        if folder_path.exists():
            for file_path in folder_path.glob('*'):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        deleted += 1
                except Exception as e:
                    click.echo(f"Error deleting {file_path}: {e}")
    
    click.echo(f"Deleted {deleted} files")

@cli.command()
@click.pass_context
def configure(ctx):
    """Interactive configuration menu"""
    
    config = ctx.obj['config']
    
    def show_menu():
        click.clear()
        click.echo("=== BG Remover Configuration ===")
        click.echo()
        click.echo(f"Current Settings:")
        current_model = config.get('processing.model')
        click.echo(f"  1. Model: {current_model}")
        click.echo(f"  2. Device: {config.get('processing.device')}")
        click.echo(f"  3. Quality: {config.get(f'models.{current_model}.quality', 'default')}")
        click.echo(f"  4. Batch Size: {config.get('processing.batch_size')}")
        click.echo(f"  5. Input Folder: {config.get('processing.input_folder')}")
        click.echo(f"  6. Output Folder: {config.get('processing.output_folder')}")
        click.echo(f"  7. Preserve Original: {config.get('processing.preserve_original')}")
        click.echo(f"  8. Overwrite Existing: {config.get('processing.overwrite_existing')}")
        
        if current_model == 'transparent-background':
            click.echo(f"  9. TB Mode: {config.get('models.transparent-background.mode', 'base')}")
        elif current_model == 'rembg':
            click.echo(f"  9. Rembg Model: {config.get('models.rembg.model_name', 'u2net')}")
        elif current_model == 'sam':
            click.echo(f"  9. SAM Model Type: {config.get('models.sam.model_type', 'vit_b')}")
        
        click.echo()
        click.echo("  s. Save configuration")
        click.echo("  t. Test current model")
        click.echo("  q. Quit")
        click.echo()
    
    def select_model():
        click.echo("\nAvailable models:")
        available_models = ModelFactory.get_available_models()
        for i, model in enumerate(available_models, 1):
            enabled = config.get(f'models.{model}.enabled', False)
            status = "✓" if enabled else "✗"
            click.echo(f"  {i}. {status} {model}")
        
        choice = click.prompt("\nSelect model (number)", type=int)
        if 1 <= choice <= len(available_models):
            selected_model = available_models[choice - 1]
            config.set('processing.model', selected_model)
            click.echo(f"Model set to: {selected_model}")
        else:
            click.echo("Invalid selection")
        click.pause()
    
    def select_quality():
        click.echo("\nQuality settings:")
        qualities = ['low', 'medium', 'high']
        for i, quality in enumerate(qualities, 1):
            click.echo(f"  {i}. {quality}")
        
        choice = click.prompt("\nSelect quality (number)", type=int)
        if 1 <= choice <= len(qualities):
            selected_quality = qualities[choice - 1]
            current_model = config.get('processing.model')
            config.set(f'models.{current_model}.quality', selected_quality)
            click.echo(f"Quality set to: {selected_quality}")
        else:
            click.echo("Invalid selection")
        click.pause()
    
    def select_device():
        click.echo("\nDevice options:")
        devices = ['auto', 'cpu', 'cuda']
        for i, device in enumerate(devices, 1):
            click.echo(f"  {i}. {device}")
        
        choice = click.prompt("\nSelect device (number)", type=int)
        if 1 <= choice <= len(devices):
            selected_device = devices[choice - 1]
            config.set('processing.device', selected_device)
            click.echo(f"Device set to: {selected_device}")
        else:
            click.echo("Invalid selection")
        click.pause()
    
    def set_batch_size():
        current = config.get('processing.batch_size', 1)
        click.echo(f"\nCurrent batch size: {current}")
        click.echo("Recommended values:")
        click.echo("  1 - Sequential (lowest memory)")
        click.echo("  2-4 - Moderate parallel processing")
        click.echo("  8+ - High CPU usage (requires more memory)")
        
        new_size = click.prompt("Enter batch size", type=int, default=current)
        if new_size > 0:
            config.set('processing.batch_size', new_size)
            click.echo(f"Batch size set to: {new_size}")
        else:
            click.echo("Invalid batch size")
        click.pause()
    
    def set_folder(folder_type):
        current = config.get(f'processing.{folder_type}_folder')
        click.echo(f"\nCurrent {folder_type} folder: {current}")
        new_path = click.prompt(f"Enter new {folder_type} folder path", default=current)
        config.set(f'processing.{folder_type}_folder', new_path)
        click.echo(f"{folder_type.title()} folder set to: {new_path}")
        click.pause()
    
    def toggle_boolean(setting_key, setting_name):
        current = config.get(setting_key, False)
        new_value = not current
        config.set(setting_key, new_value)
        click.echo(f"{setting_name} set to: {new_value}")
        click.pause()
    
    def select_transparent_bg_mode():
        click.echo("\nTransparent Background modes:")
        modes = ['base', 'base-nightly']
        descriptions = ['Stable mode', 'Experimental mode (higher quality)']
        for i, (mode, desc) in enumerate(zip(modes, descriptions), 1):
            click.echo(f"  {i}. {mode} - {desc}")
        
        choice = click.prompt("\nSelect mode (number)", type=int)
        if 1 <= choice <= len(modes):
            selected_mode = modes[choice - 1]
            config.set('models.transparent-background.mode', selected_mode)
            click.echo(f"Mode set to: {selected_mode}")
        else:
            click.echo("Invalid selection")
        click.pause()
    
    def select_rembg_model():
        if config.get('processing.model') != 'rembg':
            click.echo("This setting only applies to rembg model")
            click.pause()
            return
        
        click.echo("\nRembg model variants:")
        models = ['u2net', 'u2net_human_seg', 'u2net_cloth_seg', 'silueta', 'isnet-general-use']
        for i, model in enumerate(models, 1):
            click.echo(f"  {i}. {model}")
        
        choice = click.prompt("\nSelect rembg model (number)", type=int)
        if 1 <= choice <= len(models):
            selected_model = models[choice - 1]
            config.set('models.rembg.model_name', selected_model)
            click.echo(f"Rembg model set to: {selected_model}")
        else:
            click.echo("Invalid selection")
        click.pause()
    
    def select_sam_model():
        if config.get('processing.model') != 'sam':
            click.echo("This setting only applies to SAM model")
            click.pause()
            return
        
        click.echo("\nSAM model types:")
        models = ['vit_b', 'vit_l', 'vit_h']
        sizes = ['~350MB', '~1.2GB', '~2.4GB']
        for i, (model, size) in enumerate(zip(models, sizes), 1):
            click.echo(f"  {i}. {model} ({size})")
        
        choice = click.prompt("\nSelect SAM model (number)", type=int)
        if 1 <= choice <= len(models):
            selected_model = models[choice - 1]
            config.set('models.sam.model_type', selected_model)
            click.echo(f"SAM model type set to: {selected_model}")
        else:
            click.echo("Invalid selection")
        click.pause()
    
    def test_model():
        click.echo("\nTesting current model configuration...")
        current_model = config.get('processing.model')
        try:
            processor = BackgroundProcessor(config)
            processor._initialize_model()
            memory = processor.get_memory_usage()
            click.echo(f"✓ Model '{current_model}' initialized successfully")
            click.echo(f"Memory usage: {memory['rss_mb']:.1f} MB ({memory['percent']:.1f}%)")
            processor._cleanup_model()
            click.echo("✓ Model cleaned up successfully")
        except Exception as e:
            click.echo(f"✗ Error testing model '{current_model}': {e}")
        click.pause()
    
    # Main menu loop
    while True:
        show_menu()
        choice = click.prompt("Select option", type=str).lower()
        
        if choice == '1':
            select_model()
        elif choice == '2':
            select_device()
        elif choice == '3':
            select_quality()
        elif choice == '4':
            set_batch_size()
        elif choice == '5':
            set_folder('input')
        elif choice == '6':
            set_folder('output')
        elif choice == '7':
            toggle_boolean('processing.preserve_original', 'Preserve original')
        elif choice == '8':
            toggle_boolean('processing.overwrite_existing', 'Overwrite existing')
        elif choice == '9':
            if config.get('processing.model') == 'transparent-background':
                select_transparent_bg_mode()
            elif config.get('processing.model') == 'rembg':
                select_rembg_model()
            elif config.get('processing.model') == 'sam':
                select_sam_model()
            else:
                click.echo("No additional settings for this model")
                click.pause()
        elif choice == 's':
            config.save()
            click.echo("Configuration saved!")
            click.pause()
        elif choice == 't':
            test_model()
        elif choice == 'q':
            break
        else:
            click.echo("Invalid option")
            click.pause()
    
    click.echo("Configuration complete!")

def main():
    """Main entry point"""
    try:
        cli()
    except Exception as e:
        click.echo(f"Fatal error: {e}", err=True)
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()