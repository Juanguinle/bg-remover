import time
from typing import Dict, Any, List
from dataclasses import dataclass, field
import threading

@dataclass
class ProcessingStats:
    """Thread-safe processing statistics"""
    
    total_processed: int = 0
    total_failed: int = 0
    total_processing_time: float = 0.0
    total_file_size: int = 0
    processing_times: List[float] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def add_success(self, processing_time: float, file_size: int):
        """Add successful processing record
        
        Args:
            processing_time: Time taken to process
            file_size: Size of processed file in bytes
        """
        with self._lock:
            self.total_processed += 1
            self.total_processing_time += processing_time
            self.total_file_size += file_size
            self.processing_times.append(processing_time)
    
    def add_failure(self, file_size: int):
        """Add failed processing record
        
        Args:
            file_size: Size of failed file in bytes
        """
        with self._lock:
            self.total_failed += 1
            self.total_file_size += file_size
    
    @property
    def total_files(self) -> int:
        """Get total number of files processed (success + failed)"""
        return self.total_processed + self.total_failed
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.total_processed / self.total_files) * 100
    
    @property
    def average_processing_time(self) -> float:
        """Get average processing time per file"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    @property
    def files_per_second(self) -> float:
        """Get processing speed in files per second"""
        if self.total_processing_time == 0:
            return 0.0
        return self.total_processed / self.total_processing_time
    
    @property
    def total_runtime(self) -> float:
        """Get total runtime since start"""
        return time.time() - self.start_time
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive statistics summary
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            return {
                "total_processed": self.total_processed,
                "total_failed": self.total_failed,
                "total_files": self.total_files,
                "success_rate": round(self.success_rate, 2),
                "total_processing_time": round(self.total_processing_time, 2),
                "average_processing_time": round(self.average_processing_time, 2),
                "files_per_second": round(self.files_per_second, 2),
                "total_file_size_mb": round(self.total_file_size / 1024 / 1024, 2),
                "total_runtime": round(self.total_runtime, 2),
                "min_processing_time": round(min(self.processing_times), 2) if self.processing_times else 0,
                "max_processing_time": round(max(self.processing_times), 2) if self.processing_times else 0,
            }
    
    def reset(self):
        """Reset all statistics"""
        with self._lock:
            self.total_processed = 0
            self.total_failed = 0
            self.total_processing_time = 0.0
            self.total_file_size = 0
            self.processing_times.clear()
            self.start_time = time.time()