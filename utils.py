# utils.py - Utility functions for dev-container-launcher
import re
import logging
from pathlib import Path
from typing import Optional, List
import subprocess
import hashlib

from config import (
    CONTAINER_NAME_PATTERN,
    MAX_CONTAINER_NAME_LENGTH,
    ALLOWED_VOLUME_PATHS,
    LOG_LEVEL,
    LOG_FILE,
)

# Setup logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def validate_container_name(name: str) -> bool:
    """Validate container name according to Docker naming rules."""
    if not name:
        raise ValueError("Container name cannot be empty")
    
    if len(name) > MAX_CONTAINER_NAME_LENGTH:
        raise ValueError(f"Container name cannot exceed {MAX_CONTAINER_NAME_LENGTH} characters")
    
    if not re.match(CONTAINER_NAME_PATTERN, name):
        raise ValueError(
            "Container name must start with alphanumeric and contain only "
            "alphanumeric characters, underscores, periods, or hyphens"
        )
    
    return True


def validate_volume_path(path: Path) -> bool:
    """Validate that volume mount path is allowed."""
    path = path.resolve()
    
    # Check if path exists
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")
    
    # Check if path is in allowed locations
    allowed = False
    for allowed_path in ALLOWED_VOLUME_PATHS:
        try:
            path.relative_to(allowed_path.resolve())
            allowed = True
            break
        except ValueError:
            continue
    
    if not allowed:
        raise ValueError(
            f"Path {path} is not in allowed locations. "
            f"Allowed paths: {[str(p) for p in ALLOWED_VOLUME_PATHS]}"
        )
    
    return True


def get_container_ssh_key_fingerprint(container_name: str) -> Optional[str]:
    """Get SSH host key fingerprint from a container."""
    try:
        # Use ssh-keyscan to get the host key
        result = subprocess.run(
            ["docker", "exec", container_name, "ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub"],
            capture_output=True,
            text=True,
            check=True
        )
        # Extract fingerprint from output
        # Format: "256 SHA256:xxxxx root@hostname (ED25519)"
        parts = result.stdout.strip().split()
        if len(parts) >= 2:
            return parts[1]  # SHA256:xxxxx
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get SSH fingerprint for {container_name}: {e}")
        return None
    
    return None


def add_known_host(hostname: str, port: int, fingerprint: str) -> None:
    """Add a host to SSH known_hosts file."""
    from config import SSH_KNOWN_HOSTS_PATH
    
    SSH_KNOWN_HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Format: [hostname]:port ssh-ed25519 fingerprint
    entry = f"[{hostname}]:{port} {fingerprint}\n"
    
    # Check if entry already exists
    if SSH_KNOWN_HOSTS_PATH.exists():
        existing = SSH_KNOWN_HOSTS_PATH.read_text()
        if f"[{hostname}]:{port}" in existing:
            logger.info(f"Host {hostname}:{port} already in known_hosts")
            return
    
    # Append to known_hosts
    with SSH_KNOWN_HOSTS_PATH.open("a") as f:
        f.write(entry)
    
    logger.info(f"Added {hostname}:{port} to known_hosts")


def sanitize_path(path: str) -> Path:
    """Sanitize user-provided path input."""
    # Remove any null bytes
    path = path.replace('\0', '')
    
    # Resolve to absolute path and remove any .. components
    return Path(path).resolve()