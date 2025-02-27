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
        'version': '6.0',
        'windows': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
        'darwin': 'https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip',
        'linux': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz'
    },
    'pandoc': {
        'version': '3.1.9',
        'windows': 'https://github.com/jgm/pandoc/releases/download/3.1.9/pandoc-3.1.9-windows-x86_64.zip',
        'darwin': 'https://github.com/jgm/pandoc/releases/download/3.1.9/pandoc-3.1.9-macOS.zip',
        'linux': 'https://github.com/jgm/pandoc/releases/download/3.1.9/pandoc-3.1.9-linux-amd64.tar.gz'
    },
    'libreoffice': {
        'version': '7.6.4',
        # For Windows, use the MSI installer which is more reliable to extract from
        'windows': 'https://download.documentfoundation.org/libreoffice/stable/7.6.4/win/x86_64/LibreOffice_7.6.4_Win_x64.msi',
        'darwin': 'https://download.documentfoundation.org/libreoffice/stable/7.6.4/mac/x86_64/LibreOffice_7.6.4_MacOS_x86-64.dmg',
        'linux': 'https://download.documentfoundation.org/libreoffice/stable/7.6.4/linux/x86_64/LibreOffice_7.6.4_Linux_x86-64_portable.tar.gz'
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

# Improve download function with better error handling and retries
def download_file(url: str, target_path: Path, 
                 progress_callback: Optional[Callable[[int, int], None]] = None,
                 max_retries: int = 3) -> bool:
    """
    Download a file with progress reporting and retry support.
    
    Args:
        url: URL to download from
        target_path: Path where to save the file
        progress_callback: Optional callback function(current, total) to report progress
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if download was successful
    """
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
            
            with open(target_path, 'wb') as f:
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
            
            print(f"Download completed successfully: {target_path}")
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"Download error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print("Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"Failed to download after {max_retries} attempts: {url}")
                return False
        except Exception as e:
            print(f"Unexpected error during download: {str(e)}")
            return False
    
    return False

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
        # Handle MSI files for Windows
        if archive_path.suffix.lower() == '.msi':
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
        if archive_path.suffix.lower() == '.zip' or archive_path.name.lower().endswith('.zip'):
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
        
        elif archive_path.name.lower().endswith('.tar.gz') or archive_path.name.lower().endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                members = tar_ref.getmembers()
                total_members = len(members)
                for i, member in enumerate(members):
                    tar_ref.extract(member, target_dir)
                    if progress_callback and total_members > 0:
                        progress_callback(i+1, total_members)
                        
                print(f"Tar.gz extraction completed: {total_members} files extracted to {target_dir}")
        
        elif archive_path.name.lower().endswith('.tar.xz'):
            with tarfile.open(archive_path, 'r:xz') as tar_ref:
                members = tar_ref.getmembers()
                total_members = len(members)
                for i, member in enumerate(members):
                    tar_ref.extract(member, target_dir)
                    if progress_callback and total_members > 0:
                        progress_callback(i+1, total_members)
                        
                print(f"Tar.xz extraction completed: {total_members} files extracted to {target_dir}")
        
        elif archive_path.name.lower().endswith('.dmg') and sys.platform == 'darwin':
            # Handle DMG files on macOS using hdiutil
            print("DMG handling not implemented yet")
            return False
        
        else:
            print(f"Unsupported archive format: {archive_path}")
            return False
        
        return True
    
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
        
        if platform_name == 'windows':
            # For Windows, we need to handle different portable formats
            
            # Case 1: PortableApps format (LibreOfficePortable directory)
            if (extract_dir / 'LibreOfficePortable').exists():
                portable_dir = extract_dir / 'LibreOfficePortable'
                # Copy the program directory
                if (portable_dir / 'App' / 'libreoffice' / 'program').exists():
                    program_src = portable_dir / 'App' / 'libreoffice' / 'program'
                    program_dst = target_dir / 'program'
                    
                    # Create program directory if needed
                    program_dst.mkdir(parents=True, exist_ok=True)
                    
                    # Copy all files from program directory
                    for item in program_src.glob('*'):
                        if item.is_file():
                            shutil.copy2(str(item), str(program_dst / item.name))
                        elif item.is_dir():
                            shutil.copytree(str(item), str(program_dst / item.name), dirs_exist_ok=True)
                    
                    success = True
            
            # Case 2: Direct extraction of portable .paf.exe file
            if not success:
                # Look for the soffice.exe in any nested directory
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower() == 'soffice.exe':
                            # Found soffice.exe, get its directory
                            source_dir = Path(root)
                            program_dst = target_dir / 'program'
                            program_dst.mkdir(parents=True, exist_ok=True)
                            
                            # Copy soffice.exe and essential files
                            shutil.copy2(str(source_dir / file), str(program_dst / file))
                            
                            # Copy directory contents if possible
                            for item in source_dir.glob('*'):
                                if item.is_file() and item.name != file:  # Skip the already copied exe
                                    try:
                                        shutil.copy2(str(item), str(program_dst / item.name))
                                    except Exception as e:
                                        print(f"Error copying {item}: {e}")
                                elif item.is_dir():
                                    try:
                                        shutil.copytree(str(item), str(program_dst / item.name), dirs_exist_ok=True)
                                    except Exception as e:
                                        print(f"Error copying directory {item}: {e}")
                            
                            success = True
                            break
                    
                    if success:
                        break
            
            # Case 3: Fall back to searching for any LibreOffice directories in the extracted contents
            if not success:
                for root, dirs, files in os.walk(extract_dir):
                    for dir_name in dirs:
                        if 'libreoffice' in dir_name.lower() or 'program' in dir_name.lower():
                            possible_dir = Path(root) / dir_name
                            
                            # Check if this directory has soffice.exe
                            if list(possible_dir.glob('**/soffice.exe')):
                                # Found a directory with LibreOffice executables
                                program_dst = target_dir / 'program'
                                program_dst.mkdir(parents=True, exist_ok=True)
                                
                                # Try to copy everything from this directory
                                for item in possible_dir.glob('*'):
                                    if item.is_file():
                                        try:
                                            shutil.copy2(str(item), str(program_dst / item.name))
                                        except Exception as e:
                                            print(f"Error copying {item}: {e}")
                                    elif item.is_dir():
                                        try:
                                            shutil.copytree(str(item), str(program_dst / item.name), dirs_exist_ok=True)
                                        except Exception as e:
                                            print(f"Error copying directory {item}: {e}")
                                
                                success = True
                                break
            
        elif platform_name == 'darwin':
            # For macOS, we'd need to extract from the .app bundle
            # This is more complex as DMGs need to be mounted
            print("LibreOffice DMG handling not implemented yet")
            return False
        
        elif platform_name == 'linux':
            # For Linux portable version
            for root, dirs, files in os.walk(extract_dir):
                if 'program' in dirs:
                    program_dir = Path(root) / 'program'
                    if (program_dir / 'soffice').exists():
                        # Found the program directory
                        program_dst = target_dir / 'program'
                        program_dst.mkdir(parents=True, exist_ok=True)
                        
                        # Copy directory contents
                        for item in program_dir.glob('*'):
                            if item.is_file():
                                shutil.copy2(str(item), str(program_dst / item.name))
                                if item.name == 'soffice':
                                    os.chmod(program_dst / item.name, 0o755)
                            elif item.is_dir():
                                shutil.copytree(str(item), str(program_dst / item.name), dirs_exist_ok=True)
                        
                        success = True
                        break
        
        # Final check: Verify that we've successfully set up the expected structure
        if platform_name == 'windows':
            success = (target_dir / 'program' / 'soffice.exe').exists()
        elif platform_name in ['darwin', 'linux']:
            success = (target_dir / 'program' / 'soffice').exists()
            
        # If organization worked, log details for troubleshooting
        if success:
            print(f"Successfully organized LibreOffice to {target_dir}")
            print(f"Program directory exists: {(target_dir / 'program').exists()}")
            if platform_name == 'windows':
                print(f"soffice.exe exists: {(target_dir / 'program' / 'soffice.exe').exists()}")
            else:
                print(f"soffice exists: {(target_dir / 'program' / 'soffice').exists()}")
        else:
            print(f"Failed to organize LibreOffice to {target_dir}")
        
        return success
            
    except Exception as e:
        print(f"Error organizing LibreOffice: {str(e)}")
        return False

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
    
    extract_success = extract_archive(
        download_path, 
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
        with open(version_file, 'w') as f:
            json.dump({
                "version": TOOL_VERSIONS[tool_name]["version"],
                "platform": platform_name,
                "install_date": str(Path.ctime(Path.today()))
            }, f)
    
    return organize_success

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