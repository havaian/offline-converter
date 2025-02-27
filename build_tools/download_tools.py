    # build_tools/download_tools.py
    import os
    import requests
    import zipfile
    import tarfile
    import shutil
    from pathlib import Path

    TOOLS = {
        'ffmpeg': {
            'windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
            'darwin': 'https://evermeet.cx/ffmpeg/getrelease/zip',
            'linux': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz'
        },
        'pandoc': {
            'windows': 'https://github.com/jgm/pandoc/releases/download/3.1.6.1/pandoc-3.1.6.1-windows-x86_64.zip',
            'darwin': 'https://github.com/jgm/pandoc/releases/download/3.1.6.1/pandoc-3.1.6.1-macOS.zip',
            'linux': 'https://github.com/jgm/pandoc/releases/download/3.1.6.1/pandoc-3.1.6.1-linux-amd64.tar.gz'
        },
        'libreoffice': {
            'windows': 'https://download.documentfoundation.org/libreoffice/stable/7.5.3/win/x86_64/LibreOffice_7.5.3_Win_x86-64.msi',
            # Note: For LibreOffice, we might need a custom approach or installer
        }
    }

    def download_file(url, target_path):
        """Download a file with progress reporting"""
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024  # 1MB
        
        with open(target_path, 'wb') as f:
            for data in response.iter_content(block_size):
                f.write(data)
        
        print(f"Downloaded to {target_path}")

    def extract_archive(archive_path, target_dir):
        """Extract an archive file"""
        print(f"Extracting {archive_path}...")
        
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
        elif archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(target_dir)
        elif archive_path.endswith('.tar.xz'):
            with tarfile.open(archive_path, 'r:xz') as tar_ref:
                tar_ref.extractall(target_dir)
        else:
            print(f"Unsupported archive format: {archive_path}")
            return False
        
        print(f"Extracted to {target_dir}")
        return True

    def organize_ffmpeg(extract_dir, target_dir):
        """Organize FFmpeg files into our structure"""
        # Find the bin directory in extracted files
        for root, dirs, files in os.walk(extract_dir):
            ffmpeg_exe = None
            if os.name == 'nt':
                ffmpeg_exe = 'ffmpeg.exe'
            else:
                ffmpeg_exe = 'ffmpeg'
            
            if ffmpeg_exe in files:
                # Found the directory with ffmpeg executable
                bin_dir = Path(target_dir) / 'bin'
                bin_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy executables
                for exe in ['ffmpeg', 'ffprobe']:
                    if os.name == 'nt':
                        exe += '.exe'
                    if exe in files:
                        shutil.copy2(
                            Path(root) / exe,
                            bin_dir / exe
                        )
                return True
        
        return False

    def organize_pandoc(extract_dir, target_dir):
        """Organize Pandoc files into our structure"""
        # Find pandoc executable
        for root, dirs, files in os.walk(extract_dir):
            pandoc_exe = None
            if os.name == 'nt':
                pandoc_exe = 'pandoc.exe'
            else:
                pandoc_exe = 'pandoc'
            
            if pandoc_exe in files:
                # Found the directory with pandoc executable
                bin_dir = Path(target_dir) / 'bin'
                bin_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy executable
                shutil.copy2(
                    Path(root) / pandoc_exe,
                    bin_dir / pandoc_exe
                )
                return True
        
        return False

    def main():
        # Create directories
        tools_dir = Path(__file__).parent.parent / 'portable_tools'
        temp_dir = Path(__file__).parent.parent / 'temp'
        
        tools_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine platform
        if os.name == 'nt':
            platform = 'windows'
        elif sys.platform == 'darwin':
            platform = 'darwin'
        else:
            platform = 'linux'
        
        # Download and extract tools
        for tool, urls in TOOLS.items():
            if platform in urls:
                url = urls[platform]
                
                # Skip LibreOffice for now (requires special handling)
                if tool == 'libreoffice':
                    print("Note: LibreOffice requires manual installation or special handling")
                    continue
                
                # Create tool directory
                tool_dir = tools_dir / tool
                tool_dir.mkdir(parents=True, exist_ok=True)
                
                # Download
                download_path = temp_dir / f"{tool}.{url.split('.')[-1]}"
                download_file(url, download_path)
                
                # Extract
                extract_dir = temp_dir / tool
                extract_dir.mkdir(parents=True, exist_ok=True)
                if extract_archive(download_path, extract_dir):
                    # Organize files
                    if tool == 'ffmpeg':
                        organize_ffmpeg(extract_dir, tool_dir)
                    elif tool == 'pandoc':
                        organize_pandoc(extract_dir, tool_dir)
                
                # Clean up
                shutil.rmtree(extract_dir)
                download_path.unlink()
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)

    if __name__ == "__main__":
        main()