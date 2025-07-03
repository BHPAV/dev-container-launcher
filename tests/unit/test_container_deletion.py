"""Unit tests for container deletion functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import docker
from pathlib import Path

from scripts import devctl
from config import CONTAINER_PREFIX, SSH_CONFIG_PATH


class TestContainerDeletion:
    """Test container deletion functionality."""
    
    @pytest.mark.unit
    def test_remove_container_success(self, mock_docker_client):
        """Test successful container removal."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        with patch('scripts.devctl._remove_ssh_host') as mock_remove_ssh:
            devctl.remove_container("test", force=False)
        
        mock_docker_client.containers.get.assert_called_once_with("dev_test")
        mock_container.remove.assert_called_once_with(force=False)
        mock_remove_ssh.assert_called_once_with("test")
    
    @pytest.mark.unit
    def test_remove_container_force(self, mock_docker_client):
        """Test force removal of running container."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.status = "running"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        with patch('scripts.devctl._remove_ssh_host') as mock_remove_ssh:
            devctl.remove_container("test", force=True)
        
        mock_container.remove.assert_called_once_with(force=True)
        mock_remove_ssh.assert_called_once_with("test")
    
    @pytest.mark.unit
    def test_remove_container_not_found(self, mock_docker_client):
        """Test removal of non-existent container."""
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        
        with pytest.raises(ValueError, match="Container dev_test not found"):
            devctl.remove_container("test")
    
    @pytest.mark.unit
    def test_remove_container_api_error(self, mock_docker_client):
        """Test handling of Docker API errors during removal."""
        mock_container = Mock()
        mock_container.remove.side_effect = docker.errors.APIError("API Error")
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        with pytest.raises(docker.errors.APIError):
            devctl.remove_container("test")
    
    @pytest.mark.unit
    def test_remove_ssh_host_entry(self):
        """Test SSH config entry removal."""
        ssh_config_content = """Host other
  HostName localhost
  Port 2221
  User dev

Host test
  HostName localhost
  Port 2222
  User dev
  StrictHostKeyChecking no

Host another
  HostName localhost
  Port 2223
  User dev
"""
        expected_content = """Host other
  HostName localhost
  Port 2221
  User dev

Host another
  HostName localhost
  Port 2223
  User dev
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=ssh_config_content), \
             patch('pathlib.Path.write_text') as mock_write:
            
            devctl._remove_ssh_host("test")
            
            # Check that the correct content was written
            written_content = mock_write.call_args[0][0]
            assert "Host test" not in written_content
            assert "Port 2222" not in written_content
            assert "Host other" in written_content
            assert "Host another" in written_content
    
    @pytest.mark.unit
    def test_remove_ssh_host_no_config_file(self):
        """Test SSH host removal when config file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            # Should not raise error
            devctl._remove_ssh_host("test")
    
    @pytest.mark.unit
    def test_remove_ssh_host_io_error(self):
        """Test handling of IO errors during SSH config update."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', side_effect=IOError("Read error")):
            
            # Should not raise error (container already removed)
            devctl._remove_ssh_host("test")
    
    @pytest.mark.unit
    def test_stop_container_success(self, mock_docker_client):
        """Test successful container stop."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.status = "running"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        devctl.stop_container("test")
        
        mock_docker_client.containers.get.assert_called_once_with("dev_test")
        mock_container.stop.assert_called_once()
    
    @pytest.mark.unit
    def test_stop_container_already_stopped(self, mock_docker_client):
        """Test stopping an already stopped container."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.status = "exited"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        devctl.stop_container("test")
        
        # Should not call stop() on already stopped container
        mock_container.stop.assert_not_called()
    
    @pytest.mark.unit
    def test_stop_container_not_found(self, mock_docker_client):
        """Test stopping non-existent container."""
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        
        with pytest.raises(ValueError, match="Container dev_test not found"):
            devctl.stop_container("test")
    
    @pytest.mark.unit
    def test_start_container_success(self, mock_docker_client):
        """Test successful container start."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.status = "exited"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        devctl.start_container("test")
        
        mock_docker_client.containers.get.assert_called_once_with("dev_test")
        mock_container.start.assert_called_once()
    
    @pytest.mark.unit
    def test_start_container_already_running(self, mock_docker_client):
        """Test starting an already running container."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.status = "running"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        devctl.start_container("test")
        
        # Should not call start() on already running container
        mock_container.start.assert_not_called()
    
    @pytest.mark.unit
    def test_remove_ssh_host_complex_config(self):
        """Test SSH config removal with complex configuration."""
        ssh_config_content = """# Global settings
Host *
  ServerAliveInterval 60
  ServerAliveCountMax 3

Host test
  HostName localhost
  Port 2222
  User dev
  ForwardAgent yes
  StrictHostKeyChecking no
  # Custom settings
  LocalForward 8080 localhost:8080

Host test-other
  HostName localhost
  Port 2223
  User dev

Host production
  HostName prod.example.com
  Port 22
  User admin
  IdentityFile ~/.ssh/prod_key
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=ssh_config_content), \
             patch('pathlib.Path.write_text') as mock_write:
            
            devctl._remove_ssh_host("test")
            
            written_content = mock_write.call_args[0][0]
            # Ensure only the specific host entry is removed
            assert "Host test\n" not in written_content
            assert "Port 2222" not in written_content
            assert "LocalForward 8080" not in written_content
            # Ensure other entries remain
            assert "Host *" in written_content
            assert "Host test-other" in written_content
            assert "Host production" in written_content
            assert "ServerAliveInterval 60" in written_content
    
    @pytest.mark.unit
    def test_remove_container_cleanup_sequence(self, mock_docker_client):
        """Test that container removal follows correct cleanup sequence."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        call_sequence = []
        
        def track_remove(*args, **kwargs):
            call_sequence.append("container_remove")
        
        def track_ssh_remove(*args):
            call_sequence.append("ssh_remove")
        
        mock_container.remove.side_effect = track_remove
        
        with patch('scripts.devctl._remove_ssh_host', side_effect=track_ssh_remove):
            devctl.remove_container("test")
        
        # Verify cleanup happens in correct order
        assert call_sequence == ["container_remove", "ssh_remove"]
    
    @pytest.mark.unit
    def test_remove_container_ssh_cleanup_on_docker_error(self, mock_docker_client):
        """Test SSH config is not cleaned up if container removal fails."""
        mock_container = Mock()
        mock_container.remove.side_effect = docker.errors.APIError("Cannot remove running container")
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        with patch('scripts.devctl._remove_ssh_host') as mock_remove_ssh:
            with pytest.raises(docker.errors.APIError):
                devctl.remove_container("test")
            
            # SSH config should not be removed if container removal failed
            mock_remove_ssh.assert_not_called()
    
    @pytest.mark.unit
    def test_batch_container_removal(self, mock_docker_client):
        """Test removing multiple containers in sequence."""
        containers = []
        for i in range(3):
            mock_container = Mock()
            mock_container.name = f"dev_test{i}"
            containers.append(mock_container)
        
        def get_container(name):
            for c in containers:
                if c.name == name:
                    return c
            raise docker.errors.NotFound("Container not found")
        
        mock_docker_client.containers.get.side_effect = get_container
        
        with patch('scripts.devctl._remove_ssh_host'):
            for i in range(3):
                devctl.remove_container(f"test{i}")
                containers[i].remove.assert_called_once()