#!/usr/bin/env python3
"""
Initialize Dev-Container Launcher v2 with agent-based development.

This script sets up the complete development environment including:
- Core package structure
- Agent framework
- Testing infrastructure
- Policy engine
- CI/CD pipeline
"""

import os
import sys
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_prerequisites():
    """Check that all required tools are installed."""
    requirements = {
        "python3": "Python 3.12+",
        "docker": "Docker Engine",
        "git": "Git version control",
        "cursor": "Cursor IDE CLI (optional)"
    }
    
    missing = []
    for cmd, description in requirements.items():
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            logger.info(f"✓ {description} found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            if cmd != "cursor":  # Cursor is optional
                missing.append(description)
            else:
                logger.warning(f"⚠ {description} not found (optional)")
    
    if missing:
        logger.error(f"Missing prerequisites: {', '.join(missing)}")
        sys.exit(1)


def setup_python_environment():
    """Set up Python virtual environment and install dependencies."""
    logger.info("Setting up Python environment...")
    
    if not Path("venv").exists():
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        logger.info("✓ Created virtual environment")
    
    # Activate venv and install requirements
    pip_cmd = "venv/bin/pip" if os.name != "nt" else "venv\\Scripts\\pip"
    
    subprocess.run([pip_cmd, "install", "--upgrade", "pip"], check=True)
    subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
    
    # Install additional dev requirements
    dev_packages = [
        "pytest", "pytest-cov", "pytest-asyncio",
        "black", "ruff", "mypy", "bandit[toml]",
        "locust", "tox", "mkdocs", "conftest"
    ]
    subprocess.run([pip_cmd, "install"] + dev_packages, check=True)
    logger.info("✓ Installed Python dependencies")


def initialize_neo4j_schema():
    """Initialize Neo4j schema for roadmap tracking."""
    logger.info("Initializing Neo4j schema...")
    
    schema_script = '''
// Create constraints
CREATE CONSTRAINT feature_id IF NOT EXISTS ON (f:Feature) ASSERT f.id IS UNIQUE;
CREATE CONSTRAINT task_id IF NOT EXISTS ON (t:Task) ASSERT t.id IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS ON (u:User) ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT container_id IF NOT EXISTS ON (c:Container) ASSERT c.id IS UNIQUE;

// Create indexes
CREATE INDEX feature_status IF NOT EXISTS FOR (f:Feature) ON (f.status);
CREATE INDEX task_assignee IF NOT EXISTS FOR (t:Task) ON (t.assignee);
CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status);
CREATE INDEX container_owner IF NOT EXISTS FOR (c:Container) ON (c.owner_id);
'''
    
    # Write schema file
    schema_file = Path("scripts/neo4j_schema.cypher")
    schema_file.parent.mkdir(exist_ok=True)
    schema_file.write_text(schema_script)
    logger.info("✓ Created Neo4j schema file")


def create_example_specs():
    """Create example feature specifications."""
    logger.info("Creating example specifications...")
    
    gpu_spec = '''# Feature Specification: GPU-Ready Container Images

## Feature ID: F-001
**Title**: GPU-Ready Container Images  
**Target Release**: M1 (2 weeks)  
**Status**: Planned

## Rationale
Enable machine learning and AI workloads by providing CUDA-enabled container images with GPU support.

## Acceptance Criteria
- [x] `docker run python-3.12-cuda nvidia-smi` returns GPU information
- [ ] GPU detection works on systems with NVIDIA runtime
- [ ] UI shows GPU availability badge
- [ ] Documentation includes GPU setup instructions

## Technical Design
### Architecture Changes
- New Dockerfile variant with CUDA base image
- GPU runtime detection in devctl.core
- UI components for GPU status display

### Implementation Plan
1. Create CUDA-enabled Dockerfile based on nvidia/cuda base
2. Implement GPU detection using Docker API
3. Add GPU badge to container list UI
4. Write comprehensive tests
5. Update documentation

## Tasks
| ID | Title | Assignee | Dependencies | Status |
|----|-------|----------|--------------|--------|
| T-101 | Draft cuda.Dockerfile | Coder | - | Done |
| T-102 | Implement GPU detection | Coder | - | In Progress |
| T-103 | Unit tests for GPU detection | Tester | T-102 | Open |
| T-104 | Add GPU badge to UI | Coder | T-102 | Open |
| T-105 | Update documentation | Doc-Gen | T-101,T-104 | Open |

## Testing Strategy
- Unit tests: Mock Docker API responses for GPU detection
- Integration tests: Test with actual NVIDIA runtime if available
- UI tests: Verify GPU badge display logic

## Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CUDA version mismatch | High | Medium | Pin CUDA version, test multiple versions |
| Missing NVIDIA runtime | Medium | High | Graceful degradation, clear error messages |

## Success Metrics
- 100% of GPU-enabled containers can run nvidia-smi
- GPU detection completes in < 100ms
- Zero false positives in GPU detection
'''
    
    spec_file = Path("specs/F-001-gpu-containers.md")
    spec_file.write_text(gpu_spec)
    logger.info("✓ Created example GPU feature specification")


def create_initial_milestones():
    """Create initial milestone tracking data."""
    logger.info("Creating milestone tracking...")
    
    milestones_data = '''# Dev-Container Launcher v2 Milestones

## Current Sprint: M1 - Container Power-Ups
**Duration**: 2 weeks  
**Status**: In Progress

### Features
1. GPU-Ready Container Images (F-001)
2. Prometheus Metrics Integration (F-002)

### Progress
- [x] GPU Dockerfile created
- [ ] GPU detection implementation
- [ ] Prometheus endpoint
- [ ] Grafana dashboard

---

## Upcoming Milestones

### M2 - Build Experience (Weeks 3-4)
- BuildKit remote cache
- Self-service image wizard

### M3 - Governance & Policy (Weeks 5-6)
- OPA policy engine
- Quota enforcement
- Idle container reaper

### M4 - Productivity UX (Weeks 7-8)
- VS Code task templates
- One-click TLS tunnels
- CLI improvements

### M5 - Scalability (Weeks 9-10)
- Remote host pooling
- Agent-based image pre-fetch
- 100 container benchmark
'''
    
    milestones_file = Path("docs/milestones.md")
    milestones_file.write_text(milestones_data)
    logger.info("✓ Created milestone tracking document")


def setup_git_hooks():
    """Set up Git hooks for automated checks."""
    logger.info("Setting up Git hooks...")
    
    pre_commit_hook = '''#!/bin/bash
# Pre-commit hook for Dev-Container Launcher

echo "Running pre-commit checks..."

# Format code
black --check . || (echo "Running black formatter..." && black .)
ruff check . --fix

# Run type checks
mypy devctl/ agents/ || echo "Type check warnings (non-blocking)"

# Run security scan
bandit -r devctl/ agents/ -ll || echo "Security warnings (non-blocking)"

echo "Pre-commit checks complete!"
'''
    
    hooks_dir = Path(".git/hooks")
    if hooks_dir.exists():
        pre_commit_file = hooks_dir / "pre-commit"
        pre_commit_file.write_text(pre_commit_hook)
        pre_commit_file.chmod(0o755)
        logger.info("✓ Installed Git pre-commit hook")
    else:
        logger.warning("⚠ Git repository not initialized")


def main():
    """Run all initialization steps."""
    logger.info("🚀 Initializing Dev-Container Launcher v2...")
    
    # Check we're in the right directory
    if not Path("devctl.py").exists():
        logger.error("Please run this script from the project root directory")
        sys.exit(1)
    
    # Run initialization steps
    check_prerequisites()
    setup_python_environment()
    initialize_neo4j_schema()
    create_example_specs()
    create_initial_milestones()
    setup_git_hooks()
    
    logger.info("\n✅ Initialization complete!")
    logger.info("\nNext steps:")
    logger.info("1. Activate virtual environment: source venv/bin/activate")
    logger.info("2. Start Neo4j: docker run -p 7687:7687 neo4j:5")
    logger.info("3. Run tests: pytest tests/")
    logger.info("4. Start development: python app.py")
    logger.info("\nFor agent-based development:")
    logger.info("- View roadmap: python -m agents.roadmap show")
    logger.info("- Create milestone: python -m agents.roadmap create-milestone M1")


if __name__ == "__main__":
    main()
