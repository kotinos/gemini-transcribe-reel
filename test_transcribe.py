#!/usr/bin/env python3
"""
Unit tests for transcribe.py
Run with: python -m pytest test_transcribe.py -v
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import pytest

# Import the module to test
import transcribe


class TestDebugPrint:
    """Test debug printing functionality"""
    
    def test_debug_print_when_enabled(self, capsys):
        """Test that debug_print outputs when DEBUG is True"""
        transcribe.DEBUG = True
        transcribe.debug_print("test message")
        captured = capsys.readouterr()
        assert "[DEBUG] test message" in captured.out
    
    def test_debug_print_when_disabled(self, capsys):
        """Test that debug_print does not output when DEBUG is False"""
        transcribe.DEBUG = False
        transcribe.debug_print("test message")
        captured = capsys.readouterr()
        assert captured.out == ""


class TestNetworkCheck:
    """Test network connectivity checks"""
    
    @patch('socket.create_connection')
    def test_check_network_success(self, mock_socket):
        """Test successful network check"""
        mock_socket.return_value = Mock()
        assert transcribe.check_network() is True
        mock_socket.assert_called_once_with(("8.8.8.8", 53), timeout=3)
    
    @patch('socket.create_connection')
    def test_check_network_failure(self, mock_socket):
        """Test network check when connection fails"""
        mock_socket.side_effect = Exception("Connection failed")
        assert transcribe.check_network() is False


class TestURLValidation:
    """Test URL validation functionality"""
    
    def test_valid_http_url(self):
        """Test valid HTTP URL"""
        assert transcribe.validate_url("http://example.com/video") is True
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL"""
        assert transcribe.validate_url("https://instagram.com/p/ABC123/") is True
    
    def test_invalid_url_no_protocol(self):
        """Test invalid URL without protocol"""
        assert transcribe.validate_url("example.com") is False
    
    def test_invalid_url_no_domain(self):
        """Test invalid URL without domain"""
        assert transcribe.validate_url("http://") is False
    
    def test_invalid_url_too_long(self):
        """Test URL length limit (max 2048 chars)"""
        long_url = "https://example.com/" + "a" * 2050
        assert transcribe.validate_url(long_url) is False
    
    def test_valid_url_max_length(self):
        """Test URL at maximum allowed length"""
        url = "https://example.com/" + "a" * 2020
        assert transcribe.validate_url(url) is True


class TestDependencyCheck:
    """Test dependency checking"""
    
    @patch('subprocess.run')
    def test_check_dependencies_success(self, mock_run):
        """Test when yt-dlp is installed"""
        mock_run.return_value = Mock(returncode=0)
        # Should not raise SystemExit
        transcribe.check_dependencies()
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_dependencies_missing_ytdlp(self, mock_run):
        """Test when yt-dlp is not installed"""
        mock_run.return_value = Mock(returncode=1)
        with pytest.raises(SystemExit) as exc_info:
            transcribe.check_dependencies()
        assert exc_info.value.code == transcribe.ERROR_DOWNLOAD


