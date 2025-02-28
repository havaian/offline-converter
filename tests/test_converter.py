# test_converter.py
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.manager import ConversionManager
from converters.base import BaseConverter
from converters.ffmpeg import FFmpegConverter
from converters.pandoc import PandocConverter
from converters.libreoffice import LibreOfficeConverter
from core.exceptions import ConverterError, UnsupportedFormatError, DependencyError
from utils.dependencies import check_dependencies


class TestBaseConverter(unittest.TestCase):
    """Test the abstract base converter class functionality."""
    
    def setUp(self):
        # Create a concrete subclass for testing
        class ConcreteConverter(BaseConverter):
            def convert(self, source_path, target_path, progress_callback=None):
                return True
                
            def validate_dependencies(self):
                return True
        
        self.converter = ConcreteConverter()
        self.converter._supported_input_formats = {'jpg', 'png'}
        self.converter._supported_output_formats = {'pdf', 'docx'}
    
    def test_can_convert(self):
        """Test the can_convert method."""
        # Should return True for supported formats
        self.assertTrue(self.converter.can_convert('jpg', 'pdf'))
        self.assertTrue(self.converter.can_convert('png', 'docx'))
        
        # Should handle case-insensitive format strings
        self.assertTrue(self.converter.can_convert('JPG', 'PDF'))
        
        # Should return False for unsupported formats
        self.assertFalse(self.converter.can_convert('gif', 'pdf'))
        self.assertFalse(self.converter.can_convert('jpg', 'txt'))
    
    def test_supported_formats_properties(self):
        """Test the properties returning supported formats."""
        self.assertEqual(self.converter.supported_input_formats, {'jpg', 'png'})
        self.assertEqual(self.converter.supported_output_formats, {'pdf', 'docx'})


