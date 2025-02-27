# src/main_gui.py
import sys
from PyQt6.QtWidgets import QApplication
from gui.app import ConverterApp

def main():
    """Main entry point for the GUI application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Universal File Converter")
    
    # Create and show the main application window
    main_window = ConverterApp()
    main_window.show()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()