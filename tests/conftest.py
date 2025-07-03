"""Pytest configuration and shared fixtures for dev-container-launcher tests."""

import pytest
import docker
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


@pytest.fixture(scope="session")
def docker_client():
    """Docker client fixture for integration tests."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except docker.errors.DockerException:
        pytest.skip("Docker not available")


@pytest.fixture
def temp_directory():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for unit tests."""
    with patch('scripts.devctl.docker_client') as mock_client:
        # Configure common mock behaviors
        mock_client.ping.return_value = True
        mock_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        mock_client.images.get.return_value = Mock()
        mock_client.containers.create.return_value = Mock()
        mock_client.images.build.return_value = (Mock(), [])
        
        yield mock_client


@pytest.fixture
def mock_container():
    """Mock Docker container for tests."""
    container = Mock()
    container.id = "test_container_id"
    container.name = "dev_test_container"
    container.status = "running"
    container.attrs = {
        "NetworkSettings": {
            "Ports": {
                "22/tcp": [{"HostPort": "2222"}]
            }
        },
        "Config": {
            "Labels": {
                "devcontainer": "true",
                "devcontainer.name": "test_container"
            }
        },
        "Mounts": [
            {
                "Type": "bind",
                "Source": "/tmp/test",
                "Destination": "/workspace"
            }
        ]
    }
    return container


@pytest.fixture
def mock_valid_container_name():
    """Mock valid container name validation."""
    with patch('utils.validate_container_name') as mock_validate:
        mock_validate.return_value = True
        yield mock_validate


@pytest.fixture
def mock_valid_volume_path():
    """Mock valid volume path validation."""
    with patch('utils.validate_volume_path') as mock_validate:
        mock_validate.return_value = True
        yield mock_validate


@pytest.fixture
def mock_free_port():
    """Mock free port allocation."""
    with patch('scripts.devctl._free_port') as mock_port:
        mock_port.return_value = 2222
        yield mock_port


@pytest.fixture
def mock_sanitize_path():
    """Mock path sanitization."""
    with patch('utils.sanitize_path') as mock_sanitize:
        mock_sanitize.side_effect = lambda x: Path(x).resolve()
        yield mock_sanitize