class TestConversionManager(unittest.TestCase):
    """Test the conversion manager functionality."""
    
    def setUp(self):
        self.manager = ConversionManager()
        
        # Create mock converters
        self.mock_converter1 = MagicMock(spec=BaseConverter)
        self.mock_converter1.can_convert.return_value = False
        self.mock_converter1.supported_input_formats = {'jpg', 'png'}
        self.mock_converter1.supported_output_formats = {'pdf'}
        
        self.mock_converter2 = MagicMock(spec=BaseConverter)
        self.mock_converter2.can_convert.return_value = False
        self.mock_converter2.supported_input_formats = {'docx', 'doc'}
        self.mock_converter2.supported_output_formats = {'pdf', 'txt'}
        
        # Register mock converters
        self.manager.register_converter('mock1', self.mock_converter1)
        self.manager.register_converter('mock2', self.mock_converter2)
    
    def test_register_converter(self):
        """Test registering converters."""
        self.assertEqual(len(self.manager._converters), 2)
        self.assertIn('mock1', self.manager._converters)
        self.assertIn('mock2', self.manager._converters)
    
    def test_find_converter(self):
        """Test finding appropriate converter."""
        # Set up converter returns for specific format combinations
        self.mock_converter1.can_convert.side_effect = lambda src, tgt: (
            src == 'jpg' and tgt == 'pdf'
        )
        self.mock_converter2.can_convert.side_effect = lambda src, tgt: (
            src == 'docx' and tgt == 'pdf'
        )
        
        # Should find the correct converter
        self.assertEqual(self.manager.find_converter('jpg', 'pdf'), self.mock_converter1)
        self.assertEqual(self.manager.find_converter('docx', 'pdf'), self.mock_converter2)
        
        # Should return None if no converter is found
        self.assertIsNone(self.manager.find_converter('mp3', 'wav'))
    
    def test_convert_success(self):
        """Test successful conversion."""
        # Set up converter for specific format
        self.mock_converter1.can_convert.side_effect = lambda src, tgt: (
            src == 'jpg' and tgt == 'pdf'
        )
        self.mock_converter1.convert.return_value = True
        
        # Create temporary test files
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            source_path = Path(temp_file.name)
        
        try:
            # Run the conversion
            target_path = self.manager.convert(source_path, 'pdf')
            
            # Check that the correct converter was used
            self.mock_converter1.convert.assert_called_once()
            
            # Check output path
            self.assertEqual(target_path.suffix, '.pdf')
            
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)
            
            # Check if target path exists and clean it up
            expected_target = source_path.with_suffix('.pdf')
            if expected_target.exists():
                os.unlink(expected_target)
    
    def test_convert_file_not_found(self):
        """Test conversion with non-existent source file."""
        non_existent_path = Path('non_existent_file.jpg')
        
        with self.assertRaises(FileNotFoundError):
            self.manager.convert(non_existent_path, 'pdf')
    
    def test_convert_unsupported_format(self):
        """Test conversion with unsupported format."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as temp_file:
            source_path = Path(temp_file.name)
        
        try:
            # Attempt conversion with unsupported format
            with self.assertRaises(UnsupportedFormatError):
                self.manager.convert(source_path, 'abc')
                
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)
    
    def test_convert_failure(self):
        """Test handling of conversion failure."""
        # Set up converter for specific format but make it fail
        self.mock_converter1.can_convert.side_effect = lambda src, tgt: (
            src == 'jpg' and tgt == 'pdf'
        )
        self.mock_converter1.convert.return_value = False
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            source_path = Path(temp_file.name)
        
        try:
            # Attempt conversion that will fail
            with self.assertRaises(ConverterError):
                self.manager.convert(source_path, 'pdf')
                
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)


class TestFFmpegConverter(unittest.TestCase):
    """Test FFmpeg converter functionality."""
    
    def setUp(self):
        self.converter = FFmpegConverter()
    
    def test_supported_formats(self):
        """Test supported formats are correctly defined."""
        # Check some supported input formats
        self.assertIn('mp4', self.converter.supported_input_formats)
        self.assertIn('mp3', self.converter.supported_input_formats)
        self.assertIn('wav', self.converter.supported_input_formats)
        
        # Check some supported output formats
        self.assertIn('mp4', self.converter.supported_output_formats)
        self.assertIn('mp3', self.converter.supported_output_formats)
        self.assertIn('wav', self.converter.supported_output_formats)
    
    @patch('converters.ffmpeg.get_tool_path')
    def test_validate_dependencies_success(self, mock_get_tool_path):
        """Test successful dependency validation."""
        # Mock ffmpeg path
        mock_ffmpeg_path = MagicMock(spec=Path)
        mock_ffmpeg_path.exists.return_value = True
        mock_get_tool_path.return_value = mock_ffmpeg_path
        
        # Mock successful subprocess run
        with patch('subprocess.run') as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "ffmpeg version 7.0.2"
            mock_process.stderr = ""
            mock_run.return_value = mock_process
            
            # Test validation
            self.assertTrue(self.converter.validate_dependencies())
            self.assertEqual(self.converter._ffmpeg_path, mock_ffmpeg_path)
    
    @patch('converters.ffmpeg.get_tool_path')
    def test_validate_dependencies_missing(self, mock_get_tool_path):
        """Test dependency validation when ffmpeg is missing."""
        # Mock missing ffmpeg
        mock_get_tool_path.return_value = None
        
        # Test validation
        with self.assertRaises(DependencyError):
            self.converter.validate_dependencies()
    
    @patch('converters.ffmpeg.get_tool_path')
    def test_validate_dependencies_error(self, mock_get_tool_path):
        """Test dependency validation when ffmpeg has an error."""
        # Mock ffmpeg path
        mock_ffmpeg_path = MagicMock(spec=Path)
        mock_ffmpeg_path.exists.return_value = True
        mock_get_tool_path.return_value = mock_ffmpeg_path
        
        # Mock failed subprocess run
        with patch('subprocess.run') as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.stderr = "Error: ffmpeg failed to run"
            mock_run.return_value = mock_process
            
            # Test validation
            with self.assertRaises(DependencyError):
                self.converter.validate_dependencies()
    
    @patch('converters.ffmpeg.FFmpegConverter.validate_dependencies')
    @patch('subprocess.run')
    def test_convert_success(self, mock_run, mock_validate):
        """Test successful conversion with FFmpeg."""
        # Mock validation and subprocess
        mock_validate.return_value = True
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Set ffmpeg path
        self.converter._ffmpeg_path = Path('/path/to/ffmpeg')
        
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as source_file:
            source_path = Path(source_file.name)
        
        # Create target path
        target_path = source_path.with_suffix('.mp3')
        
        try:
            # Test conversion
            result = self.converter.convert(source_path, target_path)
            self.assertTrue(result)
            
            # Check that subprocess.run was called correctly
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]
            
            # Check command components
            self.assertEqual(cmd[0], str(self.converter._ffmpeg_path))
            self.assertEqual(cmd[1], '-i')
            self.assertEqual(cmd[2], str(source_path))
            
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)


class TestPandocConverter(unittest.TestCase):
    """Test Pandoc converter functionality."""
    
    def setUp(self):
        self.converter = PandocConverter()
    
    def test_supported_formats(self):
        """Test supported formats are correctly defined."""
        # Check some supported input formats
        self.assertIn('docx', self.converter.supported_input_formats)
        self.assertIn('md', self.converter.supported_input_formats)
        self.assertIn('html', self.converter.supported_input_formats)
        
        # Check some supported output formats
        self.assertIn('docx', self.converter.supported_output_formats)
        self.assertIn('pdf', self.converter.supported_output_formats)
        self.assertIn('html', self.converter.supported_output_formats)
    
    @patch('converters.pandoc.get_tool_path')
    def test_validate_dependencies_success(self, mock_get_tool_path):
        """Test successful dependency validation."""
        # Mock pandoc path
        mock_pandoc_path = MagicMock(spec=Path)
        mock_pandoc_path.exists.return_value = True
        mock_get_tool_path.return_value = mock_pandoc_path
        
        # Mock successful subprocess run
        with patch('subprocess.run') as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "pandoc version 3.6.3"
            mock_process.stderr = ""
            mock_run.return_value = mock_process
            
            # Test validation
            self.assertTrue(self.converter.validate_dependencies())
            self.assertEqual(self.converter._pandoc_path, mock_pandoc_path)
    
    @patch('converters.pandoc.PandocConverter.validate_dependencies')
    @patch('subprocess.run')
    def test_convert_success(self, mock_run, mock_validate):
        """Test successful conversion with Pandoc."""
        # Mock validation and subprocess
        mock_validate.return_value = True
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Set pandoc path
        self.converter._pandoc_path = Path('/path/to/pandoc')
        
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as source_file:
            source_path = Path(source_file.name)
        
        # Create target path
        target_path = source_path.with_suffix('.html')
        
        try:
            # Test conversion
            result = self.converter.convert(source_path, target_path)
            self.assertTrue(result)
            
            # Check that subprocess.run was called correctly
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]
            
            # Check command components
            self.assertEqual(cmd[0], str(self.converter._pandoc_path))
            self.assertEqual(cmd[1], str(source_path))
            self.assertEqual(cmd[2], '-o')
            self.assertEqual(cmd[3], str(target_path))
            
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)
    
    @patch('converters.pandoc.PandocConverter.validate_dependencies')
    @patch('subprocess.run')
    def test_convert_pdf_with_error(self, mock_run, mock_validate):
        """Test handling of PDF conversion error."""
        # Mock validation
        mock_validate.return_value = True
        
        # Mock subprocess with LaTeX error
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "pdflatex not found"
        mock_run.return_value = mock_process
        
        # Set pandoc path
        self.converter._pandoc_path = Path('/path/to/pandoc')
        
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as source_file:
            source_path = Path(source_file.name)
        
        # Create target path
        target_path = source_path.with_suffix('.pdf')
        
        try:
            # Test conversion - should raise specific error about LaTeX
            with self.assertRaises(ConverterError) as context:
                self.converter.convert(source_path, target_path)
            
            # Check that error message mentions LaTeX
            self.assertIn("PDF conversion requires LaTeX", str(context.exception))
            
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)


class TestLibreOfficeConverter(unittest.TestCase):
    """Test LibreOffice converter functionality."""
    
    def setUp(self):
        self.converter = LibreOfficeConverter()
    
    def test_supported_formats(self):
        """Test supported formats are correctly defined."""
        # Check some supported input formats
        self.assertIn('docx', self.converter.supported_input_formats)
        self.assertIn('xlsx', self.converter.supported_input_formats)
        self.assertIn('pptx', self.converter.supported_input_formats)
        
        # Check some supported output formats
        self.assertIn('pdf', self.converter.supported_output_formats)
        self.assertIn('odt', self.converter.supported_output_formats)
        self.assertIn('csv', self.converter.supported_output_formats)
    
    @patch('converters.libreoffice.get_tool_path')
    def test_validate_dependencies_success(self, mock_get_tool_path):
        """Test successful dependency validation."""
        # Mock libreoffice path
        mock_soffice_path = MagicMock(spec=Path)
        mock_soffice_path.exists.return_value = True
        mock_get_tool_path.return_value = mock_soffice_path
        
        # Mock successful subprocess run
        with patch('subprocess.run') as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "LibreOffice 25.2.1"
            mock_process.stderr = ""
            mock_run.return_value = mock_process
            
            # Test validation
            self.assertTrue(self.converter.validate_dependencies())
            self.assertEqual(self.converter._soffice_path, mock_soffice_path)
    
    @patch('converters.libreoffice.LibreOfficeConverter.validate_dependencies')
    @patch('subprocess.run')
    @patch('tempfile.TemporaryDirectory')
    def test_convert_success(self, mock_temp_dir, mock_run, mock_validate):
        """Test successful conversion with LibreOffice."""
        # Mock validation
        mock_validate.return_value = True
        
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Mock temporary directory
        mock_temp_path = Path('/tmp/libreoffice_temp')
        mock_temp_context = MagicMock()
        mock_temp_context.__enter__.return_value = str(mock_temp_path)
        mock_temp_dir.return_value = mock_temp_context
        
        # Set soffice path
        self.converter._soffice_path = Path('/path/to/soffice')
        
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as source_file:
            source_path = Path(source_file.name)
        
        # Create target path
        target_path = source_path.with_suffix('.pdf')
        
        # Mock existence of converted file in temp dir
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Mock shutil.move
            with patch('shutil.move') as mock_move:
                try:
                    # Test conversion
                    result = self.converter.convert(source_path, target_path)
                    self.assertTrue(result)
                    
                    # Check that subprocess.run was called correctly
                    mock_run.assert_called_once()
                    args, kwargs = mock_run.call_args
                    cmd = args[0]
                    
                    # Check command components
                    self.assertEqual(cmd[0], str(self.converter._soffice_path))
                    self.assertEqual(cmd[1], '--headless')
                    self.assertIn('--convert-to', cmd[2])
                    self.assertIn('pdf', cmd[2])
                    self.assertEqual(cmd[3], '--outdir')
                    self.assertEqual(cmd[4], str(mock_temp_path))
                    self.assertEqual(cmd[5], str(source_path))
                    
                    # Check that shutil.move was called to move the file
                    mock_move.assert_called_once()
                    
                finally:
                    # Clean up
                    if source_path.exists():
                        os.unlink(source_path)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full conversion process."""
    
    def setUp(self):
        # Create a conversion manager with all converters
        self.manager = ConversionManager()
        
        # We'll use mock converters for integration tests to avoid actual dependencies
        # But we'll set up proper format support
        self.ffmpeg_converter = MagicMock(spec=FFmpegConverter)
        self.ffmpeg_converter.supported_input_formats = {
            'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv',
            'mp3', 'wav', 'aac', 'ogg', 'm4a', 'flac'
        }
        self.ffmpeg_converter.supported_output_formats = {
            'mp4', 'avi', 'mkv', 'mov',
            'mp3', 'wav', 'aac', 'ogg'
        }
        self.ffmpeg_converter.can_convert.side_effect = lambda src, tgt: (
            src in self.ffmpeg_converter.supported_input_formats and
            tgt in self.ffmpeg_converter.supported_output_formats
        )
        self.ffmpeg_converter.convert.return_value = True
        
        self.pandoc_converter = MagicMock(spec=PandocConverter)
        self.pandoc_converter.supported_input_formats = {
            'md', 'markdown', 'docx', 'doc', 'pdf', 
            'odt', 'txt', 'html', 'epub'
        }
        self.pandoc_converter.supported_output_formats = {
            'md', 'markdown', 'docx', 'odt', 'txt', 
            'html', 'epub', 'pdf'
        }
        self.pandoc_converter.can_convert.side_effect = lambda src, tgt: (
            src in self.pandoc_converter.supported_input_formats and
            tgt in self.pandoc_converter.supported_output_formats
        )
        self.pandoc_converter.convert.return_value = True
        
        self.libreoffice_converter = MagicMock(spec=LibreOfficeConverter)
        self.libreoffice_converter.supported_input_formats = {
            'doc', 'docx', 'odt', 'rtf', 'txt',
            'xls', 'xlsx', 'ods', 'csv',
            'ppt', 'pptx', 'odp',
        }
        self.libreoffice_converter.supported_output_formats = {
            'pdf', 'docx', 'odt', 'rtf', 'txt',
            'xlsx', 'ods', 'csv',
            'pptx', 'odp', 'pdf',
        }
        self.libreoffice_converter.can_convert.side_effect = lambda src, tgt: (
            src in self.libreoffice_converter.supported_input_formats and
            tgt in self.libreoffice_converter.supported_output_formats
        )
        self.libreoffice_converter.convert.return_value = True
        
        # Register the mock converters
        self.manager.register_converter('ffmpeg', self.ffmpeg_converter)
        self.manager.register_converter('pandoc', self.pandoc_converter)
        self.manager.register_converter('libreoffice', self.libreoffice_converter)
    
    def test_document_conversion_integration(self):
        """Test converting between document formats."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
            source_path = Path(temp_file.name)
        
        try:
            # Test conversion from docx to pdf
            target_path = self.manager.convert(source_path, 'pdf')
            
            # Both Pandoc and LibreOffice can convert this - check which one was chosen
            converter_used = (
                self.pandoc_converter if self.pandoc_converter.convert.called 
                else self.libreoffice_converter
            )
            
            # Verify that one of them was called
            self.assertTrue(
                self.pandoc_converter.convert.called or 
                self.libreoffice_converter.convert.called
            )
            
            # Verify that the correct path was returned
            self.assertEqual(target_path, source_path.with_suffix('.pdf'))
            
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)
    
    def test_media_conversion_integration(self):
        """Test converting between media formats."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            source_path = Path(temp_file.name)
        
        try:
            # Test conversion from mp3 to wav
            target_path = self.manager.convert(source_path, 'wav')
            
            # Verify that FFmpeg converter was called
            self.ffmpeg_converter.convert.assert_called_once()
            
            # Verify that the correct path was returned
            self.assertEqual(target_path, source_path.with_suffix('.wav'))
            
        finally:
            # Clean up
            if source_path.exists():
                os.unlink(source_path)


