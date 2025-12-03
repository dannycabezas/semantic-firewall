import logging
import os
from dataclasses import dataclass
from typing import BinaryIO, Optional

from minio import Minio
from minio.error import S3Error


logger = logging.getLogger(__name__)


@dataclass
class MinioConfig:
    endpoint: str
    access_key: str
    secret_key: str
    bucket_name: str
    secure: bool = False


class MinioDatasetStorage:
    """
    Storage adapter for datasets using MinIO.

    It is used to store the original files (CSV/JSON) of the custom datasets
    used in benchmarks.
    """

    def __init__(self, config: Optional[MinioConfig] = None) -> None:
        if config is None:
            endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
            # Minio client expects endpoint without scheme for the host
            endpoint = endpoint.replace("http://", "").replace("https://", "")
            config = MinioConfig(
                endpoint=endpoint,
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                bucket_name=os.getenv("MINIO_BUCKET", "datasets"),
                secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            )

        self._config = config
        self._client = Minio(
            endpoint=self._config.endpoint,
            access_key=self._config.access_key,
            secret_key=self._config.secret_key,
            secure=self._config.secure,
        )

        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket if it does not exist."""
        try:
            if not self._client.bucket_exists(self._config.bucket_name):
                logger.info("Creating MinIO bucket for datasets: %s", self._config.bucket_name)
                self._client.make_bucket(self._config.bucket_name)
        except S3Error as exc:  # pragma: no cover - defensivo
            logger.error("Error checking/creating MinIO bucket: %s", exc)
            raise

    def upload_dataset(self, file_key: str, file_obj: BinaryIO, length: int, content_type: str) -> None:
        """
        Upload a dataset file to MinIO.

        Args:
            file_key: Key/object inside the bucket (e.g., \"datasets/<uuid>.csv\").
            file_obj: Binary stream of the file.
            length: Length of the file in bytes.
            content_type: Content type (\"text/csv\", \"application/json\", etc.).
        """
        try:
            logger.info("Uploading dataset to MinIO: key=%s, length=%s", file_key, length)
            self._client.put_object(
                bucket_name=self._config.bucket_name,
                object_name=file_key,
                data=file_obj,
                length=length,
                content_type=content_type,
            )
        except S3Error as exc:
            logger.error("Error uploading dataset to MinIO: %s", exc)
            raise

    def download_dataset(self, file_key: str) -> BinaryIO:
        """
        Download a dataset file from MinIO.

        The caller is responsible for closing the returned stream.
        """
        try:
            logger.info("Downloading dataset from MinIO: key=%s", file_key)
            return self._client.get_object(
                bucket_name=self._config.bucket_name,
                object_name=file_key,
            )
        except S3Error as exc:
            logger.error("Error downloading dataset from MinIO: %s", exc)
            raise

    def delete_dataset(self, file_key: str) -> None:
        """Delete a dataset file from the bucket."""
        try:
            logger.info("Deleting dataset from MinIO: key=%s", file_key)
            self._client.remove_object(
                bucket_name=self._config.bucket_name,
                object_name=file_key,
            )
        except S3Error as exc:
            logger.error("Error deleting dataset from MinIO: %s", exc)
            raise

    def dataset_exists(self, file_key: str) -> bool:
        """Check if a dataset file exists in the bucket."""
        try:
            self._client.stat_object(
                bucket_name=self._config.bucket_name,
                object_name=file_key,
            )
            return True
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return False
            logger.error("Error checking existence of dataset in MinIO: %s", exc)
            raise


