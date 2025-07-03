# agents/roadmap.py
"""
Roadmap management for tracking milestones and features.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from agents.planner import PlannerAgent
import asyncio


@dataclass
class Milestone:
    """Represents a development milestone."""
    id: str
    name: str
    features: List[str]
    acceptance_criteria: List[str]
    start_date: datetime
    end_date: datetime
    status: str = "planned"


class RoadmapManager:
    """Manages the development roadmap and milestones."""
    
    def __init__(self, neo4j_driver=None):
        self.neo4j_driver = neo4j_driver
        self.planner = PlannerAgent(neo4j_driver)
        self.milestones = self._initialize_milestones()
    
    def _initialize_milestones(self) -> Dict[str, Milestone]:
        """Initialize the roadmap milestones from the playbook."""
        start_date = datetime.now()
        
        milestones = {
            "M1": Milestone(
                id="M1",
                name="Container Power-Ups",
                features=["GPU image flavours", "live Prometheus metrics"],
                acceptance_criteria=[
                    "docker run python-3.12-cuda succeeds",
                    "Web/UI shows CPU & GPU %"
                ],
                start_date=start_date,
                end_date=start_date + timedelta(weeks=2)
            ),
            "M2": Milestone(
                id="M2",
                name="Build Experience",
                features=["BuildKit remote cache", "self-service image wizard"],
                acceptance_criteria=[
                    "Builds are ≥ 40% faster after warm cache",
                    "wizard outputs validated Dockerfile & triggers build"
                ],
                start_date=start_date + timedelta(weeks=2),
                end_date=start_date + timedelta(weeks=4)
            ),
            "M3": Milestone(
                id="M3",
                name="Governance & Policy",
                features=["OPA policy engine", "quota enforcement", "idle-reaper"],
                acceptance_criteria=[
                    "deny rules block >2 CPU containers for free users",
                    "idle containers auto-stop after N hours"
                ],
                start_date=start_date + timedelta(weeks=4),
                end_date=start_date + timedelta(weeks=6)
            ),
            "M4": Milestone(
                id="M4",
                name="Productivity UX",
                features=["VS Code task templates", "one-click TLS tunnels", "CLIs for scripts"],
                acceptance_criteria=[
                    "User can scaffold pytest task",
                    "TLS tunnel link appears in UI toolbar"
                ],
                start_date=start_date + timedelta(weeks=6),
                end_date=start_date + timedelta(weeks=8)
            ),
            "M5": Milestone(
                id="M5",
                name="Scalability",
                features=["Remote host pooling", "agent-based image pre-fetch"],
                acceptance_criteria=[
                    "Launching 100 containers < 90s P95",
                    "images pre-pulled via DOMO agents"
                ],
                start_date=start_date + timedelta(weeks=8),
                end_date=start_date + timedelta(weeks=10)
            )
        }
        
        return milestones
    
    async def create_milestone_features(self, milestone_id: str):
        """Create features and tasks for a milestone."""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            raise ValueError(f"Unknown milestone: {milestone_id}")
        
        # Feature definitions based on milestone
        feature_definitions = self._get_feature_definitions(milestone_id)
        
        for feature_def in feature_definitions:
            await self.planner.create_feature(
                title=feature_def["title"],
                rationale=feature_def["rationale"],
                target_release=milestone.end_date.isoformat(),
                task_definitions=feature_def["tasks"]
            )
    
    def _get_feature_definitions(self, milestone_id: str) -> List[Dict]:
        """Get feature definitions for a milestone."""
        definitions = {
            "M1": [
                {
                    "title": "GPU-Ready Container Images",
                    "rationale": "Enable ML/AI workloads with CUDA support",
                    "tasks": [
                        {
                            "title": "Draft cuda.Dockerfile & extend build script",
                            "description": "Create CUDA-enabled Dockerfile for Python 3.12",
                            "assignee": "coder",
                            "dependencies": []
                        },
                        {
                            "title": "Detect GPU via docker info",
                            "description": "Implement GPU runtime detection",
                            "assignee": "coder",
                            "dependencies": []
                        },
                        {
                            "title": "Test GPU detection",
                            "description": "Unit test GPU detection functionality",
                            "assignee": "tester",
                            "dependencies": ["T-102"]
                        },
                        {
                            "title": "Add GPU badge & filter in Web/TUI",
                            "description": "Update UI to show GPU availability",
                            "assignee": "coder",
                            "dependencies": ["T-102"]
                        },
                        {
                            "title": "Update docs & examples",
                            "description": "Document GPU support",
                            "assignee": "doc_gen",
                            "dependencies": ["T-101", "T-103"]
                        }
                    ]
                },
                {
                    "title": "Prometheus Metrics Integration",
                    "rationale": "Enable container monitoring and observability",
                    "tasks": [
                        {
                            "title": "Add prometheus_client to service",
                            "description": "Implement /metrics endpoint",
                            "assignee": "coder",
                            "dependencies": []
                        },
                        {
                            "title": "Collect container metrics",
                            "description": "Gather CPU, memory, network, disk I/O stats",
                            "assignee": "coder",
                            "dependencies": []
                        },
                        {
                            "title": "Test metrics endpoint",
                            "description": "Load test with 100 scrapes/second",
                            "assignee": "tester",
                            "dependencies": ["T-201"]
                        },
                        {
                            "title": "Create Grafana dashboard",
                            "description": "Design monitoring dashboard",
                            "assignee": "coder",
                            "dependencies": ["T-201", "T-202"]
                        }
                    ]
                }
            ],
            # Add more milestone definitions here...
        }
        
        return definitions.get(milestone_id, [])
    
    async def get_burndown_data(self) -> Dict:
        """Get burndown chart data for all milestones."""
        if not self.neo4j_driver:
            return {"milestones": {}}
        
        burndown_data = {}
        
        with self.neo4j_driver.session() as session:
            for milestone_id, milestone in self.milestones.items():
                # Get task counts by status for this milestone's date range
                result = session.run("""
                    MATCH (f:Feature)-[:HAS_TASK]->(t:Task)
                    WHERE f.target_release >= $start_date AND f.target_release <= $end_date
                    RETURN t.status as status, count(t) as count
                """, 
                start_date=milestone.start_date.isoformat(),
                end_date=milestone.end_date.isoformat())
                
                status_counts = {record["status"]: record["count"] for record in result}
                
                total_tasks = sum(status_counts.values())
                completed_tasks = status_counts.get("done", 0)
                
                burndown_data[milestone_id] = {
                    "name": milestone.name,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                    "status_breakdown": status_counts,
                    "days_remaining": (milestone.end_date - datetime.now()).days
                }
        
        return {"milestones": burndown_data}
    
    async def generate_retrospective(self, milestone_id: str) -> Dict:
        """Generate retrospective report for a milestone."""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            raise ValueError(f"Unknown milestone: {milestone_id}")
        
        retrospective = {
            "milestone": milestone.name,
            "period": f"{milestone.start_date.date()} to {milestone.end_date.date()}",
            "features_delivered": [],
            "metrics": {},
            "lessons_learned": [],
            "action_items": []
        }
        
        if self.neo4j_driver:
            with self.neo4j_driver.session() as session:
                # Get completed features
                result = session.run("""
                    MATCH (f:Feature {status: 'done'})
                    WHERE f.target_release >= $start_date AND f.target_release <= $end_date
                    RETURN f.title as title, f.id as id
                """,
                start_date=milestone.start_date.isoformat(),
                end_date=milestone.end_date.isoformat())
                
                retrospective["features_delivered"] = [
                    {"id": record["id"], "title": record["title"]}
                    for record in result
                ]
                
                # Get metrics
                metrics_result = session.run("""
                    MATCH (m:Metric)
                    WHERE m.timestamp >= $start_date AND m.timestamp <= $end_date
                    RETURN m
                    ORDER BY m.timestamp DESC
                    LIMIT 1
                """,
                start_date=milestone.start_date.isoformat(),
                end_date=milestone.end_date.isoformat())
                
                for record in metrics_result:
                    retrospective["metrics"] = dict(record["m"])
        
        return retrospective


# CLI for roadmap management
if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) < 2:
            print("Usage: python -m agents.roadmap [command]")
            print("Commands: show, create-milestone M1, burndown")
            return
        
        command = sys.argv[1]
        manager = RoadmapManager()
        
        if command == "show":
            for milestone_id, milestone in manager.milestones.items():
                print(f"\n{milestone_id}: {milestone.name}")
                print(f"  Duration: {milestone.start_date.date()} to {milestone.end_date.date()}")
                print(f"  Features: {', '.join(milestone.features)}")
                print(f"  Status: {milestone.status}")
        
        elif command == "create-milestone" and len(sys.argv) > 2:
            milestone_id = sys.argv[2]
            await manager.create_milestone_features(milestone_id)
            print(f"Created features and tasks for {milestone_id}")
        
        elif command == "burndown":
            data = await manager.get_burndown_data()
            for milestone_id, metrics in data["milestones"].items():
                print(f"\n{milestone_id}: {metrics['name']}")
                print(f"  Progress: {metrics['completed_tasks']}/{metrics['total_tasks']} "
                      f"({metrics['completion_percentage']:.1f}%)")
                print(f"  Days remaining: {metrics['days_remaining']}")
    
    asyncio.run(main())
