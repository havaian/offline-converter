# src/gui/settings_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                           QLabel, QTabWidget, QWidget,
                           QCheckBox, QLineEdit, QPushButton,
                           QFileDialog, QDialogButtonBox,
                           QListWidget, QGroupBox, QFormLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QApplication, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QSettings
from .first_run_dialog import FirstRunDialog

from utils.dependencies import check_dependencies

class SettingsDialog(QDialog):
    """Dialog for application settings"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.settings = QSettings("UniversalConverter", "FileConverter")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # General settings tab
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.general_tab, "General")
        
        # Tools settings tab - Create and add the widget first, then set up its contents
        self.tools_tab = QWidget()
        self.tabs.addTab(self.tools_tab, "External Tools")
        self.setup_tools_tab()  # Set up the contents after adding to tabs
        
        # About tab
        self.about_tab = QWidget()
        self.setup_about_tab()
        self.tabs.addTab(self.about_tab, "About")
        
        layout.addWidget(self.tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                    QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def setup_general_tab(self):
        """Set up the general settings tab"""
        layout = QVBoxLayout()
        
        # Output directory settings
        output_group = QGroupBox("Output Files")
        output_layout = QFormLayout()
        
        # Remember last directory
        self.remember_dir_checkbox = QCheckBox("Remember last used directory")
        output_layout.addRow(self.remember_dir_checkbox)
        
        # Default output directory
        default_dir_layout = QHBoxLayout()
        self.default_dir_edit = QLineEdit()
        self.default_dir_edit.setPlaceholderText("Same as input file")
        self.default_dir_edit.setReadOnly(True)
        
        self.browse_dir_button = QPushButton("Browse...")
        self.browse_dir_button.clicked.connect(self.browse_output_dir)
        
        default_dir_layout.addWidget(self.default_dir_edit)
        default_dir_layout.addWidget(self.browse_dir_button)
        
        output_layout.addRow("Default output directory:", default_dir_layout)
        
        # File naming options
        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        output_layout.addRow(self.overwrite_checkbox)
        
        self.append_format_checkbox = QCheckBox("Append format to filename")
        output_layout.addRow(self.append_format_checkbox)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Interface settings
        interface_group = QGroupBox("Interface")
        interface_layout = QFormLayout()
        
        self.confirm_conversion_checkbox = QCheckBox("Confirm before starting conversion")
        interface_layout.addRow(self.confirm_conversion_checkbox)
        
        self.show_notifications_checkbox = QCheckBox("Show notifications when conversion completes")
        interface_layout.addRow(self.show_notifications_checkbox)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        layout.addStretch(1)
        self.general_tab.setLayout(layout)
    
    def setup_tools_tab(self):
        """Set up the external tools settings tab"""
        layout = QVBoxLayout()
        
        # Dependencies status
        deps_group = QGroupBox("External Dependencies Status")
        deps_layout = QVBoxLayout()
        
        self.deps_table = QTableWidget(3, 3)
        self.deps_table.setHorizontalHeaderLabels(["Tool", "Status", "Path"])
        self.deps_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.deps_table.verticalHeader().setVisible(False)
        
        # Populate table with current status
        self.update_deps_table()
        
        deps_layout.addWidget(self.deps_table)
        
        # Add buttons for managing tools
        tools_buttons_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self.update_deps_table)
        tools_buttons_layout.addWidget(refresh_button)
        
        download_button = QPushButton("Download Missing Tools")
        download_button.clicked.connect(self.download_missing_tools)
        tools_buttons_layout.addWidget(download_button)
        
        check_updates_button = QPushButton("Check for Updates")
        check_updates_button.clicked.connect(self.check_for_updates)
        tools_buttons_layout.addWidget(check_updates_button)
        
        deps_layout.addLayout(tools_buttons_layout)
        deps_group.setLayout(deps_layout)
        layout.addWidget(deps_group)
        
        # Custom paths settings
        paths_group = QGroupBox("Custom Tool Paths")
        paths_layout = QFormLayout()
        
        # FFmpeg path
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("Use default path")
        
        self.ffmpeg_browse_button = QPushButton("Browse...")
        self.ffmpeg_browse_button.clicked.connect(lambda: self.browse_tool_path("ffmpeg"))
        
        ffmpeg_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout.addWidget(self.ffmpeg_browse_button)
        
        paths_layout.addRow("FFmpeg executable:", ffmpeg_layout)
        
        # Pandoc path
        pandoc_layout = QHBoxLayout()
        self.pandoc_path_edit = QLineEdit()
        self.pandoc_path_edit.setPlaceholderText("Use default path")
        
        self.pandoc_browse_button = QPushButton("Browse...")
        self.pandoc_browse_button.clicked.connect(lambda: self.browse_tool_path("pandoc"))
        
        pandoc_layout.addWidget(self.pandoc_path_edit)
        pandoc_layout.addWidget(self.pandoc_browse_button)
        
        paths_layout.addRow("Pandoc executable:", pandoc_layout)
        
        # LibreOffice path
        office_layout = QHBoxLayout()
        self.office_path_edit = QLineEdit()
        self.office_path_edit.setPlaceholderText("Use default path")
        
        self.office_browse_button = QPushButton("Browse...")
        self.office_browse_button.clicked.connect(lambda: self.browse_tool_path("libreoffice"))
        
        office_layout.addWidget(self.office_path_edit)
        office_layout.addWidget(self.office_browse_button)
        
        paths_layout.addRow("LibreOffice executable:", office_layout)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Auto-update settings
        update_group = QGroupBox("Update Settings")
        update_layout = QVBoxLayout()

        # Replace the simple checkbox with radio buttons for different intervals
        self.update_options_group = QButtonGroup(self)

        self.no_updates_radio = QRadioButton("Never check for updates")
        self.update_options_group.addButton(self.no_updates_radio)
        update_layout.addWidget(self.no_updates_radio)

        self.weekly_updates_radio = QRadioButton("Check for updates weekly (recommended)")
        self.update_options_group.addButton(self.weekly_updates_radio)
        update_layout.addWidget(self.weekly_updates_radio)

        self.monthly_updates_radio = QRadioButton("Check for updates monthly")
        self.update_options_group.addButton(self.monthly_updates_radio)
        update_layout.addWidget(self.monthly_updates_radio)

        # Select the appropriate radio button based on settings
        update_interval = self.settings.value("update_interval", "weekly", type=str)
        if update_interval == "never":
            self.no_updates_radio.setChecked(True)
        elif update_interval == "monthly":
            self.monthly_updates_radio.setChecked(True)
        else:  # Default to weekly
            self.weekly_updates_radio.setChecked(True)

        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
    
        # Add stretch to keep everything at the top
        layout.addStretch(1)
        
        # Set the layout for the tools tab
        self.tools_tab.setLayout(layout)
    
    def setup_about_tab(self):
        """Set up the about tab"""
        layout = QVBoxLayout()
        
        # App information
        app_label = QLabel("Universal File Converter")
        app_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(app_label)
        
        version_label = QLabel("Version 1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        description = QLabel(
            "A versatile tool for converting files between different formats "
            "using FFmpeg, Pandoc, and LibreOffice."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        # Credits
        credits_group = QGroupBox("Credits")
        credits_layout = QVBoxLayout()
        
        author_label = QLabel("Created by: Your Name")
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_layout.addWidget(author_label)
        
        tools_label = QLabel(
            "This application uses the following open-source tools:\n"
            "• FFmpeg - https://ffmpeg.org\n"
            "• Pandoc - https://pandoc.org\n"
            "• LibreOffice - https://libreoffice.org\n"
        )
        tools_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_layout.addWidget(tools_label)
        
        credits_group.setLayout(credits_layout)
        layout.addWidget(credits_group)
        
        # License
        license_group = QGroupBox("License")
        license_layout = QVBoxLayout()
        
        license_text = QLabel(
            "This application is open-source software licensed under the MIT License.\n\n"
            "You are free to use, modify, and distribute this software, provided "
            "that the original copyright notice and permission notice are included."
        )
        license_text.setWordWrap(True)
        license_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_layout.addWidget(license_text)
        
        license_group.setLayout(license_layout)
        layout.addWidget(license_group)
        
        layout.addStretch(1)
        self.about_tab.setLayout(layout)
    
    def update_deps_table(self):
        """Update dependencies status table"""
        # Start updating UI before checking dependencies to provide feedback
        self.deps_table.setItem(0, 0, QTableWidgetItem("FFmpeg"))
        self.deps_table.setItem(0, 1, QTableWidgetItem("Checking..."))
        self.deps_table.setItem(0, 2, QTableWidgetItem(""))
        
        self.deps_table.setItem(1, 0, QTableWidgetItem("Pandoc"))
        self.deps_table.setItem(1, 1, QTableWidgetItem("Checking..."))
        self.deps_table.setItem(1, 2, QTableWidgetItem(""))
        
        self.deps_table.setItem(2, 0, QTableWidgetItem("LibreOffice"))
        self.deps_table.setItem(2, 1, QTableWidgetItem("Checking..."))
        self.deps_table.setItem(2, 2, QTableWidgetItem(""))
        
        # Process events to update UI
        QApplication.processEvents()
        
        # Now check dependencies quietly
        deps = check_dependencies()
        
        # FFmpeg
        if deps['ffmpeg']['available']:
            self.deps_table.setItem(0, 1, QTableWidgetItem("Available"))
            self.deps_table.setItem(0, 2, QTableWidgetItem(deps['ffmpeg']['path']))
        else:
            self.deps_table.setItem(0, 1, QTableWidgetItem("Not Found"))
            self.deps_table.setItem(0, 2, QTableWidgetItem(""))
        
        # Pandoc
        if deps['pandoc']['available']:
            self.deps_table.setItem(1, 1, QTableWidgetItem("Available"))
            self.deps_table.setItem(1, 2, QTableWidgetItem(deps['pandoc']['path']))
        else:
            self.deps_table.setItem(1, 1, QTableWidgetItem("Not Found"))
            self.deps_table.setItem(1, 2, QTableWidgetItem(""))
        
        # LibreOffice
        if deps['libreoffice']['available']:
            self.deps_table.setItem(2, 1, QTableWidgetItem("Available"))
            self.deps_table.setItem(2, 2, QTableWidgetItem(deps['libreoffice']['path']))
        else:
            self.deps_table.setItem(2, 1, QTableWidgetItem("Not Found"))
            self.deps_table.setItem(2, 2, QTableWidgetItem(""))
    
    def browse_output_dir(self):
        """Browse for default output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Output Directory",
            self.default_dir_edit.text()
        )
        
        if dir_path:
            self.default_dir_edit.setText(dir_path)
    
    def browse_tool_path(self, tool_name):
        """Browse for tool executable path"""
        file_dialog = QFileDialog(self, f"Select {tool_name} Executable")
        
        if tool_name == "ffmpeg":
            edit_widget = self.ffmpeg_path_edit
            file_name = "ffmpeg.exe" if self.is_windows() else "ffmpeg"
        elif tool_name == "pandoc":
            edit_widget = self.pandoc_path_edit
            file_name = "pandoc.exe" if self.is_windows() else "pandoc"
        elif tool_name == "libreoffice":
            edit_widget = self.office_path_edit
            file_name = "soffice.exe" if self.is_windows() else "soffice"
        
        file_path, _ = file_dialog.getOpenFileName(
            self,
            f"Select {tool_name} Executable",
            "",
            f"{file_name};;All Files (*.*)"
        )
        
        if file_path:
            edit_widget.setText(file_path)
    
    def is_windows(self):
        """Check if running on Windows"""
        import platform
        return platform.system() == "Windows"
    
    def load_settings(self):
        """Load settings from QSettings"""
        # General tab
        self.remember_dir_checkbox.setChecked(
            self.settings.value("remember_last_dir", False, type=bool)
        )
        
        self.default_dir_edit.setText(
            self.settings.value("default_output_dir", "")
        )
        
        self.overwrite_checkbox.setChecked(
            self.settings.value("overwrite_files", False, type=bool)
        )
        
        self.append_format_checkbox.setChecked(
            self.settings.value("append_format", True, type=bool)
        )
        
        self.confirm_conversion_checkbox.setChecked(
            self.settings.value("confirm_conversion", True, type=bool)
        )
        
        self.show_notifications_checkbox.setChecked(
            self.settings.value("show_notifications", True, type=bool)
        )
        
        # Tools tab
        self.ffmpeg_path_edit.setText(
            self.settings.value("ffmpeg_path", "")
        )
        
        self.pandoc_path_edit.setText(
            self.settings.value("pandoc_path", "")
        )
        
        self.office_path_edit.setText(
            self.settings.value("libreoffice_path", "")
        )
    
    def accept(self):
        """Save settings and close dialog"""
        # Save update interval setting
        if self.no_updates_radio.isChecked():
            self.settings.setValue("update_interval", "never")
            self.settings.setValue("check_updates", False)
        elif self.monthly_updates_radio.isChecked():
            self.settings.setValue("update_interval", "monthly")
            self.settings.setValue("check_updates", True)
        else:  # Weekly
            self.settings.setValue("update_interval", "weekly")
            self.settings.setValue("check_updates", True)
        
        super().accept()

    def download_missing_tools(self):
        """Show dialog to download missing tools"""
        # Get missing tools
        deps = check_dependencies()
        missing = [name for name, info in deps.items() if not info['available']]
        
        if not missing:
            QMessageBox.information(
                self,
                "No Missing Tools",
                "All required tools are already installed.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Show download dialog
        download_dialog = FirstRunDialog(self)
        download_dialog.exec()
        
        # Refresh status after download
        self.update_deps_table()

    def check_for_updates(self):
        """Show dialog to check for tool updates"""
        update_dialog = FirstRunDialog(self, check_mode=True)
        update_dialog.exec()
        
        # Refresh status after potential updates
        self.update_deps_table()