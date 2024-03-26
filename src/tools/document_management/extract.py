import concurrent.futures
import json
import logging
import os
from typing import Any, Dict, Optional

from azure.storage.blob import BlobServiceClient
from tools.research.schemas import SourceEngineSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DocumentEngine:

    def __init__(
        self,
        schema: SourceEngineSchema,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.schema = schema
        self.data = data

    def __upload_file_to_blob(
        self, connect_str: str, container_name: str, file_path: str
    ) -> None:
        try:
            file_name = os.path.basename(file_path)
            blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(connect_str)
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=file_name
            )

            with open(file_path, 'rb') as data:
                blob_client.upload_blob(data)

            logger.info("Successfully uploaded file: %s", file_name)

        except Exception as e:
            logger.error(
                "Error occurred while uploading to Azure Blob Storage: %s",
                str(e),
            )
            raise e

    def post_data(self) -> None:
        """Uploads all files in a specified folder to Azure Blob Storage."""
        folder_path = "C:\\Users\\rcataldi\\Downloads\\OneDrive_2024-03-26"
        container_name: str = self.schema.destination.get("blob-container", "")
        connect_str: str = self.schema.destination.get("blob-connection-string", "")

        if any((container_name == "", connect_str == "")):
            raise AttributeError("You must define destination parameters.")

        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                self.__upload_file_to_blob(connect_str, container_name, file_path)
