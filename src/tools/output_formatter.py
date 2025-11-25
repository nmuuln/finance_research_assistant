import os
import io
import base64
from datetime import datetime

class OutputFormatterTool:
    """
    Converts final text into a .docx file and returns the path and text.
    Also returns base64 encoded content for download.
    """
    name = "OutputFormatterTool"
    description = "Converts final text into a .docx and returns {'path','text','download_url'}."

    def __call__(self, text: str, out_dir: str = "outputs", filename_prefix: str = "ufe_finance_report"):
        try:
            from docx import Document  # lazy import so missing dependency doesn't break agent load
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "python-docx is required to export reports. "
                "Install with `pip install python-docx` or `pip install -r requirements.txt`."
            ) from exc

        os.makedirs(out_dir, exist_ok=True)
        fname = f"{filename_prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        path = os.path.join(out_dir, fname)

        # Create document
        doc = Document()
        for line in text.split("\n"):
            doc.add_paragraph(line)

        # Save to file
        doc.save(path)

        # Also save to bytes buffer for immediate access
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Base64 encode for embedding in response (if needed for download)
        file_data = buffer.getvalue()
        base64_data = base64.b64encode(file_data).decode('utf-8')

        # Check if we should upload to cloud storage
        download_url = self._upload_to_storage(fname, file_data)

        return {
            "path": path,
            "text": text,
            "filename": fname,
            "download_url": download_url or f"file://{path}",
            "size_bytes": len(file_data)
        }

    def _upload_to_storage(self, filename: str, file_data: bytes) -> str | None:
        """Upload to Google Cloud Storage or DigitalOcean Spaces if credentials available."""

        # Try Google Cloud Storage first
        gcs_url = self._upload_to_gcs(filename, file_data)
        if gcs_url:
            return gcs_url

        # Fall back to DigitalOcean Spaces
        return self._upload_to_do_spaces(filename, file_data)

    def _upload_to_gcs(self, filename: str, file_data: bytes) -> str | None:
        """Upload to Google Cloud Storage."""
        try:
            from google.cloud import storage

            # Get bucket name from env
            bucket_name = os.getenv("GCS_BUCKET_NAME")
            if not bucket_name:
                # Try extracting from VERTEX_STAGING_BUCKET
                vertex_bucket = os.getenv("VERTEX_STAGING_BUCKET", "")
                if vertex_bucket.startswith("gs://"):
                    bucket_name = vertex_bucket.replace("gs://", "")
                else:
                    return None

            # Initialize GCS client
            client = storage.Client(project=os.getenv("PROJECT_ID"))
            bucket = client.bucket(bucket_name)

            # Upload file
            blob = bucket.blob(f"reports/{filename}")
            blob.upload_from_string(
                file_data,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

            # Make public and return URL
            blob.make_public()
            return blob.public_url

        except ImportError:
            return None
        except Exception as e:
            print(f"Failed to upload to GCS: {e}")
            return None

    def _upload_to_do_spaces(self, filename: str, file_data: bytes) -> str | None:
        """Upload to DigitalOcean Spaces if credentials available."""
        try:
            import boto3
            from botocore.client import Config

            # Check for DO Spaces credentials
            spaces_key = os.getenv("SPACES_ACCESS_KEY")
            spaces_secret = os.getenv("SPACES_SECRET_KEY")
            spaces_region = os.getenv("SPACES_REGION", "nyc3")
            spaces_bucket = os.getenv("SPACES_BUCKET", "ufe-reports")

            if not spaces_key or not spaces_secret:
                return None

            # Initialize S3 client for DO Spaces
            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name=spaces_region,
                endpoint_url=f'https://{spaces_region}.digitaloceanspaces.com',
                aws_access_key_id=spaces_key,
                aws_secret_access_key=spaces_secret,
                config=Config(signature_version='s3v4')
            )

            # Upload file
            client.put_object(
                Bucket=spaces_bucket,
                Key=f"reports/{filename}",
                Body=file_data,
                ACL='public-read',
                ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

            # Return public URL
            return f"https://{spaces_bucket}.{spaces_region}.digitaloceanspaces.com/reports/{filename}"

        except ImportError:
            # boto3 not installed
            return None
        except Exception as e:
            print(f"Failed to upload to Spaces: {e}")
            return None
