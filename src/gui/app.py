# src/gui/app.py
from PyQt6.QtWidgets import (QMainWindow, QMessageBox, QFileDialog, 
                            QStyle, QMenu, QMenuBar)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon, QAction  # QAction is in QtGui, not QtWidgets

from .main_window import ConverterMainWindow
from .settings_dialog import SettingsDialog
from .conversion_dialog import ConversionDialog
from .first_run_dialog import FirstRunDialog

from core.manager import ConversionManager
from converters.ffmpeg import FFmpegConverter
from converters.pandoc import PandocConverter
from converters.libreoffice import LibreOfficeConverter
from utils.dependencies import check_dependencies

class ConverterApp(QMainWindow):
    """Main application window for the Universal File Converter"""
    
    def __init__(self):
        super().__init__()
        
        # Load settings
        self.settings = QSettings("UniversalConverter", "FileConverter")
        
        # Initialize conversion manager and register converters
        self.conversion_manager = ConversionManager()
        self.conversion_manager.register_converter("ffmpeg", FFmpegConverter())
        self.conversion_manager.register_converter("pandoc", PandocConverter())
        self.conversion_manager.register_converter("libreoffice", LibreOfficeConverter())
        
        # Initialize UI
        self.init_ui()
        
        # Check if this is the first run
        self.check_first_run()
        
        # Check for scheduled updates if enabled
        self.check_scheduled_updates()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Universal File Converter")
        self.setMinimumSize(800, 600)
        
        # Set window icon
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        
        # Create menubar
        self.create_menus()
        
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
    
    def create_menus(self):
        """Create application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def check_first_run(self):
        """Check if this is the first run of the application"""
        first_run_complete = self.settings.value("first_run_complete", False, type=bool)
        
        if not first_run_complete:
            # Show first run dialog
            first_run_dialog = FirstRunDialog(self)
            first_run_dialog.exec()
    
    def check_scheduled_updates(self):
        """Check for scheduled tool updates based on configured interval"""
        # First check if updates are enabled at all
        check_updates = self.settings.value("check_updates", True, type=bool)
        if not check_updates:
            return
        
        # Get the update interval setting
        update_interval = self.settings.value("update_interval", "weekly", type=str)
        
        # Get last update check timestamp
        last_update_check = self.settings.value("last_update_check", 0, type=int)
        
        import time
        current_time = int(time.time())
        
        # Calculate seconds in the interval
        interval_seconds = {
            "weekly": 7 * 24 * 60 * 60,  # 7 days
            "monthly": 30 * 24 * 60 * 60,  # 30 days
            "never": float('inf')  # never check
        }.get(update_interval, 7 * 24 * 60 * 60)  # default to weekly
        
        # Check if it's time to check for updates
        if current_time - last_update_check > interval_seconds:
            self.settings.setValue("last_update_check", current_time)
            
            # Check dependencies quietly first
            deps = check_dependencies()
            missing = [name for name, info in deps.items() if not info['available']]
            
            if missing:
                # Show first run dialog for missing tools
                QMessageBox.information(
                    self,
                    "Missing Tools",
                    "Some conversion tools are not available. You'll be prompted to download them."
                )
                first_run_dialog = FirstRunDialog(self)
                first_run_dialog.exec()
            else:
                # We have all tools, just check for updates quietly
                # We'll only notify if updates are available
                from utils.tool_downloader import check_for_updates
                updates = check_for_updates()
                
                update_available = any(info.get("update_available", False) 
                                    for info in updates.values())
                
                if update_available:
                    # Show notification about updates
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Updates Available")
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setText("Updates are available for some conversion tools.")
                    msg.setInformativeText("Would you like to check for updates now?")
                    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if msg.exec() == QMessageBox.StandardButton.Yes:
                        self.check_for_updates()
    
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
            details += "You can download the missing tools in the Settings dialog."
            
            msg.setDetailedText(details)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            
            # Ask if user wants to open settings
            settings_msg = QMessageBox(self)
            settings_msg.setWindowTitle("Open Settings")
            settings_msg.setText("Would you like to open the Settings dialog to download the missing tools?")
            settings_msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            settings_msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            if settings_msg.exec() == QMessageBox.StandardButton.Yes:
                self.show_settings()
        else:
            QMessageBox.information(
                self,
                "Dependencies Check",
                "All external dependencies are available.",
                QMessageBox.StandardButton.Ok
            )

    def check_for_updates(self):
        """Check for updates to external tools"""
        # Open settings dialog directly to the Tools tab
        dialog = SettingsDialog(self)
        dialog.tabs.setCurrentIndex(1)  # Tools tab
        dialog.exec()

    def show_settings(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()
    
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
    
    def show_about(self):
        """Show the about dialog"""
        about_text = (
            "<h2>Universal File Converter</h2>"
            "<p>Version 1.0</p>"
            "<p>A versatile tool for converting files between different formats "
            "using FFmpeg, Pandoc, and LibreOffice.</p>"
            "<p>This application is open-source software.</p>"
        )
        
        QMessageBox.about(self, "About Universal File Converter", about_text)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window geometry
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()