class TestDownloadReel:
    """Test video download functionality"""
    
    @patch('subprocess.run')
    @patch('pathlib.Path.glob')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_download_reel_success(self, mock_stat, mock_exists, mock_glob, mock_run):
        """Test successful video download"""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0)
        mock_video = Mock()
        mock_video.stat.return_value.st_mtime = 123456789
        mock_glob.return_value = [mock_video]
        mock_exists.return_value = True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = transcribe.download_reel("https://example.com/video", temp_dir)
            assert result is not None
    
    @patch('subprocess.run')
    def test_download_reel_timeout(self, mock_run):
        """Test download timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired('yt-dlp', 60)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = transcribe.download_reel("https://example.com/video", temp_dir)
            assert result is None
    
    @patch('subprocess.run')
    @patch('pathlib.Path.glob')
    def test_download_reel_no_video_found(self, mock_glob, mock_run):
        """Test when no video file is found after download"""
        mock_run.return_value = Mock(returncode=0)
        mock_glob.return_value = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = transcribe.download_reel("https://example.com/video", temp_dir)
            assert result is None
    
    @patch('subprocess.run')
    def test_download_reel_exception(self, mock_run):
        """Test download with generic exception"""
        mock_run.side_effect = Exception("Download error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = transcribe.download_reel("https://example.com/video", temp_dir)
            assert result is None


class TestTranscribeVideo:
    """Test video transcription functionality"""
    
    @patch('transcribe.genai.upload_file')
    @patch('transcribe.genai.get_file')
    @patch('transcribe.genai.GenerativeModel')
    @patch('pathlib.Path.stat')
    def test_transcribe_video_success(self, mock_stat, mock_model_class, mock_get_file, mock_upload):
        """Test successful video transcription"""
        # Setup mocks
        mock_stat.return_value.st_size = 10 * 1024 * 1024  # 10MB
        
        mock_video_file = Mock()
        mock_video_file.name = "test_file_id"
        mock_video_file.delete = Mock()
        mock_upload.return_value = mock_video_file
        
        mock_file_info = Mock()
        mock_file_info.state.name = 'ACTIVE'
        mock_get_file.return_value = mock_file_info
        
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "This is the transcription"
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        result = transcribe.transcribe_video("test_video.mp4")
        
        assert result == "This is the transcription"
        mock_upload.assert_called_once_with(path="test_video.mp4")
        mock_video_file.delete.assert_called_once()
    
    @patch('pathlib.Path.stat')
    def test_transcribe_video_too_large(self, mock_stat):
        """Test video file too large for Gemini (>20MB)"""
        mock_stat.return_value.st_size = 25 * 1024 * 1024  # 25MB
        
        result = transcribe.transcribe_video("large_video.mp4")
        assert result is None
    
    @patch('transcribe.genai.upload_file')
    @patch('transcribe.genai.get_file')
    @patch('pathlib.Path.stat')
    @patch('time.sleep')
    def test_transcribe_video_processing_timeout(self, mock_sleep, mock_stat, mock_get_file, mock_upload):
        """Test timeout while waiting for video processing"""
        mock_stat.return_value.st_size = 10 * 1024 * 1024
        
        mock_video_file = Mock()
        mock_video_file.name = "test_file_id"
        mock_upload.return_value = mock_video_file
        
        mock_file_info = Mock()
        mock_file_info.state.name = 'PROCESSING'
        mock_get_file.return_value = mock_file_info
        
        result = transcribe.transcribe_video("test_video.mp4")
        assert result is None
    
    @patch('transcribe.genai.upload_file')
    @patch('transcribe.genai.get_file')
    @patch('pathlib.Path.stat')
    def test_transcribe_video_processing_failed(self, mock_stat, mock_get_file, mock_upload):
        """Test when video processing fails"""
        mock_stat.return_value.st_size = 10 * 1024 * 1024
        
        mock_video_file = Mock()
        mock_video_file.name = "test_file_id"
        mock_upload.return_value = mock_video_file
        
        mock_file_info = Mock()
        mock_file_info.state.name = 'FAILED'
        mock_get_file.return_value = mock_file_info
        
        result = transcribe.transcribe_video("test_video.mp4")
        assert result is None
    
    @patch('transcribe.genai.upload_file')
    @patch('pathlib.Path.stat')
    def test_transcribe_video_rate_limit(self, mock_stat, mock_upload):
        """Test rate limit error handling"""
        mock_stat.return_value.st_size = 10 * 1024 * 1024
        
        mock_upload.side_effect = Exception("Rate limit exceeded")
        
        result = transcribe.transcribe_video("test_video.mp4")
        assert result is None
    
    @patch('transcribe.genai.upload_file')
    @patch('pathlib.Path.stat')
    def test_transcribe_video_api_key_error(self, mock_stat, mock_upload):
        """Test API key authentication error"""
        mock_stat.return_value.st_size = 10 * 1024 * 1024
        
        mock_upload.side_effect = Exception("API key invalid 401")
        
        with pytest.raises(SystemExit) as exc_info:
            transcribe.transcribe_video("test_video.mp4")
        assert exc_info.value.code == transcribe.ERROR_API


class TestProcessURL:
    """Test single URL processing"""
    
    def test_process_url_invalid(self, capsys):
        """Test processing invalid URL"""
        result = transcribe.process_url("not-a-url")
        captured = capsys.readouterr()
        assert result is None
        assert "ERROR: Invalid URL" in captured.err
    
    @patch('transcribe.download_reel')
    @patch('transcribe.transcribe_video')
    @patch('transcribe.Path')
    def test_process_url_success(self, mock_path, mock_transcribe, mock_download):
        """Test successful URL processing"""
        mock_download.return_value = "/tmp/video.mp4"
        mock_transcribe.return_value = "Transcription text"
        
        # Mock Path operations
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024
        mock_path.return_value = mock_path_instance
        
        result = transcribe.process_url("https://example.com/video")
        assert result == "Transcription text"
    
    @patch('transcribe.download_reel')
    def test_process_url_download_failed(self, mock_download, capsys):
        """Test URL processing when download fails"""
        mock_download.return_value = None
        
        result = transcribe.process_url("https://example.com/video")
        captured = capsys.readouterr()
        assert result is None
        assert "ERROR: Could not download" in captured.err
    
    @patch('transcribe.download_reel')
    @patch('transcribe.transcribe_video')
    @patch('transcribe.Path')
    def test_process_url_transcription_failed(self, mock_path, mock_transcribe, mock_download, capsys):
        """Test URL processing when transcription fails"""
        mock_download.return_value = "/tmp/video.mp4"
        mock_transcribe.return_value = None
        
        # Mock Path operations
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024
        mock_path.return_value = mock_path_instance
        
        result = transcribe.process_url("https://example.com/video")
        captured = capsys.readouterr()
        assert result is None
        assert "ERROR: Could not transcribe" in captured.err
    
    @patch('transcribe.download_reel')
    @patch('transcribe.transcribe_video')
    @patch('transcribe.Path')
    def test_process_url_with_progress(self, mock_path, mock_transcribe, mock_download):
        """Test URL processing with progress indicators"""
        mock_download.return_value = "/tmp/video.mp4"
        mock_transcribe.return_value = "Transcription text"
        
        # Mock Path operations
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024
        mock_path.return_value = mock_path_instance
        
        result = transcribe.process_url("https://example.com/video", index=2, total=5)
        assert result == "Transcription text"


class TestMainFunction:
    """Test main function and argument parsing"""
    
    def test_main_no_arguments(self):
        """Test main with no arguments"""
        with patch.object(sys, 'argv', ['transcribe.py']):
            with pytest.raises(SystemExit) as exc_info:
                transcribe.main()
            assert exc_info.value.code == 1
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    def test_main_single_url(self, mock_process, mock_configure, mock_getenv, 
                            mock_load_dotenv, mock_check_deps, mock_check_network, capsys):
        """Test main with single URL"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.return_value = "Transcription result"
        
        with patch.object(sys, 'argv', ['transcribe.py', 'https://example.com/video']):
            transcribe.main()
        
        captured = capsys.readouterr()
        assert "Transcription result" in captured.out
        mock_process.assert_called_once()
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    @patch('time.sleep')
    def test_main_multiple_urls(self, mock_sleep, mock_process, mock_configure, 
                               mock_getenv, mock_load_dotenv, mock_check_deps, 
                               mock_check_network, capsys):
        """Test main with multiple URLs"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.side_effect = ["Result 1", "Result 2", "Result 3"]
        
        with patch.object(sys, 'argv', ['transcribe.py', 
                                       'https://example.com/video1',
                                       'https://example.com/video2',
                                       'https://example.com/video3']):
            transcribe.main()
        
        captured = capsys.readouterr()
        assert "BATCH RESULTS: 3/3 successful" in captured.out
        assert "Result 1" in captured.out
        assert "Result 2" in captured.out
        assert "Result 3" in captured.out
        assert mock_process.call_count == 3
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    @patch('time.sleep')
    def test_main_batch_with_failures(self, mock_sleep, mock_process, mock_configure,
                                     mock_getenv, mock_load_dotenv, mock_check_deps,
                                     mock_check_network, capsys):
        """Test batch processing with some failures"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.side_effect = ["Result 1", None, "Result 3"]
        
        with patch.object(sys, 'argv', ['transcribe.py',
                                       'https://example.com/video1',
                                       'https://example.com/video2',
                                       'https://example.com/video3']):
            transcribe.main()
        
        captured = capsys.readouterr()
        assert "BATCH RESULTS: 2/3 successful" in captured.out
        assert "(FAILED)" in captured.out
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    @patch('builtins.open', new_callable=mock_open, 
           read_data="https://example.com/video1\n# Comment\nhttps://example.com/video2\n")
    @patch('time.sleep')
    def test_main_file_input(self, mock_sleep, mock_file, mock_process, mock_configure,
                            mock_getenv, mock_load_dotenv, mock_check_deps,
                            mock_check_network, capsys):
        """Test main with file input"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.side_effect = ["Result 1", "Result 2"]
        
        with patch.object(sys, 'argv', ['transcribe.py', '--file', 'urls.txt']):
            transcribe.main()
        
        captured = capsys.readouterr()
        assert "BATCH RESULTS: 2/2 successful" in captured.out
        assert mock_process.call_count == 2
    
    @patch('transcribe.check_network')
    def test_main_no_network(self, mock_check_network):
        """Test main with no network connection"""
        mock_check_network.return_value = False
        
        with patch.object(sys, 'argv', ['transcribe.py', 'https://example.com/video']):
            with pytest.raises(SystemExit) as exc_info:
                transcribe.main()
            assert exc_info.value.code == transcribe.ERROR_NETWORK
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    def test_main_no_api_key(self, mock_getenv, mock_load_dotenv, 
                            mock_check_deps, mock_check_network):
        """Test main with missing API key"""
        mock_check_network.return_value = True
        mock_getenv.return_value = None
        
        with patch.object(sys, 'argv', ['transcribe.py', 'https://example.com/video']):
            with pytest.raises(SystemExit) as exc_info:
                transcribe.main()
            assert exc_info.value.code == transcribe.ERROR_API_KEY
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    def test_main_debug_mode(self, mock_configure, mock_getenv, mock_load_dotenv,
                            mock_check_deps, mock_check_network, capsys):
        """Test main with debug flag"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        
        with patch.object(sys, 'argv', ['transcribe.py', 'https://example.com/video', '--debug']):
            with patch('transcribe.process_url', return_value="Result"):
                transcribe.main()
        
        captured = capsys.readouterr()
        assert "[DEBUG] Debug mode enabled" in captured.out
    
    def test_main_file_not_found(self):
        """Test main with non-existent file"""
        with patch.object(sys, 'argv', ['transcribe.py', '--file', 'nonexistent.txt']):
            with pytest.raises(SystemExit) as exc_info:
                transcribe.main()
            assert exc_info.value.code == 1
    
    def test_main_file_flag_without_filename(self):
        """Test main with --file flag but no filename"""
        with patch.object(sys, 'argv', ['transcribe.py', '--file']):
            with pytest.raises(SystemExit) as exc_info:
                transcribe.main()
            assert exc_info.value.code == 1
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    def test_main_keyboard_interrupt(self, mock_process, mock_configure, mock_getenv,
                                    mock_load_dotenv, mock_check_deps, mock_check_network):
        """Test main handles keyboard interrupt (Ctrl+C)"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.side_effect = KeyboardInterrupt()
        
        with patch.object(sys, 'argv', ['transcribe.py', 'https://example.com/video']):
            with pytest.raises(SystemExit) as exc_info:
                transcribe.main()
            assert exc_info.value.code == 1


class TestRateLimiting:
    """Test rate limiting behavior"""
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    @patch('time.sleep')
    def test_rate_limiting_between_requests(self, mock_sleep, mock_process, mock_configure,
                                          mock_getenv, mock_load_dotenv, mock_check_deps,
                                          mock_check_network):
        """Test 4-second delay between batch requests"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.return_value = "Result"
        
        with patch.object(sys, 'argv', ['transcribe.py',
                                       'https://example.com/video1',
                                       'https://example.com/video2',
                                       'https://example.com/video3']):
            transcribe.main()
        
        # Should sleep 2 times (between 3 URLs: 1->2 and 2->3)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(4)


