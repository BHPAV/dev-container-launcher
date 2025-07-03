# agents/coder.py
"""
Coder Agent - Generates and refactors code, writes unit tests.
"""

from typing import Dict, Any, List
import os
import subprocess
from pathlib import Path
from agents import BaseAgent, AgentRole, Task, TaskStatus


class CoderAgent(BaseAgent):
    """Agent responsible for code generation and refactoring."""
    
    def __init__(self, neo4j_driver=None, repo_path: Path = None):
        super().__init__(AgentRole.CODER, neo4j_driver)
        self.repo_path = repo_path or Path.cwd()
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a coding task."""
        self.logger.info(f"Executing task: {task.id} - {task.title}")
        
        await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        
        try:
            # Determine task type and execute
            if "dockerfile" in task.title.lower():
                result = await self._create_dockerfile(task)
            elif "test" in task.title.lower():
                result = await self._write_tests(task)
            elif "refactor" in task.title.lower():
                result = await self._refactor_code(task)
            else:
                result = await self._implement_feature(task)
            
            await self.update_task_status(
                task.id, 
                TaskStatus.REVIEW,
                {"result": result}
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute task {task.id}: {e}")
            await self.update_task_status(
                task.id,
                TaskStatus.BLOCKED,
                {"error": str(e)}
            )
            raise
    
    async def _create_dockerfile(self, task: Task) -> Dict[str, Any]:
        """Create a Dockerfile based on task requirements."""
        # Example: Create GPU-enabled Dockerfile
        if "cuda" in task.description.lower():
            dockerfile_content = '''FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \\
    USER=dev \\
    UID=1000 \\
    PYTHON_VERSION=3.12

# Install Python and development tools
RUN apt-get update && \\
    apt-get install -y --no-install-recommends \\
        openssh-server git curl sudo build-essential \\
        software-properties-common && \\
    add-apt-repository ppa:deadsnakes/ppa && \\
    apt-get update && \\
    apt-get install -y python${PYTHON_VERSION} \\
        python${PYTHON_VERSION}-dev \\
        python${PYTHON_VERSION}-venv \\
        python3-pip && \\
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

# Install CUDA-specific Python packages
RUN python3 -m pip install --upgrade pip && \\
    python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Create user and setup SSH
RUN useradd -m -u ${UID} -s /bin/bash ${USER} && \\
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \\
    mkdir /var/run/sshd && \\
    ssh-keygen -A

COPY --chown=${USER}:${USER} authorized_keys /home/${USER}/.ssh/authorized_keys
RUN chmod 600 /home/${USER}/.ssh/authorized_keys

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]
'''
            
            cuda_dockerfile = self.repo_path / "images" / "python-3.12-cuda.Dockerfile"
            cuda_dockerfile.write_text(dockerfile_content)
            
            return {
                "created_files": [str(cuda_dockerfile)],
                "description": "Created CUDA-enabled Python 3.12 Dockerfile"
            }
        
        return {"error": "Unknown Dockerfile type"}
    
    async def _write_tests(self, task: Task) -> Dict[str, Any]:
        """Write unit tests for a feature."""
        # Example: Write tests for GPU detection
        if "gpu" in task.description.lower():
            test_content = '''import pytest
from unittest.mock import Mock, patch
from devctl.core import detect_gpu_support


class TestGPUDetection:
    """Test GPU detection functionality."""
    
    @patch('subprocess.run')
    def test_detect_gpu_with_nvidia_runtime(self, mock_run):
        """Test GPU detection when NVIDIA runtime is available."""
        # Mock docker info output
        mock_run.return_value = Mock(
            stdout='{"Runtimes": {"nvidia": {"path": "nvidia-container-runtime"}}}',
            returncode=0
        )
        
        assert detect_gpu_support() is True
        mock_run.assert_called_once_with(
            ["docker", "info", "--format", "{{json .Runtimes}}"],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_detect_gpu_without_nvidia_runtime(self, mock_run):
        """Test GPU detection when NVIDIA runtime is not available."""
        mock_run.return_value = Mock(
            stdout='{"Runtimes": {}}',
            returncode=0
        )
        
        assert detect_gpu_support() is False
    
    @patch('subprocess.run')
    def test_detect_gpu_docker_error(self, mock_run):
        """Test GPU detection when Docker command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["docker", "info"])
        
        assert detect_gpu_support() is False
'''
            
            test_file = self.repo_path / "tests" / "unit" / "test_gpu_detection.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(test_content)
            
            return {
                "created_files": [str(test_file)],
                "description": "Created GPU detection unit tests"
            }
        
        return {"error": "Unknown test type"}
    
    async def _refactor_code(self, task: Task) -> Dict[str, Any]:
        """Refactor existing code."""
        # This would analyze and refactor code based on task requirements
        return {
            "refactored_files": [],
            "description": "Code refactoring completed"
        }
    
    async def _implement_feature(self, task: Task) -> Dict[str, Any]:
        """Implement a new feature."""
        # This would generate new feature code based on task requirements
        return {
            "implemented_files": [],
            "description": "Feature implementation completed"
        }
    
    def run_formatter(self, files: List[str]):
        """Run code formatter on files."""
        try:
            subprocess.run(["black"] + files, check=True)
            subprocess.run(["ruff", "--fix"] + files, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Formatter failed: {e}")