class TestDependenciesCheck(unittest.TestCase):
    """Test dependency checking functionality."""
    
    @patch('utils.dependencies.get_ffmpeg_path')
    @patch('utils.dependencies.get_pandoc_path')
    @patch('utils.dependencies.get_libreoffice_path')
    @patch('utils.dependencies.run_subprocess_without_window')
    def test_check_dependencies(self, mock_run, mock_lo_path, mock_pandoc_path, mock_ffmpeg_path):
        """Test the check_dependencies function."""
        # Mock paths
        mock_ffmpeg_path = MagicMock(spec=Path)
        mock_ffmpeg_path.exists.return_value = True
        mock_ffmpeg_path.__str__.return_value = '/path/to/ffmpeg'
        
        mock_pandoc_path = MagicMock(spec=Path)
        mock_pandoc_path.exists.return_value = True
        mock_pandoc_path.__str__.return_value = '/path/to/pandoc'
        
        mock_lo_path = MagicMock(spec=Path)
        mock_lo_path.exists.return_value = True
        mock_lo_path.__str__.return_value = '/path/to/soffice'
        
        mock_get_ffmpeg_path.return_value = mock_ffmpeg_path
        mock_get_pandoc_path.return_value = mock_pandoc_path
        mock_get_libreoffice_path.return_value = mock_lo_path
        
        # Mock subprocess results
        mock_run.side_effect = [
            {'returncode': 0, 'stdout': 'ffmpeg version 7.0.2', 'stderr': ''},
            {'returncode': 0, 'stdout': 'pandoc version 3.6.3', 'stderr': ''},
            {'returncode': 0, 'stdout': 'LibreOffice found (existence check only)', 'stderr': ''}
        ]
        
        # Run the function
        results = check_dependencies()
        
        # Check that all tools were found
        self.assertTrue(results['ffmpeg']['available'])
        self.assertTrue(results['pandoc']['available'])
        self.assertTrue(results['libreoffice']['available'])
        
        # Check that paths were recorded
        self.assertEqual(results['ffmpeg']['path'], '/path/to/ffmpeg')
        self.assertEqual(results['pandoc']['path'], '/path/to/pandoc')
        self.assertEqual(results['libreoffice']['path'], '/path/to/soffice')


