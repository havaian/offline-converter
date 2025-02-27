# src/gui/main_window.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QComboBox, 
                           QListWidget, QListWidgetItem, QMenu,
                           QFileDialog, QStyle, QSizePolicy,
                           QSpacerItem, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from pathlib import Path
import os

from .widgets.file_selector import FileSelector
from .widgets.format_selector import FormatSelector
from utils.format_utils import get_file_category, format_can_be_converted

class ConverterMainWindow(QWidget):
    """Main window widget for the converter application"""
    
    # Signals
    conversion_requested = pyqtSignal(Path, str)  # input_path, output_format
    settings_requested = pyqtSignal()
    
    def __init__(self, conversion_manager):
        super().__init__()
        
        self.conversion_manager = conversion_manager
        self.selected_file = None
        self.output_format = None
        
        # Get supported formats
        self.supported_formats = set()
        for converter in self.conversion_manager._converters.values():
            self.supported_formats.update(converter.supported_output_formats)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Universal File Converter")
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # File selector
        self.file_selector = FileSelector()
        self.file_selector.files_selected.connect(self.on_files_selected)
        self.file_selector.selection_changed.connect(self.on_file_selection_changed)
        layout.addWidget(self.file_selector)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Conversion section
        conversion_section = QWidget()
        conversion_layout = QVBoxLayout(conversion_section)
        
        # Format selector
        format_label = QLabel("Output Format:")
        self.format_selector = FormatSelector(self.supported_formats, self.conversion_manager)
        self.format_selector.format_selected.connect(self.on_format_selected)
        self.format_selector.setEnabled(False)  # Disabled until file is selected
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_selector)
        conversion_layout.addLayout(format_layout)
        
        # Conversion info
        self.conversion_info = QLabel("")
        self.conversion_info.setStyleSheet("color: gray; font-style: italic;")
        conversion_layout.addWidget(self.conversion_info)
        
        layout.addWidget(conversion_section)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.convert_button = QPushButton("Convert")
        self.convert_button.setEnabled(False)
        self.convert_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.convert_button.clicked.connect(self.on_convert_clicked)
        
        settings_button = QPushButton("Settings")
        settings_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        settings_button.clicked.connect(self.settings_requested)
        
        button_layout.addWidget(settings_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.convert_button)
        
        layout.addLayout(button_layout)
        
        # Set main layout
        self.setLayout(layout)
    
    def on_files_selected(self, files):
        """Handle files list changes"""
        # This is called when files are added or removed
        if not files:
            self.selected_file = None
            self.format_selector.setEnabled(False)
            self.conversion_info.setText("")
            self.convert_button.setEnabled(False)
    
    def on_file_selection_changed(self, file_path):
        """Handle file selection change"""
        self.selected_file = file_path
        
        # Update format selector for this file
        self.format_selector.update_for_file(file_path)
        
        # Reset output format
        self.output_format = None
        
        # Update conversion button
        self.update_convert_button()
        
        # Update conversion info
        self.update_conversion_info()
    
    def on_format_selected(self, format_name):
        """Handle format selection"""
        self.output_format = format_name
        
        # Update conversion button
        self.update_convert_button()
        
        # Update conversion info
        self.update_conversion_info()
    
    def update_convert_button(self):
        """Update convert button state based on selections"""
        self.convert_button.setEnabled(
            self.selected_file is not None and 
            self.output_format is not None
        )
    
    def update_conversion_info(self):
        """Update conversion information display"""
        if not self.selected_file or not self.output_format:
            self.conversion_info.setText("")
            return
        
        # Get source file info
        source_format = self.selected_file.suffix.lower().lstrip('.')
        source_category = get_file_category(self.selected_file)
        
        # Check if conversion is possible
        if format_can_be_converted(source_format, self.output_format, self.conversion_manager):
            # Get converter that will be used
            from utils.format_utils import get_converter_for_formats
            converter = get_converter_for_formats(
                source_format, self.output_format, self.conversion_manager
            )
            
            if converter:
                # Show conversion path
                self.conversion_info.setText(
                    f"Converting {source_format} to {self.output_format} using {converter}"
                )
                self.conversion_info.setStyleSheet("color: green;")
            else:
                self.conversion_info.setText(
                    f"Converting {source_format} to {self.output_format}"
                )
                self.conversion_info.setStyleSheet("color: green;")
        else:
            # Conversion not supported
            self.conversion_info.setText(
                f"Conversion from {source_format} to {self.output_format} not supported"
            )
            self.conversion_info.setStyleSheet("color: red;")
    
    def on_convert_clicked(self):
        """Handle convert button click"""
        if not self.selected_file or not self.output_format:
            return
        
        # Emit conversion request signal
        self.conversion_requested.emit(self.selected_file, self.output_format)
    
    def reset_ui(self):
        """Reset the UI after conversion"""
        # Clear file selector
        self.file_selector.reset()
        
        # Reset format selector
        self.format_selector.clear()
        self.format_selector.addItem("Select output format", "")
        self.format_selector.setEnabled(False)
        
        # Reset state variables
        self.selected_file = None
        self.output_format = None
        
        # Reset conversion info
        self.conversion_info.setText("")
        
        # Disable convert button
        self.convert_button.setEnabled(False)