@pytest.fixture
def sample_container_data():
    """Sample container data for tests."""
    return {
        "name": "test_container",
        "image": "devbox:latest",
        "status": "running",
        "port": 2222,
        "volume": "/tmp/test",
        "created": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_containers_list():
    """Sample list of containers for tests."""
    return [
        {
            "name": "container1",
            "image": "devbox:latest",
            "status": "running",
            "port": 2222,
            "volume": "/tmp/test1",
            "created": "2024-01-01T00:00:00Z"
        },
        {
            "name": "container2",
            "image": "python:3.12",
            "status": "stopped",
            "port": 2223,
            "volume": "/tmp/test2",
            "created": "2024-01-01T01:00:00Z"
        },
        {
            "name": "container3",
            "image": "node:20",
            "status": "running",
            "port": 2224,
            "volume": "/tmp/test3",
            "created": "2024-01-01T02:00:00Z"
        }
    ]


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for SSH operations."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_ssh_config():
    """Mock SSH configuration operations."""
    with patch('utils.SSH_CONFIG_PATH') as mock_config_path, \
         patch('utils.SSH_KNOWN_HOSTS_PATH') as mock_known_hosts:
        
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = "# Test SSH config\n"
        mock_config_path.open.return_value.__enter__.return_value = Mock()
        
        mock_known_hosts.exists.return_value = True
        mock_known_hosts.read_text.return_value = "# Test known hosts\n"
        mock_known_hosts.open.return_value.__enter__.return_value = Mock()
        
        yield mock_config_path, mock_known_hosts


@pytest.fixture
def mock_logger():
    """Mock logger for tests."""
    with patch('utils.logger') as mock_log:
        yield mock_log


@pytest.fixture
def test_authorized_keys():
    """Create test authorized_keys file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pub') as f:
        f.write("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com\n")
        f.flush()
        yield Path(f.name)
    os.unlink(f.name)


@pytest.fixture
def mock_config_values():
    """Mock configuration values."""
    with patch('config.IMAGE_TAG', 'test-devbox:latest'), \
         patch('config.CONTAINER_PREFIX', 'test_'), \
         patch('config.DEVCONTAINER_LABEL', 'devcontainer=test'), \
         patch('config.SSH_USER', 'testuser'), \
         patch('config.SSH_HOST', 'localhost'), \
         patch('config.DEFAULT_WORKSPACE', '/workspace'), \
         patch('config.ALLOWED_VOLUME_PATHS', [Path('/tmp')]), \
         patch('config.MAX_CONTAINER_NAME_LENGTH', 50):
        yield


@pytest.fixture
def integration_test_image():
    """Build a minimal test image for integration tests."""
    dockerfile_content = """
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y openssh-server sudo netcat-openbsd
RUN mkdir /var/run/sshd

# Create dev user
RUN useradd -m -s /bin/bash dev
RUN echo 'dev:dev' | chpasswd
RUN usermod -aG sudo dev

# SSH configuration
RUN mkdir -p /home/dev/.ssh
RUN ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N '' || true
RUN chmod 600 /etc/ssh/ssh_host_ed25519_key || true
RUN chmod 644 /etc/ssh/ssh_host_ed25519_key.pub || true

# Create dummy authorized_keys
RUN echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... test@example.com" > /home/dev/.ssh/authorized_keys
RUN chown -R dev:dev /home/dev/.ssh
RUN chmod 700 /home/dev/.ssh
RUN chmod 600 /home/dev/.ssh/authorized_keys

# SSH daemon config
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
RUN sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
"""
    
    return dockerfile_content


@pytest.fixture
def container_cleanup_list():
    """List to track containers for cleanup."""
    containers = []
    yield containers
    
    # Cleanup containers after test
    try:
        client = docker.from_env()
        for container_name in containers:
            try:
                container = client.containers.get(f"dev_{container_name}")
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass
    except docker.errors.DockerException:
        pass


@pytest.fixture
def mock_textual_app():
    """Mock Textual application for UI tests."""
    with patch('textual.app.App') as mock_app:
        mock_app.return_value.run.return_value = None
        yield mock_app


# Pytest markers for different test categories
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add security marker for security tests
        if "security" in str(item.fspath) or "security" in item.name:
            item.add_marker(pytest.mark.security)
        
        # Add slow marker for certain tests
        if "slow" in item.name or any(keyword in str(item.fspath) for keyword in ["integration", "performance"]):
            item.add_marker(pytest.mark.slow)


# Custom assertions for testing
def assert_container_running(docker_client, container_name):
    """Assert that a container is running."""
    try:
        container = docker_client.containers.get(f"dev_{container_name}")
        assert container.status == "running", f"Container {container_name} is not running"
    except docker.errors.NotFound:
        pytest.fail(f"Container {container_name} not found")


def assert_container_stopped(docker_client, container_name):
    """Assert that a container is stopped."""
    try:
        container = docker_client.containers.get(f"dev_{container_name}")
        assert container.status == "exited", f"Container {container_name} is not stopped"
    except docker.errors.NotFound:
        pytest.fail(f"Container {container_name} not found")


def assert_container_not_exists(docker_client, container_name):
    """Assert that a container does not exist."""
    try:
        docker_client.containers.get(f"dev_{container_name}")
        pytest.fail(f"Container {container_name} still exists")
    except docker.errors.NotFound:
        pass  # Expected


def assert_valid_port(port):
    """Assert that a port is valid."""
    assert isinstance(port, int), f"Port {port} is not an integer"
    assert 1024 <= port <= 65535, f"Port {port} is not in valid range (1024-65535)"


def assert_container_has_labels(docker_client, container_name, expected_labels):
    """Assert that a container has the expected labels."""
    try:
        container = docker_client.containers.get(f"dev_{container_name}")
        labels = container.labels
        for key, value in expected_labels.items():
            assert key in labels, f"Label {key} not found in container {container_name}"
            assert labels[key] == value, f"Label {key} has value {labels[key]}, expected {value}"
    except docker.errors.NotFound:
        pytest.fail(f"Container {container_name} not found")


# Make custom assertions available to tests
pytest.assert_container_running = assert_container_running
pytest.assert_container_stopped = assert_container_stopped
pytest.assert_container_not_exists = assert_container_not_exists
pytest.assert_valid_port = assert_valid_port
pytest.assert_container_has_labels = assert_container_has_labels