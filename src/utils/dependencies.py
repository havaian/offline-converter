# src/utils/dependencies.py
import os
import sys
import shutil
from pathlib import Path
import subprocess

def find_project_root():
    """Find the project root by locating the portable_tools directory"""
    # Start from current working directory
    current_dir = Path.cwd()
    
    # First, check current directory
    if (current_dir / 'portable_tools').exists():
        return current_dir
        
    # Check parent directories (up to 3 levels)
    for _ in range(3):
        if current_dir.parent == current_dir:  # We're at the root
            break
        current_dir = current_dir.parent
        if (current_dir / 'portable_tools').exists():
            return current_dir
            
    # Check the directory of the script
    script_dir = Path(__file__).parent.parent.parent
    if (script_dir / 'portable_tools').exists():
        return script_dir
    
    # If frozen with PyInstaller
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
        
    # Fallback to cwd
    return Path.cwd()

def get_ffmpeg_path():
    """Get path to FFmpeg executable"""
    project_root = find_project_root()
    ffmpeg_path = project_root / 'portable_tools' / 'ffmpeg' / 'bin' / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    return ffmpeg_path if ffmpeg_path.exists() else None

def get_pandoc_path():
    """Get path to Pandoc executable"""
    project_root = find_project_root()
    pandoc_path = project_root / 'portable_tools' / 'pandoc' / 'bin' / ('pandoc.exe' if os.name == 'nt' else 'pandoc')
    return pandoc_path if pandoc_path.exists() else None

def get_libreoffice_path():
    """Get path to LibreOffice executable"""
    project_root = find_project_root()
    
    # Log all search paths for debugging
    print(f"Searching for LibreOffice in portable_tools directory")
    
    # Try all possible locations for LibreOffice portable
    possible_paths = [
        # Standard path
        project_root / 'portable_tools' / 'libreoffice' / 'program' / 'soffice.exe',
        # Portable structure
        project_root / 'portable_tools' / 'libreoffice' / 'App' / 'libreoffice' / 'program' / 'soffice.exe',
        # Alternate portable structure
        project_root / 'portable_tools' / 'LibreOfficePortable' / 'App' / 'libreoffice' / 'program' / 'soffice.exe'
    ]
    
    # Check if the file exists at each path
    for path in possible_paths:
        print(f"Checking path: {path}")
        print(f"Path exists: {path.exists()}")
        if path.exists():
            return path
    
    # If no path exists, return None
    return None

def run_subprocess_without_window(cmd, timeout=2):
    """Run subprocess without showing a window and with timeout"""
    startupinfo = None
    
    if os.name == 'nt':
        # Hide the console window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
    
    try:
        # For LibreOffice, just check existence instead of running
        if 'soffice' in str(cmd[0]).lower():
            # Simply check if the executable exists
            if os.path.exists(cmd[0]):
                return {
                    'returncode': 0,
                    'stdout': 'LibreOffice found (existence check only)',
                    'stderr': ''
                }
            else:
                return {
                    'returncode': 1,
                    'stdout': '',
                    'stderr': 'LibreOffice executable not found'
                }
        
        # For other tools, run with timeout
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            timeout=timeout,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': 'Process timed out'
        }
    except Exception as e:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e)
        }

def check_dependencies():
    """
    Check if all required external tools are available.
    
    Returns:
        dict: Status of each dependency
    """
    project_root = find_project_root()
    print(f"Project root: {project_root}")
    results = {}
    
    # Check FFmpeg
    ffmpeg_path = get_tool_path('ffmpeg')
    if ffmpeg_path:
        print(f"FFmpeg path: {ffmpeg_path}")
        try:
            result = run_subprocess_without_window([str(ffmpeg_path), '-version'])
            results['ffmpeg'] = {
                'available': result['returncode'] == 0,
                'path': str(ffmpeg_path),
                'version': result['stdout'].split('\n')[0] if result['returncode'] == 0 else None
            }
        except Exception as e:
            print(f"Error checking FFmpeg: {e}")
            results['ffmpeg'] = {'available': False, 'path': str(ffmpeg_path), 'version': None}
    else:
        print("FFmpeg path not found")
        results['ffmpeg'] = {'available': False, 'path': None, 'version': None}
    
    # Check Pandoc
    pandoc_path = get_tool_path('pandoc')
    if pandoc_path:
        print(f"Pandoc path: {pandoc_path}")
        try:
            result = run_subprocess_without_window([str(pandoc_path), '--version'])
            results['pandoc'] = {
                'available': result['returncode'] == 0,
                'path': str(pandoc_path),
                'version': result['stdout'].split('\n')[0] if result['returncode'] == 0 else None
            }
        except Exception as e:
            print(f"Error checking Pandoc: {e}")
            results['pandoc'] = {'available': False, 'path': str(pandoc_path), 'version': None}
    else:
        print("Pandoc path not found")
        results['pandoc'] = {'available': False, 'path': None, 'version': None}
    
    # Check LibreOffice
    libreoffice_path = get_tool_path('libreoffice')
    if libreoffice_path:
        print(f"LibreOffice path: {libreoffice_path}")
        
        # For LibreOffice, just check if the file exists rather than running it
        results['libreoffice'] = {
            'available': True,  # If path exists, consider it available
            'path': str(libreoffice_path),
            'version': "LibreOffice (version check skipped)"
        }
    else:
        print("LibreOffice path not found")
        results['libreoffice'] = {'available': False, 'path': None, 'version': None}
        
    return results

def get_tool_path(tool_name):
    """
    Get path to tool in portable_tools directory
    
    Args:
        tool_name: Name of the tool ('ffmpeg', 'pandoc', 'libreoffice')
        
    Returns:
        Path to executable or None if not found
    """
    if tool_name == 'ffmpeg':
        return get_ffmpeg_path()
    elif tool_name == 'pandoc':
        return get_pandoc_path()
    elif tool_name == 'libreoffice':
        return get_libreoffice_path()
    return None