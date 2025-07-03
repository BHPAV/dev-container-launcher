# agents/planner.py
"""
Planner Agent - Breaks large epics into executable tasks and maintains roadmap.
"""

from typing import Dict, List, Any
from agents import BaseAgent, AgentRole, Task, Feature, TaskStatus
import uuid
from datetime import datetime


class PlannerAgent(BaseAgent):
    """Agent responsible for planning and task breakdown."""
    
    def __init__(self, neo4j_driver=None):
        super().__init__(AgentRole.PLANNER, neo4j_driver)
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Planner doesn't execute tasks, it creates them."""
        raise NotImplementedError("Planner creates tasks, doesn't execute them")
    
    async def create_feature(self, 
                           title: str, 
                           rationale: str, 
                           target_release: str,
                           task_definitions: List[Dict]) -> Feature:
        """Create a new feature with associated tasks."""
        feature_id = f"F-{uuid.uuid4().hex[:8]}"
        
        feature = Feature(
            id=feature_id,
            title=title,
            rationale=rationale,
            target_release=target_release
        )
        
        # Create tasks for the feature
        for task_def in task_definitions:
            task = Task(
                id=f"T-{uuid.uuid4().hex[:8]}",
                title=task_def["title"],
                description=task_def["description"],
                assignee=AgentRole[task_def["assignee"].upper()],
                status=TaskStatus.OPEN,
                feature_id=feature_id,
                dependencies=task_def.get("dependencies", [])
            )
            feature.tasks.append(task)
        
        # Store in Neo4j
        await self._store_feature_graph(feature)
        
        return feature
    
    async def _store_feature_graph(self, feature: Feature):
        """Store feature and tasks in Neo4j."""
        if not self.neo4j_driver:
            return
        
        with self.neo4j_driver.session() as session:
            # Create feature node
            session.run("""
                CREATE (f:Feature {
                    id: $id,
                    title: $title,
                    rationale: $rationale,
                    target_release: $target_release,
                    status: $status,
                    created_at: datetime()
                })
            """, **feature.__dict__)
            
            # Create task nodes and relationships
            for task in feature.tasks:
                session.run("""
                    MATCH (f:Feature {id: $feature_id})
                    CREATE (t:Task {
                        id: $task_id,
                        title: $title,
                        description: $description,
                        assignee: $assignee,
                        status: $status,
                        created_at: datetime()
                    })
                    CREATE (f)-[:HAS_TASK]->(t)
                """, 
                feature_id=feature.id,
                task_id=task.id,
                title=task.title,
                description=task.description,
                assignee=task.assignee.value,
                status=task.status.value)
                
                # Create dependency relationships
                for dep_id in task.dependencies:
                    session.run("""
                        MATCH (t1:Task {id: $task_id})
                        MATCH (t2:Task {id: $dep_id})
                        CREATE (t1)-[:DEPENDS_ON]->(t2)
                    """, task_id=task.id, dep_id=dep_id)
    
    async def get_roadmap(self) -> Dict[str, Any]:
        """Get current roadmap from Neo4j."""
        if not self.neo4j_driver:
            return {"features": [], "milestones": []}
        
        with self.neo4j_driver.session() as session:
            # Get all features with their tasks
            result = session.run("""
                MATCH (f:Feature)
                OPTIONAL MATCH (f)-[:HAS_TASK]->(t:Task)
                RETURN f, collect(t) as tasks
                ORDER BY f.target_release, f.created_at
            """)
            
            features = []
            for record in result:
                feature_data = dict(record["f"])
                feature_data["tasks"] = [dict(t) for t in record["tasks"] if t]
                features.append(feature_data)
            
            return {
                "features": features,
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def update_burndown(self):
        """Update burndown metrics in Neo4j."""
        if not self.neo4j_driver:
            return
        
        with self.neo4j_driver.session() as session:
            # Calculate burndown metrics
            result = session.run("""
                MATCH (t:Task)
                RETURN t.status as status, count(t) as count
            """)
            
            metrics = {record["status"]: record["count"] for record in result}
            
            # Store metrics
            session.run("""
                CREATE (b:BurndownMetric {
                    timestamp: datetime(),
                    open_tasks: $open,
                    in_progress: $in_progress,
                    done: $done
                })
            """, 
            open=metrics.get("open", 0),
            in_progress=metrics.get("in_progress", 0),
            done=metrics.get("done", 0))
