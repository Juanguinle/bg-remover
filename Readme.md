# BG Remover

Professional background removal application with automatic folder monitoring and multiple AI models.

## Features

- **Multiple AI Models**: Support for transparent-background, rembg, and SAM (Segment Anything Model)
- **Automatic Monitoring**: Real-time folder monitoring with file processing
- **GPU/CPU Support**: Automatic device detection with manual override options
- **Batch Processing**: Efficient parallel processing capabilities
- **Production Ready**: Comprehensive error handling, logging, and statistics
- **Cross-Platform**: Windows, macOS, and Linux support
- **Interactive Configuration**: Easy-to-use configuration menu
- **Detailed Output**: Files named with model, quality, device, and processing time
- **Flexible Processing**: Process existing files, monitor new ones, or both

## Quick Start

### Installation

#### Windows Installation
```bash
# Create virtual environment
python -m venv bg_remover_env
bg_remover_env\Scripts\activate

# Install PyTorch with CUDA support (optional)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install dependencies
pip install transparent-background==1.2.5
pip install onnxruntime easydict kornia opencv-python pyvirtualcam rembg

# Install bg-remover
pip install -e .
```

#### macOS/Linux Installation
```bash
# Create virtual environment
python3 -m venv bg_remover_env
source bg_remover_env/bin/activate

# Install dependencies
pip install torch torchvision
pip install transparent-background==1.2.5
pip install onnxruntime easydict kornia opencv-python pyvirtualcam rembg

# Install bg-remover
pip install -e .
```

### Basic Usage

```bash
# Interactive configuration menu
bg-remover configure

# Process all images in a folder
bg-remover process --input ./images --output ./processed

# Monitor folder (processes existing files + watches for new ones)
bg-remover monitor --input ./watch_folder

# Monitor new files only (skip existing)
bg-remover monitor --input ./watch_folder --new-only

# Test model functionality
bg-remover test --model rembg --device cpu

# Show system information
bg-remover info
```

## Supported Models

### Rembg
- **Variants**: u2net, u2net_human_seg, u2net_cloth_seg, silueta, isnet-general-use
- **Performance**: Fast processing, good general results
- **Best for**: Quick processing, batch operations

### Transparent Background
- **Quality**: High-quality results with multiple quality settings
- **Modes**: base (stable), base-nightly (experimental, higher quality)
- **Performance**: Slower but higher quality
- **Best for**: High-quality single image processing

### SAM (Segment Anything Model)
- **Variants**: vit_b (~350MB), vit_l (~1.2GB), vit_h (~2.4GB)
- **Features**: State-of-the-art segmentation, automatic checkpoint download
- **Performance**: Excellent quality, moderate speed
- **Best for**: Complex segmentation tasks

## CLI Commands

### Configuration Commands
```bash
# Interactive configuration menu
bg-remover configure

# Show current configuration
bg-remover config-show

# Set specific values
bg-remover config-set processing.model rembg
bg-remover config-set models.rembg.model_name u2net_human_seg
bg-remover config-set processing.batch_size 4
```

### Processing Commands
```bash
# Process folder
bg-remover process --input ./input --output ./output

# Process with specific model and settings
bg-remover process --input ./input --model rembg --device cpu --quality high

# Compare multiple models and qualities
bg-remover compare --input ./input --models "rembg,transparent-background" --qualities "low,high"

# Analyze processed results
bg-remover analyze-results --output ./output
```

### Monitoring Commands
```bash
# Monitor folder (default: process existing + watch new)
bg-remover monitor --input ./input

# Monitor new files only
bg-remover monitor --input ./input --new-only

# Monitor with specific settings
bg-remover monitor --input ./input --model transparent-background --device cpu
```

### Utility Commands
```bash
# Test model functionality
bg-remover test --model rembg --device cpu

# Clean output folders
bg-remover clean --folders output,processed

# System information
bg-remover info
```

## Configuration

### Interactive Configuration
Use the interactive menu for easy configuration:

```bash
bg-remover configure
```

### Manual Configuration
Create a `config.yaml` file:

