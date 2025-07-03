# devctl.py - Core library for dev-container management
from pathlib import Path
import subprocess, socket, os
import docker
import click
import json
import logging
from typing import Optional, Tuple, List, Dict, Any

from config import (
    IMAGE_TAG,
    CONTAINER_PREFIX,
    DEVCONTAINER_LABEL,
    SSH_CONFIG_PATH,
    SSH_USER,
    SSH_HOST,
    DEFAULT_WORKSPACE,
    DEFAULT_WORKING_DIR,
    STRICT_HOST_KEY_CHECKING,
)
from utils import (
    validate_container_name,
    validate_volume_path,
    get_container_ssh_key_fingerprint,
    add_known_host,
    sanitize_path,
    logger,
)

try:
    docker_client = docker.from_env()
except docker.errors.DockerException as e:
    logger.error(f"Failed to connect to Docker: {e}")
    logger.error("Please ensure Docker is installed and running")
    raise

def _free_port() -> int:
    """Find an unused TCP port on localhost."""
    try:
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]
    except OSError as e:
        logger.error(f"Failed to find free port: {e}")
        raise

def build_image(tag: str = IMAGE_TAG, dockerfile: str = "Dockerfile") -> None:
    """Build the Docker image for dev containers."""
    try:
        logger.info(f"Building image {tag} from {dockerfile}")
        image, logs = docker_client.images.build(
            path=".", 
            dockerfile=dockerfile, 
            tag=tag, 
            quiet=False
        )
        for log in logs:
            if 'stream' in log:
                logger.debug(log['stream'].strip())
        logger.info(f"Successfully built image {tag}")
    except docker.errors.BuildError as e:
        logger.error(f"Failed to build image: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error building image: {e}")
        raise

def create(name: str, image: str = IMAGE_TAG, volume: Optional[Path] = None) -> Tuple[docker.models.containers.Container, int]:
    """Create and start a new dev container."""
    # Validate inputs
    try:
        validate_container_name(name)
    except ValueError as e:
        logger.error(f"Invalid container name: {e}")
        raise
    
    # Handle volume path
    volume = volume or Path.cwd()
    try:
        volume = sanitize_path(str(volume))
        validate_volume_path(volume)
    except ValueError as e:
        logger.error(f"Invalid volume path: {e}")
        raise
    
    # Check if container already exists
    container_name = f"{CONTAINER_PREFIX}{name}"
    try:
        existing = docker_client.containers.get(container_name)
        logger.error(f"Container {container_name} already exists")
        raise ValueError(f"Container {container_name} already exists")
    except docker.errors.NotFound:
        pass  # Good, container doesn't exist
    
    # Check if image exists
    try:
        docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        logger.error(f"Image {image} not found. Please build it first.")
        raise ValueError(f"Image {image} not found")
    
    # Find free port
    port = _free_port()
    
    # Create container
    try:
        logger.info(f"Creating container {container_name} with image {image}")
        container = docker_client.containers.run(
            image,
            name=container_name,
            labels=DEVCONTAINER_LABEL,
            detach=True,
            tty=True,
            ports={22: port},
            volumes={str(volume): {"bind": DEFAULT_WORKSPACE, "mode": "rw"}},
            working_dir=DEFAULT_WORKING_DIR,
            remove=False,
        )
        logger.info(f"Container {container_name} created successfully on port {port}")
        
        # Setup SSH configuration
        _ensure_ssh_host(name, port, container_name)
        
        return container, port
    except docker.errors.APIError as e:
        logger.error(f"Docker API error creating container: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating container: {e}")
        raise

def list_all() -> List[docker.models.containers.Container]:
    """List all dev containers."""
    try:
        return docker_client.containers.list(
            all=True, 
            filters={"label": "devcontainer=true"}
        )
    except docker.errors.APIError as e:
        logger.error(f"Failed to list containers: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing containers: {e}")
        raise

