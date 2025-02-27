# setup.py
from setuptools import setup, find_packages

setup(
    name="offline-converter",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'tqdm>=4.65.0',
        'python-ffmpeg>=2.0.0',
        'pypandoc>=1.11',
        'python-docx>=0.8.11',
        'PyPDF2>=3.0.0',
        'python-magic>=0.4.27',
        'pyqt6>=6.4.0',
    ],
)