"""Asynchronous background task worker module for CivicOS.

Handles heavy document triage workloads non-blockingly.
"""

import asyncio
import json
from typing import Any

from app.services.audit.audit_services import AuditLogger


class BackgroundTaskWorker:
    """Asynchronous background task worker for document processing."""

    def __init__(self, queue_name: str = 'document_triage'):
        """Initialize the background worker.

        Args:
            queue_name: Name of the task queue
        """
        self.queue_name = queue_name
        self.logger = AuditLogger(__name__)

    async def enqueue_task(self, task_data: dict[str, Any]) -> str:
        """Add a new document triage task to the queue.

        Args:
            task_data: Document information and processing instructions

        Returns:
            Task ID of the queued work
        """
        task_id = self._generate_task_id()
        await self._store_task(task_id, task_data)
        self.logger.info(f'Enqueued document task {task_id}')
        return task_id

    async def process_tasks(self):
        """Process queued document triage tasks non-blockingly."""
        while True:
            tasks = await self._fetch_pending_tasks()
            for task in tasks:
                try:
                    await self._process_single_task(task)
                except Exception as e:
                    self.logger.error(f'Error processing task {task.id}: {e!s}')
            await asyncio.sleep(1)

    async def _process_single_task(self, task: dict[str, Any]) -> None:
        """Handle individual document processing task."""
        self.logger.info(f'Processing task {task.get("id")}')
        document_content = task.get('content')
        if document_content:
            # Example: Extract key phrases or classify the document
            extracted_phrases = self._extract_key_phrases(document_content)
            self.logger.info(f'Extracted phrases: {extracted_phrases}')
        else:
            self.logger.error('Task has no document content')

    def _generate_task_id(self) -> str:
        """Generate unique task identifier."""
        from uuid import uuid4
        return str(uuid4())

    async def _store_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Store task data in persistent storage."""
        try:
            # Use Redis or a database to store the task
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.set(task_id, json.dumps(task_data))
            self.logger.info(f'Stored task {task_id} in Redis')
        except Exception as e:
            self.logger.error(f'Failed to store task {task_id}: {e!s}')

    async def _fetch_pending_tasks(self) -> list[dict[str, Any]]:
        """Retrieve pending tasks from storage."""
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            tasks = []
            for task_id in redis_client.keys():
                task_data = redis_client.get(task_id)
                if task_data:
                    tasks.append(json.loads(task_data))
            self.logger.info(f'Fetched {len(tasks)} pending tasks from Redis')
            return tasks
        except Exception as e:
            self.logger.error(f'Failed to fetch pending tasks: {e!s}')
            return []


async def start_worker():
    """Start the background worker service."""
    worker = BackgroundTaskWorker()
    await worker.process_tasks()
