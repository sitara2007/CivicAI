from pathlib import Path
from typing import Any

import magic


class DocumentValidator:
    """Validates incoming document structure and size limits."""
    
    ALLOWED_MIME_TYPES = {
        "application/pdf": "PDF",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
        "text/plain": "TXT",
    }
    MAX_FILE_SIZE_MB = 10

    @classmethod
    def validate_file(cls, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"valid": False, "error": "File not found"}

        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > cls.MAX_FILE_SIZE_MB:
            return {"valid": False, "error": f"File exceeds {cls.MAX_FILE_SIZE_MB}MB limit"}

        mime = magic.from_file(file_path, mime=True)
        if mime not in cls.ALLOWED_MIME_TYPES:
            return {"valid": False, "error": f"Unsupported file type: {mime}"}

        return {
            "valid": True,
            "mime_type": mime,
            "file_type": cls.ALLOWED_MIME_TYPES[mime],
            "size_mb": round(file_size_mb, 2),
        }
