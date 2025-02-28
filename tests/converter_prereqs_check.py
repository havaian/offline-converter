#!/usr/bin/env python3
"""
Universal File Converter - Prerequisites Checker

This script checks for the presence of required tools and generates 
a comprehensive report of supported file formats and conversions.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import json
from pprint import pprint

# Represent conversion capabilities
class ConversionCapability:
    def __init__(self):
        # File format categories
        self.categories = {
            'document': ['pdf', 'docx', 'doc', 'odt', 'rtf', 'txt', 'md', 'html', 'epub'],
            'spreadsheet': ['xls', 'xlsx', 'ods', 'csv'],
            'presentation': ['ppt', 'pptx', 'odp'],
            'audio': ['mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac'],
            'video': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg'],
        }
        
        # FFmpeg supported formats
        self.ffmpeg_formats = {
            'input': set(self.categories['audio'] + self.categories['video'] + 
                         self.categories['image']),
            'output': set(self.categories['audio'] + self.categories['video'] + 
                          ['jpg', 'jpeg', 'png', 'gif'])
        }
        
        # Pandoc supported formats
        self.pandoc_formats = {
            'input': {'md', 'markdown', 'docx', 'doc', 'odt', 'txt', 'html', 'epub', 
                      'rst', 'latex', 'tex', 'rtf', 'xml', 'json'},
            'output': {'md', 'markdown', 'docx', 'odt', 'txt', 'html', 'epub', 'pdf',
                       'rst', 'latex', 'tex', 'rtf', 'xml', 'json', 'pptx'}
        }
        
        # LibreOffice supported formats
        self.libreoffice_formats = {
            'input': set(self.categories['document'] + self.categories['spreadsheet'] + 
                         self.categories['presentation']),
            'output': {'pdf', 'docx', 'odt', 'rtf', 'txt', 'xlsx', 'ods', 'csv', 
                       'pptx', 'odp'}
        }
        
        # Initialize conversion matrix
        self.format_matrix = self._build_format_matrix()
    
    def _build_format_matrix(self) -> Dict[str, Dict[str, str]]:
        """Build a format conversion matrix indicating which tool handles each conversion."""
        all_formats = set()
        for category in self.categories.values():
            all_formats.update(category)
        
        matrix = {}
        for src_format in all_formats:
            matrix[src_format] = {}
            for dst_format in all_formats:
                tool = self._get_conversion_tool(src_format, dst_format)
                if tool:
                    matrix[src_format][dst_format] = tool
        
        return matrix
    
    def _get_conversion_tool(self, src_format: str, dst_format: str) -> Optional[str]:
        """Determine which tool can handle a specific conversion."""
        # Handle same-format "conversions"
        if src_format == dst_format:
            return 'copy'
        
        # Check FFmpeg
        if src_format in self.ffmpeg_formats['input'] and dst_format in self.ffmpeg_formats['output']:
            # Check if both formats are in the same category
            src_category = self._get_format_category(src_format)
            dst_category = self._get_format_category(dst_format)
            
            # Allow conversion within audio, within video, or from video to audio
            if ((src_category == dst_category and src_category in ['audio', 'video']) or
                (src_category == 'video' and dst_category == 'audio') or
                (src_category == dst_category and src_category == 'image') or
                (src_category == 'image' and dst_category == 'image')):
                return 'ffmpeg'
        
        # Check Pandoc
        if src_format in self.pandoc_formats['input'] and dst_format in self.pandoc_formats['output']:
            # Primarily for document formats
            return 'pandoc'
        
        # Check LibreOffice
        if src_format in self.libreoffice_formats['input'] and dst_format in self.libreoffice_formats['output']:
            # Handle specific cross-category conversions
            src_category = self._get_format_category(src_format)
            dst_category = self._get_format_category(dst_format)
            
            # Allow everything to convert to PDF
            if dst_format == 'pdf':
                return 'libreoffice'
            
            # Allow conversions within the same category
            if src_category == dst_category:
                return 'libreoffice'
            
            # No cross-category conversions except to PDF
            return None
        
        return None
    
    def _get_format_category(self, file_format: str) -> str:
        """Determine the category of a file format."""
        for category, formats in self.categories.items():
            if file_format in formats:
                return category
        return 'unknown'
    
    def get_supported_input_formats(self) -> Set[str]:
        """Get all supported input formats."""
        formats = set()
        for src in self.format_matrix:
            if any(self.format_matrix[src].values()):
                formats.add(src)
        return formats
    
    def get_supported_output_formats(self) -> Set[str]:
        """Get all supported output formats."""
        formats = set()
        for src in self.format_matrix:
            formats.update(self.format_matrix[src].keys())
        return formats
    
    def get_compatible_formats(self, input_format: str) -> Dict[str, str]:
        """Get all compatible output formats for a given input format."""
        if input_format in self.format_matrix:
            return self.format_matrix[input_format]
        return {}
    
    def get_summary_stats(self) -> Dict[str, int]:
        """Get summary statistics about conversion capabilities."""
        # Count total supported formats
        input_formats = self.get_supported_input_formats()
        output_formats = self.get_supported_output_formats()
        
        # Count possible conversions
        total_conversions = 0
        tool_conversions = {'ffmpeg': 0, 'pandoc': 0, 'libreoffice': 0, 'copy': 0}
        
        for src in self.format_matrix:
            for dst, tool in self.format_matrix[src].items():
                if tool:
                    total_conversions += 1
                    if tool in tool_conversions:
                        tool_conversions[tool] += 1
        
        # Count conversions by category
        category_conversions = {}
        for src_cat in self.categories:
            category_conversions[src_cat] = {}
            for dst_cat in self.categories:
                count = 0
                for src_fmt in self.categories[src_cat]:
                    for dst_fmt in self.categories[dst_cat]:
                        if src_fmt in self.format_matrix and dst_fmt in self.format_matrix[src_fmt]:
                            if self.format_matrix[src_fmt][dst_fmt]:
                                count += 1
                category_conversions[src_cat][dst_cat] = count
        
        return {
            'total_input_formats': len(input_formats),
            'total_output_formats': len(output_formats),
            'total_conversions': total_conversions,
            'tool_conversions': tool_conversions,
            'category_conversions': category_conversions
        }


class PrerequisitesChecker:
    def __init__(self):
        self.system_info = self._get_system_info()
        self.tools = {
            'ffmpeg': {'name': 'FFmpeg', 'command': 'ffmpeg', 'path': None, 'available': False},
            'pandoc': {'name': 'Pandoc', 'command': 'pandoc', 'path': None, 'available': False},
            'libreoffice': {
                'name': 'LibreOffice', 
                'command': 'soffice' if platform.system() != 'Darwin' else '/Applications/LibreOffice.app/Contents/MacOS/soffice',
                'path': None,
                'available': False
            }
        }
        
        # Find tools
        self._locate_tools()
        
        # Initialize conversion capability
        self.capability = ConversionCapability()
    
    def _get_system_info(self) -> Dict[str, str]:
        """Get system information."""
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': platform.python_version(),
            'platform': platform.platform()
        }
    
    def _locate_tools(self) -> None:
        """Locate required conversion tools on the system."""
        for tool_id, tool_info in self.tools.items():
            # Check if tool exists in PATH
            tool_path = shutil.which(tool_info['command'])
            
            if tool_path:
                tool_info['path'] = tool_path
                tool_info['available'] = True
                
                # Get version information
                try:
                    if tool_id == 'ffmpeg':
                        # FFmpeg prints version to stderr
                        result = subprocess.run([tool_path, '-version'], 
                                              capture_output=True, text=True, check=False)
                        version_output = result.stderr if result.stderr else result.stdout
                        # Extract version from output
                        version = version_output.split('\n')[0] if version_output else 'Unknown version'
                        tool_info['version'] = version
                    
                    elif tool_id == 'pandoc':
                        result = subprocess.run([tool_path, '--version'], 
                                              capture_output=True, text=True, check=False)
                        # Extract version from output
                        version = result.stdout.split('\n')[0] if result.stdout else 'Unknown version'
                        tool_info['version'] = version
                    
                    elif tool_id == 'libreoffice':
                        result = subprocess.run([tool_path, '--version'], 
                                              capture_output=True, text=True, check=False)
                        # Extract version from output
                        version = result.stdout.strip() if result.stdout else 'Unknown version'
                        tool_info['version'] = version
                
                except Exception as e:
                    tool_info['version'] = f"Error getting version: {str(e)}"
            else:
                alternative_paths = self._get_alternative_paths(tool_id)
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        tool_info['path'] = alt_path
                        tool_info['available'] = True
                        tool_info['version'] = 'Version unknown (found in non-standard location)'
                        break
    
    def _get_alternative_paths(self, tool_id: str) -> List[str]:
        """Get alternative installation paths for tools based on the platform."""
        system = platform.system()
        
        if system == 'Windows':
            if tool_id == 'ffmpeg':
                return [
                    r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                    r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe'
                ]
            elif tool_id == 'pandoc':
                return [
                    r'C:\Program Files\Pandoc\pandoc.exe',
                    os.path.expanduser(r'~\AppData\Local\Pandoc\pandoc.exe')
                ]
            elif tool_id == 'libreoffice':
                return [
                    r'C:\Program Files\LibreOffice\program\soffice.exe',
                    r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'
                ]
        
        elif system == 'Darwin':  # macOS
            if tool_id == 'ffmpeg':
                return [
                    '/usr/local/bin/ffmpeg',
                    '/opt/homebrew/bin/ffmpeg'
                ]
            elif tool_id == 'pandoc':
                return [
                    '/usr/local/bin/pandoc',
                    '/opt/homebrew/bin/pandoc'
                ]
            elif tool_id == 'libreoffice':
                return [
                    '/Applications/LibreOffice.app/Contents/MacOS/soffice'
                ]
        
        elif system == 'Linux':
            if tool_id == 'ffmpeg':
                return [
                    '/usr/bin/ffmpeg',
                    '/usr/local/bin/ffmpeg'
                ]
            elif tool_id == 'pandoc':
                return [
                    '/usr/bin/pandoc',
                    '/usr/local/bin/pandoc'
                ]
            elif tool_id == 'libreoffice':
                return [
                    '/usr/bin/soffice',
                    '/usr/bin/libreoffice',
                    '/usr/lib/libreoffice/program/soffice',
                    '/opt/libreoffice/program/soffice'
                ]
        
        return []
    
    def get_tool_check_results(self) -> Dict[str, Dict[str, Any]]:
        """Get results of tool checks."""
        return self.tools
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """Get all supported formats."""
        return {
            'input_formats': sorted(list(self.capability.get_supported_input_formats())),
            'output_formats': sorted(list(self.capability.get_supported_output_formats())),
            'format_matrix': self.capability.format_matrix,
            'stats': self.capability.get_summary_stats()
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a complete report of prerequisites check."""
        supported_formats = self.get_supported_formats()
        conversions_by_tool = supported_formats['stats']['tool_conversions']
        
        # Get category stats
        category_conversions = supported_formats['stats']['category_conversions']
        
        # Create a report
        report = {
            'system_info': self.system_info,
            'tools': self.get_tool_check_results(),
            'formats': {
                'total_input_formats': supported_formats['stats']['total_input_formats'],
                'total_output_formats': supported_formats['stats']['total_output_formats'],
                'input_formats': supported_formats['input_formats'],
                'output_formats': supported_formats['output_formats'],
            },
            'conversion_stats': {
                'total_conversions': supported_formats['stats']['total_conversions'],
                'by_tool': conversions_by_tool,
                'by_category': category_conversions
            }
        }
        
        return report


