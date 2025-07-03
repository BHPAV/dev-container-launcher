"""Integration tests for Docker operations."""

import pytest
import docker
import time
from pathlib import Path
import subprocess
import tempfile
import shutil

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from devctl import create, build_image, list_all, stop_container, start_container, remove_container


@pytest.fixture(scope="module")
def docker_client():
    """Docker client fixture."""
    try:
        client = docker.from_env()
        # Test connection
        client.ping()
        return client
    except docker.errors.DockerException:
        pytest.skip("Docker not available")


@pytest.fixture(scope="module")
def test_image(docker_client):
    """Build a test image for integration tests."""
    dockerfile_content = """
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y openssh-server sudo
RUN mkdir /var/run/sshd

# Create dev user
RUN useradd -m -s /bin/bash dev
RUN echo 'dev:dev' | chpasswd
RUN usermod -aG sudo dev

# SSH configuration
RUN mkdir -p /home/dev/.ssh
RUN ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N ''
RUN chmod 600 /etc/ssh/ssh_host_ed25519_key
RUN chmod 644 /etc/ssh/ssh_host_ed25519_key.pub

COPY authorized_keys /home/dev/.ssh/authorized_keys
RUN chown -R dev:dev /home/dev/.ssh
RUN chmod 700 /home/dev/.ssh
RUN chmod 600 /home/dev/.ssh/authorized_keys

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
"""
    
    # Create temporary directory for build context
    with tempfile.TemporaryDirectory() as temp_dir:
        dockerfile_path = Path(temp_dir) / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        # Create dummy authorized_keys file
        authorized_keys_path = Path(temp_dir) / "authorized_keys"
        authorized_keys_path.write_text("# Test key placeholder\n")
        
        # Build the image
        image, _ = docker_client.images.build(
            path=str(temp_dir),
            tag="test-devbox:latest",
            rm=True
        )
        
        yield "test-devbox:latest"
        
        # Cleanup
        try:
            docker_client.images.remove("test-devbox:latest", force=True)
        except docker.errors.ImageNotFound:
            pass


