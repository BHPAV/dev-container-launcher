# agents/__init__.py
"""
Agent-based development framework for Dev-Container Launcher.

This module provides the base classes and interfaces for the autonomous
development agents described in the feature delivery playbook.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a development task."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class AgentRole(Enum):
    """Roles that agents can perform."""
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DOC_GEN = "doc_gen"
    INTEGRATOR = "integrator"


@dataclass
class Task:
    """Represents a development task."""
    id: str
    title: str
    description: str
    assignee: AgentRole
    status: TaskStatus
    feature_id: str
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Feature:
    """Represents a feature to be implemented."""
    id: str
    title: str
    rationale: str
    target_release: str
    tasks: List[Task] = None
    status: str = "planned"

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []


class BaseAgent(ABC):
    """Base class for all development agents."""
    
    def __init__(self, role: AgentRole, neo4j_driver=None):
        self.role = role
        self.neo4j_driver = neo4j_driver
        self.logger = logging.getLogger(f"{__name__}.{role.value}")
    
    @abstractmethod
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a task and return the result."""
        pass
    
    async def get_assigned_tasks(self) -> List[Task]:
        """Get tasks assigned to this agent from Neo4j."""
        if not self.neo4j_driver:
            return []
        
        query = """
        MATCH (t:Task {assignee: $assignee, status: 'open'})
        RETURN t
        ORDER BY t.created_at
        """
        
        with self.neo4j_driver.session() as session:
            result = session.run(query, assignee=self.role.value)
            return [Task(**record["t"]) for record in result]
    
    async def update_task_status(self, task_id: str, status: TaskStatus, metadata: Dict = None):
        """Update task status in Neo4j."""
        if not self.neo4j_driver:
            return
        
        query = """
        MATCH (t:Task {id: $task_id})
        SET t.status = $status,
            t.updated_at = datetime()
        """
        
        if metadata:
            query += ", t += $metadata"
        
        with self.neo4j_driver.session() as session:
            session.run(query, task_id=task_id, status=status.value, metadata=metadata or {})
