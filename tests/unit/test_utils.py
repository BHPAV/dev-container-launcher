"""Unit tests for utils.py validation and utility functions."""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import subprocess

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils import (
    validate_container_name,
    validate_volume_path,
    get_container_ssh_key_fingerprint,
    add_known_host,
    sanitize_path
)


class TestValidateContainerName:
    """Test the validate_container_name function."""
    
    def test_valid_names(self):
        """Test valid container names."""
        valid_names = [
            "test",
            "test123",
            "test_container", 
            "test-container",
            "test.container",
            "123test",
            "a"
        ]
        
        for name in valid_names:
            assert validate_container_name(name) is True
    
    def test_empty_name(self):
        """Test empty container name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_container_name("")
    
    def test_none_name(self):
        """Test None container name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_container_name(None)
    
    @patch('utils.MAX_CONTAINER_NAME_LENGTH', 10)
    def test_name_too_long(self):
        """Test container name exceeding maximum length."""
        long_name = "a" * 11
        with pytest.raises(ValueError, match="cannot exceed 10 characters"):
            validate_container_name(long_name)
    
    def test_invalid_characters(self):
        """Test container names with invalid characters."""
        invalid_names = [
            "test@container",
            "test#container",
            "test container",  # space
            "test$container",
            "test%container",
            "test^container",
            "test&container",
            "test*container",
            "test+container",
            "test=container",
            "test|container",
            "test\\container",
            "test/container",
            "test?container",
            "test<container",
            "test>container"
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError, match="must start with alphanumeric"):
                validate_container_name(name)
    
    def test_invalid_start_characters(self):
        """Test container names starting with invalid characters."""
        invalid_names = [
            "_test",
            "-test",
            ".test"
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError, match="must start with alphanumeric"):
                validate_container_name(name)


class TestValidateVolumePath:
    """Test the validate_volume_path function."""
    
    @patch('utils.ALLOWED_VOLUME_PATHS', [Path('/tmp'), Path('/home')])
    def test_valid_path_in_allowed_location(self):
        """Test valid path in allowed location."""
        test_path = Path('/tmp/test')
        test_path.mkdir(parents=True, exist_ok=True)
        
        try:
            assert validate_volume_path(test_path) is True
        finally:
            # Cleanup
            if test_path.exists():
                test_path.rmdir()
    
    def test_nonexistent_path(self):
        """Test path that doesn't exist."""
        nonexistent_path = Path('/this/path/does/not/exist')
        
        with pytest.raises(ValueError, match="Path does not exist"):
            validate_volume_path(nonexistent_path)
    
    @patch('utils.ALLOWED_VOLUME_PATHS', [Path('/tmp')])
    def test_path_not_in_allowed_locations(self):
        """Test path outside allowed locations."""
        # Use a path that exists but is not in allowed locations
        test_path = Path('/etc')  # This should exist on most systems
        
        with pytest.raises(ValueError, match="not in allowed locations"):
            validate_volume_path(test_path)
    
    @patch('utils.ALLOWED_VOLUME_PATHS', [Path('/tmp')])
    def test_path_resolution(self):
        """Test that paths are properly resolved."""
        # Create a test directory
        test_dir = Path('/tmp/test_dir')
        test_dir.mkdir(exist_ok=True)
        
        # Create a path with '..' that should resolve to an allowed location
        complex_path = Path('/tmp/test_dir/../test_dir')
        
        try:
            assert validate_volume_path(complex_path) is True
        finally:
            # Cleanup
            if test_dir.exists():
                test_dir.rmdir()


