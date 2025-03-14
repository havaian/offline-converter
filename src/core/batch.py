# core/batch.py
from pathlib import Path
import glob
import os
from typing import Dict, List, Any, Union
from core.exceptions import ConverterError

class BatchConverter:
    """Handles batch conversion of multiple files."""
    
    def __init__(self, conversion_manager):
        """Initialize with a conversion manager instance."""
        self.manager = conversion_manager
    
    def batch_convert(self, source_dir: Union[str, Path], target_format: str, 
                      output_dir: Union[str, Path] = None, 
                      file_patterns: List[str] = None) -> Dict[str, List[str]]:
        """
        Convert multiple files matching patterns to the target format.
        
        Args:
            source_dir: Directory containing source files
            target_format: Target format to convert to
            output_dir: Directory to save converted files (default: source_dir)
            file_patterns: List of glob patterns to match files (default: ["*.*"])
            
        Returns:
            Dict with 'successful' and 'failed' lists of file paths
        """
        # Ensure Path objects
        source_dir = Path(source_dir)
        if output_dir:
            output_dir = Path(output_dir)
        else:
            output_dir = source_dir
            
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Default to all files if patterns not specified
        if not file_patterns:
            file_patterns = ["*.*"]
            
        # Find all files matching patterns
        all_files = []
        for pattern in file_patterns:
            matched_files = list(source_dir.glob(pattern))
            all_files.extend(matched_files)
            
        # Remove duplicates and directories
        all_files = list(set([f for f in all_files if f.is_file()]))
        
        # Track conversion results
        results = {
            "successful": [],
            "failed": []
        }
        
        # Process each file
        for source_path in all_files:
            try:
                # Call the conversion manager to convert the file
                self.manager.convert(source_path, target_format)
                
                # Add to successful list
                results["successful"].append(str(source_path))
            except Exception as e:
                # Add to failed list with error message
                results["failed"].append(f"{source_path}")
        
        return results