def main():
    """Run the prerequisites check and display results."""
    print("Universal File Converter - Prerequisites Check")
    print("=============================================\n")
    
    checker = PrerequisitesChecker()
    report = checker.generate_report()
    
    # Display system info
    print("System Information:")
    print(f"  OS: {report['system_info']['os']} ({report['system_info']['os_version']})")
    print(f"  Python: {report['system_info']['python_version']}")
    print(f"  Platform: {report['system_info']['platform']}")
    print()
    
    # Display tool availability
    print("Required Tools:")
    for tool_id, tool_info in report['tools'].items():
        status = "✓ Available" if tool_info['available'] else "✗ Not Found"
        version = tool_info.get('version', 'Unknown')
        print(f"  {tool_info['name']}: {status}")
        if tool_info['available']:
            print(f"    Path: {tool_info['path']}")
            print(f"    Version: {version}")
    print()
    
    # Display format support
    print("Format Support:")
    print(f"  Total Input Formats: {report['formats']['total_input_formats']}")
    print(f"  Total Output Formats: {report['formats']['total_output_formats']}")
    print(f"  Total Possible Conversions: {report['conversion_stats']['total_conversions']}")
    print()
    
    # Display conversions by tool
    print("Conversions by Tool:")
    for tool, count in report['conversion_stats']['by_tool'].items():
        print(f"  {tool.capitalize()}: {count} conversions")
    print()
    
    # Display category matrix
    print("Conversion Matrix by Category:")
    categories = list(report['conversion_stats']['by_category'].keys())
    
    # Print header
    header = "          "
    for dst_cat in categories:
        header += f"{dst_cat[:7]:10s}"
    print(header)
    
    # Print rows
    for src_cat in categories:
        row = f"{src_cat[:10]:10s}"
        for dst_cat in categories:
            count = report['conversion_stats']['by_category'][src_cat][dst_cat]
            row += f"{count:10d}"
        print(row)
    print()
    
    # Display supported input formats by category
    print("Supported Input Formats:")
    input_formats = report['formats']['input_formats']
    _display_formats_by_category(input_formats)
    print()
    
    # Display supported output formats by category
    print("Supported Output Formats:")
    output_formats = report['formats']['output_formats']
    _display_formats_by_category(output_formats)
    print()
    
    # Check if all tools are available
    all_tools_available = all(tool['available'] for tool in report['tools'].values())
    if all_tools_available:
        print("✓ All required tools are available. Ready for testing!")
    else:
        missing_tools = [tool_info['name'] for tool_id, tool_info in report['tools'].items() 
                         if not tool_info['available']]
        print(f"✗ Some tools are missing: {', '.join(missing_tools)}")
        print("Please install the missing tools to enable full functionality.")
    
    # Save report to JSON
    results_dir = os.path.join('tests', 'results')
    os.makedirs(results_dir, exist_ok=True)  # Create directory if it doesn't exist
    report_path = os.path.join(results_dir, 'converter_report.json')

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to {report_path}"


def _display_formats_by_category(formats: List[str]) -> None:
    """Display a list of formats grouped by category."""
    # Define categories
    categories = {
        'document': ['pdf', 'docx', 'doc', 'odt', 'rtf', 'txt', 'md', 'html', 'epub'],
        'spreadsheet': ['xls', 'xlsx', 'ods', 'csv'],
        'presentation': ['ppt', 'pptx', 'odp'],
        'audio': ['mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac'],
        'video': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'],
        'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg'],
    }
    
    # Group formats by category
    by_category = {}
    for cat, cat_formats in categories.items():
        cat_supported = [fmt for fmt in formats if fmt in cat_formats]
        if cat_supported:
            by_category[cat] = cat_supported
    
    # Find formats that don't belong to any category
    all_category_formats = []
    for cat_formats in categories.values():
        all_category_formats.extend(cat_formats)
    
    other_formats = [fmt for fmt in formats if fmt not in all_category_formats]
    if other_formats:
        by_category['other'] = other_formats
    
    # Display formats by category
    for cat, cat_formats in by_category.items():
        print(f"  {cat.capitalize()}: {', '.join(cat_formats)}")


if __name__ == "__main__":
    main()