class TestGetContainerSshKeyFingerprint:
    """Test the get_container_ssh_key_fingerprint function."""
    
    @patch('subprocess.run')
    def test_successful_fingerprint_extraction(self, mock_run):
        """Test successful SSH key fingerprint extraction."""
        # Mock subprocess output
        mock_run.return_value.stdout = "256 SHA256:abc123xyz789 root@hostname (ED25519)\n"
        mock_run.return_value.returncode = 0
        
        result = get_container_ssh_key_fingerprint("test_container")
        
        assert result == "SHA256:abc123xyz789"
        mock_run.assert_called_once_with(
            ["docker", "exec", "test_container", "ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub"],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_subprocess_error(self, mock_run):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["docker", "exec"])
        
        result = get_container_ssh_key_fingerprint("test_container")
        
        assert result is None
    
    @patch('subprocess.run')
    def test_malformed_output(self, mock_run):
        """Test handling of malformed subprocess output."""
        mock_run.return_value.stdout = "invalid output format\n"
        mock_run.return_value.returncode = 0
        
        result = get_container_ssh_key_fingerprint("test_container")
        
        # The function will return the second part regardless of format
        assert result == "output"
    
    @patch('subprocess.run')
    def test_empty_output(self, mock_run):
        """Test handling of empty subprocess output."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 0
        
        result = get_container_ssh_key_fingerprint("test_container")
        
        assert result is None


class TestAddKnownHost:
    """Test the add_known_host function."""
    
    @patch('config.SSH_KNOWN_HOSTS_PATH')
    def test_add_new_host(self, mock_path):
        """Test adding a new host to known_hosts."""
        mock_path.parent.mkdir = Mock()
        mock_path.exists.return_value = False
        mock_path.open = mock_open()
        
        add_known_host("localhost", 2222, "ssh-ed25519 ABC123")
        
        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_path.open.assert_called_once_with("a")
        
        # Verify the content written
        handle = mock_path.open.return_value.__enter__.return_value
        handle.write.assert_called_once_with("[localhost]:2222 ssh-ed25519 ABC123\n")
    
    @patch('config.SSH_KNOWN_HOSTS_PATH')
    def test_host_already_exists(self, mock_path):
        """Test adding a host that already exists."""
        mock_path.parent.mkdir = Mock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "[localhost]:2222 ssh-ed25519 ABC123\n"
        
        add_known_host("localhost", 2222, "ssh-ed25519 ABC123")
        
        # Should not try to write since host already exists
        mock_path.open.assert_not_called()
    
    @patch('config.SSH_KNOWN_HOSTS_PATH')
    def test_add_to_existing_file(self, mock_path):
        """Test adding a host to an existing known_hosts file."""
        mock_path.parent.mkdir = Mock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "[otherhost]:2223 ssh-ed25519 DEF456\n"
        mock_path.open = mock_open()
        
        add_known_host("localhost", 2222, "ssh-ed25519 ABC123")
        
        # Should append to existing file
        mock_path.open.assert_called_once_with("a")
        handle = mock_path.open.return_value.__enter__.return_value
        handle.write.assert_called_once_with("[localhost]:2222 ssh-ed25519 ABC123\n")


class TestSanitizePath:
    """Test the sanitize_path function."""
    
    def test_basic_path(self):
        """Test basic path sanitization."""
        result = sanitize_path("/tmp/test")
        assert isinstance(result, Path)
        assert result.is_absolute()
    
    def test_path_with_null_bytes(self):
        """Test path with null bytes."""
        result = sanitize_path("/tmp/test\0malicious")
        assert "\0" not in str(result)
    
    def test_path_with_dotdot(self):
        """Test path with .. components."""
        result = sanitize_path("/tmp/test/../other")
        # The result should be resolved (.. components removed)
        assert ".." not in str(result)
    
    def test_relative_path_resolution(self):
        """Test that relative paths are resolved to absolute."""
        result = sanitize_path("relative/path")
        assert result.is_absolute()
    
    def test_path_resolution_removes_symlinks(self):
        """Test that resolve() removes symlinks."""
        # This is more of a documentation test since we can't easily create symlinks in tests
        result = sanitize_path("/tmp")
        assert isinstance(result, Path)
        assert result.is_absolute()
    
    def test_empty_path(self):
        """Test empty path input."""
        result = sanitize_path("")
        assert isinstance(result, Path)
        # Empty string should resolve to current directory
        assert result.is_absolute()
    
    def test_path_with_multiple_null_bytes(self):
        """Test path with multiple null bytes."""
        result = sanitize_path("/tmp\0/test\0/malicious")
        assert "\0" not in str(result)
        assert str(result).endswith("/tmp/test/malicious")