# src/utils/tool_downloader.py
import os
import sys
import platform
import requests
import zipfile
import tarfile
import shutil
from pathlib import Path
import subprocess
import json
from typing import Dict, List, Optional, Callable, Tuple
import threading

# Tool version information - can be updated as new versions are released
TOOL_VERSIONS = {
    'ffmpeg': {
        'version': '7.0.2',
        'windows': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
        'darwin': 'https://evermeet.cx/ffmpeg/ffmpeg-7.0.2.zip',
        'linux': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz'
    },
    'pandoc': {
        'version': '3.6.3',
        'windows': 'https://github.com/jgm/pandoc/releases/download/3.6.3/pandoc-3.6.3-windows-x86_64.zip',
        'darwin': 'https://github.com/jgm/pandoc/releases/download/3.6.3/pandoc-3.6.3-macOS.zip',
        'linux': 'https://github.com/jgm/pandoc/releases/download/3.6.3/pandoc-3.6.3-linux-amd64.tar.gz'
    },
    'libreoffice': {
        'version': '25.2.1',
        # Direct links to the official LibreOffice downloads
        'windows': 'https://sourceforge.net/projects/portableapps/files/LibreOffice%20Portable/LibreOfficePortableLegacy75_7.5.9_MultilingualStandard.paf.exe/download',
        'darwin': 'https://www.libreoffice.org/donate/dl/mac-x86_64/25.2.1/en-US/LibreOffice_25.2.1_MacOS_x86-64.dmg',
        'linux': 'https://www.libreoffice.org/donate/dl/deb-x86_64/25.2.1/en-US/LibreOffice_25.2.1_Linux_x86-64_deb.tar.gz'
    }
}

# Thread-local storage for download operations
_local = threading.local()

def get_platform() -> str:
    """Get the current platform identifier."""
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'darwin'
    else:
        return 'linux'

def get_project_root() -> Path:
    """Find the project root directory."""
    # Start from the directory of this script
    current_dir = Path(__file__).resolve().parent
    
    # Walk up until we find the root (where src/ is)
    while current_dir.name != 'src' and current_dir.parent != current_dir:
        current_dir = current_dir.parent
    
    # If we found src/, return its parent
    if current_dir.name == 'src':
        return current_dir.parent
    
    # Fallback to current working directory
    return Path.cwd()

def ensure_directories() -> Tuple[Path, Path]:
    """Ensure the necessary directories exist."""
    project_root = get_project_root()
    tools_dir = project_root / 'portable_tools'
    temp_dir = project_root / 'temp'
    
    tools_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    return tools_dir, temp_dir

