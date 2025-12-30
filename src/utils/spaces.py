"""DigitalOcean Spaces utility for file upload/download."""
import os
import io
from typing import Optional, BinaryIO
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class SpacesClient:
    """Client for DigitalOcean Spaces (S3-compatible object storage)."""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        bucket_name: Optional[str] = None
    ):
        """Initialize Spaces client.

        Args:
            access_key: Spaces access key (defaults to SPACES_ACCESS_KEY env)
            secret_key: Spaces secret key (defaults to SPACES_SECRET_KEY env)
            region: Spaces region (defaults to SPACES_REGION env, fallback: sgp1)
            bucket_name: Bucket name (defaults to SPACES_BUCKET env, fallback: finance-bucket)
        """
        self.access_key = access_key or os.getenv("SPACES_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("SPACES_SECRET_KEY")
        self.region = region or os.getenv("SPACES_REGION", "sgp1")
        self.bucket_name = bucket_name or os.getenv("SPACES_BUCKET", "finance-bucket")

        if not self.access_key or not self.secret_key:
            raise ValueError(
                "Spaces credentials not found. Set SPACES_ACCESS_KEY and SPACES_SECRET_KEY "
                "environment variables or pass them to SpacesClient()"
            )

        # Initialize S3 client for Spaces
        self.client = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=f'https://{self.region}.digitaloceanspaces.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

        self.endpoint = f'https://{self.bucket_name}.{self.region}.digitaloceanspaces.com'

    def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        make_public: bool = False
    ) -> str:
        """Upload file to Spaces.

        Args:
            file_content: File bytes to upload
            object_key: Object key (path) in Spaces (e.g., "uploads/session123/file.pdf")
            content_type: MIME type (e.g., "application/pdf")
            make_public: Whether to make file publicly accessible

        Returns:
            Public URL of uploaded file
        """
        extra_args = {}

        if content_type:
            extra_args['ContentType'] = content_type

        if make_public:
            extra_args['ACL'] = 'public-read'

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                **extra_args
            )

            # Return public URL
            url = f"{self.endpoint}/{object_key}"
            return url

        except ClientError as e:
            raise Exception(f"Failed to upload to Spaces: {str(e)}")

    def upload_file_from_path(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        make_public: bool = False
    ) -> str:
        """Upload file from local path to Spaces.

        Args:
            file_path: Local file path
            object_key: Object key in Spaces
            content_type: MIME type
            make_public: Whether to make file publicly accessible

        Returns:
            Public URL of uploaded file
        """
        with open(file_path, 'rb') as f:
            file_content = f.read()

        return self.upload_file(
            file_content=file_content,
            object_key=object_key,
            content_type=content_type,
            make_public=make_public
        )

    def download_file(self, object_key: str) -> bytes:
        """Download file from Spaces.

        Args:
            object_key: Object key in Spaces

        Returns:
            File content as bytes
        """
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response['Body'].read()

        except ClientError as e:
            raise Exception(f"Failed to download from Spaces: {str(e)}")

    def download_to_path(self, object_key: str, local_path: str) -> str:
        """Download file from Spaces to local path.

        Args:
            object_key: Object key in Spaces
            local_path: Local file path to save to

        Returns:
            Local file path
        """
        content = self.download_file(object_key)

        # Ensure directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, 'wb') as f:
            f.write(content)

        return local_path

    def delete_file(self, object_key: str) -> bool:
        """Delete file from Spaces.

        Args:
            object_key: Object key in Spaces

        Returns:
            True if successful
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True

        except ClientError as e:
            raise Exception(f"Failed to delete from Spaces: {str(e)}")

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in Spaces.

        Args:
            object_key: Object key in Spaces

        Returns:
            True if file exists
        """
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError:
            return False

    def get_public_url(self, object_key: str) -> str:
        """Get public URL for an object.

        Args:
            object_key: Object key in Spaces

        Returns:
            Public URL
        """
        return f"{self.endpoint}/{object_key}"


# Singleton instance
_spaces_client = None


def get_spaces_client() -> Optional[SpacesClient]:
    """Get or create Spaces client singleton.

    Returns:
        SpacesClient instance, or None if credentials not configured
    """
    global _spaces_client

    if _spaces_client is None:
        # Check if credentials are available
        if not os.getenv("SPACES_ACCESS_KEY") or not os.getenv("SPACES_SECRET_KEY"):
            return None

        try:
            _spaces_client = SpacesClient()
        except ValueError:
            return None

    return _spaces_client
