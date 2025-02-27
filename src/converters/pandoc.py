# src/converters/pandoc.py
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .base import BaseConverter
from core.exceptions import ConverterError, DependencyError
from utils.dependencies import get_tool_path

class PandocConverter(BaseConverter):
    """
    Converter implementation using Pandoc for document formats.
    """
    
    def __init__(self):
        super().__init__()
        self._supported_input_formats = {
            'md', 'markdown', 'docx', 'doc', 'pdf', 
            'odt', 'txt', 'html', 'epub'
        }
        self._supported_output_formats = {
            'md', 'markdown', 'docx', 'odt', 'txt', 
            'html', 'epub', 'pdf'
        }
        
        # Pandoc path
        self._pandoc_path = None
        
    def validate_dependencies(self) -> bool:
        """Check if Pandoc is available."""
        try:
            # Find Pandoc
            pandoc_path = get_tool_path('pandoc')
            if not pandoc_path:
                raise DependencyError(
                    "Pandoc not found. Please install Pandoc or use the portable version."
                )
                
            # Check if it works
            result = subprocess.run(
                [str(pandoc_path), '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise DependencyError(
                    f"Pandoc found but failed to run: {result.stderr}"
                )
                
            # Store path for later use
            self._pandoc_path = pandoc_path
            return True
            
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise DependencyError(f"Pandoc error: {str(e)}")
            
    def convert(self, 
                source_path: Path, 
                target_path: Path, 
                progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Convert document using Pandoc.
        """
        if not self._pandoc_path:
            self.validate_dependencies()
            
        try:
            source_format = source_path.suffix[1:].lower()
            target_format = target_path.suffix[1:].lower()
            
            if not self.can_convert(source_format, target_format):
                raise ConverterError(
                    f"Unsupported conversion: {source_format} to {target_format}"
                )
            
            # Start conversion
            if progress_callback:
                progress_callback(10)
                
            # Special handling for PDF output
            if target_format == 'pdf':
                # For PDF, provide a better error message if latex is missing
                try:
                    cmd = [
                        str(self._pandoc_path),
                        str(source_path),
                        '-o', str(target_path)
                    ]
                    process = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if process.returncode != 0:
                        # Check for common PDF conversion errors
                        if 'pdflatex not found' in process.stderr:
                            raise ConverterError(
                                "PDF conversion requires LaTeX. Please install TeX Live, MiKTeX, or try converting to a different format."
                            )
                        else:
                            raise ConverterError(f"Pandoc error: {process.stderr}")
                except Exception as e:
                    raise ConverterError(f"PDF conversion failed: {str(e)}")
            else:
                # For non-PDF formats
                cmd = [
                    str(self._pandoc_path),
                    str(source_path),
                    '-o', str(target_path)
                ]
                
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if process.returncode != 0:
                    raise ConverterError(f"Pandoc error: {process.stderr}")
            
            if progress_callback:
                progress_callback(100)
                
            return True
            
        except Exception as e:
            raise ConverterError(f"Conversion failed: {str(e)}")