```yaml
processing:
  input_folder: "./input"
  output_folder: "./output" 
  processed_folder: "./processed"
  model: "rembg"
  device: "auto"  # auto, cpu, cuda
  batch_size: 4
  preserve_original: true
  overwrite_existing: false

models:
  transparent-background:
    enabled: true
    quality: "high"
    mode: "base"  # or "base-nightly"
  rembg:
    enabled: true
    model_name: "u2net"  # u2net, silueta, u2net_human_seg, etc.
    quality: "high"
  sam:
    enabled: true
    model_type: "vit_b"  # vit_b, vit_l, vit_h

monitoring:
  enabled: true
  recursive: false
  debounce_seconds: 1.0

logging:
  level: "INFO"
  file: "bg_remover.log"
```

## Output File Naming

Processed files include detailed information in the filename:
```
original_model_quality_device_time.png

Examples:
photo1_rembg_u2net_high_cpu_2.3s.png
photo1_transparent-background_high_cpu_45.7s.png
photo1_sam_vit_b_high_cpu_8.1s.png
```

## Performance Optimization

### CPU Processing
- **Fastest**: rembg with u2net model
- **Balanced**: rembg with silueta model
- **Highest Quality**: transparent-background with base-nightly mode

### GPU Processing
```bash
# Set device to CUDA
bg-remover config-set processing.device cuda

# Or specify per model
bg-remover config-set models.transparent-background.device cuda
```

### Batch Processing
```bash
# Increase parallel processing (uses more CPU/memory)
bg-remover config-set processing.batch_size 8
```

## API Usage

```python
from bg_remover import BackgroundProcessor, ConfigManager

# Initialize
config = ConfigManager()
processor = BackgroundProcessor(config)

# Process single folder
results = processor.process_folder("./images")
print(f"Processed: {results['processed']} files")

# Process with custom callback
def progress_callback(input_path, output_path, success, time):
    print(f"Processed: {input_path} -> {output_path}")

processor.process_folder("./images", progress_callback)

# Get statistics
stats = processor.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
```

## System Requirements

- Python 3.8+
- Windows 10/11, macOS, or Linux
- 4GB+ RAM (8GB+ recommended for GPU processing)
- CUDA-compatible GPU (optional, for acceleration)

## Troubleshooting

### Windows Issues

1. **Package installation errors**:
   ```bash
   pip install transparent-background==1.2.5
   pip install onnxruntime easydict kornia opencv-python pyvirtualcam
   ```

2. **CUDA installation**:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

### Performance Issues

1. **Slow processing**: Switch to rembg model for faster processing
2. **Out of memory**: Reduce batch_size or use CPU processing
3. **File not found errors**: Ensure files aren't being moved during processing

### Common Solutions

```bash
# Fix file monitoring issues
bg-remover config-set processing.preserve_original false

# Reset to default configuration
bg-remover clean --folders output,processed
bg-remover config-set processing.model rembg
bg-remover config-set processing.device auto

# Test model functionality
bg-remover test --model rembg --device cpu
```

## Development

### Project Structure
```
bg_remover/
├── cli/              # Command-line interface
├── config/           # Configuration management
├── core/             # Main processing engine
├── models/           # AI model implementations
└── utils/            # Utility functions
```

### Adding Custom Models

```python
from bg_remover.models.base import BaseModel
from bg_remover.models.factory import ModelFactory

class CustomModel(BaseModel):
    def initialize(self):
        # Initialize your model
        pass
    
    def process_image(self, image):
        # Process and return result
        return processed_image
    
    def cleanup(self):
        # Clean up resources
        pass

# Register the model
ModelFactory.register_model("custom", CustomModel)
```

### Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Docker Support

```bash
# Build secure image
docker build -t bg-remover:latest .

# Run with volume mounts
docker run -v ./input:/app/input -v ./output:/app/output bg-remover:latest
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Ensure all tests pass
5. Submit a pull request

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: Check the README for detailed guides
- Configuration: Use `bg-remover configure` for interactive setup