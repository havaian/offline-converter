# src/converters/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional, Set

class BaseConverter(ABC):
    """
    Abstract base class for all file converters.
    """
    
    def __init__(self):
        self._supported_input_formats: Set[str] = set()
        self._supported_output_formats: Set[str] = set()

    @property
    def supported_input_formats(self) -> Set[str]:
        """Returns set of supported input formats"""
        return self._supported_input_formats

    @property
    def supported_output_formats(self) -> Set[str]:
        """Returns set of supported output formats"""
        return self._supported_output_formats

    def can_convert(self, source_format: str, target_format: str) -> bool:
        """
        Check if converter supports the given format conversion.
        
        Args:
            source_format: Input file format (e.g., 'pdf', 'docx')
            target_format: Output file format
            
        Returns:
            bool: True if conversion is supported
        """
        return (source_format.lower() in self._supported_input_formats and 
                target_format.lower() in self._supported_output_formats)

    @abstractmethod
    def convert(self, 
                source_path: Path, 
                target_path: Path, 
                progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Convert file from source path to target path.
        
        Args:
            source_path: Path to source file
            target_path: Path where converted file should be saved
            progress_callback: Optional callback function to report progress (0-100)
            
        Returns:
            bool: True if conversion successful
            
        Raises:
            ConverterError: If conversion fails
        """
        pass

    @abstractmethod
    def validate_dependencies(self) -> bool:
        """
        Check if all required dependencies are available.
        
        Returns:
            bool: True if all dependencies are satisfied
        """
        pass