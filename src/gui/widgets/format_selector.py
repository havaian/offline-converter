# src/gui/widgets/format_selector.py
from PyQt6.QtWidgets import QComboBox, QLabel
from PyQt6.QtCore import pyqtSignal
from pathlib import Path

from utils.format_utils import (
    get_compatible_formats, 
    get_file_category,
    get_converter_for_formats
)

class FormatSelector(QComboBox):
    """Widget for selecting output format"""
    
    # Signal emitted when a format is selected
    format_selected = pyqtSignal(str)
    
    def __init__(self, formats=None, conversion_manager=None):
        super().__init__()
        
        self.conversion_manager = conversion_manager
        self.all_formats = formats or []
        self.current_file = None
        
        # Add placeholder item
        self.addItem("Select output format", "")
        
        # Connect signals
        self.currentIndexChanged.connect(self.on_format_changed)
    
    def set_conversion_manager(self, manager):
        """Set the conversion manager"""
        self.conversion_manager = manager
    
    def update_for_file(self, file_path):
        """Update available formats for the selected file"""
        if not file_path or not self.conversion_manager:
            self.clear()
            self.addItem("Select output format", "")
            self.setEnabled(False)
            return
        
        self.current_file = file_path
        
        # Get compatible formats
        compatible_formats = get_compatible_formats(file_path, self.conversion_manager)
        
        # Remember current selection
        current_format = self.currentData()
        
        # Clear and rebuild the dropdown
        self.clear()
        self.addItem("Select output format", "")
        
        if not compatible_formats:
            self.setEnabled(False)
            return
        
        # Group formats by category
        source_ext = file_path.suffix.lower().lstrip('.')
        
        # Add formats
        for format_name in sorted(compatible_formats):
            # Get the converter that will be used
            converter = get_converter_for_formats(source_ext, format_name, self.conversion_manager)
            
            # Create display text with converter info
            if converter:
                display_text = f".{format_name.upper()} (via {converter.capitalize()})"
            else:
                display_text = f".{format_name.upper()}"
                
            self.addItem(display_text, format_name)
        
        # Restore previous selection if it's still valid
        if current_format:
            index = self.findData(current_format)
            if index >= 0:
                self.setCurrentIndex(index)
        
        self.setEnabled(True)
    
    def on_format_changed(self, index):
        """Handle format selection change"""
        if index <= 0:
            return
        
        format_name = self.itemData(index)
        self.format_selected.emit(format_name)
        
    def reset(self):
        """Reset the format selector"""
        self.clear()
        self.addItem("Select output format", "")
        self.current_file = None