"""Integration tests for DatabaseManager operations.

These tests verify actual PostgreSQL inserts/updates.
Requires a running PostgreSQL instance with pgvector.
"""

from uuid import uuid4
import pytest
import psycopg

from src.memory.db_manager import DatabaseManager


@pytest.fixture
def test_db_config():
    """Provides configuration for the test database.
    
    In a true fully-automated CI environment, this would spin up a testcontainer.
    For local testing, we assume a local or Docker PostgreSQL instance listening on 5432.
    """
    return {
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'miracle_agent',  # You might want to use a specific 'miracle_test' db
            'user': 'postgres',
            'password': 'password',
            'pool_size': 2
        }
    }


@pytest.mark.asyncio
@pytest.mark.skip(reason="Integration test requires a live PostgreSQL instance with pgvector.")
async def test_full_task_lifecycle(test_db_config):
    """Integrates create_task, create_iteration, and update_iteration flows."""
    # 1. Initialize the manager
    db = DatabaseManager(test_db_config)
    
    try:
        # 2. Create task
        task_id = await db.create_task(
            description="Integration test goal",
            goal="Test the database",
            metadata={"problem_type": "testing"}
        )
        assert task_id is not None
        
        # 3. Create iteration
        iteration_id = await db.create_iteration(
            task_id=task_id,
            iteration_number=1,
            phase='planning'
        )
        assert iteration_id is not None
        
        # 4. Update iteration
        await db.update_iteration(
            iteration_id=iteration_id,
            reflection="This went well",
            tokens_used=150
        )
        
        # 5. Retrieve task
        task = await db.get_task(task_id)
        assert task['status'] == 'planning'
        assert task['description'] == "Integration test goal"
        
        # 6. Finalize task
        await db.update_task_status(
            task_id=task_id,
            status='success',
            total_iterations=1,
            final_code="print('done')"
        )
        
        final_task = await db.get_task(task_id)
        assert final_task['status'] == 'success'
        assert final_task['final_code'] == "print('done')"
        
    finally:
        await db.close()
