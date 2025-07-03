# config.py - Configuration management for dev-container-launcher
from pathlib import Path
import os

# Base configuration
IMAGE_TAG = os.getenv("DEVCONTAINER_IMAGE", "devbox:latest")
CONTAINER_PREFIX = "dev_"
DEVCONTAINER_LABEL = {"devcontainer": "true"}

# SSH Configuration
SSH_CONFIG_PATH = Path.home() / ".ssh" / "config"
SSH_KNOWN_HOSTS_PATH = Path.home() / ".ssh" / "known_hosts"
SSH_USER = "dev"
SSH_HOST = "127.0.0.1"

# Container defaults
DEFAULT_WORKSPACE = "/workspace"
DEFAULT_WORKING_DIR = "/workspace"

# Security settings
STRICT_HOST_KEY_CHECKING = os.getenv("DEVCONTAINER_STRICT_SSH", "accept-new")  # accept-new, yes, no
ALLOWED_VOLUME_PATHS = [
    Path.home() / "Dev",
    Path.home() / "Projects",
    Path.home() / "workspace",
    Path("/tmp"),
]

# Validation rules
CONTAINER_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
MAX_CONTAINER_NAME_LENGTH = 63

# Logging
LOG_LEVEL = os.getenv("DEVCONTAINER_LOG_LEVEL", "INFO")
LOG_FILE = Path.home() / ".devcontainer" / "devcontainer.log"

# Language images
LANGUAGE_IMAGES = {
    "python": "python-3.12:latest",
    "node": "node-20:latest",
    "go": "go-1.22:latest",
}