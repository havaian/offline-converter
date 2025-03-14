# cli/main.py
import sys
import argparse
from pathlib import Path
from core.manager import ConversionManager
from utils.dependencies import check_dependencies
from core.batch import BatchConverter

def main():
    """Entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description='Universal File Converter')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert a single file')
    convert_parser.add_argument('--input', '-i', required=True, help='Input file path')
    convert_parser.add_argument('--output-format', '-f', required=True, 
                               help='Output format (e.g., pdf, docx)')
    convert_parser.add_argument('--output', '-o', help='Output file path (optional)')
    
    # Batch convert command
    batch_parser = subparsers.add_parser('batch-convert', help='Convert multiple files')
    batch_parser.add_argument('--input-dir', '-i', required=True, help='Input directory')
    batch_parser.add_argument('--output-format', '-f', required=True, 
                             help='Output format for all files')
    batch_parser.add_argument('--output-dir', '-o', help='Output directory (optional)')
    batch_parser.add_argument('--pattern', '-p', action='append', 
                             help='File pattern to match (can specify multiple times)')
    
    # Check dependencies command
    deps_parser = subparsers.add_parser('check-deps', help='Check dependencies')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check dependencies
    print("Checking dependencies...")
    dependencies = check_dependencies()
    
    # Check if all required tools are available
    all_available = all(tool['available'] for tool in dependencies.values())
    if not all_available:
        missing = [name for name, info in dependencies.items() if not info['available']]
        print(f"Error: Missing required tools: {', '.join(missing)}")
        print("Please install the missing tools and try again.")
        sys.exit(1)
    
    # Create conversion manager
    manager = ConversionManager()
    
    # Initialize converters based on available tools
    for tool_name, tool_info in dependencies.items():
        if tool_info['available']:
            if tool_name == 'ffmpeg':
                from converters.ffmpeg import FFmpegConverter
                manager.register_converter('ffmpeg', FFmpegConverter())
            elif tool_name == 'pandoc':
                from converters.pandoc import PandocConverter
                manager.register_converter('pandoc', PandocConverter())
            elif tool_name == 'libreoffice':
                from converters.libreoffice import LibreOfficeConverter
                manager.register_converter('libreoffice', LibreOfficeConverter())
    
    # Execute command
    if args.command == 'convert':
        # Convert a single file
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file not found: {input_path}")
            sys.exit(1)
        
        try:
            output_path = manager.convert(input_path, args.output_format)
            print(f"Conversion successful: {output_path}")
        except Exception as e:
            print(f"Error during conversion: {str(e)}")
            sys.exit(1)
    
    elif args.command == 'batch-convert':
        # Convert multiple files
        input_dir = Path(args.input_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            print(f"Error: Input directory not found: {input_dir}")
            sys.exit(1)
        
        output_dir = Path(args.output_dir) if args.output_dir else input_dir
        batch_converter = BatchConverter(manager)
        
        try:
            results = batch_converter.batch_convert(
                input_dir, 
                args.output_format,
                output_dir,
                args.pattern
            )
            
            # Print results
            print(f"Batch conversion complete!")
            print(f"Successfully converted: {len(results['successful'])} files")
            print(f"Failed: {len(results['failed'])} files")
            
            if results['failed']:
                print("\nFailed conversions:")
                for failed in results['failed']:
                    print(f"  - {failed}")
        
        except Exception as e:
            print(f"Error during batch conversion: {str(e)}")
            sys.exit(1)
    
    elif args.command == 'check-deps':
        # Already checked dependencies above, just print them
        print("\nDependency Check Results:")
        for name, info in dependencies.items():
            status = "Available" if info['available'] else "Not Found"
            print(f"  {name}: {status}")
            if info['available'] and 'path' in info:
                print(f"    Path: {info['path']}")
    
    else:
        # No command specified
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()