# Dev-Container Launcher: Implementation Plan & Standards

## Table of Contents
1. [Project Overview](#project-overview)
2. [Implementation Phases](#implementation-phases)
3. [Coding Standards](#coding-standards)
4. [Best Practices](#best-practices)
5. [Development Workflow](#development-workflow)
6. [Testing Standards](#testing-standards)
7. [Documentation Standards](#documentation-standards)
8. [Security Guidelines](#security-guidelines)

---

## Project Overview

The Dev-Container Launcher is a comprehensive development environment management system that provides:
- One-click containerized development environments
- Seamless Cursor IDE integration
- Multi-language support (Python, Node.js, Go, etc.)
- Persistent workspaces
- Web and terminal UIs
- Enterprise-grade authentication
- Observability through Neo4j graph database

---

## Implementation Phases

### Phase 1: Core Service Architecture (Foundation)

#### 1.1 Refactor devctl into a package structure
**Priority**: High  
**Dependencies**: None  
**Time Estimate**: 2-3 hours

**Directory Structure**:
```
devctl/
├── __init__.py
├── core.py          # Container lifecycle management
├── service.py       # FastAPI service implementation
├── graph.py         # Neo4j integration
├── auth.py          # SSH CA authentication
├── config.py        # Configuration management
├── models.py        # Pydantic models
├── exceptions.py    # Custom exceptions
└── utils.py         # Utility functions
```

**Implementation Tasks**:
- [ ] Create package directory structure
- [ ] Extract container operations to `core.py`
- [ ] Define Pydantic models for type safety
- [ ] Implement configuration management with environment variables
- [ ] Add comprehensive logging setup

#### 1.2 Implement FastAPI Service Mode
**Priority**: High  
**Dependencies**: 1.1  
**Time Estimate**: 3-4 hours

**API Endpoints**:
```python
# Container Management
GET    /api/v1/containers                    # List all containers
POST   /api/v1/containers                    # Create new container
GET    /api/v1/containers/{name}             # Get container details
PUT    /api/v1/containers/{name}             # Update container
DELETE /api/v1/containers/{name}             # Delete container

# Container Operations
POST   /api/v1/containers/{name}/start       # Start container
POST   /api/v1/containers/{name}/stop        # Stop container
POST   /api/v1/containers/{name}/restart     # Restart container
POST   /api/v1/containers/{name}/open_cursor # Open in Cursor
GET    /api/v1/containers/{name}/logs        # Stream logs
GET    /api/v1/containers/{name}/stats       # Get resource stats

# Image Management
GET    /api/v1/images                        # List available images
POST   /api/v1/images/build                  # Build new image
DELETE /api/v1/images/{name}                 # Remove image

# System
GET    /api/v1/health                        # Health check
GET    /api/v1/info                          # System information
WS     /api/v1/ws                           # WebSocket for real-time updates
```

### Phase 2: Neo4j Graph Integration

#### 2.1 Neo4j Connection and Schema
**Priority**: Medium  
**Dependencies**: 1.1  
**Time Estimate**: 2-3 hours

**Graph Schema**:
```cypher
// Nodes
(:Container {
  id: string (UUID),
  name: string (unique),
  image: string,
  port: integer,
  status: string,
  created_at: datetime,
  updated_at: datetime,
  volume_path: string,
  host_name: string,
  environment: map
})

(:User {
  id: string (UUID),
  username: string (unique),
  email: string,
  created_at: datetime,
  last_active: datetime
})

(:Image {
  id: string (UUID),
  name: string,
  tag: string,
  digest: string,
  built_at: datetime,
  size: integer,
  base_image: string
})

(:Host {
  id: string (UUID),
  hostname: string,
  ip_address: string,
  total_memory: integer,
  total_cpu: integer,
  docker_version: string
})

(:Session {
  id: string (UUID),
  started_at: datetime,
  ended_at: datetime,
  duration_seconds: integer
})

// Relationships
(:User)-[:CREATED {at: datetime}]->(:Container)
(:User)-[:STARTED]->(:Session)
(:Session)-[:IN_CONTAINER]->(:Container)
(:Container)-[:USES]->(:Image)
(:Container)-[:RUNS_ON]->(:Host)
(:Container)-[:SUCCEEDED_BY]->(:Container)  // For rebuilds
(:Image)-[:BASED_ON]->(:Image)              // Image hierarchy
```

#### 2.2 Event Tracking and Analytics
**Priority**: Medium  
**Dependencies**: 2.1  
**Time Estimate**: 2-3 hours

**Event Types**:
```python
class EventType(Enum):
    CONTAINER_CREATED = "container.created"
    CONTAINER_STARTED = "container.started"
    CONTAINER_STOPPED = "container.stopped"
    CONTAINER_DELETED = "container.deleted"
    IMAGE_BUILT = "image.built"
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    ERROR_OCCURRED = "error.occurred"
```

**Analytics Queries**:
```cypher
// Most popular images
MATCH (c:Container)-[:USES]->(i:Image)
RETURN i.name, COUNT(c) as usage_count
ORDER BY usage_count DESC

// User activity patterns
MATCH (u:User)-[:STARTED]->(s:Session)
RETURN u.username, 
       COUNT(s) as session_count,
       AVG(s.duration_seconds) as avg_duration
```

### Phase 3: Web UI Implementation

#### 3.1 Backend API Gateway
**Priority**: High  
**Dependencies**: 1.2  
**Time Estimate**: 2 hours

**Features**:
- JWT-based authentication
- Rate limiting (100 req/min per user)
- Request validation
- CORS configuration
- API versioning
- OpenAPI documentation

#### 3.2 React Frontend
**Priority**: High  
**Dependencies**: 3.1  
**Time Estimate**: 6-8 hours

**Component Architecture**:
```
web/frontend/src/
├── components/
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   └── Spinner.tsx
│   ├── containers/
│   │   ├── ContainerList.tsx
│   │   ├── ContainerCard.tsx
│   │   ├── ContainerDetails.tsx
│   │   └── CreateContainerModal.tsx
│   ├── images/
│   │   ├── ImageList.tsx
│   │   └── BuildImageModal.tsx
│   └── layout/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Layout.tsx
├── hooks/
│   ├── useWebSocket.ts
│   ├── useContainers.ts
│   └── useAuth.ts
├── services/
│   ├── api.ts
│   ├── auth.ts
│   └── websocket.ts
├── store/
│   ├── index.ts
│   └── slices/
│       ├── containers.ts
│       └── ui.ts
├── types/
│   └── index.ts
└── utils/
    ├── constants.ts
    └── helpers.ts
```

### Phase 4: SSH Certificate Authority

#### 4.1 CA Infrastructure
**Priority**: Low  
**Dependencies**: 1.1  
**Time Estimate**: 4-5 hours

**Certificate Structure**:
```python
# Host Certificate
{
    "type": "ssh-rsa-cert-v01@openssh.com",
    "serial": 12345,
    "valid_principals": ["dev-container-*"],
    "valid_after": "2024-01-01T00:00:00Z",
    "valid_before": "2025-01-01T00:00:00Z",
    "critical_options": {},
    "extensions": {
        "permit-X11-forwarding": "",
        "permit-agent-forwarding": "",
        "permit-port-forwarding": "",
        "permit-pty": ""
    }
}

# Client Certificate
{
    "type": "ssh-rsa-cert-v01@openssh.com",
    "serial": 67890,
    "valid_principals": ["dev", "developer"],
    "valid_after": "2024-01-01T00:00:00Z",
    "valid_before": "2024-01-01T08:00:00Z",  # 8-hour validity
    "critical_options": {},
    "extensions": {
        "permit-pty": "",
        "permit-user-rc": ""
    }
}
```

### Phase 5: Advanced Features

#### 5.1 Multi-Host Support
**Priority**: Low  
**Dependencies**: 1.2, 2.1  
**Time Estimate**: 6-8 hours

**Architecture**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Host A    │     │   Host B    │     │   Host C    │
│  (Primary)  │     │ (Secondary) │     │ (Secondary) │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ Scheduler   │     │   Agent     │     │   Agent     │
│ API Service │     │   Docker    │     │   Docker    │
│   Neo4j     │     │             │     │             │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                     Message Bus
```

#### 5.2 Template System
**Priority**: Medium  
**Dependencies**: 1.2  
**Time Estimate**: 4 hours

**Template Format**:
```yaml
apiVersion: devcontainer/v1
kind: Template
metadata:
  name: python-ml-stack
  description: Python with ML/Data Science tools
spec:
  base_image: python:3.12
  packages:
    apt:
      - build-essential
      - libhdf5-dev
    pip:
      - numpy
      - pandas
      - scikit-learn
      - jupyter
  environment:
    PYTHONPATH: /workspace
    JUPYTER_PORT: 8888
  volumes:
    - host: ./data
      container: /data
      mode: rw
  ports:
    - 8888:8888  # Jupyter
  post_create:
    - pip install -e .
    - jupyter notebook --generate-config
```

---

## Coding Standards

### Python Standards

#### Style Guide
- Follow PEP 8 with 88-character line length (Black formatter)
- Use type hints for all function signatures
- Docstrings for all public functions (Google style)

#### Code Organization
```python
# Standard import order
import os
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

import third_party_module
from third_party import specific_function

from devctl.core import Container
from devctl.models import ContainerCreate
from devctl.utils import logger

# Constants at module level
DEFAULT_IMAGE = "python:3.12"
MAX_CONTAINERS = 100

# Type aliases
ContainerDict = Dict[str, Any]
```

#### Function Structure
```python
def create_container(
    name: str,
    image: str = DEFAULT_IMAGE,
    volume: Optional[Path] = None,
    environment: Optional[Dict[str, str]] = None,
) -> Container:
    """Create a new development container.
    
    Args:
        name: Unique container name
        image: Docker image to use
        volume: Host volume to mount
        environment: Environment variables
        
    Returns:
        Created container instance
        
    Raises:
        ContainerExistsError: If container name already exists
        DockerError: If Docker operation fails
    """
    # Validation
    if not name or not name.isalnum():
        raise ValueError("Container name must be alphanumeric")
    
    # Implementation
    try:
        container = _create_docker_container(name, image, volume)
        _record_creation_event(container)
        return container
    except docker.errors.APIError as e:
        logger.error(f"Failed to create container: {e}")
        raise DockerError(f"Container creation failed: {e}") from e
```

#### Error Handling
```python
# Custom exceptions
class DevContainerError(Exception):
    """Base exception for all devcontainer errors."""
    pass

class ContainerNotFoundError(DevContainerError):
    """Raised when container doesn't exist."""
    pass

# Usage
try:
    container = get_container(name)
except ContainerNotFoundError:
    logger.warning(f"Container {name} not found")
    return None
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### JavaScript/TypeScript Standards

#### Style Guide
- Use ESLint with Airbnb configuration
- Prettier for formatting (2 spaces, single quotes)
- TypeScript strict mode enabled
- Functional components with hooks for React

#### Component Structure
```typescript
// ContainerCard.tsx
import React, { useState, useCallback } from 'react';
import { Container } from '@/types';
import { useContainerActions } from '@/hooks/useContainerActions';
import { Button } from '@/components/common';

interface ContainerCardProps {
  container: Container;
  onSelect?: (container: Container) => void;
}

export const ContainerCard: React.FC<ContainerCardProps> = ({
  container,
  onSelect,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const { startContainer, stopContainer } = useContainerActions();

  const handleStart = useCallback(async () => {
    setIsLoading(true);
    try {
      await startContainer(container.name);
    } finally {
      setIsLoading(false);
    }
  }, [container.name, startContainer]);

  return (
    <div className="container-card">
      {/* Component JSX */}
    </div>
  );
};
```

#### API Service Pattern
```typescript
// services/api.ts
class ApiService {
  private baseURL: string;
  private token: string | null = null;

  constructor(baseURL: string = '/api/v1') {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
        ...options.headers,
      },
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }

  async getContainers(): Promise<Container[]> {
    return this.request<Container[]>('/containers');
  }
}

export const api = new ApiService();
```

### Docker Standards

#### Dockerfile Best Practices
```dockerfile
# Use specific versions
FROM python:3.12-slim AS base

# Metadata
LABEL maintainer="dev-team@company.com"
LABEL version="1.0.0"

# Use ARG for build-time variables
ARG USER_UID=1000
ARG USER_GID=1000

# Minimize layers
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g ${USER_GID} dev \
    && useradd -m -u ${USER_UID} -g dev dev

# Switch to non-root user
USER dev
WORKDIR /home/dev

# Copy requirements first for better caching
COPY --chown=dev:dev requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=dev:dev . .

# Use ENTRYPOINT for main command
ENTRYPOINT ["python", "-m", "devctl"]
```

---

## Best Practices

### API Design

#### RESTful Principles
1. Use proper HTTP methods (GET, POST, PUT, DELETE)
2. Return appropriate status codes
3. Use consistent naming conventions
4. Version your APIs
5. Implement pagination for lists

#### Response Format
```json
{
  "data": {
    "id": "123",
    "type": "container",
    "attributes": {
      "name": "dev-api",
      "status": "running"
    }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "1.0.0"
  }
}
```

#### Error Response
```json
{
  "error": {
    "code": "CONTAINER_NOT_FOUND",
    "message": "Container 'dev-api' not found",
    "details": {
      "container_name": "dev-api",
      "suggestion": "Check container name or create a new one"
    }
  }
}
```

### Database Practices

#### Neo4j Queries
```python
# Use parameters to prevent injection
query = """
    MATCH (u:User {username: $username})
    -[:CREATED]->(c:Container)
    WHERE c.created_at > $since
    RETURN c
    ORDER BY c.created_at DESC
    LIMIT $limit
"""

# Use transactions for multiple operations
def transfer_container_ownership(container_id: str, new_owner: str):
    with driver.session() as session:
        with session.begin_transaction() as tx:
            # Remove old ownership
            tx.run("""
                MATCH (c:Container {id: $container_id})<-[r:CREATED]-()
                DELETE r
            """, container_id=container_id)
            
            # Create new ownership
            tx.run("""
                MATCH (c:Container {id: $container_id})
                MATCH (u:User {username: $username})
                CREATE (u)-[:CREATED]->(c)
            """, container_id=container_id, username=new_owner)
```

### Container Management

#### Resource Limits
```python
# Always set resource limits
container_config = {
    "mem_limit": "2g",
    "memswap_limit": "2g",
    "cpu_period": 100000,
    "cpu_quota": 50000,  # 50% of one CPU
    "pids_limit": 1000,
}
```

#### Health Checks
```python
# Implement container health checks
healthcheck = {
    "test": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
    "interval": 30000000000,  # 30s in nanoseconds
    "timeout": 3000000000,    # 3s
    "retries": 3,
    "start_period": 60000000000,  # 60s
}
```

---

## Development Workflow

### Git Workflow

#### Branch Strategy
```
main
├── develop
│   ├── feature/web-ui
│   ├── feature/neo4j-integration
│   └── feature/ssh-ca
├── release/v1.0
└── hotfix/critical-bug
```

#### Commit Messages
```
<type>(<scope>): <subject>

<body>

<footer>

# Examples:
feat(containers): add volume mount support
fix(auth): handle expired JWT tokens correctly
docs(api): update OpenAPI specification
perf(neo4j): optimize container listing query
```

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling comprehensive
- [ ] Logging appropriate
- [ ] Breaking changes documented

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Python Lint
        run: |
          pip install black flake8 mypy
          black --check .
          flake8 .
          mypy .
      
  test:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/testpass
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: |
          pip install -r requirements-test.txt
          pytest --cov=devctl --cov-report=xml
          
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Security Scan
        run: |
          pip install bandit safety
          bandit -r devctl/
          safety check
```

---

## Testing Standards

### Test Structure

#### Unit Tests
```python
# test_container.py
import pytest
from unittest.mock import Mock, patch
from devctl.core import create_container
from devctl.exceptions import ContainerExistsError

class TestCreateContainer:
    @pytest.fixture
    def mock_docker(self):
        with patch('devctl.core.docker.from_env') as mock:
            yield mock.return_value
    
    def test_create_container_success(self, mock_docker):
        # Arrange
        mock_docker.containers.run.return_value = Mock(
            name="dev_test",
            ports={"22/tcp": [{"HostPort": "32768"}]}
        )
        
        # Act
        container, port = create_container("test")
        
        # Assert
        assert container.name == "dev_test"
        assert port == 32768
        mock_docker.containers.run.assert_called_once()
    
    def test_create_container_duplicate_name(self, mock_docker):
        # Arrange
        mock_docker.containers.list.return_value = [
            Mock(name="dev_test")
        ]
        
        # Act & Assert
        with pytest.raises(ContainerExistsError):
            create_container("test")
```

#### Integration Tests
```python
# test_integration.py
import pytest
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def docker_services():
    with DockerCompose(".", compose_file_name="docker-compose.test.yml") as compose:
        compose.wait_for("neo4j")
        yield compose

def test_full_container_lifecycle(docker_services):
    # Create container
    response = client.post("/api/v1/containers", json={
        "name": "test-integration",
        "image": "python:3.12"
    })
    assert response.status_code == 201
    
    # Start container
    response = client.post(f"/api/v1/containers/test-integration/start")
    assert response.status_code == 200
    
    # Verify in Neo4j
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Container {name: $name}) RETURN c",
            name="test-integration"
        )
        assert len(list(result)) == 1
```

### Coverage Requirements

- Minimum 80% code coverage
- 100% coverage for critical paths
- Integration tests for all API endpoints
- Performance tests for operations > 100ms

---

## Documentation Standards

### Code Documentation

#### Module Documentation
```python
"""Container management module.

This module provides the core functionality for creating, managing,
and destroying development containers. It interfaces with the Docker
API and maintains state in Neo4j.

Example:
    >>> from devctl.core import create_container
    >>> container, port = create_container("myapp", image="python:3.12")
    >>> print(f"Container {container.name} running on port {port}")
"""
```

#### API Documentation
```python
@app.post("/api/v1/containers", response_model=ContainerResponse)
async def create_container(
    container: ContainerCreate,
    current_user: User = Depends(get_current_user)
) -> ContainerResponse:
    """Create a new development container.
    
    Creates a Docker container with the specified configuration and
    registers it in the system. The container is started automatically
    and SSH access is configured.
    
    Args:
        container: Container creation parameters
        current_user: Authenticated user
        
    Returns:
        Created container details
        
    Raises:
        HTTPException: 
            - 400: Invalid container configuration
            - 409: Container name already exists
            - 500: Docker operation failed
    """
```

### User Documentation

#### README Structure
1. Project overview
2. Quick start guide
3. Installation instructions
4. Configuration options
5. Usage examples
6. API reference
7. Troubleshooting
8. Contributing guidelines

#### Tutorial Format
```markdown
## Creating Your First Container

Follow these steps to create and access your first development container:

1. **Start the service**
   ```bash
   devctl service start
   ```

2. **Create a Python container**
   ```bash
   devctl create my-python-app --image python:3.12
   ```

3. **Open in Cursor**
   ```bash
   devctl open my-python-app
   ```

💡 **Tip**: Use `devctl ls` to see all your containers
```

---

## Security Guidelines

### Authentication & Authorization

#### JWT Token Structure
```json
{
  "sub": "user123",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": ["developer"],
  "iat": 1700000000,
  "exp": 1700086400,
  "jti": "unique-token-id"
}
```

#### Permission Model
```python
class Permission(Enum):
    CONTAINER_CREATE = "container:create"
    CONTAINER_READ = "container:read"
    CONTAINER_UPDATE = "container:update"
    CONTAINER_DELETE = "container:delete"
    IMAGE_BUILD = "image:build"
    SYSTEM_ADMIN = "system:admin"

@require_permission(Permission.CONTAINER_CREATE)
async def create_container(request: Request):
    # Implementation
```

### Container Security

#### Security Policies
```python
# Mandatory security options
SECURITY_OPTS = [
    "no-new-privileges",
    "seccomp=default",
]

# Dropped capabilities
CAP_DROP = [
    "CAP_NET_RAW",
    "CAP_SYS_ADMIN",
    "CAP_SYS_TIME",
]

# Read-only root filesystem
READ_ONLY_ROOTFS = True
```

### Secret Management

#### Environment Variables
```python
# Never hardcode secrets
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ConfigurationError("DATABASE_URL not set")

# Use secret management service
from devctl.secrets import SecretManager

secrets = SecretManager()
api_key = secrets.get("external_api_key")
```

#### SSH Key Management
```python
# Generate ephemeral keys
def generate_ssh_keypair():
    key = paramiko.RSAKey.generate(4096)
    private_key = StringIO()
    key.write_private_key(private_key)
    public_key = f"{key.get_name()} {key.get_base64()}"
    return private_key.getvalue(), public_key

# Rotate keys periodically
@scheduler.scheduled_job('cron', hour=0)
def rotate_ca_keys():
    old_key = load_ca_key()
    new_key = generate_ca_key()
    
    # Overlap period for smooth transition
    save_ca_key(new_key, backup=old_key)
    notify_key_rotation()
```

---

## Performance Guidelines

### Optimization Strategies

1. **Connection Pooling**
   ```python
   # Database connections
   driver = GraphDatabase.driver(
       uri, 
       auth=auth,
       max_connection_pool_size=100,
       connection_acquisition_timeout=30
   )
   ```

2. **Caching**
   ```python
   from functools import lru_cache
   from cachetools import TTLCache
   
   # In-memory cache
   container_cache = TTLCache(maxsize=1000, ttl=300)
   
   @lru_cache(maxsize=128)
   def get_image_info(image_name: str) -> ImageInfo:
       # Expensive operation cached
       return fetch_image_metadata(image_name)
   ```

3. **Async Operations**
   ```python
   async def list_containers_with_stats():
       containers = await get_containers()
       
       # Parallel stats fetching
       stats_tasks = [
           fetch_container_stats(c.id) 
           for c in containers
       ]
       stats = await asyncio.gather(*stats_tasks)
       
       return [
           {**c.dict(), "stats": s}
           for c, s in zip(containers, stats)
       ]
   ```

### Monitoring & Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
container_creates = Counter(
    'devcontainer_creates_total',
    'Total number of containers created'
)

operation_duration = Histogram(
    'devcontainer_operation_duration_seconds',
    'Duration of container operations',
    ['operation']
)

active_containers = Gauge(
    'devcontainer_active_total',
    'Number of active containers'
)

# Use decorators
@operation_duration.labels(operation='create').time()
def create_container(name: str) -> Container:
    container = _do_create(name)
    container_creates.inc()
    active_containers.inc()
    return container
```

---

## Appendix: Quick Reference

### Common Commands

```bash
# Development
make dev           # Start development environment
make test          # Run test suite
make lint          # Run linters
make docs          # Build documentation

# Operations
devctl service start    # Start service
devctl service status   # Check status
devctl service logs     # View logs
devctl service stop     # Stop service

# Container Management
devctl create NAME [--image IMAGE] [--volume PATH]
devctl list [--format json]
devctl start NAME
devctl stop NAME
devctl delete NAME
devctl logs NAME [--follow]
```

### Environment Variables

```bash
# Required
DEVCTL_DATABASE_URL=bolt://localhost:7687
DEVCTL_DATABASE_USER=neo4j
DEVCTL_DATABASE_PASS=password

# Optional
DEVCTL_LOG_LEVEL=INFO
DEVCTL_API_PORT=7070
DEVCTL_API_HOST=0.0.0.0
DEVCTL_MAX_CONTAINERS=100
DEVCTL_DEFAULT_IMAGE=python:3.12
DEVCTL_ENABLE_METRICS=true
DEVCTL_METRICS_PORT=9090
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Container won't start | Check Docker daemon, verify image exists |
| SSH connection failed | Verify SSH key in authorized_keys |
| API returns 500 | Check service logs: `devctl service logs` |
| Neo4j connection error | Verify Neo4j is running and credentials |
| Port already in use | Stop conflicting service or change port |

---

This document serves as the authoritative guide for implementing and maintaining the Dev-Container Launcher system. All contributors should familiarize themselves with these standards and practices.