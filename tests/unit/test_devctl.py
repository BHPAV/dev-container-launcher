"""Unit tests for devctl.py core functions."""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import docker

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from scripts.devctl import _free_port, build_image, create


class TestFreePort:
    """Test the _free_port function."""
    
    def test_free_port_returns_valid_port(self):
        """Test that _free_port returns a valid port number."""
        port = _free_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535
    
    def test_free_port_returns_available_port(self):
        """Test that returned port is actually available."""
        port = _free_port()
        
        # Try to bind to the port to verify it's available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            # If this doesn't raise an exception, the port is available
    
    @patch('socket.socket')
    def test_free_port_handles_os_error(self, mock_socket):
        """Test that _free_port handles OSError appropriately."""
        mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError("No ports available")
        
        with pytest.raises(OSError):
            _free_port()


class TestBuildImage:
    """Test the build_image function."""
    
    @patch('scripts.devctl.docker_client')
    def test_build_image_success(self, mock_docker_client):
        """Test successful image building."""
        mock_image = Mock()
        mock_logs = [
            {'stream': 'Step 1/5 : FROM ubuntu:22.04\n'},
            {'stream': 'Successfully built abc123\n'}
        ]
        mock_docker_client.images.build.return_value = (mock_image, mock_logs)
        
        # Should not raise an exception
        build_image("test-image", "docker/Dockerfile")
        
        mock_docker_client.images.build.assert_called_once_with(
            path=".",
            dockerfile="docker/Dockerfile",
            tag="test-image",
            quiet=False
        )
    
    @patch('scripts.devctl.docker_client')
    def test_build_image_build_error(self, mock_docker_client):
        """Test handling of Docker build errors."""
        mock_docker_client.images.build.side_effect = docker.errors.BuildError("Build failed", "")
        
        with pytest.raises(docker.errors.BuildError):
            build_image("test-image", "docker/Dockerfile")
    
    @patch('scripts.devctl.docker_client')
    def test_build_image_uses_defaults(self, mock_docker_client):
        """Test that build_image uses default parameters."""
        mock_image = Mock()
        mock_docker_client.images.build.return_value = (mock_image, [])
        
        with patch('scripts.devctl.IMAGE_TAG', 'devbox:latest'):
            build_image()
            
            mock_docker_client.images.build.assert_called_once_with(
                path=".",
                dockerfile="docker/Dockerfile",
                tag="devbox:latest",
                quiet=False
            )


class TestCreate:
    """Test the create function."""
    
    @patch('scripts.devctl.docker_client')
    @patch('scripts.devctl.validate_container_name')
    @patch('scripts.devctl.validate_volume_path')
    @patch('scripts.devctl.sanitize_path')
    @patch('scripts.devctl._free_port')
    @patch('scripts.devctl._ensure_ssh_host')
    def test_create_success(self, mock_ssh, mock_free_port, mock_sanitize, mock_validate_volume, 
                           mock_validate_name, mock_docker_client):
        """Test successful container creation."""
        # Setup mocks
        mock_free_port.return_value = 2222
        mock_sanitize.return_value = Path("/test/path")
        mock_validate_name.return_value = True
        mock_validate_volume.return_value = True
        
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        mock_docker_client.images.get.return_value = Mock()
        
        mock_container = Mock()
        mock_docker_client.containers.run.return_value = mock_container
        
        with patch('scripts.devctl.CONTAINER_PREFIX', 'dev_'):
            container, port = create("test-container", "test-image", Path("/test/path"))
            
            assert container == mock_container
            assert port == 2222
            mock_validate_name.assert_called_once_with("test-container")
            mock_validate_volume.assert_called_once_with(Path("/test/path"))
    
    @patch('scripts.devctl.validate_container_name')
    def test_create_invalid_name(self, mock_validate_name):
        """Test create function with invalid container name."""
        mock_validate_name.side_effect = ValueError("Invalid name")
        
        with pytest.raises(ValueError, match="Invalid name"):
            create("invalid-name")
    
    @patch('scripts.devctl.docker_client')
    @patch('scripts.devctl.validate_container_name')
    @patch('scripts.devctl.validate_volume_path')
    @patch('scripts.devctl.sanitize_path')
    def test_create_existing_container(self, mock_sanitize, mock_validate_volume, 
                                      mock_validate_name, mock_docker_client):
        """Test create function when container already exists."""
        mock_validate_name.return_value = True
        mock_validate_volume.return_value = True
        mock_sanitize.return_value = Path("/test/path")
        
        # Container already exists
        mock_docker_client.containers.get.return_value = Mock()
        
        with patch('scripts.devctl.CONTAINER_PREFIX', 'dev_'):
            with pytest.raises(ValueError, match="already exists"):
                create("existing-container")
    
    @patch('scripts.devctl.docker_client')
    @patch('scripts.devctl.validate_container_name')
    @patch('scripts.devctl.validate_volume_path')
    @patch('scripts.devctl.sanitize_path')
    def test_create_missing_image(self, mock_sanitize, mock_validate_volume, 
                                 mock_validate_name, mock_docker_client):
        """Test create function when image doesn't exist."""
        mock_validate_name.return_value = True
        mock_validate_volume.return_value = True
        mock_sanitize.return_value = Path("/test/path")
        
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        mock_docker_client.images.get.side_effect = docker.errors.ImageNotFound("Image not found")
        
        with pytest.raises(ValueError, match="not found"):
            create("test-container", "missing-image")
    
    @patch('scripts.devctl.sanitize_path')
    @patch('scripts.devctl.validate_container_name')
    def test_create_uses_cwd_default(self, mock_validate_name, mock_sanitize):
        """Test that create uses current working directory as default volume."""
        mock_validate_name.return_value = True
        mock_sanitize.return_value = Path.cwd()
        
        with patch('scripts.devctl.validate_volume_path') as mock_validate_volume:
            mock_validate_volume.return_value = True
            
            with patch('scripts.devctl.docker_client') as mock_docker_client:
                mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
                mock_docker_client.images.get.side_effect = docker.errors.ImageNotFound("Image not found")
                
                with pytest.raises(ValueError):  # Will fail on missing image, but that's expected
                    create("test-container")
                
                # Verify that sanitize_path was called with current directory
                mock_sanitize.assert_called_once_with(str(Path.cwd()))