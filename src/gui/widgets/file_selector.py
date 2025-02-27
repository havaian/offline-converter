# src/gui/widgets/file_selector.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QListWidget, 
                           QListWidgetItem, QFileDialog, QStyle,
                           QSizePolicy, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from pathlib import Path
import os

from utils.format_utils import get_file_category, FILE_CATEGORIES

class FileSelector(QWidget):
    """Widget for selecting input files"""
    
    # Signal emitted when files are selected
    files_selected = pyqtSignal(list)
    
    # Signal emitted when file selection changes
    selection_changed = pyqtSignal(Path)
    
    def __init__(self):
        super().__init__()
        
        self.files = []
        self.current_category = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Input Files:")
        layout.addWidget(label)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)
        self.file_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.file_list)
        
        # File type info
        self.file_type_label = QLabel("")
        layout.addWidget(self.file_type_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add Files")
        add_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart))
        add_button.clicked.connect(self.add_files)
        
        remove_button = QPushButton("Remove")
        remove_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        remove_button.clicked.connect(self.remove_selected)
        
        clear_button = QPushButton("Clear All")
        clear_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        clear_button.clicked.connect(self.clear_files)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(clear_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_files(self):
        """Open file dialog to add files"""
        # Create a filter string from the file categories
        filter_items = []
        
        # If we already have files, only show filter for same category
        if self.current_category and self.current_category != "unknown":
            category_info = FILE_CATEGORIES[self.current_category]
            exts = ' '.join(f"*.{ext}" for ext in category_info['extensions'])
            filter_items.append(f"{category_info['description']} ({exts})")
        else:
            # Add "All Files" as the first option
            filter_items.append("All Files (*.*)")
            
            # Add all categories
            for category, info in FILE_CATEGORIES.items():
                exts = ' '.join(f"*.{ext}" for ext in info['extensions'])
                filter_items.append(f"{info['description']} ({exts})")
        
        filter_string = ";;".join(filter_items)
        
        file_paths, selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Select Input Files",
            "",
            filter_string
        )
        
        # Rest of the method remains unchanged
        if not file_paths:
            return
        
        for file_path in file_paths:
            path = Path(file_path)
            
            # Check if this is a new category
            category = get_file_category(path)
            
            # If we already have files of a different category
            if self.files and self.current_category != "unknown" and category != self.current_category:
                QMessageBox.warning(
                    self,
                    "Mixed File Types",
                    f"You can only add files of the same type. Current type: {self.current_category}",
                    QMessageBox.StandardButton.Ok
                )
                continue
            
            # Set current category if this is the first file
            if not self.files:
                self.current_category = category
            
            # Add the file if it's not already in the list
            if path not in self.files:
                self.files.append(path)
                
                # Create list item with file info
                item = QListWidgetItem(path.name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                
                # Set icon based on file type
                if category == 'document':
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
                elif category == 'spreadsheet':
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)
                elif category == 'presentation':
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton)
                elif category in ('audio', 'video'):
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                elif category == 'image':
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
                else:
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
                
                item.setIcon(icon)
                self.file_list.addItem(item)
        
        # Select the first file if this is the first addition
        if self.file_list.count() > 0 and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)
        
        self.files_selected.emit(self.files)
    
    def remove_selected(self):
        """Remove selected files from the list"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            path = item.data(Qt.ItemDataRole.UserRole)
            self.files.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        
        # Reset category if no files left
        if not self.files:
            self.current_category = None
            self.file_type_label.setText("")
        
        self.files_selected.emit(self.files)
    
    def clear_files(self):
        """Clear all files from the list"""
        self.files.clear()
        self.file_list.clear()
        self.current_category = None
        self.file_type_label.setText("")
        self.files_selected.emit(self.files)
    
    def on_selection_changed(self):
        """Handle selection changes in the file list"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            self.file_type_label.setText("")
            return
        
        # Get the selected file path
        file_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Update file type info
        category = get_file_category(file_path)
        extension = file_path.suffix.lower()
        
        if category != 'unknown':
            category_info = FILE_CATEGORIES[category]
            self.file_type_label.setText(
                f"File Type: {category_info['description']} ({extension})"
            )
        else:
            self.file_type_label.setText(
                f"File Type: Unknown ({extension})"
            )
        
        # Emit signal with selected file
        self.selection_changed.emit(file_path)
    
    def show_context_menu(self, position):
        """Show context menu for file list"""
        menu = QMenu()
        
        add_action = QAction("Add Files", self)
        add_action.triggered.connect(self.add_files)
        
        remove_action = QAction("Remove Selected", self)
        remove_action.triggered.connect(self.remove_selected)
        
        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self.clear_files)
        
        menu.addAction(add_action)
        menu.addAction(remove_action)
        menu.addSeparator()
        menu.addAction(clear_action)
        
        menu.exec(self.file_list.mapToGlobal(position))
        
    def get_selected_file(self):
        """Get the currently selected file"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return None
        
        return selected_items[0].data(Qt.ItemDataRole.UserRole)
        
    def reset(self):
        """Reset the file selector"""
        self.clear_files()