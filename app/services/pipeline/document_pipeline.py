"""Document pipeline for CivicOS.

Handles incoming document triage requests and enqueues them for processing.
"""

from app.services.pii.analyzer import PIIAnalyzer
from app.services.pipeline.validation import DocumentValidator
from app.services.workers.background import BackgroundTaskWorker


class DocumentPipeline:
    """Pipeline for processing document triage requests."""

    def __init__(self):
        """Initialize the document pipeline."""
        self.worker = BackgroundTaskWorker()

    async def process_triage_request(self, file_path: str) -> str:
        """Process an incoming document triage request.

        Args:
            file_path: Path to the document file

        Returns:
            Task ID of the enqueued work
        """
        # Validate document
        validation_result = DocumentValidator.validate_file(file_path)
        if not validation_result["valid"]:
            raise ValueError(validation_result["error"])

        # Detect PII
        with open(file_path, "r") as f:  # Adjust for binary files (PDF/DOCX)
            text_content = f.read()
        pii_found = PIIAnalyzer.detect_pii(text_content)

        # Enqueue if valid
        if pii_found:
            masked_text = PIIAnalyzer.mask_pii(text_content)
            # Push to Redis queue (via BackgroundTaskWorker)
            task_id = await self.worker.enqueue_task({
                "file_path": file_path,
                "pii_detected": pii_found,
                "masked_content": masked_text,
            })
            return task_id
