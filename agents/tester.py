# agents/tester.py
"""
Tester Agent - Runs smoke, integration, and performance tests.
"""

from typing import Dict, Any, List
import subprocess
import asyncio
import time
from pathlib import Path
from agents import BaseAgent, AgentRole, Task, TaskStatus
import docker
import json


class TesterAgent(BaseAgent):
    """Agent responsible for testing implementations."""
    
    def __init__(self, neo4j_driver=None, repo_path: Path = None):
        super().__init__(AgentRole.TESTER, neo4j_driver)
        self.repo_path = repo_path or Path.cwd()
        self.docker_client = docker.from_env()
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a testing task."""
        self.logger.info(f"Executing test task: {task.id} - {task.title}")
        
        await self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        
        try:
            # Determine test type and execute
            if "unit" in task.title.lower():
                result = await self._run_unit_tests(task)
            elif "integration" in task.title.lower():
                result = await self._run_integration_tests(task)
            elif "performance" in task.title.lower():
                result = await self._run_performance_tests(task)
            elif "smoke" in task.title.lower():
                result = await self._run_smoke_tests(task)
            else:
                result = await self._run_all_tests(task)
            
            # Update task status based on results
            status = TaskStatus.DONE if result["passed"] else TaskStatus.BLOCKED
            await self.update_task_status(task.id, status, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute test task {task.id}: {e}")
            await self.update_task_status(
                task.id,
                TaskStatus.BLOCKED,
                {"error": str(e)}
            )
            raise
    
    async def _run_unit_tests(self, task: Task) -> Dict[str, Any]:
        """Run unit tests with pytest."""
        try:
            result = subprocess.run(
                ["pytest", "tests/unit", "-v", "--cov=devctl", "--cov-report=json"],
                capture_output=True,
                text=True
            )
            
            # Parse coverage report
            coverage_data = {}
            coverage_file = Path("coverage.json")
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                "test_count": result.stdout.count(" PASSED") + result.stdout.count(" FAILED")
            }
            
        except Exception as e:
            return {
                "passed": False,
                "error": str(e)
            }
    
    async def _run_integration_tests(self, task: Task) -> Dict[str, Any]:
        """Run integration tests with Docker containers."""
        try:
            # Start test environment
            compose_file = self.repo_path / "docker-compose.test.yml"
            if compose_file.exists():
                subprocess.run(
                    ["docker-compose", "-f", str(compose_file), "up", "-d"],
                    check=True
                )
                
                # Wait for services to be ready
                await asyncio.sleep(5)
            
            # Run integration tests
            result = subprocess.run(
                ["pytest", "tests/integration", "-v"],
                capture_output=True,
                text=True
            )
            
            # Cleanup
            if compose_file.exists():
                subprocess.run(
                    ["docker-compose", "-f", str(compose_file), "down"],
                    check=True
                )
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
            
        except Exception as e:
            return {
                "passed": False,
                "error": str(e)
            }
    
    async def _run_performance_tests(self, task: Task) -> Dict[str, Any]:
        """Run performance tests using Locust."""
        try:
            # Start the service
            service_process = subprocess.Popen(
                ["python", "-m", "devctl.service"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for service to start
            await asyncio.sleep(3)
            
            # Run Locust tests
            locust_result = subprocess.run(
                [
                    "locust",
                    "-f", "tests/performance/locustfile.py",
                    "--headless",
                    "-u", "100",  # 100 users
                    "-r", "10",   # 10 users/second spawn rate
                    "-t", "30s",  # 30 second test
                    "--host", "http://localhost:7070"
                ],
                capture_output=True,
                text=True
            )
            
            # Stop the service
            service_process.terminate()
            service_process.wait()
            
            # Parse results
            metrics = self._parse_locust_output(locust_result.stdout)
            
            return {
                "passed": metrics.get("failure_rate", 100) < 1,  # Less than 1% failure
                "metrics": metrics,
                "output": locust_result.stdout
            }
            
        except Exception as e:
            return {
                "passed": False,
                "error": str(e)
            }
    
    async def _run_smoke_tests(self, task: Task) -> Dict[str, Any]:
        """Run smoke tests to verify basic functionality."""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Can build image
        try:
            subprocess.run(["python", "scripts/devctl.py", "build"], check=True)
            tests_passed.append("Image build")
        except:
            tests_failed.append("Image build")
        
        # Test 2: Can create container
        try:
            result = subprocess.run(
                ["python", "scripts/devctl.py", "new", "test-smoke"],
                capture_output=True,
                text=True,
                check=True
            )
            tests_passed.append("Container creation")
            
            # Test 3: Can list containers
            result = subprocess.run(
                ["python", "scripts/devctl.py", "ls"],
                capture_output=True,
                text=True,
                check=True
            )
            if "test-smoke" in result.stdout:
                tests_passed.append("Container listing")
            else:
                tests_failed.append("Container listing")
                
        except:
            tests_failed.append("Container operations")
        
        # Cleanup
        try:
            container = self.docker_client.containers.get("dev_test-smoke")
            container.remove(force=True)
        except:
            pass
        
        return {
            "passed": len(tests_failed) == 0,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "total_tests": len(tests_passed) + len(tests_failed)
        }
    
    async def _run_all_tests(self, task: Task) -> Dict[str, Any]:
        """Run all test suites."""
        results = {}
        
        # Run each test type
        for test_type, test_func in [
            ("unit", self._run_unit_tests),
            ("integration", self._run_integration_tests),
            ("smoke", self._run_smoke_tests)
        ]:
            self.logger.info(f"Running {test_type} tests...")
            results[test_type] = await test_func(task)
        
        # Aggregate results
        all_passed = all(r.get("passed", False) for r in results.values())
        
        return {
            "passed": all_passed,
            "results": results
        }
    
    def _parse_locust_output(self, output: str) -> Dict[str, Any]:
        """Parse Locust output for metrics."""
        metrics = {
            "requests_per_second": 0,
            "failure_rate": 0,
            "average_response_time": 0,
            "p95_response_time": 0
        }
        
        # Simple parsing - in production, use Locust's stats API
        lines = output.split("\n")
        for line in lines:
            if "Requests/s" in line:
                try:
                    metrics["requests_per_second"] = float(line.split()[-1])
                except:
                    pass
            elif "Failure rate" in line:
                try:
                    metrics["failure_rate"] = float(line.split()[-1].strip("%"))
                except:
                    pass
        
        return metrics
