# src/core/manager.py
from pathlib import Path
from typing import Dict, List, Type, Callable, Optional

from converters.base import BaseConverter
from core.exceptions import ConverterError, UnsupportedFormatError

class ConversionManager:
    """
    Manages file conversions by selecting appropriate converters.
    """
    
    def __init__(self):
        self._converters: Dict[str, BaseConverter] = {}
        
    def register_converter(self, name: str, converter: BaseConverter) -> None:
        """
        Register a new converter instance.
        """
        self._converters[name] = converter
        
    def find_converter(self, source_format: str, target_format: str) -> Optional[BaseConverter]:
        """
        Find appropriate converter for the given formats.
        """
        for converter in self._converters.values():
            if converter.can_convert(source_format, target_format):
                return converter
        return None
        
    def convert(self, 
                source_path: Path, 
                target_format: str,
                progress_callback: Optional[Callable[[int], None]] = None) -> Path:
        """
        Convert file to target format.
        
        Args:
            source_path: Path to source file
            target_format: Desired output format
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path: Path to converted file
            
        Raises:
            ConverterError: If conversion fails
            UnsupportedFormatError: If no suitable converter found
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
            
        source_format = source_path.suffix[1:].lower()
        target_format = target_format.lower()
        
        # Find appropriate converter
        converter = self.find_converter(source_format, target_format)
        if not converter:
            raise UnsupportedFormatError(
                f"No converter found for {source_format} to {target_format}"
            )
            
        # Prepare target path
        target_path = source_path.with_suffix(f".{target_format}")
        
        # Perform conversion
        success = converter.convert(source_path, target_path, progress_callback)
        
        if not success:
            raise ConverterError("Conversion failed")
            
        return target_path