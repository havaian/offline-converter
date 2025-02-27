# src/utils/format_utils.py
from pathlib import Path
from typing import Set, Dict, List

# Mapping of file categories to their extensions
FILE_CATEGORIES = {
    'document': {
        'extensions': {'doc', 'docx', 'odt', 'rtf', 'txt', 'pdf', 'md', 'markdown', 'html', 'epub'},
        'description': 'Document Files'
    },
    'spreadsheet': {
        'extensions': {'xls', 'xlsx', 'ods', 'csv'},
        'description': 'Spreadsheet Files'
    },
    'presentation': {
        'extensions': {'ppt', 'pptx', 'odp'},
        'description': 'Presentation Files'
    },
    'audio': {
        'extensions': {'mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac'},
        'description': 'Audio Files'
    },
    'video': {
        'extensions': {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'},
        'description': 'Video Files'
    },
    'image': {
        'extensions': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg'},
        'description': 'Image Files'
    }
}

# Mapping of converter tools to the file categories they can handle
CONVERTER_CATEGORIES = {
    'pandoc': {'document'},
    'libreoffice': {'document', 'spreadsheet', 'presentation'},
    'ffmpeg': {'audio', 'video', 'image'}
}

def get_file_category(file_path: Path) -> str:
    """
    Determine the category of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Category name or 'unknown' if not recognized
    """
    extension = file_path.suffix.lower().lstrip('.')
    
    for category, info in FILE_CATEGORIES.items():
        if extension in info['extensions']:
            return category
    
    return 'unknown'

def get_compatible_formats(file_path: Path, conversion_manager) -> List[str]:
    """
    Get a list of compatible output formats for a given file.
    
    Args:
        file_path: Path to the file
        conversion_manager: Conversion manager instance
        
    Returns:
        List[str]: List of compatible formats
    """
    # Get file extension
    source_format = file_path.suffix.lower().lstrip('.')
    
    # Get all supported formats from conversion manager
    supported_formats = set()
    for converter in conversion_manager._converters.values():
        if source_format in converter.supported_input_formats:
            supported_formats.update(converter.supported_output_formats)
    
    # Remove the current format from the list
    if source_format in supported_formats:
        supported_formats.remove(source_format)
    
    return sorted(supported_formats)

def format_can_be_converted(source_format: str, target_format: str, conversion_manager) -> bool:
    """
    Check if a file format can be converted to another format.
    
    Args:
        source_format: Source file format (e.g., 'pdf')
        target_format: Target file format (e.g., 'docx')
        conversion_manager: Conversion manager instance
        
    Returns:
        bool: True if conversion is possible
    """
    for converter in conversion_manager._converters.values():
        if (source_format in converter.supported_input_formats and
            target_format in converter.supported_output_formats):
            return True
    
    return False

def get_converter_for_formats(source_format: str, target_format: str, conversion_manager) -> str:
    """
    Get the name of the converter that can handle a specific conversion.
    
    Args:
        source_format: Source file format
        target_format: Target file format
        conversion_manager: Conversion manager instance
        
    Returns:
        str: Name of the converter or None if not supported
    """
    for name, converter in conversion_manager._converters.items():
        if (source_format in converter.supported_input_formats and
            target_format in converter.supported_output_formats):
            return name
    
    return None