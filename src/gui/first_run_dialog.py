# src/gui/first_run_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QProgressBar, QPushButton,
                            QCheckBox, QGroupBox, QListWidget,
                            QListWidgetItem, QTableWidget, 
                            QTableWidgetItem, QHeaderView,
                            QDialogButtonBox, QMessageBox,
                            QWidget, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QMetaObject, Q_ARG, QObject
from PyQt6.QtGui import QFont, QIcon

import os
from pathlib import Path
import time

from utils.dependencies import check_dependencies
from utils.tool_downloader import (download_and_setup_tool, 
                                  check_for_updates, 
                                  get_installed_version)

class ToolStatusCheckerThread(QThread):
    """Thread for checking tools status"""
    
    status_updated = pyqtSignal(dict)  # tools status dictionary
    
    def run(self):
        """Run the checking process"""
        try:
            # Check current installations
            deps = check_dependencies()
            
            # Check for updates if needed
            updates = {}
            try:
                updates = check_for_updates()
            except Exception as e:
                print(f"Error checking for updates: {str(e)}")
            
            # Process results
            status = {}
            for tool_name, info in deps.items():
                tool_key = tool_name.lower()
                
                status[tool_key] = {
                    'available': info['available'],
                    'path': info['path']
                }
                
                # Add update info if available
                if tool_key in updates:
                    status[tool_key]['current_version'] = updates[tool_key]['installed']
                    status[tool_key]['latest_version'] = updates[tool_key]['latest']
                    status[tool_key]['update_available'] = updates[tool_key]['update_available']
            
            # Emit results
            self.status_updated.emit(status)
            
        except Exception as e:
            print(f"Error checking tools: {str(e)}")
            self.status_updated.emit({})

class ToolDownloadThread(QThread):
    """Thread for downloading tools in background"""
    
    progress_updated = pyqtSignal(str, str, int)  # tool, stage, percentage
    download_finished = pyqtSignal(str, bool)     # tool, success
    
    def __init__(self, tool_name):
        super().__init__()
        self.tool_name = tool_name
        self.is_cancelled = False
    
    def run(self):
        """Run the download process"""
        try:
            # Forward progress updates to the UI
            success = download_and_setup_tool(
                self.tool_name,
                lambda stage, percentage: self.progress_updated.emit(
                    self.tool_name, stage, percentage
                ) if not self.is_cancelled else None
            )
            
            if not self.is_cancelled:
                self.download_finished.emit(self.tool_name, success)
            
        except Exception as e:
            print(f"Download error: {str(e)}")
            if not self.is_cancelled:
                self.download_finished.emit(self.tool_name, False)
    
    def cancel(self):
        """Cancel the download"""
        self.is_cancelled = True

