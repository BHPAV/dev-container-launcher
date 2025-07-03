# tests/performance/locustfile.py
"""
Performance tests for Dev-Container Launcher API using Locust.
"""

from locust import HttpUser, task, between
import json
import random
import string


class DevContainerUser(HttpUser):
    """Simulates a user interacting with the Dev-Container API."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session."""
        self.container_names = []
        self.user_id = ''.join(random.choices(string.ascii_lowercase, k=8))
    
    @task(3)
    def list_containers(self):
        """List all containers - most common operation."""
        with self.client.get("/api/v1/containers", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def create_container(self):
        """Create a new container."""
        container_name = f"perf-test-{self.user_id}-{len(self.container_names)}"
        
        payload = {
            "name": container_name,
            "image": "python:3.12",
            "volume": "/tmp/test"
        }
        
        with self.client.post(
            "/api/v1/containers",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                self.container_names.append(container_name)
                response.success()
            elif response.status_code == 403:
                # Quota exceeded - expected for some users
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def get_container_details(self):
        """Get details of a specific container."""
        if not self.container_names:
            return
        
        container_name = random.choice(self.container_names)
        
        with self.client.get(
            f"/api/v1/containers/{container_name}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def get_metrics(self):
        """Get Prometheus metrics."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    def on_stop(self):
        """Cleanup created containers."""
        for container_name in self.container_names:
            self.client.delete(f"/api/v1/containers/{container_name}")


class AdminUser(HttpUser):
    """Simulates an admin user with different access patterns."""
    
    wait_time = between(2, 5)
    
    @task(2)
    def list_all_containers(self):
        """List all containers across all users."""
        self.client.get("/api/v1/containers?all=true")
    
    @task(1)
    def build_image(self):
        """Trigger image build."""
        payload = {
            "dockerfile": "images/python-3.12.Dockerfile",
            "tag": "python:3.12-test"
        }
        self.client.post("/api/v1/images/build", json=payload)
    
    @task(1)
    def get_system_info(self):
        """Get system information."""
        self.client.get("/api/v1/info")