class TestFormatUtils(unittest.TestCase):
    """Test utilities for file format handling."""
    
    def setUp(self):
        # Import here to avoid circular imports
        from utils.format_utils import get_file_category, get_compatible_formats, format_can_be_converted
        self.get_file_category = get_file_category
        self.get_compatible_formats = get_compatible_formats
        self.format_can_be_converted = format_can_be_converted
        
        # Setup mock conversion manager
        self.manager = ConversionManager()
        
        # Mock converters
        mock_ffmpeg = MagicMock(spec=BaseConverter)
        mock_ffmpeg.supported_input_formats = {'mp3', 'wav', 'mp4'}
        mock_ffmpeg.supported_output_formats = {'mp3', 'wav', 'mp4'}
        
        mock_pandoc = MagicMock(spec=BaseConverter)
        mock_pandoc.supported_input_formats = {'md', 'docx', 'html'}
        mock_pandoc.supported_output_formats = {'md', 'docx', 'html', 'pdf'}
        
        # Register converters
        self.manager.register_converter('ffmpeg', mock_ffmpeg)
        self.manager.register_converter('pandoc', mock_pandoc)
    
    def test_get_file_category(self):
        """Test file category detection."""
        # Test document formats
        self.assertEqual(self.get_file_category('pdf'), 'document')
        self.assertEqual(self.get_file_category('docx'), 'document')
        self.assertEqual(self.get_file_category('txt'), 'document')
        self.assertEqual(self.get_file_category('md'), 'document')
        
        # Test spreadsheet formats
        self.assertEqual(self.get_file_category('xlsx'), 'spreadsheet')
        self.assertEqual(self.get_file_category('csv'), 'spreadsheet')
        
        # Test presentation formats
        self.assertEqual(self.get_file_category('pptx'), 'presentation')
        self.assertEqual(self.get_file_category('odp'), 'presentation')
        
        # Test audio formats
        self.assertEqual(self.get_file_category('mp3'), 'audio')
        self.assertEqual(self.get_file_category('wav'), 'audio')
        
        # Test video formats
        self.assertEqual(self.get_file_category('mp4'), 'video')
        self.assertEqual(self.get_file_category('avi'), 'video')
        
        # Test image formats
        self.assertEqual(self.get_file_category('jpg'), 'image')
        self.assertEqual(self.get_file_category('png'), 'image')
        
        # Test unknown format
        self.assertEqual(self.get_file_category('xyz'), 'unknown')
    
    def test_get_compatible_formats(self):
        """Test getting compatible formats for conversion."""
        # Test with document format
        docx_compatible = self.get_compatible_formats('docx', self.manager)
        self.assertIn('md', docx_compatible)
        self.assertIn('html', docx_compatible)
        self.assertIn('pdf', docx_compatible)
        
        # Test with audio format
        mp3_compatible = self.get_compatible_formats('mp3', self.manager)
        self.assertIn('wav', mp3_compatible)
        self.assertIn('mp4', mp3_compatible)
        
        # Test with unknown format
        unknown_compatible = self.get_compatible_formats('xyz', self.manager)
        self.assertEqual(unknown_compatible, [])
    
    def test_format_can_be_converted(self):
        """Test checking if a format can be converted."""
        # Test valid conversions
        self.assertTrue(self.format_can_be_converted('mp3', 'wav', self.manager))
        self.assertTrue(self.format_can_be_converted('docx', 'pdf', self.manager))
        
        # Test invalid conversions
        self.assertFalse(self.format_can_be_converted('mp3', 'docx', self.manager))
        self.assertFalse(self.format_can_be_converted('xyz', 'pdf', self.manager))


