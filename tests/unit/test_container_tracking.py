"""Unit tests for container tracking functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import docker
from pathlib import Path

from scripts import devctl
from config import CONTAINER_PREFIX, DEVCONTAINER_LABEL


class TestContainerTracking:
    """Test container tracking functionality."""
    
    @pytest.mark.unit
    def test_list_all_returns_empty_list_when_no_containers(self, mock_docker_client):
        """Test list_all returns empty list when no containers exist."""
        mock_docker_client.containers.list.return_value = []
        
        result = devctl.list_all()
        
        assert result == []
        mock_docker_client.containers.list.assert_called_once_with(
            all=True,
            filters={"label": "devcontainer=true"}
        )
    
    @pytest.mark.unit
    def test_list_all_returns_containers_with_correct_label(self, mock_docker_client):
        """Test list_all returns only containers with devcontainer label."""
        # Create mock containers
        container1 = Mock()
        container1.name = "dev_test1"
        container1.status = "running"
        container1.ports = {"22/tcp": [{"HostPort": "2222"}]}
        container1.image.tags = ["devbox:latest"]
        
        container2 = Mock()
        container2.name = "dev_test2"
        container2.status = "exited"
        container2.ports = {"22/tcp": [{"HostPort": "2223"}]}
        container2.image.tags = ["python:3.12"]
        
        mock_docker_client.containers.list.return_value = [container1, container2]
        
        result = devctl.list_all()
        
        assert len(result) == 2
        assert result[0].name == "dev_test1"
        assert result[1].name == "dev_test2"
        mock_docker_client.containers.list.assert_called_once_with(
            all=True,
            filters={"label": "devcontainer=true"}
        )
    
    @pytest.mark.unit
    def test_list_all_handles_docker_api_error(self, mock_docker_client):
        """Test list_all handles Docker API errors gracefully."""
        mock_docker_client.containers.list.side_effect = docker.errors.APIError("API Error")
        
        with pytest.raises(docker.errors.APIError):
            devctl.list_all()
    
    @pytest.mark.unit
    def test_get_container_info_returns_correct_data(self, mock_docker_client):
        """Test get_container_info returns correct container information."""
        # Create mock container
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.short_id = "abc123"
        mock_container.status = "running"
        mock_container.ports = {"22/tcp": [{"HostPort": "2222"}]}
        mock_container.image.tags = ["devbox:latest"]
        mock_container.attrs = {
            "Created": "2024-01-01T00:00:00Z",
            "Mounts": [{
                "Type": "bind",
                "Source": "/home/user/project",
                "Destination": "/workspace"
            }]
        }
        
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        result = devctl.get_container_info("test")
        
        assert result["name"] == "dev_test"
        assert result["id"] == "abc123"
        assert result["status"] == "running"
        assert result["port"] == "2222"
        assert result["image"] == "devbox:latest"
        assert result["created"] == "2024-01-01T00:00:00Z"
        assert len(result["volumes"]) == 1
        
        mock_docker_client.containers.get.assert_called_once_with("dev_test")
    
    @pytest.mark.unit
    def test_get_container_info_handles_missing_port(self, mock_docker_client):
        """Test get_container_info handles containers without SSH port."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.short_id = "abc123"
        mock_container.status = "running"
        mock_container.ports = {}  # No ports exposed
        mock_container.image.tags = []
        mock_container.image.short_id = "sha256:xyz"
        mock_container.attrs = {"Created": "2024-01-01T00:00:00Z"}
        
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        result = devctl.get_container_info("test")
        
        assert result["port"] is None
        assert result["image"] == "sha256:xyz"
    
    @pytest.mark.unit
    def test_get_container_info_raises_error_for_nonexistent_container(self, mock_docker_client):
        """Test get_container_info raises error for non-existent container."""
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        
        with pytest.raises(ValueError, match="Container dev_test not found"):
            devctl.get_container_info("test")
    
    @pytest.mark.unit
    def test_container_name_formatting(self, mock_docker_client):
        """Test container names are properly formatted with prefix."""
        mock_container = Mock()
        mock_container.name = "dev_myproject"
        mock_container.short_id = "abc123"
        mock_container.status = "running"
        mock_container.ports = {}
        mock_container.image.tags = ["devbox:latest"]
        mock_container.attrs = {"Created": "2024-01-01T00:00:00Z"}
        
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        # Test that the prefix is correctly added
        devctl.get_container_info("myproject")
        mock_docker_client.containers.get.assert_called_with("dev_myproject")
    
    @pytest.mark.unit
    def test_list_all_with_various_container_states(self, mock_docker_client):
        """Test list_all handles containers in different states."""
        states = ["running", "exited", "paused", "restarting", "removing", "dead"]
        containers = []
        
        for i, state in enumerate(states):
            container = Mock()
            container.name = f"dev_test{i}"
            container.status = state
            container.ports = {"22/tcp": [{"HostPort": str(2222 + i)}]}
            container.image.tags = ["devbox:latest"]
            containers.append(container)
        
        mock_docker_client.containers.list.return_value = containers
        
        result = devctl.list_all()
        
        assert len(result) == len(states)
        for i, container in enumerate(result):
            assert container.status == states[i]
    
    @pytest.mark.unit
    def test_container_tracking_with_labels(self, mock_docker_client):
        """Test that containers are tracked using the correct label."""
        # This test verifies the label-based tracking mechanism
        devctl.list_all()
        
        # Verify the correct filter is used
        call_args = mock_docker_client.containers.list.call_args
        assert call_args[1]["filters"]["label"] == "devcontainer=true"
        assert call_args[1]["all"] is True  # Should list all containers, not just running
    
    @pytest.mark.unit
    def test_get_container_info_with_multiple_volumes(self, mock_docker_client):
        """Test get_container_info with multiple volume mounts."""
        mock_container = Mock()
        mock_container.name = "dev_test"
        mock_container.short_id = "abc123"
        mock_container.status = "running"
        mock_container.ports = {"22/tcp": [{"HostPort": "2222"}]}
        mock_container.image.tags = ["devbox:latest"]
        mock_container.attrs = {
            "Created": "2024-01-01T00:00:00Z",
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": "/home/user/project",
                    "Destination": "/workspace"
                },
                {
                    "Type": "bind",
                    "Source": "/home/user/.ssh",
                    "Destination": "/home/dev/.ssh"
                },
                {
                    "Type": "volume",
                    "Name": "dev_test_data",
                    "Destination": "/data"
                }
            ]
        }
        
        # Reset mock to override default side effect
        mock_docker_client.containers.get.side_effect = None
        mock_docker_client.containers.get.return_value = mock_container
        
        result = devctl.get_container_info("test")
        
        assert len(result["volumes"]) == 3
        assert result["volumes"][0]["Source"] == "/home/user/project"
        assert result["volumes"][1]["Source"] == "/home/user/.ssh"
        assert result["volumes"][2]["Name"] == "dev_test_data"