def download_and_setup_tool(tool_name: str, progress_callback: Optional[Callable[[str, int], None]] = None) -> bool:
    """
    Download and set up a specific tool.
    
    Args:
        tool_name: Name of the tool to download ('ffmpeg', 'pandoc', 'libreoffice')
        progress_callback: Optional callback function(stage, percentage) for progress updates
        
    Returns:
        bool: True if the tool was successfully set up
    """
    platform_name = get_platform()
    
    # Check if tool is supported for this platform
    if tool_name not in TOOL_VERSIONS:
        print(f"Unknown tool: {tool_name}")
        return False
    
    if platform_name not in TOOL_VERSIONS[tool_name]:
        print(f"{tool_name} is not supported on {platform_name}")
        return False
    
    # Get download URL
    url = TOOL_VERSIONS[tool_name][platform_name]
    
    # Setup directories
    tools_dir, temp_dir = ensure_directories()
    tool_dir = tools_dir / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    
    # Temporary extraction directory
    extract_dir = temp_dir / tool_name
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine archive filename from URL
    archive_filename = url.split('/')[-1]
    download_path = temp_dir / archive_filename
    
    # Progress tracking for callbacks
    if progress_callback:
        progress_callback("download", 0)
    
    # 1. Download
    download_success = download_file(
        url, 
        download_path, 
        lambda current, total: progress_callback("download", int(current * 100 / total)) 
        if progress_callback and total > 0 else None
    )
    
    if not download_success:
        return False
    
    # 2. Extract
    if progress_callback:
        progress_callback("extract", 0)
    
    
    
    # Download
    actual_download_path = download_file(
        url, 
        download_path, 
        lambda current, total: progress_callback("download", int(current * 100 / total)) 
        if progress_callback and total > 0 else None
    )
    
    if actual_download_path is None:  # Check for None, not False
        return False
    
    # Extract - use the actual_download_path, not download_path
    extract_success = extract_archive(
        actual_download_path,  # Use the path returned from download_file
        extract_dir,
        lambda current, total: progress_callback("extract", int(current * 100 / total)) 
        if progress_callback and total > 0 else None
    )
    
    if not extract_success:
        return False
    
    # 3. Organize
    if progress_callback:
        progress_callback("organize", 0)
    
    organize_success = False
    if tool_name == 'ffmpeg':
        organize_success = organize_ffmpeg(extract_dir, tool_dir)
    elif tool_name == 'pandoc':
        organize_success = organize_pandoc(extract_dir, tool_dir)
    elif tool_name == 'libreoffice':
        organize_success = organize_libreoffice(extract_dir, tool_dir)
    
    if progress_callback:
        progress_callback("organize", 100 if organize_success else 0)
    
    # 4. Clean up
    try:
        if download_path.exists():
            download_path.unlink()
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
    except Exception as e:
        print(f"Warning: Cleanup error: {str(e)}")
    
    # 5. Save version info
    if organize_success:
        version_file = tool_dir / "version.json"
        
        # Use a valid date format instead of Path.ctime
        import datetime
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(version_file, 'w') as f:
            json.dump({
                "version": TOOL_VERSIONS[tool_name]["version"],
                "platform": platform_name,
                "install_date": current_date
            }, f)
    
    return organize_success

