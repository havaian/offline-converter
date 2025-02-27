# src/gui/app.py
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QStyle
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon

from .main_window import ConverterMainWindow
from .settings_dialog import SettingsDialog
from .conversion_dialog import ConversionDialog

from core.manager import ConversionManager
from converters.ffmpeg import FFmpegConverter
from converters.pandoc import PandocConverter
from converters.libreoffice import LibreOfficeConverter
from utils.dependencies import check_dependencies

class ConverterApp(QMainWindow):
    """Main application window for the Universal File Converter"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize conversion manager and register converters
        self.conversion_manager = ConversionManager()
        self.conversion_manager.register_converter("ffmpeg", FFmpegConverter())
        self.conversion_manager.register_converter("pandoc", PandocConverter())
        self.conversion_manager.register_converter("libreoffice", LibreOfficeConverter())
        
        # Load settings
        self.settings = QSettings("UniversalConverter", "FileConverter")
        
        # Initialize UI
        self.init_ui()
        
        # Check dependencies on startup
        self.check_dependencies()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Universal File Converter")
        self.setMinimumSize(800, 600)
        
        # Set window icon
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        
        # Create main window widget
        self.main_window = ConverterMainWindow(self.conversion_manager)
        self.setCentralWidget(self.main_window)
        
        # Connect signals
        self.main_window.conversion_requested.connect(self.start_conversion)
        self.main_window.settings_requested.connect(self.show_settings)
        
        # Restore window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def check_dependencies(self):
        """Check if all required external dependencies are available"""
        deps = check_dependencies()
        
        missing = [name for name, info in deps.items() if not info['available']]
        
        if missing:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Missing Dependencies")
            msg.setText("Some conversion tools are not available.")
            
            details = "The following conversion tools were not found:\n\n"
            for tool in missing:
                details += f"- {tool.capitalize()}\n"
            
            details += "\nSome file conversions may not be available. "
            details += "You can still use the application with limited functionality."
            
            msg.setDetailedText(details)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
    
    def start_conversion(self, input_path, output_format):
        """Start a file conversion process"""
        dialog = ConversionDialog(self, input_path, output_format, self.conversion_manager)
        
        # Connect conversion complete signal
        dialog.conversion_complete.connect(self.on_conversion_complete)
        
        dialog.exec()
    
    def on_conversion_complete(self, success):
        """Handle conversion completion"""
        # Reset the UI regardless of success
        self.main_window.reset_ui()
    
    def show_settings(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window geometry
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()