def _ensure_ssh_host(alias: str, port: int, container_name: str) -> None:
    """Add or update SSH config entry for the container."""
    SSH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Build SSH config entry
    entry_lines = [
        f"Host {alias}",
        f"  HostName {SSH_HOST}",
        f"  Port {port}",
        f"  User {SSH_USER}",
    ]
    
    # Handle SSH host key checking based on configuration
    if STRICT_HOST_KEY_CHECKING == "yes":
        # Get container's SSH fingerprint and add to known_hosts
        fingerprint = get_container_ssh_key_fingerprint(container_name)
        if fingerprint:
            add_known_host(SSH_HOST, port, fingerprint)
        entry_lines.append("  StrictHostKeyChecking yes")
    elif STRICT_HOST_KEY_CHECKING == "accept-new":
        entry_lines.append("  StrictHostKeyChecking accept-new")
    else:
        # Only use 'no' if explicitly configured (not recommended)
        entry_lines.append("  StrictHostKeyChecking no")
        logger.warning("StrictHostKeyChecking is disabled - this is insecure!")
    
    entry = "\n".join(entry_lines) + "\n"
    
    try:
        # Read existing config
        text = SSH_CONFIG_PATH.read_text() if SSH_CONFIG_PATH.exists() else ""
        
        # Check if host already exists
        if f"Host {alias}\n" in text:
            logger.info(f"SSH config for {alias} already exists, updating...")
            # TODO: Implement update logic
        else:
            # Append new entry
            with SSH_CONFIG_PATH.open("a") as f:
                f.write("\n" + entry)
            logger.info(f"Added SSH config for {alias}")
    except IOError as e:
        logger.error(f"Failed to update SSH config: {e}")
        raise

def open_cursor(alias: str) -> None:
    """Open Cursor IDE connected to the container."""
    uri = f"vscode-remote://ssh-remote+{alias}/home/{SSH_USER}"
    try:
        logger.info(f"Opening Cursor for {alias}")
        subprocess.Popen(["cursor", "--folder-uri", uri])
    except FileNotFoundError:
        logger.error("Cursor command not found. Please install Cursor CLI.")
        raise ValueError("Cursor CLI not installed")
    except Exception as e:
        logger.error(f"Failed to open Cursor: {e}")
        raise


def stop_container(name: str) -> None:
    """Stop a running dev container."""
    container_name = f"{CONTAINER_PREFIX}{name}"
    try:
        container = docker_client.containers.get(container_name)
        if container.status == "running":
            logger.info(f"Stopping container {container_name}")
            container.stop()
            logger.info(f"Container {container_name} stopped")
        else:
            logger.info(f"Container {container_name} is not running")
    except docker.errors.NotFound:
        logger.error(f"Container {container_name} not found")
        raise ValueError(f"Container {container_name} not found")
    except docker.errors.APIError as e:
        logger.error(f"Failed to stop container: {e}")
        raise


def start_container(name: str) -> None:
    """Start a stopped dev container."""
    container_name = f"{CONTAINER_PREFIX}{name}"
    try:
        container = docker_client.containers.get(container_name)
        if container.status != "running":
            logger.info(f"Starting container {container_name}")
            container.start()
            logger.info(f"Container {container_name} started")
        else:
            logger.info(f"Container {container_name} is already running")
    except docker.errors.NotFound:
        logger.error(f"Container {container_name} not found")
        raise ValueError(f"Container {container_name} not found")
    except docker.errors.APIError as e:
        logger.error(f"Failed to start container: {e}")
        raise


def remove_container(name: str, force: bool = False) -> None:
    """Remove a dev container."""
    container_name = f"{CONTAINER_PREFIX}{name}"
    try:
        container = docker_client.containers.get(container_name)
        logger.info(f"Removing container {container_name}")
        container.remove(force=force)
        logger.info(f"Container {container_name} removed")
        
        # Clean up SSH config entry
        _remove_ssh_host(name)
    except docker.errors.NotFound:
        logger.error(f"Container {container_name} not found")
        raise ValueError(f"Container {container_name} not found")
    except docker.errors.APIError as e:
        logger.error(f"Failed to remove container: {e}")
        raise


def _remove_ssh_host(alias: str) -> None:
    """Remove SSH config entry for a container."""
    try:
        if not SSH_CONFIG_PATH.exists():
            return
        
        lines = SSH_CONFIG_PATH.read_text().splitlines()
        new_lines = []
        skip = False
        
        for line in lines:
            if line.strip() == f"Host {alias}":
                skip = True
            elif skip and line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                skip = False
            
            if not skip:
                new_lines.append(line)
        
        SSH_CONFIG_PATH.write_text("\n".join(new_lines) + "\n")
        logger.info(f"Removed SSH config for {alias}")
    except IOError as e:
        logger.error(f"Failed to update SSH config: {e}")
        # Don't raise here as container is already removed