class TestBatchConversion(unittest.TestCase):
    """Test batch conversion functionality."""
    
    def setUp(self):
        # Import batch conversion module
        from src.core.batch import BatchConverter
        
        # Create a mock conversion manager
        self.manager = MagicMock(spec=ConversionManager)
        self.manager.convert.return_value = Path('/path/to/output.pdf')
        
        # Create batch converter
        self.batch_converter = BatchConverter(self.manager)
    
    def test_batch_convert_single_format(self):
        """Test batch conversion to a single format."""
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            file1_path = temp_path / 'file1.docx'
            file2_path = temp_path / 'file2.docx'
            file3_path = temp_path / 'file3.txt'
            
            file1_path.touch()
            file2_path.touch()
            file3_path.touch()
            
            # Create output directory
            output_dir = temp_path / 'output'
            output_dir.mkdir()
            
            # Run batch conversion
            results = self.batch_converter.batch_convert(
                source_dir=temp_path,
                target_format='pdf',
                output_dir=output_dir,
                file_patterns=['*.docx', '*.txt']
            )
            
            # Verify conversion manager was called for each file
            self.assertEqual(self.manager.convert.call_count, 3)
            
            # Check results
            self.assertEqual(len(results['successful']), 3)
            self.assertEqual(len(results['failed']), 0)
    
    def test_batch_convert_with_failures(self):
        """Test batch conversion with some failures."""
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            file1_path = temp_path / 'file1.docx'
            file2_path = temp_path / 'file2.docx'
            file3_path = temp_path / 'file3.xyz'  # Unsupported format
            
            file1_path.touch()
            file2_path.touch()
            file3_path.touch()
            
            # Create output directory
            output_dir = temp_path / 'output'
            output_dir.mkdir()
            
            # Mock conversion errors for file3
            def mock_convert(source, target_format):
                if source.suffix == '.xyz':
                    raise UnsupportedFormatError(f"Format {source.suffix[1:]} is not supported")
                return Path('/path/to/output.pdf')
            
            self.manager.convert.side_effect = mock_convert
            
            # Run batch conversion
            results = self.batch_converter.batch_convert(
                source_dir=temp_path,
                target_format='pdf',
                output_dir=output_dir,
                file_patterns=['*.*']
            )
            
            # Check results
            self.assertEqual(len(results['successful']), 2)
            self.assertEqual(len(results['failed']), 1)
            self.assertIn(str(file3_path), results['failed'])