class FirstRunDialog(QDialog):
    """Dialog shown on first run to download required tools"""
    
    def __init__(self, parent=None, check_mode=False):
        super().__init__(parent)
        
        self.check_mode = check_mode  # True if just checking for updates
        self.settings = QSettings("UniversalConverter", "FileConverter")
        self.download_threads = {}
        self.tool_status = {}
        self.download_in_progress = False
        self.tool_widgets = {}  # Store references to action buttons by tool name
        
        self.init_ui()
        self.check_tools()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Universal File Converter - Setup" if not self.check_mode 
                           else "Check for Updates")
        self.setMinimumSize(600, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Universal File Converter Setup" if not self.check_mode 
                             else "Check for Tool Updates")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Description
        if not self.check_mode:
            desc_text = (
                "This tool requires several external applications to convert files. "
                "We'll help you download and set them up automatically."
            )
        else:
            desc_text = (
                "Check if updates are available for the external tools used by this application."
            )
            
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Tools status section
        tools_group = QGroupBox("External Tools")
        tools_layout = QVBoxLayout()
        
        # Create table for tools status
        self.tools_table = QTableWidget(3, 4 if self.check_mode else 3)
        self.tools_table.setHorizontalHeaderLabels(
            ["Tool", "Status", "Action", "Version"] if self.check_mode else 
            ["Tool", "Status", "Action"]
        )
        self.tools_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tools_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tools_table.verticalHeader().setVisible(False)
        self.tools_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        # Set up table with tool names
        tools = ["FFmpeg", "Pandoc", "LibreOffice"]
        tool_keys = ["ffmpeg", "pandoc", "libreoffice"]
        
        for i, (tool, key) in enumerate(zip(tools, tool_keys)):
            self.tools_table.setItem(i, 0, QTableWidgetItem(tool))
            
            # Status will be set after checking
            status_item = QTableWidgetItem("Checking...")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tools_table.setItem(i, 1, status_item)
            
            # Create a cell widget to hold the action button
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(2, 2, 2, 2)
            
            action_button = QPushButton("Waiting...")
            action_button.setEnabled(False)
            cell_layout.addWidget(action_button)
            
            self.tools_table.setCellWidget(i, 2, cell_widget)
            self.tool_widgets[key] = action_button
            
            if self.check_mode:
                # Version column for update check mode
                version_item = QTableWidgetItem("")
                version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tools_table.setItem(i, 3, version_item)
        
        tools_layout.addWidget(self.tools_table)
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)
        
        # Progress section
        self.progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout()
        
        self.current_tool_label = QLabel("No download in progress")
        progress_layout.addWidget(self.current_tool_label)
        
        self.stage_label = QLabel("")
        progress_layout.addWidget(self.stage_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_group.setLayout(progress_layout)
        layout.addWidget(self.progress_group)
        
        # Options
        if not self.check_mode:
            options_group = QGroupBox("Update Settings")
            options_layout = QVBoxLayout()
            
            # Use radio buttons for update frequency
            self.update_options_group = QButtonGroup(self)
            
            self.weekly_updates_radio = QRadioButton("Check for updates weekly (recommended)")
            self.update_options_group.addButton(self.weekly_updates_radio)
            self.weekly_updates_radio.setChecked(True)  # Default option
            options_layout.addWidget(self.weekly_updates_radio)
            
            self.monthly_updates_radio = QRadioButton("Check for updates monthly")
            self.update_options_group.addButton(self.monthly_updates_radio)
            options_layout.addWidget(self.monthly_updates_radio)
            
            self.no_updates_radio = QRadioButton("Never check for updates")
            self.update_options_group.addButton(self.no_updates_radio)
            options_layout.addWidget(self.no_updates_radio)
            
            options_group.setLayout(options_layout)
            layout.addWidget(options_group)
            
            # Buttons
            button_layout = QHBoxLayout()
        
        if not self.check_mode:
            self.skip_button = QPushButton("Skip Setup")
            self.skip_button.clicked.connect(self.skip_setup)
            button_layout.addWidget(self.skip_button)
        
        button_layout.addStretch(1)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)  # Disabled until checking is done
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def check_tools(self):
        """Check which tools are installed and their status"""
        # Start a background thread to check dependencies
        self.checker_thread = ToolStatusCheckerThread()
        self.checker_thread.status_updated.connect(self.on_status_updated)
        self.checker_thread.start()
    
    def on_status_updated(self, status):
        """Handle tool status update from the checker thread"""
        self.tool_status = status
        
        # Update UI for each tool
        for tool_key in ['ffmpeg', 'pandoc', 'libreoffice']:
            info = status.get(tool_key, {})
            self._update_tool_ui(tool_key, info)
        
        # Enable close button once checking is done
        self.close_button.setEnabled(True)
        
        # Check if we need to recommend downloads
        if not self.check_mode:
            missing_tools = [tool for tool, status in self.tool_status.items() 
                           if not status.get('available', False)]
            
            if missing_tools:
                self._show_download_recommendation(missing_tools)
    
    def _update_tool_ui(self, tool_key, info=None):
        """Update the UI for a specific tool"""
        if info is None:
            info = self.tool_status.get(tool_key, {})
            
        try:
            row = ['ffmpeg', 'pandoc', 'libreoffice'].index(tool_key)
            
            # Update status text
            if info.get('available', False):
                status_text = "Available"
                if self.check_mode and info.get('update_available', False):
                    status_text = "Update Available"
            else:
                status_text = "Not Found"
            
            self.tools_table.item(row, 1).setText(status_text)
            
            # Update action button
            action_button = self.tool_widgets[tool_key]
            
            # Disconnect any previous connections
            try:
                action_button.clicked.disconnect()
            except:
                pass
                
            if not info.get('available', False):
                # Tool is missing, show download button
                action_button.setText("Download")
                action_button.setEnabled(True)
                action_button.clicked.connect(
                    lambda checked=False, t=tool_key: self.download_tool(t)
                )
            elif self.check_mode and info.get('update_available', False):
                # Update is available
                action_button.setText("Update")
                action_button.setEnabled(True)
                action_button.clicked.connect(
                    lambda checked=False, t=tool_key: self.download_tool(t)
                )
            else:
                # Tool is available and no update needed
                action_button.setText("Installed" if not self.check_mode else "Up to date")
                action_button.setEnabled(False)
            
            # Update version info if in check mode
            if self.check_mode:
                version_text = ""
                if info.get('current_version'):
                    if info.get('update_available', False):
                        version_text = f"{info['current_version']} → {info['latest_version']}"
                    else:
                        version_text = f"{info['current_version']}"
                self.tools_table.item(row, 3).setText(version_text)
            
        except Exception as e:
            print(f"Error updating UI for {tool_key}: {str(e)}")
    
    def _show_download_recommendation(self, missing_tools):
        """Show recommendation to download missing tools"""
        if not missing_tools:
            return
        
        tools_text = ", ".join([t.capitalize() for t in missing_tools])
        
        # Use QTimer to ensure this runs in the main thread after UI is fully initialized
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._show_download_dialog(tools_text, missing_tools))
        
    def _show_download_dialog(self, tools_text, missing_tools):
        """Show the actual download recommendation dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Missing Tools")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Some required conversion tools are missing: {tools_text}")
        msg.setInformativeText("Would you like to download them now?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Download first missing tool
            self.download_tool(missing_tools[0])
    
    def download_tool(self, tool_name):
        """Start downloading a tool"""
        if self.download_in_progress:
            QMessageBox.warning(self, "Download in Progress", 
                               "Please wait for the current download to complete.")
            return
        
        # Disable all action buttons during download
        for button in self.tool_widgets.values():
            button.setEnabled(False)
        
        # Update progress section
        self.current_tool_label.setText(f"Downloading {tool_name.capitalize()}...")
        self.stage_label.setText("Starting...")
        self.progress_bar.setValue(0)
        self.download_in_progress = True
        
        # Create and start download thread
        thread = ToolDownloadThread(tool_name)
        thread.progress_updated.connect(self.update_download_progress)
        thread.download_finished.connect(self.download_finished)
        
        self.download_threads[tool_name] = thread
        thread.start()
    
    def update_download_progress(self, tool_name, stage, percentage):
        """Update progress display"""
        stage_text = stage.capitalize()
        self.stage_label.setText(f"{stage_text}: {percentage}%")
        self.progress_bar.setValue(percentage)
    
    def download_finished(self, tool_name, success):
        """Handle download completion"""
        # Update tool status
        thread = self.download_threads.pop(tool_name, None)
        
        if thread:
            thread.wait()  # Ensure thread is finished
        
        # Check tool status again - start a status check thread
        checker = ToolStatusCheckerThread()
        checker.status_updated.connect(self.on_download_status_updated)
        checker.start()
        
        # Reset progress display
        self.download_in_progress = False
        self.current_tool_label.setText("Download complete" if success else "Download failed")
        self.stage_label.setText("" if success else "Error occurred")
        self.progress_bar.setValue(100 if success else 0)
        
        # Show message to user
        if success:
            QMessageBox.information(self, "Download Complete", 
                                   f"{tool_name.capitalize()} was successfully downloaded and installed.")
        else:
            QMessageBox.warning(self, "Download Failed", 
                               f"Failed to download {tool_name.capitalize()}. Please try again later.")
    
    def on_download_status_updated(self, status):
        """Handle status update after download"""
        self.tool_status = status
        
        # Update UI for each tool
        for tool_key in ['ffmpeg', 'pandoc', 'libreoffice']:
            info = status.get(tool_key, {})
            self._update_tool_ui(tool_key, info)
            
        # Check for more missing tools
        if not self.check_mode:
            missing_tools = [tool for tool, info in self.tool_status.items() 
                           if not info.get('available', False)]
            
            if missing_tools:
                # Ask to download next tool
                tools_text = ", ".join([t.capitalize() for t in missing_tools])
                
                msg = QMessageBox(self)
                msg.setWindowTitle("Missing Tools")
                msg.setText(f"There are still some missing tools: {tools_text}")
                msg.setInformativeText("Would you like to download them now?")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                if msg.exec() == QMessageBox.StandardButton.Yes:
                    self.download_tool(missing_tools[0])
    
    def skip_setup(self):
        """Skip the setup process"""
        missing_tools = [tool for tool, status in self.tool_status.items() 
                       if not status.get('available', False)]
        
        if missing_tools:
            msg = QMessageBox(self)
            msg.setWindowTitle("Skip Setup")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Some tools are missing. This will limit conversion capabilities.")
            msg.setInformativeText("Are you sure you want to continue without downloading?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.No:
                return
        
        # User confirmed or no missing tools
        self.save_settings()
        self.accept()
    
    def save_settings(self):
        """Save user preferences"""
        if not self.check_mode:
            # Save update settings based on radio button selection
            if self.no_updates_radio.isChecked():
                self.settings.setValue("update_interval", "never")
                self.settings.setValue("check_updates", False)
            elif self.monthly_updates_radio.isChecked():
                self.settings.setValue("update_interval", "monthly")
                self.settings.setValue("check_updates", True)
            else:  # Weekly
                self.settings.setValue("update_interval", "weekly")
                self.settings.setValue("check_updates", True)
            
            # Mark first run as complete
            self.settings.setValue("first_run_complete", True)
    
    def accept(self):
        """Close dialog"""
        # Cancel any ongoing downloads
        for thread in self.download_threads.values():
            if thread.isRunning():
                thread.cancel()
                thread.wait()
        
        self.save_settings()
        super().accept()
    
    def reject(self):
        """Handle dialog rejection (close button or Escape)"""
        if self.download_in_progress:
            # Ask for confirmation if downloads are in progress
            msg = QMessageBox(self)
            msg.setWindowTitle("Cancel Downloads")
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText("Downloads are in progress.")
            msg.setInformativeText("Are you sure you want to cancel and close?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.No:
                return
        
        # User confirmed or no downloads in progress
        self.accept()  # Use accept to ensure settings are saved