# src/gui/conversion_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                           QLabel, QProgressBar, QPushButton,
                           QDialogButtonBox, QStyle, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSettings, QTemporaryDir
from PyQt6.QtGui import QDesktopServices

from pathlib import Path
import os
import shutil
import time

class ConversionWorker(QThread):
    """Worker thread for running conversions"""
    
    progress_updated = pyqtSignal(int)
    conversion_finished = pyqtSignal(Path)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, conversion_manager, input_path, output_format):
        super().__init__()
        
        self.conversion_manager = conversion_manager
        self.input_path = input_path
        self.output_format = output_format
        self.output_path = None
    
    def run(self):
        """Run the conversion process"""
        try:
            # Perform conversion
            self.output_path = self.conversion_manager.convert(
                self.input_path,
                self.output_format,
                progress_callback=self.progress_callback
            )
            
            # Emit finished signal
            self.conversion_finished.emit(self.output_path)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def progress_callback(self, progress):
        """Callback for conversion progress updates"""
        self.progress_updated.emit(progress)

class ConversionDialog(QDialog):
    """Dialog for displaying conversion progress"""
    
    conversion_complete = pyqtSignal(bool)  # Signal emitted when conversion completes
    
    def __init__(self, parent, input_path, output_format, conversion_manager):
        super().__init__(parent)
        
        self.input_path = input_path
        self.output_format = output_format
        self.conversion_manager = conversion_manager
        self.output_path = None
        self.temp_dir = QTemporaryDir()
        
        # Load settings
        self.settings = QSettings("UniversalConverter", "FileConverter")
        
        self.init_ui()
        self.start_conversion()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Converting File")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # File info
        input_file_label = QLabel(f"Converting: {self.input_path.name}")
        layout.addWidget(input_file_label)
        
        output_format_label = QLabel(f"To format: {self.output_format.upper()}")
        layout.addWidget(output_format_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Starting conversion...")
        layout.addWidget(self.status_label)
        
        # Buttons
        self.button_layout = QHBoxLayout()
        
        # Save button (initially hidden)
        self.save_button = QPushButton("Save To...")
        self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_file)
        self.save_button.hide()
        
        # Open button (initially hidden)
        self.open_button = QPushButton("Open")
        self.open_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output_file)
        self.open_button.hide()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_conversion)
        
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.open_button)
        self.button_layout.addWidget(self.save_button)
        
        layout.addLayout(self.button_layout)
        
        self.setLayout(layout)
    
    def start_conversion(self):
        """Start the conversion process"""
        # Create and start worker thread
        self.worker = ConversionWorker(
            self.conversion_manager,
            self.input_path,
            self.output_format
        )
        
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.conversion_finished.connect(self.conversion_finished)
        self.worker.error_occurred.connect(self.conversion_error)
        
        self.worker.start()
    
    def update_progress(self, progress):
        """Update progress bar and status"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Converting... {progress}%")
    
    def conversion_finished(self, output_path):
        """Handle conversion completion"""
        self.output_path = output_path
        self.progress_bar.setValue(100)
        self.status_label.setText("Conversion completed successfully!")
        
        # Update buttons
        self.cancel_button.hide()
        self.save_button.setEnabled(True)
        self.save_button.show()
        self.open_button.setEnabled(True)
        self.open_button.show()
        
        # Check if we should automatically save to a default location
        default_dir = self.settings.value("default_output_dir", "")
        auto_save = self.settings.value("auto_save", False, type=bool)
        
        if auto_save and default_dir and os.path.isdir(default_dir):
            # Auto-save to default directory
            target_path = os.path.join(default_dir, output_path.name)
            try:
                shutil.copy2(str(output_path), target_path)
                self.status_label.setText(f"Saved to: {target_path}")
            except Exception as e:
                self.status_label.setText(f"Auto-save failed: {str(e)}")
        
        # Emit completion signal
        self.conversion_complete.emit(True)
    
    def conversion_error(self, error_message):
        """Handle conversion error"""
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {error_message}")
        
        # Update buttons
        self.cancel_button.setText("Close")
        
        # Emit completion signal with failure
        self.conversion_complete.emit(False)
    
    def save_file(self):
        """Save the converted file"""
        if not self.output_path or not self.output_path.exists():
            return
        
        # Get initial directory
        initial_dir = self.settings.value("last_save_dir", str(self.input_path.parent))
        
        # Get suggested filename (same as output but in target directory)
        suggested_name = self.output_path.name
        
        # Show save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Converted File",
            os.path.join(initial_dir, suggested_name),
            f"{self.output_format.upper()} Files (*.{self.output_format});;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Save last used directory
            self.settings.setValue("last_save_dir", os.path.dirname(file_path))
            
            # Check if target exists and is different from source
            if Path(file_path) != self.output_path and Path(file_path).exists():
                # Ask for confirmation before overwriting
                confirm = QMessageBox.question(
                    self,
                    "Confirm Overwrite",
                    f"File already exists: {file_path}\nDo you want to replace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if confirm != QMessageBox.StandardButton.Yes:
                    return
            
            # Copy the file
            shutil.copy2(str(self.output_path), file_path)
            
            # Update status
            self.status_label.setText(f"Saved to: {file_path}")
            
            # Update output path to point to saved location
            self.output_path = Path(file_path)
            
            # Auto-close after saving
            QDialog.accept(self)
            
        except Exception as e:
            self.status_label.setText(f"Save failed: {str(e)}")
            
            # Show error message
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Could not save file: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
    
    def cancel_conversion(self):
        """Cancel the conversion process"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            
            self.status_label.setText("Conversion canceled")
            self.conversion_complete.emit(False)
        
        # Close dialog
        QDialog.reject(self)
    
    def open_output_file(self):
        """Open the output file"""
        if self.output_path and self.output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path)))
            
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()