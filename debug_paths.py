# debug_paths.py
import os
from pathlib import Path
import sys

# Print current working directory
print(f"Current working directory: {os.getcwd()}")

# Print script directory
print(f"Script directory: {Path(__file__).parent.absolute()}")

# Print path to portable_tools
portable_tools_path = Path(__file__).parent / 'portable_tools'
print(f"Portable tools path: {portable_tools_path}")
print(f"Portable tools path exists: {portable_tools_path.exists()}")

# Check specific tool paths
tools = {
    'ffmpeg': {'bin': ['ffmpeg.exe', 'ffprobe.exe']},
    'pandoc': {'bin': ['pandoc.exe']},
    'libreoffice': {'program': ['soffice.exe']}
}

for tool_name, folders in tools.items():
    tool_path = portable_tools_path / tool_name
    print(f"\n{tool_name} path: {tool_path}")
    print(f"{tool_name} path exists: {tool_path.exists()}")
    
    for folder_name, files in folders.items():
        folder_path = tool_path / folder_name
        print(f"  {folder_name} folder: {folder_path}")
        print(f"  {folder_name} folder exists: {folder_path.exists()}")
        
        for file_name in files:
            file_path = folder_path / file_name
            print(f"    {file_name}: {file_path}")
            print(f"    {file_name} exists: {file_path.exists()}")

# Print all files in portable_tools recursively
print("\nAll files in portable_tools:")
if portable_tools_path.exists():
    for root, dirs, files in os.walk(portable_tools_path):
        for file in files:
            print(os.path.join(root, file))