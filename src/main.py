# src/main.py
import argparse
import sys
from pathlib import Path
from typing import Optional, Set
import tqdm

from core.manager import ConversionManager
from converters.pandoc import PandocConverter
from converters.ffmpeg import FFmpegConverter
from converters.libreoffice import LibreOfficeConverter
from core.exceptions import ConverterError, UnsupportedFormatError, DependencyError
from utils.dependencies import check_dependencies

def create_progress_bar(desc: str) -> tqdm.tqdm:
    return tqdm.tqdm(total=100, desc=desc, unit="%")

def setup_converters() -> ConversionManager:
    manager = ConversionManager()
    manager.register_converter("pandoc", PandocConverter())
    manager.register_converter("ffmpeg", FFmpegConverter())
    manager.register_converter("libreoffice", LibreOfficeConverter())
    return manager

def get_supported_formats(manager: ConversionManager) -> Set[str]:
    formats = set()
    for converter in manager._converters.values():
        formats.update(converter.supported_input_formats)
        formats.update(converter.supported_output_formats)
    return formats

def show_dependency_status():
    """Display status of bundled dependencies"""
    status = check_dependencies()
    
    print("\nBundled Dependencies Status:")
    print("-" * 60)
    
    for tool, info in status.items():
        if info['available']:
            print(f"✅ {tool.capitalize()}: Available")
            print(f"   Path: {info['path']}")
            if info['version']:
                print(f"   Version: {info['version']}")
        else:
            print(f"❌ {tool.capitalize()}: Not found")
            print(f"   Expected at: {Path('portable_tools') / tool / ('bin' if tool != 'libreoffice' else 'program')}")
    
    print("\nNote: Missing dependencies will limit conversion capabilities.")
    print("-" * 60)

def main():
    # Setup conversion manager first to get supported formats
    manager = setup_converters()
    supported_formats = get_supported_formats(manager)
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Universal File Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add --list-formats before required arguments
    parser.add_argument("--list-formats", "-l", 
                       action="store_true", 
                       help="List supported formats and exit")
    
    parser.add_argument("--check-deps", "-d",
                       action="store_true",
                       help="Check bundled dependencies and exit")
    
    # Make input/output optional so --list-formats can work alone
    parser.add_argument("--input", "-i",
                       help="Input file path")
    parser.add_argument("--output-format", "-o",
                       help="Desired output format (e.g., pdf, mp4)",
                       choices=sorted(supported_formats))
    parser.add_argument("--quiet", "-q", 
                       action="store_true", 
                       help="Suppress progress bar")
    
    args = parser.parse_args()
    
    # Handle --check-deps
    if args.check_deps:
        show_dependency_status()
        return 0
    
    # Handle --list-formats
    if args.list_formats:
        print("\nSupported formats:")
        for fmt in sorted(supported_formats):
            print(f"  - {fmt}")
        return 0
    
    # Check required arguments if not just listing formats
    if not args.input or not args.output_format:
        parser.error("Both --input and --output-format are required for conversion")
    
    # Convert paths to Path objects
    input_path = Path(args.input)
    
    try:
        # Check if input file exists
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        # Create progress bar if not in quiet mode
        if not args.quiet:
            pbar = create_progress_bar("Converting")
            progress_callback = lambda x: pbar.update(x - pbar.n)
        else:
            progress_callback = None
        
        # Perform conversion
        output_path = manager.convert(
            input_path,
            args.output_format,
            progress_callback=progress_callback
        )
        
        if not args.quiet:
            pbar.close()
        
        print(f"\nConversion successful! Output saved to: {output_path}")
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1
    except UnsupportedFormatError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        print("\nTip: Use --list-formats to see supported formats", file=sys.stderr)
        return 1
    except ConverterError as e:
        print(f"Conversion error: {str(e)}", file=sys.stderr)
        print("\nTip: Use --check-deps to verify that all required bundled tools are available", file=sys.stderr)
        return 1
    except DependencyError as e:
        print(f"Dependency error: {str(e)}", file=sys.stderr)
        print("\nMake sure the bundled tools are properly installed in the portable_tools directory", file=sys.stderr)
        print("Use --check-deps to verify the bundled tools", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())