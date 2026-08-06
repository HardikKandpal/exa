import mimetypes
import os

from app.services.artifact_service import ArtifactService
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.get("/{artifact_id}")
async def download_artifact(artifact_id: str):
    """Downloads or serves generated artifact files (.xlsx, .pptx, .png)."""
    filepath = ArtifactService.get_artifact_path(artifact_id)
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artifact file not found or has expired.")

    media_type, _ = mimetypes.guess_type(filepath)
    if not media_type:
        if filepath.endswith(".xlsx"):
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filepath.endswith(".pptx"):
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif filepath.endswith(".png"):
            media_type = "image/png"
        else:
            media_type = "application/octet-stream"

    filename = os.path.basename(filepath)
    return FileResponse(
        path=filepath,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