# Add MSI extraction capability for LibreOffice
def extract_archive(archive_path: Path, target_dir: Path, 
                   progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
    """
    Extract an archive file.
    
    Args:
        archive_path: Path to the archive file
        target_dir: Directory where to extract files
        progress_callback: Optional callback function(current, total) for progress
        
    Returns:
        bool: True if extraction was successful
    """
    try:
        print(f"Extracting file: {archive_path}")
        
        # Handle .paf.exe files (PortableApps format)
        if str(archive_path).lower().endswith('.paf.exe'):
            print(f"Detected PortableApps installer: {archive_path}")
            
            # Try to find 7-Zip
            seven_zip_path = None
            possible_7z_paths = [
                "C:\\Program Files\\7-Zip\\7z.exe",
                "C:\\Program Files (x86)\\7-Zip\\7z.exe",
                shutil.which("7z")
            ]
            
            for path in possible_7z_paths:
                if path and Path(path).exists():
                    seven_zip_path = path
                    break
            
            if seven_zip_path:
                print(f"Using 7-Zip at {seven_zip_path} to extract {archive_path}")
                
                try:
                    # Extract using 7-Zip
                    cmd = [
                        seven_zip_path,
                        'x',  # Extract with full paths
                        str(archive_path),
                        f'-o{target_dir}',  # Output directory
                        '-y'  # Yes to all prompts
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if result.returncode != 0:
                        print(f"7-Zip extraction failed: {result.stderr}")
                    else:
                        print(f"7-Zip extraction completed successfully")
                        return True
                        
                except Exception as e:
                    print(f"Error using 7-Zip: {str(e)}")
            
            # If 7-Zip not available or failed, try to execute the installer
            print(f"Attempting to run the installer {archive_path} in silent mode")
            try:
                # Create a directory for the extraction
                portable_dir = target_dir / "LibreOfficePortable"
                portable_dir.mkdir(exist_ok=True)
                
                cmd = [
                    str(archive_path),
                    f'/DESTINATION={portable_dir}',
                    '/SILENT'
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                # Check if files were extracted
                if list(portable_dir.glob('*')):
                    print(f"Installer appears to have extracted files to {portable_dir}")
                    return True
                else:
                    print(f"Installer did not extract files to {portable_dir}")
                    return False
                
            except Exception as e:
                print(f"Error executing installer: {str(e)}")
                return False
        
        # Handle MSI files for Windows
        elif archive_path.suffix.lower() == '.msi':
            import tempfile
            print(f"Extracting MSI file: {archive_path}")
            
            # Create a temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_extract_dir:
                temp_path = Path(temp_extract_dir)
                
                # Use msiexec to extract the MSI file
                cmd = [
                    'msiexec', 
                    '/a', str(archive_path), 
                    '/qb', 
                    f'TARGETDIR={temp_path}'
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                
                try:
                    # Execute the MSI extraction
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if result.returncode != 0:
                        print(f"MSI extraction failed: {result.stderr}")
                        return False
                        
                    # Copy extracted contents to the target directory
                    print(f"MSI extraction succeeded. Copying from {temp_path} to {target_dir}")
                    
                    # Copy contents
                    for item in temp_path.glob('*'):
                        try:
                            if item.is_file():
                                shutil.copy2(item, target_dir / item.name)
                            elif item.is_dir():
                                shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
                        except Exception as copy_error:
                            print(f"Error copying {item}: {copy_error}")
                    
                    if progress_callback:
                        progress_callback(100, 100)  # Indicate completion
                        
                    return True
                    
                except Exception as msi_error:
                    print(f"Error during MSI extraction: {msi_error}")
                    return False
        
        # Handle standard archive formats
        elif archive_path.suffix.lower() == '.zip' or archive_path.name.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Get total size for progress reporting
                total_size = sum(file.file_size for file in zip_ref.filelist)
                extracted_size = 0
                
                # Extract files one by one for progress reporting
                for file in zip_ref.filelist:
                    zip_ref.extract(file, target_dir)
                    extracted_size += file.file_size
                    
                    if progress_callback and total_size > 0:
                        progress_callback(extracted_size, total_size)
                        
                print(f"Zip extraction completed: {len(zip_ref.filelist)} files extracted to {target_dir}")
            return True
        
        elif archive_path.name.lower().endswith('.tar.gz') or archive_path.name.lower().endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                members = tar_ref.getmembers()
                total_members = len(members)
                for i, member in enumerate(members):
                    tar_ref.extract(member, target_dir)
                    if progress_callback and total_members > 0:
                        progress_callback(i+1, total_members)
                        
                print(f"Tar.gz extraction completed: {total_members} files extracted to {target_dir}")
            return True
        
        elif archive_path.name.lower().endswith('.tar.xz'):
            with tarfile.open(archive_path, 'r:xz') as tar_ref:
                members = tar_ref.getmembers()
                total_members = len(members)
                for i, member in enumerate(members):
                    tar_ref.extract(member, target_dir)
                    if progress_callback and total_members > 0:
                        progress_callback(i+1, total_members)
                        
                print(f"Tar.xz extraction completed: {total_members} files extracted to {target_dir}")
            return True
        
        elif archive_path.name.lower().endswith('.dmg') and sys.platform == 'darwin':
            # Handle DMG files on macOS using hdiutil
            print("DMG handling not implemented yet")
            return False
        
        else:
            print(f"Unsupported archive format: {archive_path}")
            return False
        
    except Exception as e:
        print(f"Error extracting {archive_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def organize_ffmpeg(extract_dir: Path, target_dir: Path) -> bool:
    """
    Organize FFmpeg files into the expected structure.
    
    Args:
        extract_dir: Directory where files were extracted
        target_dir: Target directory for organized files
        
    Returns:
        bool: True if successful
    """
    try:
        # Create bin directory
        bin_dir = target_dir / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        # Find the FFmpeg executables in the extracted directory
        platform_name = get_platform()
        found_executables = False
        
        # Different archive structures based on platform
        if platform_name == 'windows':
            # Windows builds typically have bin/ in a nested directory
            for root, dirs, files in os.walk(extract_dir):
                if 'bin' in dirs:
                    bin_path = Path(root) / 'bin'
                    for exe in ['ffmpeg.exe', 'ffprobe.exe']:
                        if (bin_path / exe).exists():
                            shutil.copy2(bin_path / exe, bin_dir / exe)
                            found_executables = True
                
                # Some archives may have executables directly in a directory
                for exe in ['ffmpeg.exe', 'ffprobe.exe']:
                    matches = list(Path(root).glob(f"**/{exe}"))
                    if matches:
                        for src_path in matches:
                            dst_path = bin_dir / exe
                            shutil.copy2(src_path, dst_path)
                            found_executables = True
        
        elif platform_name in ['darwin', 'linux']:
            # Mac/Linux builds might have executables directly in the archive
            for root, dirs, files in os.walk(extract_dir):
                for exe in ['ffmpeg', 'ffprobe']:
                    for file in files:
                        if file == exe or file.startswith(exe):
                            src_path = Path(root) / file
                            dst_path = bin_dir / exe
                            shutil.copy2(src_path, dst_path)
                            # Make sure the files are executable
                            os.chmod(dst_path, 0o755)
                            found_executables = True
        
        return found_executables
    
    except Exception as e:
        print(f"Error organizing FFmpeg: {str(e)}")
        return False

def organize_pandoc(extract_dir: Path, target_dir: Path) -> bool:
    """
    Organize Pandoc files into the expected structure.
    
    Args:
        extract_dir: Directory where files were extracted
        target_dir: Target directory for organized files
        
    Returns:
        bool: True if successful
    """
    try:
        # Create bin directory
        bin_dir = target_dir / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        platform_name = get_platform()
        found_executable = False
        
        # Find pandoc executable
        pandoc_exe = 'pandoc.exe' if platform_name == 'windows' else 'pandoc'
        
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == pandoc_exe:
                    # Found the executable
                    src_path = Path(root) / file
                    dst_path = bin_dir / file
                    shutil.copy2(src_path, dst_path)
                    
                    # Make executable on Unix
                    if platform_name != 'windows':
                        os.chmod(dst_path, 0o755)
                    
                    found_executable = True
        
        return found_executable
    
    except Exception as e:
        print(f"Error organizing Pandoc: {str(e)}")
        return False

def organize_libreoffice(extract_dir: Path, target_dir: Path) -> bool:
    """
    Organize LibreOffice files into the expected structure.
    
    Args:
        extract_dir: Directory where files were extracted
        target_dir: Target directory for organized files
        
    Returns:
        bool: True if successful
    """
    try:
        platform_name = get_platform()
        success = False
        
        # Create program directory
        program_dir = target_dir / 'program'
        program_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Organizing LibreOffice from {extract_dir} to {target_dir}")
        print(f"Platform: {platform_name}")
        
        # Log the directory contents for debugging
        print("Extract directory contents:")
        
        # Just list the top-level directories instead of trying depth-limited traversal
        print(f"Top-level directories in {extract_dir}:")
        for item in extract_dir.iterdir():
            if item.is_dir():
                print(f"  Directory: {item.name}")
                # List first level of subdirectories
                subdirs = [subitem.name for subitem in item.iterdir() if subitem.is_dir()]
                if subdirs:
                    print(f"    Subdirectories: {', '.join(subdirs[:5])}" + ("..." if len(subdirs) > 5 else ""))
        
        if platform_name == 'windows':
            # For Windows, look for LibreOfficePortable structure
            # First look for the App directory which is standard in PortableApps
            app_dirs = list(extract_dir.glob('**/App'))
            if app_dirs:
                print(f"Found App directory: {app_dirs[0]}")
                # Look for LibreOffice program directory
                program_paths = list(app_dirs[0].glob('**/program'))
                
                if program_paths:
                    source_program_dir = program_paths[0]
                    print(f"Found program directory: {source_program_dir}")
                    
                    # Look for soffice.exe
                    if (source_program_dir / 'soffice.exe').exists():
                        print(f"Found soffice.exe in {source_program_dir}")
                        
                        # Copy all files from program directory
                        for item in source_program_dir.glob('*'):
                            try:
                                if item.is_file():
                                    print(f"Copying file: {item.name}")
                                    shutil.copy2(item, program_dir / item.name)
                                elif item.is_dir():
                                    print(f"Copying directory: {item.name}")
                                    shutil.copytree(item, program_dir / item.name, dirs_exist_ok=True)
                            except Exception as e:
                                print(f"Error copying {item}: {e}")
                        
                        success = True
            
            # If App directory not found, search directly for soffice.exe
            if not success:
                soffice_paths = list(extract_dir.glob('**/soffice.exe'))
                if soffice_paths:
                    soffice_path = soffice_paths[0]
                    soffice_dir = soffice_path.parent
                    
                    print(f"Found soffice.exe at: {soffice_path}")
                    
                    # Copy all files from this directory
                    for item in soffice_dir.glob('*'):
                        try:
                            if item.is_file():
                                print(f"Copying file: {item.name}")
                                shutil.copy2(item, program_dir / item.name)
                            elif item.is_dir():
                                print(f"Copying directory: {item.name}")
                                shutil.copytree(item, program_dir / item.name, dirs_exist_ok=True)
                        except Exception as e:
                            print(f"Error copying {item}: {e}")
                    
                    success = True
        
        # Final check: Verify that we've successfully set up the expected structure
        if platform_name == 'windows':
            success = (program_dir / 'soffice.exe').exists()
        elif platform_name in ['darwin', 'linux']:
            success = (program_dir / 'soffice').exists()
            
        if success:
            print(f"Successfully organized LibreOffice to {target_dir}")
        else:
            print(f"Failed to organize LibreOffice to {target_dir}")
            
            # More specific debugging - check the full structure
            print("\nDetailed directory listing to help diagnose the issue:")
            for root, dirs, files in os.walk(extract_dir):
                print(f"Directory: {root}")
                if len(files) > 0:
                    print(f"  Files: {', '.join(files[:5])}" + ("..." if len(files) > 5 else ""))
                if len(dirs) > 0:
                    print(f"  Subdirs: {', '.join(dirs)}")
        
        return success
            
    except Exception as e:
        print(f"Error organizing LibreOffice: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
           
def download_file(url: str, target_path: Path, 
                 progress_callback: Optional[Callable[[int, int], None]] = None,
                 max_retries: int = 3,
                 force_download: bool = False) -> Optional[Path]:
    """
    Download a file with progress reporting and retry support.
    
    Args:
        url: URL to download from
        target_path: Path where to save the file
        progress_callback: Optional callback function(current, total) to report progress
        max_retries: Maximum number of retry attempts
        force_download: If True, always download even if file exists
        
    Returns:
        Optional[Path]: Path to the downloaded file or None if failed
    """
    # Check if we need to adjust the filename (for SourceForge downloads)
    file_path = target_path
    if "sourceforge.net" in url and "libreoffice" in url.lower():
        # Extract a better filename from the URL
        for part in url.split('/'):
            if "libreofficeportable" in part.lower() and ".paf.exe" in part.lower():
                file_path = target_path.parent / part
                break
    
    # Check if file already exists
    if not force_download and file_path.exists():
        file_size = file_path.stat().st_size
        if file_size > 0:  # Make sure it's not an empty file
            print(f"File already exists: {file_path} ({file_size} bytes)")
            if progress_callback:
                progress_callback(100, 100)  # Indicate completion
            return file_path
    
    # If file doesn't exist or force_download is True, proceed with download
    for attempt in range(max_retries):
        try:
            print(f"Downloading {url} (attempt {attempt + 1}/{max_retries})...")
            
            # Use a session to better handle connections
            session = requests.Session()
            # Set a reasonable timeout
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            block_size = 1024 * 1024  # 1MB
            
            with open(file_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)
            
            # Verify the download is complete
            if total_size > 0 and downloaded != total_size:
                print(f"Warning: Download size mismatch. Expected {total_size}, got {downloaded}.")
                if attempt < max_retries - 1:
                    print("Retrying download...")
                    continue
            
            print(f"Download completed successfully: {file_path}")
            return file_path
        
        except requests.exceptions.RequestException as e:
            print(f"Download error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print("Retrying in 2 seconds...")
                import time
                time.sleep(2)
            else:
                print(f"Failed to download after {max_retries} attempts: {url}")
                return None
        except Exception as e:
            print(f"Unexpected error during download: {str(e)}")
            return None
    
    return None
     
def get_installed_version(tool_name: str) -> Optional[str]:
    """
    Get the installed version of a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Optional[str]: Version string or None if not installed or version info not available
    """
    project_root = get_project_root()
    version_file = project_root / 'portable_tools' / tool_name / "version.json"
    
    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get("version")
        except Exception:
            pass
    
    return None

def check_for_updates() -> Dict[str, Dict]:
    """
    Check for available updates for installed tools.
    
    Returns:
        Dict[str, Dict]: Dictionary with update information for each tool
    """
    updates = {}
    
    for tool_name in TOOL_VERSIONS:
        installed_version = get_installed_version(tool_name)
        latest_version = TOOL_VERSIONS[tool_name]["version"]
        
        if installed_version:
            updates[tool_name] = {
                "installed": installed_version,
                "latest": latest_version,
                "update_available": installed_version != latest_version
            }
        else:
            updates[tool_name] = {
                "installed": None,
                "latest": latest_version,
                "update_available": False
            }
    
    return updates

def download_all_tools(progress_callback: Optional[Callable[[str, str, int], None]] = None) -> Dict[str, bool]:
    """
    Download and set up all tools.
    
    Args:
        progress_callback: Optional callback function(tool_name, stage, percentage)
        
    Returns:
        Dict[str, bool]: Dictionary with success status for each tool
    """
    results = {}
    
    for tool_name in TOOL_VERSIONS:
        if progress_callback:
            progress_callback(tool_name, "start", 0)
        
        success = download_and_setup_tool(
            tool_name,
            lambda stage, percentage: progress_callback(tool_name, stage, percentage) 
            if progress_callback else None
        )
        
        results[tool_name] = success
        
        if progress_callback:
            progress_callback(tool_name, "complete", 100 if success else 0)
    
    return results

def main():
    """Main function when run as a script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download and set up converter tools")
    parser.add_argument("--tool", choices=["ffmpeg", "pandoc", "libreoffice", "all"],
                       default="all", help="Tool to download (default: all)")
    parser.add_argument("--check-updates", action="store_true", 
                       help="Check for available updates")
    
    args = parser.parse_args()
    
    if args.check_updates:
        updates = check_for_updates()
        print("\nAvailable Updates:")
        for tool, info in updates.items():
            if info["installed"]:
                status = f"v{info['installed']} → v{info['latest']}" if info["update_available"] else "Up to date"
            else:
                status = "Not installed"
            print(f"{tool.capitalize()}: {status}")
        return
    
    # Progress callback for terminal output
    def terminal_progress(tool_name, stage, percentage):
        print(f"{tool_name} - {stage}: {percentage}%")
    
    if args.tool == "all":
        results = download_all_tools(lambda t, s, p: terminal_progress(t, s, p))
        
        print("\nDownload Results:")
        for tool, success in results.items():
            print(f"{tool.capitalize()}: {'Success' if success else 'Failed'}")
    else:
        success = download_and_setup_tool(
            args.tool,
            lambda stage, percentage: terminal_progress(args.tool, stage, percentage)
        )
        print(f"\n{args.tool.capitalize()}: {'Success' if success else 'Failed'}")

if __name__ == "__main__":
    main()