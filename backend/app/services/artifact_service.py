import logging
import os
import time
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class ArtifactService:

    @staticmethod
    def ensure_artifacts_dir() -> str:
        artifacts_dir = os.path.abspath(settings.ARTIFACTS_DIR)
        os.makedirs(artifacts_dir, exist_ok=True)
        return artifacts_dir

    @classmethod
    def get_artifact_path(cls, artifact_id: str) -> str | None:
        artifacts_dir = cls.ensure_artifacts_dir()
        for fname in os.listdir(artifacts_dir):
            if fname.startswith(artifact_id):
                return os.path.join(artifacts_dir, fname)
        return None

    @classmethod
    def create_artifact_file(cls, extension: str) -> tuple[str, str]:
        """Generates a unique artifact ID and filepath, running periodic cleanup."""
        cls.cleanup_old_artifacts()
        artifacts_dir = cls.ensure_artifacts_dir()
        artifact_id = str(uuid.uuid4())[:8]
        ext = extension if extension.startswith(".") else f".{extension}"
        filename = f"{artifact_id}{ext}"
        filepath = os.path.join(artifacts_dir, filename)
        return artifact_id, filepath

    @classmethod
    def cleanup_old_artifacts(cls, max_age_hours: float = 24.0):
        """Deletes generated artifact files older than max_age_hours to prevent disk growth."""
        try:
            artifacts_dir = cls.ensure_artifacts_dir()
            cutoff_time = time.time() - (max_age_hours * 3600)
            removed_count = 0

            for fname in os.listdir(artifacts_dir):
                fpath = os.path.join(artifacts_dir, fname)
                if os.path.isfile(fpath):
                    if os.path.getmtime(fpath) < cutoff_time:
                        os.remove(fpath)
                        removed_count += 1

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} expired artifact files older than {max_age_hours}h.")
        except Exception as e:
            logger.warning(f"Error during artifact cleanup: {e}")
