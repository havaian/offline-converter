# src/converters/libreoffice.py
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Callable, Optional
import shutil
import sys

from .base import BaseConverter
from core.exceptions import ConverterError, DependencyError
from utils.dependencies import get_tool_path

class LibreOfficeConverter(BaseConverter):
    """
    Converter implementation using LibreOffice for office document formats.
    Handles formats like DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, ODS, ODP.
    """
    
    def __init__(self):
        super().__init__()
        self._supported_input_formats = {
            # Text documents
            'doc', 'docx', 'odt', 'rtf', 'txt',
            # Spreadsheets
            'xls', 'xlsx', 'ods', 'csv',
            # Presentations
            'ppt', 'pptx', 'odp',
        }
        
        self._supported_output_formats = {
            # Text documents
            'pdf', 'docx', 'odt', 'rtf', 'txt',
            # Spreadsheets
            'xlsx', 'ods', 'csv',
            # Presentations
            'pptx', 'odp', 'pdf',
        }
        
        # LibreOffice path
        self._soffice_path = None
        
    def validate_dependencies(self) -> bool:
        """Check if LibreOffice is installed and accessible."""
        try:
            # Find LibreOffice
            soffice_path = get_tool_path('libreoffice') or get_tool_path('soffice')
            if not soffice_path:
                raise DependencyError(
                    "LibreOffice not found. Please install LibreOffice or use the portable version."
                )
                
            # Check if it works
            process = subprocess.run(
                [str(soffice_path), '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                raise DependencyError(
                    f"LibreOffice found but failed to run: {process.stderr}"
                )
                
            # Store path for later use
            self._soffice_path = soffice_path
            return True
            
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise DependencyError(f"LibreOffice error: {str(e)}")
            
    def _get_filter_name(self, target_format: str) -> str:
        """Get LibreOffice filter name for target format."""
        filter_map = {
            'pdf': 'writer_pdf_Export',
            'docx': 'MS Word 2007 XML',
            'odt': 'writer8',
            'rtf': 'Rich Text Format',
            'txt': 'Text',
            'xlsx': 'Calc MS Excel 2007 XML',
            'ods': 'calc8',
            'csv': 'Text - CSV',
            'pptx': 'Impress MS PowerPoint 2007 XML',
            'odp': 'impress8',
        }
        return filter_map.get(target_format, '')

    def convert(self, 
                source_path: Path, 
                target_path: Path, 
                progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Convert document using LibreOffice.
        """
        if not self._soffice_path:
            self.validate_dependencies()
            
        try:
            source_format = source_path.suffix[1:].lower()
            target_format = target_path.suffix[1:].lower()
            
            if not self.can_convert(source_format, target_format):
                raise ConverterError(
                    f"Unsupported conversion: {source_format} to {target_format}"
                )
            
            # Create temporary directory for conversion
            with tempfile.TemporaryDirectory() as temp_dir:
                if progress_callback:
                    progress_callback(10)
                
                # Prepare LibreOffice command
                filter_name = self._get_filter_name(target_format)
                
                cmd = [
                    str(self._soffice_path),
                    '--headless',
                    '--convert-to', f"{target_format}:{filter_name}",
                    '--outdir', temp_dir,
                    str(source_path)
                ]
                
                # Run conversion
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if process.returncode != 0:
                    error_msg = f"LibreOffice conversion failed with code {process.returncode}"
                    if process.stderr:
                        error_msg += f": {process.stderr}"
                    raise ConverterError(error_msg)
                
                if progress_callback:
                    progress_callback(80)
                
                # Move converted file to target path
                temp_file = Path(temp_dir) / source_path.with_suffix(f".{target_format}").name
                if temp_file.exists():
                    shutil.move(str(temp_file), str(target_path))
                else:
                    # Check if file was created with a different name
                    possible_files = list(Path(temp_dir).glob(f"*.{target_format}"))
                    if possible_files:
                        shutil.move(str(possible_files[0]), str(target_path))
                    else:
                        raise ConverterError("Converted file not found")
                
                if progress_callback:
                    progress_callback(100)
                
                return True
                
        except Exception as e:
            raise ConverterError(f"Conversion failed: {str(e)}")
            
    def _kill_running_instances(self):
        """Kill any running LibreOffice instances to prevent conflicts."""
        if os.name == 'nt':  # Windows
            os.system('taskkill /f /im soffice.bin* /t')
        else:  # Unix/Linux
            os.system('killall -9 soffice.bin')