class TestCLI(unittest.TestCase):
    """Test command-line interface functionality."""
    
    @patch('core.manager.ConversionManager')
    @patch('cli.main.check_dependencies')
    def test_cli_single_file_conversion(self, mock_check_deps, mock_manager_class):
        """Test CLI single file conversion."""
        # Import CLI module
        from cli.main import main
        
        # Mock dependencies check
        mock_check_deps.return_value = {
            'ffmpeg': {'available': True, 'path': '/path/to/ffmpeg'},
            'pandoc': {'available': True, 'path': '/path/to/pandoc'},
            'libreoffice': {'available': True, 'path': '/path/to/soffice'}
        }
        
        # Mock conversion manager
        mock_manager = MagicMock()
        mock_manager.convert.return_value = Path('/path/to/output.pdf')
        mock_manager_class.return_value = mock_manager
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.docx') as temp_file:
            # Prepare CLI arguments
            test_args = [
                'convert',
                '--input', temp_file.name,
                '--output-format', 'pdf'
            ]
            
            # Run CLI command
            with patch('sys.argv', ['universal_converter'] + test_args):
                main()
            
            # Verify conversion was called
            mock_manager.convert.assert_called_once()
    
    @patch('core.manager.ConversionManager')
    @patch('cli.main.check_dependencies')
    @patch('src.core.batch.BatchConverter')
    def test_cli_batch_conversion(self, mock_batch_class, mock_check_deps, mock_manager_class):
        """Test CLI batch conversion."""
        # Import CLI module
        from cli.main import main
        
        # Mock dependencies check
        mock_check_deps.return_value = {
            'ffmpeg': {'available': True, 'path': '/path/to/ffmpeg'},
            'pandoc': {'available': True, 'path': '/path/to/pandoc'},
            'libreoffice': {'available': True, 'path': '/path/to/soffice'}
        }
        
        # Mock conversion manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        # Mock batch converter
        mock_batch = MagicMock()
        mock_batch.batch_convert.return_value = {
            'successful': ['/path/to/file1.pdf', '/path/to/file2.pdf'],
            'failed': []
        }
        mock_batch_class.return_value = mock_batch
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Prepare CLI arguments
            test_args = [
                'batch-convert',
                '--input-dir', temp_dir,
                '--output-format', 'pdf',
                '--pattern', '*.docx'
            ]
            
            # Run CLI command
            with patch('sys.argv', ['universal_converter'] + test_args):
                main()
            
            # Verify batch conversion was called
            mock_batch.batch_convert.assert_called_once()


if __name__ == '__main__':
    unittest.main()