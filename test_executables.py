# test_executables.py
import subprocess
from pathlib import Path
import sys

def test_executable(name, path):
    print(f"\nTesting {name}: {path}")
    print(f"File exists: {Path(path).exists()}")
    
    try:
        # Try running with version flag
        if name == "ffmpeg":
            cmd = [path, "-version"]
        elif name == "pandoc":
            cmd = [path, "--version"]
        elif name == "libreoffice":
            cmd = [path, "--version"]
        
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=10,  # Set a timeout in case it hangs
            text=True
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Output first 100 chars: {result.stdout[:100]}")
        
        if result.stderr:
            print(f"Error output: {result.stderr[:100]}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("ERROR: Process timed out after 10 seconds")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        return False

# Define paths to executables
project_root = Path.cwd()
ffmpeg_path = str(project_root / "portable_tools" / "ffmpeg" / "bin" / "ffmpeg.exe")
pandoc_path = str(project_root / "portable_tools" / "pandoc" / "bin" / "pandoc.exe")
libreoffice_path = str(project_root / "portable_tools" / "libreoffice" / "program" / "soffice.exe")

# Test each executable
print("Testing portable executables...")
ffmpeg_ok = test_executable("ffmpeg", ffmpeg_path)
pandoc_ok = test_executable("pandoc", pandoc_path)
libreoffice_ok = test_executable("libreoffice", libreoffice_path)

# Summary
print("\n--- Summary ---")
print(f"FFmpeg: {'OK' if ffmpeg_ok else 'FAILED'}")
print(f"Pandoc: {'OK' if pandoc_ok else 'FAILED'}")
print(f"LibreOffice: {'OK' if libreoffice_ok else 'FAILED'}")