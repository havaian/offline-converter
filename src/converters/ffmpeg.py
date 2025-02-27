# src/converters/ffmpeg.py
import subprocess
import os
from pathlib import Path
from typing import Callable, Optional

from .base import BaseConverter
from core.exceptions import ConverterError, DependencyError
from utils.dependencies import get_tool_path

class FFmpegConverter(BaseConverter):
    """
    Converter implementation using FFmpeg for audio/video formats.
    """
    
    def __init__(self):
        super().__init__()
        # Video formats
        self._supported_input_formats = {
            'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv',
            'mp3', 'wav', 'aac', 'ogg', 'm4a', 'flac'
        }
        self._supported_output_formats = {
            'mp4', 'avi', 'mkv', 'mov',
            'mp3', 'wav', 'aac', 'ogg'
        }
        
        # Find FFmpeg path
        self._ffmpeg_path = None
        
    def validate_dependencies(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            # Find FFmpeg
            ffmpeg_path = get_tool_path('ffmpeg')
            if not ffmpeg_path:
                raise DependencyError(
                    "FFmpeg not found. Please install FFmpeg or use the portable version."
                )
                
            # Check if it works
            result = subprocess.run(
                [str(ffmpeg_path), '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise DependencyError(
                    f"FFmpeg found but failed to run: {result.stderr}"
                )
                
            # Store path for later use
            self._ffmpeg_path = ffmpeg_path
            return True
            
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise DependencyError(f"FFmpeg error: {str(e)}")
            
    def convert(self, 
                source_path: Path, 
                target_path: Path, 
                progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Convert media using FFmpeg.
        """
        if not self._ffmpeg_path:
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
                progress_callback(0)

            # Build the FFmpeg command based on target format
            cmd = [str(self._ffmpeg_path), '-i', str(source_path)]
            
            # Add format-specific parameters
            if target_format in ['mp4', 'mkv', 'avi']:
                cmd.extend(['-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium'])
            elif target_format == 'mp3':
                cmd.extend(['-vn', '-c:a', 'libmp3lame', '-b:a', '192k'])
            elif target_format == 'wav':
                cmd.extend(['-vn', '-c:a', 'pcm_s16le'])
            elif target_format == 'ogg':
                cmd.extend(['-vn', '-c:a', 'libvorbis', '-q:a', '4'])
            elif target_format == 'aac':
                cmd.extend(['-vn', '-c:a', 'aac', '-b:a', '192k'])
                
            # Add output file
            cmd.append(str(target_path))
            
            # Add overwrite flag
            cmd.extend(['-y'])
            
            # Run FFmpeg
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if process.returncode != 0:
                raise ConverterError(f"FFmpeg error: {process.stderr}")
                
            if progress_callback:
                progress_callback(100)
                
            return True
            
        except subprocess.SubprocessError as e:
            raise ConverterError(f"FFmpeg conversion failed: {str(e)}")
        except Exception as e:
            raise ConverterError(f"Conversion failed: {str(e)}")