@pytest.fixture
def temp_volume():
    """Create a temporary volume directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def container_cleanup():
    """Cleanup containers after tests."""
    containers_to_cleanup = []
    
    def add_container(name):
        containers_to_cleanup.append(name)
    
    yield add_container
    
    # Cleanup
    client = docker.from_env()
    for container_name in containers_to_cleanup:
        try:
            container = client.containers.get(f"dev_{container_name}")
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass


class TestDockerOperations:
    """Integration tests for Docker operations."""
    
    def test_create_container_success(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test successful container creation."""
        container_name = "test-create-success"
        container_cleanup(container_name)
        
        # Create container
        container, port = create(container_name, test_image, temp_volume)
        
        assert container is not None
        assert isinstance(port, int)
        assert 1024 <= port <= 65535
        
        # Verify container was created
        created_container = docker_client.containers.get(f"dev_{container_name}")
        assert created_container.status in ["created", "running"]
        
        # Verify labels
        labels = created_container.labels
        assert labels.get("devcontainer") == "true"
        assert labels.get("devcontainer.name") == container_name
    
    def test_create_duplicate_container_fails(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test that creating duplicate containers fails."""
        container_name = "test-duplicate"
        container_cleanup(container_name)
        
        # Create first container
        create(container_name, test_image, temp_volume)
        
        # Try to create duplicate - should fail
        with pytest.raises(ValueError, match="already exists"):
            create(container_name, test_image, temp_volume)
    
    def test_create_with_invalid_image_fails(self, temp_volume):
        """Test creating container with non-existent image."""
        with pytest.raises(ValueError, match="not found"):
            create("test-invalid-image", "nonexistent:latest", temp_volume)
    
    def test_list_containers(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test listing containers."""
        container_name = "test-list"
        container_cleanup(container_name)
        
        # Create a container
        create(container_name, test_image, temp_volume)
        
        # List containers
        containers = list_all()
        
        # Find our container
        found_container = None
        for container in containers:
            if container["name"] == container_name:
                found_container = container
                break
        
        assert found_container is not None
        assert found_container["status"] in ["created", "running"]
        assert found_container["image"] == test_image
        assert "port" in found_container
    
    def test_stop_start_container(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test stopping and starting containers."""
        container_name = "test-stop-start"
        container_cleanup(container_name)
        
        # Create and start container
        create(container_name, test_image, temp_volume)
        
        # Wait for container to be running
        time.sleep(2)
        
        # Stop container
        stop_container(container_name)
        
        # Verify container is stopped
        container = docker_client.containers.get(f"dev_{container_name}")
        assert container.status == "exited"
        
        # Start container
        start_container(container_name)
        
        # Wait for container to start
        time.sleep(2)
        
        # Verify container is running
        container.reload()
        assert container.status == "running"
    
    def test_remove_container(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test removing containers."""
        container_name = "test-remove"
        
        # Create container
        create(container_name, test_image, temp_volume)
        
        # Remove container
        remove_container(container_name)
        
        # Verify container is removed
        with pytest.raises(docker.errors.NotFound):
            docker_client.containers.get(f"dev_{container_name}")
    
    def test_remove_running_container_with_force(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test force removing running containers."""
        container_name = "test-force-remove"
        
        # Create container
        create(container_name, test_image, temp_volume)
        
        # Force remove container (should stop and remove)
        remove_container(container_name, force=True)
        
        # Verify container is removed
        with pytest.raises(docker.errors.NotFound):
            docker_client.containers.get(f"dev_{container_name}")
    
    @pytest.mark.slow
    def test_container_port_allocation(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test that multiple containers get different ports."""
        container_names = ["test-port-1", "test-port-2", "test-port-3"]
        ports = []
        
        for name in container_names:
            container_cleanup(name)
            _, port = create(name, test_image, temp_volume)
            ports.append(port)
        
        # All ports should be different
        assert len(set(ports)) == len(ports)
        
        # All ports should be in valid range
        for port in ports:
            assert 1024 <= port <= 65535
    
    @pytest.mark.slow
    def test_container_ssh_accessibility(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test that containers are accessible via SSH."""
        container_name = "test-ssh"
        container_cleanup(container_name)
        
        # Create container
        container, port = create(container_name, test_image, temp_volume)
        
        # Wait for SSH to be ready
        time.sleep(5)
        
        # Test SSH connection (without authentication, just connection)
        try:
            result = subprocess.run(
                ["nc", "-z", "localhost", str(port)],
                capture_output=True,
                timeout=5
            )
            # Port should be open (nc returns 0 if connection successful)
            assert result.returncode == 0
        except subprocess.TimeoutExpired:
            pytest.fail("SSH port not accessible within timeout")
        except FileNotFoundError:
            pytest.skip("netcat (nc) not available for SSH port test")
    
    def test_volume_mounting(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test that volumes are properly mounted."""
        container_name = "test-volume"
        container_cleanup(container_name)
        
        # Create test file in volume
        test_file = temp_volume / "test.txt"
        test_file.write_text("Hello from host!")
        
        # Create container
        container, _ = create(container_name, test_image, temp_volume)
        
        # Check if volume is mounted correctly
        mounts = container.attrs["Mounts"]
        workspace_mount = None
        for mount in mounts:
            if mount["Destination"] == "/workspace":
                workspace_mount = mount
                break
        
        assert workspace_mount is not None
        assert workspace_mount["Type"] == "bind"
        assert workspace_mount["Source"] == str(temp_volume)


class TestContainerLifecycle:
    """Integration tests for complete container lifecycle."""
    
    def test_complete_lifecycle(self, docker_client, test_image, temp_volume, container_cleanup):
        """Test complete container lifecycle: create -> stop -> start -> remove."""
        container_name = "test-lifecycle"
        container_cleanup(container_name)
        
        # Create
        container, port = create(container_name, test_image, temp_volume)
        assert container is not None
        assert port > 0
        
        # Verify it's in the list
        containers = list_all()
        assert any(c["name"] == container_name for c in containers)
        
        # Stop
        stop_container(container_name)
        container.reload()
        assert container.status == "exited"
        
        # Start
        start_container(container_name)
        time.sleep(1)
        container.reload()
        assert container.status == "running"
        
        # Remove
        remove_container(container_name)
        with pytest.raises(docker.errors.NotFound):
            docker_client.containers.get(f"dev_{container_name}")
    
    def test_error_handling_for_nonexistent_container(self):
        """Test error handling for operations on non-existent containers."""
        nonexistent_name = "nonexistent-container"
        
        with pytest.raises(docker.errors.NotFound):
            stop_container(nonexistent_name)
        
        with pytest.raises(docker.errors.NotFound):
            start_container(nonexistent_name)
        
        with pytest.raises(docker.errors.NotFound):
            remove_container(nonexistent_name)


@pytest.mark.slow
class TestBuildImage:
    """Integration tests for image building."""
    
    def test_build_simple_image(self, docker_client):
        """Test building a simple Docker image."""
        dockerfile_content = """
FROM ubuntu:22.04
RUN echo "Test image"
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            # Change to temp directory for build
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Build image
                build_image("test-build:latest", "Dockerfile")
                
                # Verify image was built
                image = docker_client.images.get("test-build:latest")
                assert image is not None
                
                # Cleanup
                docker_client.images.remove("test-build:latest", force=True)
                
            finally:
                os.chdir(original_cwd)
    
    def test_build_with_invalid_dockerfile(self):
        """Test building with invalid Dockerfile."""
        with pytest.raises(docker.errors.BuildError):
            build_image("test-invalid:latest", "nonexistent/Dockerfile")