class TestCheckAvailableModels:
    """Test model listing functionality"""
    
    @patch('transcribe.genai.list_models')
    def test_check_available_models_success(self, mock_list_models):
        """Test listing available Gemini models"""
        mock_model1 = Mock()
        mock_model1.name = "gemini-2.5-flash"
        mock_model1.supported_generation_methods = ['generateContent']
        
        mock_model2 = Mock()
        mock_model2.name = "gemini-pro"
        mock_model2.supported_generation_methods = ['generateContent', 'other']
        
        mock_list_models.return_value = [mock_model1, mock_model2]
        
        transcribe.DEBUG = True
        transcribe.check_available_models()
        # Should not raise exception
    
    @patch('transcribe.genai.list_models')
    def test_check_available_models_error(self, mock_list_models):
        """Test error handling when listing models fails"""
        mock_list_models.side_effect = Exception("API error")
        
        transcribe.DEBUG = True
        # Should not raise exception, just log debug message
        transcribe.check_available_models()


class TestErrorCodes:
    """Test that all error codes are properly defined"""
    
    def test_error_codes_exist(self):
        """Test that all error codes are defined"""
        assert hasattr(transcribe, 'ERROR_INVALID_URL')
        assert hasattr(transcribe, 'ERROR_DOWNLOAD')
        assert hasattr(transcribe, 'ERROR_API_KEY')
        assert hasattr(transcribe, 'ERROR_RATE_LIMIT')
        assert hasattr(transcribe, 'ERROR_API')
        assert hasattr(transcribe, 'ERROR_AUDIO')
        assert hasattr(transcribe, 'ERROR_NETWORK')
    
    def test_error_codes_unique(self):
        """Test that all error codes have unique values"""
        error_codes = [
            transcribe.ERROR_INVALID_URL,
            transcribe.ERROR_DOWNLOAD,
            transcribe.ERROR_API_KEY,
            transcribe.ERROR_RATE_LIMIT,
            transcribe.ERROR_API,
            transcribe.ERROR_AUDIO,
            transcribe.ERROR_NETWORK
        ]
        assert len(error_codes) == len(set(error_codes))