def get_container_info(name: str) -> Dict[str, Any]:
    """Get detailed information about a container."""
    container_name = f"{CONTAINER_PREFIX}{name}"
    try:
        container = docker_client.containers.get(container_name)
        
        # Extract port mapping
        port = None
        if "22/tcp" in container.ports and container.ports["22/tcp"]:
            port = container.ports["22/tcp"][0]["HostPort"]
        
        return {
            "name": container.name,
            "id": container.short_id,
            "status": container.status,
            "image": container.image.tags[0] if container.image.tags else container.image.short_id,
            "created": container.attrs["Created"],
            "port": port,
            "volumes": container.attrs.get("Mounts", []),
        }
    except docker.errors.NotFound:
        logger.error(f"Container {container_name} not found")
        raise ValueError(f"Container {container_name} not found")
    except Exception as e:
        logger.error(f"Failed to get container info: {e}")
        raise

if __name__ == "__main__":
    @click.group()
    def cli():
        """Dev-container manager"""

    @cli.command()
    @click.argument("name")
    @click.option("--image", default=IMAGE_TAG, help="Docker image to use")
    @click.option("--volume", type=click.Path(exists=True), help="Directory to mount as workspace")
    def new(name, image, volume):
        """Create a new dev container."""
        try:
            volume_path = Path(volume) if volume else None
            container, port = create(name, image=image, volume=volume_path)
            click.echo(f"✅ Started {container.name} on port {port}")
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.Abort()

    @cli.command()
    @click.option("--format", type=click.Choice(["json", "table"]), default="table", help="Output format")
    def ls(format):
        """List all dev containers."""
        try:
            containers = list_all()
            if not containers:
                click.echo("No dev containers found")
                return
            
            data = []
            for c in containers:
                port = None
                if "22/tcp" in c.ports and c.ports["22/tcp"]:
                    port = c.ports["22/tcp"][0]["HostPort"]
                
                data.append({
                    "name": c.name.replace(CONTAINER_PREFIX, ""),
                    "status": c.status,
                    "port": port or "N/A",
                    "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                })
            
            if format == "json":
                click.echo(json.dumps(data, indent=2))
            else:
                # Table format
                click.echo(f"{'Name':<20} {'Status':<15} {'Port':<10} {'Image':<30}")
                click.echo("-" * 75)
                for item in data:
                    click.echo(f"{item['name']:<20} {item['status']:<15} {item['port']:<10} {item['image']:<30}")
        except Exception as e:
            click.echo(f"❌ Error listing containers: {e}", err=True)
            raise click.Abort()

    @cli.command()
    @click.argument("name")
    def code(name):
        """Open a container in Cursor."""
        try:
            open_cursor(name)
            click.echo(f"✅ Opening {name} in Cursor")
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.Abort()

    @cli.command()
    @click.option("--tag", default=IMAGE_TAG, help="Image tag")
    @click.option("--dockerfile", default="Dockerfile", help="Dockerfile to use")
    def build(tag, dockerfile):
        """Build the dev container image."""
        try:
            build_image(tag=tag, dockerfile=dockerfile)
            click.echo(f"✅ Image {tag} built successfully")
        except Exception as e:
            click.echo(f"❌ Build failed: {e}", err=True)
            raise click.Abort()
    
    @cli.command()
    @click.argument("name")
    def stop(name):
        """Stop a running dev container."""
        try:
            stop_container(name)
            click.echo(f"✅ Container {name} stopped")
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.Abort()
    
    @cli.command()
    @click.argument("name")
    def start(name):
        """Start a stopped dev container."""
        try:
            start_container(name)
            click.echo(f"✅ Container {name} started")
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.Abort()
    
    @cli.command()
    @click.argument("name")
    @click.option("--force", is_flag=True, help="Force remove even if running")
    def rm(name, force):
        """Remove a dev container."""
        try:
            remove_container(name, force=force)
            click.echo(f"✅ Container {name} removed")
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.Abort()
    
    @cli.command()
    @click.argument("name")
    def info(name):
        """Show detailed information about a container."""
        try:
            info = get_container_info(name)
            click.echo(json.dumps(info, indent=2, default=str))
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.Abort()

    cli()
