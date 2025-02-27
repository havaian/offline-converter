# build_tools/build_exe.py
import subprocess
import sys
import os
from pathlib import Path

def check_bundled_tools():
    """Check if all portable tools are in place before building"""
    project_root = Path(__file__).parent.parent
    
    required_files = [
        project_root / 'portable_tools' / 'ffmpeg' / 'bin' / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'),
        project_root / 'portable_tools' / 'ffmpeg' / 'bin' / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe'),
        project_root / 'portable_tools' / 'pandoc' / 'bin' / ('pandoc.exe' if os.name == 'nt' else 'pandoc'),
        project_root / 'portable_tools' / 'libreoffice' / 'program' / ('soffice.exe' if os.name == 'nt' else 'soffice')
    ]
    
    missing = [str(f) for f in required_files if not f.exists()]
    
    if missing:
        print("Error: Some required bundled tools are missing:")
        for file in missing:
            print(f"  - {file}")
        print("\nPlease make sure all required tools are in the portable_tools directory.")
        return False
    
    return True

def build_executable():
    """Build the executable using PyInstaller"""
    project_root = Path(__file__).parent.parent
    spec_file = project_root / 'universal-converter.spec'
    
    print("Building executable with PyInstaller...")
    
    try:
        result = subprocess.run(
            ['pyinstaller', str(spec_file), '--clean'],
            check=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\nBuild successful!")
            print(f"Executable created in {project_root / 'dist' / 'universal-converter.exe'}")
        else:
            print("\nBuild failed.")
            
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {str(e)}")
    except FileNotFoundError:
        print("\nError: PyInstaller not found. Please install it with 'pip install pyinstaller'.")

def main():
    if not check_bundled_tools():
        return 1
        
    build_executable()
    return 0

if __name__ == "__main__":
    sys.exit(main())