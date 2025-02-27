# find_libreoffice.py
import os
from pathlib import Path
import subprocess

def check_path(path, description):
    print(f"Checking {description}: {path}")
    exists = path.exists()
    print(f"  Exists: {exists}")
    
    if exists:
        try:
            result = subprocess.run(
                [str(path), '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=5
            )
            print(f"  Return code: {result.returncode}")
            if result.stdout:
                print(f"  Output: {result.stdout[:100]}")
            if result.stderr:
                print(f"  Error: {result.stderr[:100]}")
            return True
        except Exception as e:
            print(f"  Error running: {e}")
    
    return False

# Start from current directory
project_root = Path.cwd()
print(f"Project root: {project_root}")

# Find LibreOffice Portable files
print("\nSearching for LibreOffice Portable files...")
found = False

# Look for portable executable launchers
portable_exes = [
    'LibreOfficePortable.exe',
    'LibreOfficeWriterPortable.exe',
    'LibreOfficeCalcPortable.exe',
    'LibreOfficeBasePortable.exe'
]

for exe in portable_exes:
    for search_path in [
        project_root,
        project_root / 'portable_tools',
        project_root / 'portable_tools' / 'libreoffice'
    ]:
        path = search_path / exe
        if path.exists():
            print(f"\nFound portable launcher: {path}")
            
            # Try to find the actual soffice.exe
            app_dir = path.parent / 'App'
            if app_dir.exists():
                print(f"App directory exists: {app_dir}")
                
                # Check standard LibreOffice portable structure
                soffice_path = app_dir / 'libreoffice' / 'program' / 'soffice.exe'
                if check_path(soffice_path, "soffice.exe in standard location"):
                    found = True
                
                # Try alternate locations
                for alt_path in [
                    app_dir / 'program' / 'soffice.exe',
                    app_dir / 'soffice.exe'
                ]:
                    if check_path(alt_path, "soffice.exe in alternate location"):
                        found = True

# Check standard paths in portable_tools
standard_paths = [
    project_root / 'portable_tools' / 'libreoffice' / 'program' / 'soffice.exe',
    project_root / 'portable_tools' / 'libreoffice' / 'App' / 'libreoffice' / 'program' / 'soffice.exe',
    project_root / 'portable_tools' / 'LibreOfficePortable' / 'App' / 'libreoffice' / 'program' / 'soffice.exe'
]

for path in standard_paths:
    if check_path(path, "Standard path"):
        found = True

# Check system-installed LibreOffice
if os.name == 'nt':
    for program_files in ['C:\\Program Files', 'C:\\Program Files (x86)']:
        path = Path(program_files) / 'LibreOffice' / 'program' / 'soffice.exe'
        if check_path(path, "System installation"):
            found = True

# Summary
print("\nSummary:")
if found:
    print("LibreOffice was found in at least one location.")
else:
    print("LibreOffice was not found in any expected location.")
    print("\nTo fix this:")
    print("1. Install LibreOffice Portable from PortableApps.com")
    print("2. Copy the entire LibreOfficePortable folder to portable_tools/ in your project")
    print("3. Update dependencies.py to look for: portable_tools/LibreOfficePortable/App/libreoffice/program/soffice.exe")