"""Integration tests for container lifecycle and tracking/deletion features."""

import pytest
import docker
import time
from pathlib import Path

from scripts import devctl
from config import CONTAINER_PREFIX, IMAGE_TAG
import tempfile
import shutil


@pytest.mark.integration
@pytest.mark.slow
class TestContainerLifecycle:
    """Integration tests for complete container lifecycle."""
    
    def test_container_create_track_delete_cycle(self, docker_client, container_cleanup_list):
        """Test complete lifecycle: create -> track -> delete."""
        container_name = "test_lifecycle"
        container_cleanup_list.append(container_name)
        
        # Ensure container doesn't exist
        try:
            container = docker_client.containers.get(f"{CONTAINER_PREFIX}{container_name}")
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        
        # Create container - use /tmp which is in allowed paths
        test_volume = Path("/tmp/test_devcontainer")
        test_volume.mkdir(exist_ok=True)
        container, port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
        
        # Verify container is tracked
        containers = devctl.list_all()
        container_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        assert container_name in container_names
        
        # Get container info
        info = devctl.get_container_info(container_name)
        assert info["name"] == f"{CONTAINER_PREFIX}{container_name}"
        assert info["status"] == "running"
        assert info["port"] == str(port)
        
        # Delete container
        devctl.remove_container(container_name, force=True)
        
        # Verify container is no longer tracked
        containers = devctl.list_all()
        container_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        assert container_name not in container_names
        
        # Verify container doesn't exist in Docker
        with pytest.raises(docker.errors.NotFound):
            docker_client.containers.get(f"{CONTAINER_PREFIX}{container_name}")
    
    def test_multiple_container_tracking(self, docker_client, container_cleanup_list):
        """Test tracking multiple containers simultaneously."""
        num_containers = 3
        container_names = [f"test_multi_{i}" for i in range(num_containers)]
        container_cleanup_list.extend(container_names)
        
        # Create multiple containers
        created_containers = []
        for name in container_names:
            try:
                test_volume = Path(f"/tmp/test_multi_{name}")
                test_volume.mkdir(exist_ok=True)
                container, port = devctl.create(name, image=IMAGE_TAG, volume=test_volume)
                created_containers.append((name, container, port))
            except Exception:
                # Cleanup on failure
                for n in container_names:
                    try:
                        devctl.remove_container(n, force=True)
                    except:
                        pass
                raise
        
        # Verify all containers are tracked
        containers = devctl.list_all()
        tracked_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        
        for name in container_names:
            assert name in tracked_names
        
        # Verify each container's info
        for name, container, expected_port in created_containers:
            info = devctl.get_container_info(name)
            assert info["status"] == "running"
            assert info["port"] == str(expected_port)
        
        # Remove all containers
        for name in container_names:
            devctl.remove_container(name, force=True)
        
        # Verify all containers are removed
        containers = devctl.list_all()
        tracked_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        
        for name in container_names:
            assert name not in tracked_names
    
    def test_container_stop_start_tracking(self, docker_client, container_cleanup_list):
        """Test container tracking through stop/start cycles."""
        container_name = "test_stop_start"
        container_cleanup_list.append(container_name)
        
        # Create container
        test_volume = Path("/tmp/test_stop_start")
        test_volume.mkdir(exist_ok=True)
        container, port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
        
        # Verify running status
        info = devctl.get_container_info(container_name)
        assert info["status"] == "running"
        
        # Stop container
        devctl.stop_container(container_name)
        time.sleep(1)  # Give Docker time to update status
        
        # Verify stopped status
        info = devctl.get_container_info(container_name)
        assert info["status"] in ["exited", "stopped"]
        
        # Verify container is still tracked when stopped
        containers = devctl.list_all()
        tracked_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        assert container_name in tracked_names
        
        # Start container
        devctl.start_container(container_name)
        time.sleep(2)  # Give container time to start
        
        # Verify running status again
        info = devctl.get_container_info(container_name)
        assert info["status"] == "running"
        
        # Clean up
        devctl.remove_container(container_name, force=True)
    
    def test_force_delete_running_container(self, docker_client, container_cleanup_list):
        """Test force deletion of a running container."""
        container_name = "test_force_delete"
        container_cleanup_list.append(container_name)
        
        # Create and verify container is running
        test_volume = Path("/tmp/test_force_delete")
        test_volume.mkdir(exist_ok=True)
        container, port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
        assert container.status == "running"
        
        # Force delete without stopping
        devctl.remove_container(container_name, force=True)
        
        # Verify container is removed
        with pytest.raises(docker.errors.NotFound):
            docker_client.containers.get(f"{CONTAINER_PREFIX}{container_name}")
        
        # Verify container is not tracked
        containers = devctl.list_all()
        tracked_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        assert container_name not in tracked_names
    
    def test_container_tracking_persistence(self, docker_client, container_cleanup_list):
        """Test that container tracking persists across list_all calls."""
        container_name = "test_persistence"
        container_cleanup_list.append(container_name)
        
        # Create container
        test_volume = Path("/tmp/test_persistence")
        test_volume.mkdir(exist_ok=True)
        container, port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
        
        # Multiple list_all calls should return consistent results
        for _ in range(3):
            containers = devctl.list_all()
            tracked_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
            assert container_name in tracked_names
            
            # Verify container details remain consistent
            info = devctl.get_container_info(container_name)
            assert info["port"] == str(port)
        
        # Clean up
        devctl.remove_container(container_name, force=True)
    
    def test_delete_stopped_container(self, docker_client, container_cleanup_list):
        """Test deletion of a stopped container."""
        container_name = "test_delete_stopped"
        container_cleanup_list.append(container_name)
        
        # Create and stop container
        test_volume = Path("/tmp/test_delete_stopped")
        test_volume.mkdir(exist_ok=True)
        container, port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
        devctl.stop_container(container_name)
        time.sleep(1)
        
        # Delete stopped container (without force)
        devctl.remove_container(container_name, force=False)
        
        # Verify container is removed
        with pytest.raises(docker.errors.NotFound):
            docker_client.containers.get(f"{CONTAINER_PREFIX}{container_name}")
        
        # Verify not tracked
        containers = devctl.list_all()
        tracked_names = [c.name.replace(CONTAINER_PREFIX, "") for c in containers]
        assert container_name not in tracked_names
    
    def test_container_tracking_with_label_filter(self, docker_client):
        """Test that only containers with correct label are tracked."""
        # Create a container without the devcontainer label
        other_container = docker_client.containers.run(
            IMAGE_TAG,
            name="non_devcontainer_test",
            detach=True,
            tty=True,
            remove=False
        )
        
        try:
            # Create a devcontainer
            container_name = "test_label_filter"
            test_volume = Path("/tmp/test_label_filter")
            test_volume.mkdir(exist_ok=True)
            container, port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
            
            try:
                # List all containers
                containers = devctl.list_all()
                tracked_names = [c.name for c in containers]
                
                # Verify only labeled container is tracked
                assert f"{CONTAINER_PREFIX}{container_name}" in tracked_names
                assert "non_devcontainer_test" not in tracked_names
                
            finally:
                # Clean up devcontainer
                devctl.remove_container(container_name, force=True)
        finally:
            # Clean up non-labeled container
            other_container.stop()
            other_container.remove()
    
    def test_container_info_after_restart(self, docker_client, container_cleanup_list):
        """Test container info remains accurate after Docker restart simulation."""
        container_name = "test_restart_info"
        container_cleanup_list.append(container_name)
        
        # Create container
        test_volume = Path("/tmp/test_restart_info")
        test_volume.mkdir(exist_ok=True)
        container, original_port = devctl.create(container_name, image=IMAGE_TAG, volume=test_volume)
        original_id = container.short_id
        
        # Get initial info
        info_before = devctl.get_container_info(container_name)
        
        # Stop and start to simulate restart
        devctl.stop_container(container_name)
        time.sleep(1)
        devctl.start_container(container_name)
        time.sleep(2)
        
        # Get info after restart
        info_after = devctl.get_container_info(container_name)
        
        # Verify consistency
        assert info_after["id"] == original_id
        assert info_after["port"] == str(original_port)
        assert info_after["status"] == "running"
        
        # Clean up
        devctl.remove_container(container_name, force=True)