# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dev-Container Launcher is a Docker-based development environment management system that provides seamless integration with Cursor IDE. It features both a terminal UI (Textual-based) and CLI interface for managing containerized development environments with SSH access.

## Common Development Commands

### Build Commands
- `make build` - Build the base devbox Docker image
- `make build-all` - Build all language-specific images (Python, Node.js, Go)
- `python devctl.py build` - Build the base image directly

### Testing and Development
- `make test` - Run pytest tests (tests/ directory)
- `make install` - Install Python dependencies from requirements.txt
- `make dev-setup` - Complete setup: install deps + build image
- `make run` - Launch the Textual UI application
- `make clean` - Stop and remove all dev containers
- `make lint` - Run code linting checks
- `make check` - Run security and type checks
- `make logs` - View application logs

### Container Management
- `python devctl.py new <name>` - Create a new dev container
- `python devctl.py ls` - List all containers (table/JSON output)
- `python devctl.py code <name>` - Open container in Cursor IDE
- `python devctl.py stop <name>` - Stop a running container
- `python devctl.py start <name>` - Start a stopped container
- `python devctl.py rm <name>` - Remove a container
- `python devctl.py info <name>` - Get detailed container information
- `python app.py` - Launch the Terminal UI

## Architecture

### Core Components
1. **devctl.py**: Core library with functional API for Docker container management
   - Container lifecycle (create, list, build, stop, start, remove)
   - SSH configuration management with security options
   - Port allocation and Cursor integration
   - Comprehensive error handling and logging

2. **app.py**: Textual-based Terminal UI
   - DevBoxUI class inheriting from Textual App
   - Interactive container management interface
   - Error handling and user notifications
   - Additional keybindings (d: delete, s: stop, S: start)

3. **config.py**: Centralized configuration management
   - Environment variable support
   - Security settings (SSH, paths)
   - Container defaults and validation rules

4. **utils.py**: Validation and utility functions
   - Container name validation
   - Path sanitization and validation
   - SSH fingerprint management
   - Logging configuration

### Key Design Patterns
- **Functional Core**: devctl.py uses stateless functions for easy testing and reuse
- **Label-based Management**: Containers identified by `devcontainer=true` label
- **SSH Protocol**: Universal access method for maximum compatibility
- **Dynamic Port Allocation**: Prevents conflicts between containers
- **Volume Mounting**: Current directory → `/workspace` for persistence

### Container Architecture
- Base image: Ubuntu 22.04 with SSH server
- Non-root user (`dev`) with limited sudo privileges (apt, pip3, npm, yarn only)
- SSH key authentication (public keys in `authorized_keys`)
- SSH hardening: no root login, no password auth, restricted to dev user
- Language-specific images extend the base (Python 3.12, Node.js 20, Go 1.22)

### Interaction Flow
```
User → app.py (UI) → devctl.py (Core) → Docker API
         ↓                ↓
    Textual UI      SSH Config → Cursor IDE
```

## Key Functions

### devctl.py
- `_free_port()`: Find available TCP port
- `build_image(tag, dockerfile)`: Build Docker images
- `create(name, image, volume)`: Create and configure container with validation
- `list_all()`: List containers with devcontainer label
- `stop_container(name)`: Stop a running container
- `start_container(name)`: Start a stopped container
- `remove_container(name, force)`: Remove a container and SSH config
- `get_container_info(name)`: Get detailed container information
- `_ensure_ssh_host(alias, port, container_name)`: Manage SSH config with security options
- `_remove_ssh_host(alias)`: Clean up SSH config entries
- `open_cursor(alias)`: Launch Cursor with SSH remote

### app.py
- `refresh_table()`: Update container list display with error handling
- `on_data_table_row_selected()`: Handle container selection
- `action_create()`: Interactive container creation with validation
- `action_delete()`: Delete selected container with confirmation
- `action_stop()`: Stop selected container
- `action_start()`: Start selected container
- `action_refresh()`: Refresh container list
- `ContainerCreateScreen`: Dedicated screen for container creation

## Development Guidelines

1. **Adding New Language Images**: Create Dockerfile in `images/` directory following existing patterns
2. **SSH Configuration**: Automatically managed in `~/.ssh/config` - don't edit manually
3. **Container Naming**: Always prefixed with "dev_" for consistency, validated against Docker rules
4. **Port Management**: Use `_free_port()` for allocation - never hardcode ports
5. **Volume Mounts**: Default to current directory, validated against allowed paths in config
6. **Error Handling**: Always wrap Docker operations in try-except blocks
7. **Logging**: Use the logger from utils.py for consistent logging
8. **Security**: Follow principle of least privilege, validate all inputs

## Dependencies
- docker>=6.0.0 (Docker SDK)
- textual>=0.40.0 (Terminal UI)
- rich>=13.0.0 (Text formatting)
- click>=8.1.0 (CLI framework)

## Troubleshooting Common Issues

1. **SSH Access Denied**: Ensure public key is in `authorized_keys` before building
2. **Cursor Not Found**: Install Cursor CLI via command palette in Cursor
3. **Port Conflicts**: Use `docker ps` to check existing containers
4. **Container Won't Start**: Verify Docker daemon is running
5. **Invalid Container Name**: Names must be alphanumeric, start with letter/number
6. **Volume Mount Denied**: Check allowed paths in config.py
7. **Logs Location**: Check `~/.devcontainer/devcontainer.log` for detailed errors

## Recent Updates (MVP Release)

### Security Enhancements
- SSH host key checking (configurable: accept-new/yes/no)
- Input validation for container names and paths
- Limited sudo access in containers
- SSH hardening in Dockerfile

### New Features
- Container stop/start/remove commands
- Configuration management (config.py)
- Comprehensive logging system
- Enhanced error handling throughout
- Improved UI with more keybindings

### Code Quality
- Type hints added
- Modular architecture
- Removed unused dependencies
- Better separation of concerns

## Git Repository

This project is version controlled with Git and hosted on GitHub:
- **Repository**: https://github.com/BHPAV/dev-container-launcher
- **Remote**: origin (https://github.com/BHPAV/dev-container-launcher.git)
- **Branch**: main (default)

### Git Commands
- `git status` - Check repository status
- `git add .` - Stage all changes
- `git commit -m "message"` - Commit changes
- `git push` - Push to GitHub
- `git pull` - Pull latest changes

## Session Management

**IMPORTANT**: When ending a development session, always:
1. Commit any uncommitted changes with descriptive messages
2. Push changes to GitHub to ensure work is preserved
3. Update this CLAUDE.md file if any significant changes were made to the project structure or workflow

This ensures continuity between sessions and prevents work loss.