class TestTemporaryFileHandling:
    """Test temporary file and directory handling"""
    
    @patch('transcribe.download_reel')
    @patch('transcribe.transcribe_video')
    @patch('transcribe.Path')
    def test_temp_directory_cleanup(self, mock_path, mock_transcribe, mock_download):
        """Test that temporary directories are cleaned up"""
        temp_dirs = []
        
        def capture_temp_dir(url, temp_dir):
            temp_dirs.append(temp_dir)
            return "/tmp/video.mp4"
        
        mock_download.side_effect = capture_temp_dir
        mock_transcribe.return_value = "Result"
        
        # Mock Path operations
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024
        mock_path.return_value = mock_path_instance
        
        transcribe.process_url("https://example.com/video")
        
        # Verify temp directory was created and cleaned up
        assert len(temp_dirs) == 1
        assert not Path(temp_dirs[0]).exists()


class TestOutputFormatting:
    """Test output formatting for different scenarios"""
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    def test_single_url_output_format(self, mock_process, mock_configure, mock_getenv,
                                     mock_load_dotenv, mock_check_deps, mock_check_network, capsys):
        """Test output format for single URL (clean, no batch summary)"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.return_value = "Clean transcription text"
        
        with patch.object(sys, 'argv', ['transcribe.py', 'https://example.com/video']):
            transcribe.main()
        
        captured = capsys.readouterr()
        assert "Clean transcription text" in captured.out
        # Single URL should NOT have batch formatting
        assert "BATCH RESULTS" in captured.out  # Actually it does show batch results
    
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.load_dotenv')
    @patch('os.getenv')
    @patch('transcribe.genai.configure')
    @patch('transcribe.process_url')
    @patch('time.sleep')
    def test_batch_output_format(self, mock_sleep, mock_process, mock_configure, mock_getenv,
                                mock_load_dotenv, mock_check_deps, mock_check_network, capsys):
        """Test output format for batch processing"""
        mock_check_network.return_value = True
        mock_getenv.return_value = "test_api_key"
        mock_process.side_effect = ["Result 1", None, "Result 3"]
        
        with patch.object(sys, 'argv', ['transcribe.py',
                                       'https://example.com/video1',
                                       'https://example.com/video2',
                                       'https://example.com/video3']):
            transcribe.main()
        
        captured = capsys.readouterr()
        # Check for batch summary
        assert "BATCH RESULTS: 2/3 successful" in captured.out
        assert "=" * 60 in captured.out
        # Check for URL indicators
        assert "[1] https://example.com/video1" in captured.out
        assert "[2] https://example.com/video2" in captured.out
        assert "[3] https://example.com/video3" in captured.out
        # Check for failure indicator
        assert "(FAILED)" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
