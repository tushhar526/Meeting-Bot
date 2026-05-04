"""Custom FileResponse with success metadata headers."""
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any
import json


class FileSuccessResponse(FileResponse):
    """
    FileResponse with success metadata in headers.
    Returns the file directly while including success info in X-* headers.
    """

    def __init__(
        self,
        path: str,
        message: str = "File delivered successfully",
        data: Optional[Dict[str, Any]] = None,
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        status_code: int = 200,
        **kwargs
    ):
        # Build headers with success metadata
        all_headers = headers or {}
        all_headers["X-Success"] = "true"
        all_headers["X-Message"] = message
        if data:
            all_headers["X-Data"] = json.dumps(data, default=str)

        super().__init__(
            path=path,
            media_type=media_type,
            filename=filename,
            headers=all_headers,
            status_code=status_code,
            **kwargs
        )
