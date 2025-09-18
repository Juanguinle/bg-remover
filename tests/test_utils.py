"""
import pytest
from pathlib import Path
import tempfile

from bg_remover.utils.file_utils import ensure_directory, get_file_size_mb, is_image_file
from bg_remover.utils.device_utils import detect_device, get_system_info

class TestFileUtils:
    def test_ensure_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "new" / "nested" / "directory"
            result = ensure_directory(str(test_path))
            
            assert result.exists()
            assert result.is_dir()
    
    def test_file_size_calculation(self):
        with tempfile.NamedTemporaryFile() as tmp_file:
            # Write 1KB of data
            tmp_file.write(b'x' * 1024)
            tmp_file.flush()
            
            size_mb = get_file_size_mb(Path(tmp_file.name))
            assert 0.0009 < size_mb < 0.0011  # Approximately 1KB in MB
    
    def test_image_file_detection(self):
        assert is_image_file(Path("test.jpg"))
        assert is_image_file(Path("test.PNG"))
        assert not is_image_file(Path("test.txt"))
        assert not is_image_file(Path("test.doc"))

class TestDeviceUtils:
    def test_device_detection(self):
        device = detect_device()
        assert device in ["cpu", "cuda"]
    
    def test_system_info(self):
        info = get_system_info()
        
        required_keys = ["platform", "system", "python_version"]
        for key in required_keys:
            assert key in info
            assert info[key] is not None
"""