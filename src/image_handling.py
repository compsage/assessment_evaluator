from pathlib import Path
import base64
from urllib.parse import urlparse
from PIL import Image, ExifTags
from fractions import Fraction
import json
import io
import requests
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError, PartialCredentialsError
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Common functions
def extract_file_suffix(source):
    """Extracts the file suffix from the source path or URL."""
    return Path(source).suffix.lower()

def parse_s3_url(s3_url):
    """Parses an S3 URL into bucket name and key."""
    parsed = urlparse(s3_url)
    if not parsed.netloc or not parsed.path:
        raise ValueError("Invalid S3 URL format. Expected 's3://bucket/key'.")
    return parsed.netloc, parsed.path.lstrip("/")

def extract_image_metadata(binary_data):
    """Extracts metadata from image binary data."""
    try:
        image = Image.open(io.BytesIO(binary_data))
        metadata = {
            "format": image.format,
            "size": image.size,
            "mode": image.mode
        }

        if hasattr(image, "_getexif"):
            exif_data = image._getexif()
            if exif_data is not None:
                metadata["exif"] = {
                    ExifTags.TAGS.get(tag, tag): make_json_serializable(value)
                    for tag, value in exif_data.items()
                }
        return metadata
    except Exception as e:
        print(f"Warning: Failed to extract metadata: {e}")
        return {}

def make_json_serializable(value):
    """Converts non-serializable objects to JSON-serializable formats."""
    if isinstance(value, Fraction):
        return float(value)
    elif isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    elif isinstance(value, (tuple, list)):
        return [make_json_serializable(v) for v in value]
    elif isinstance(value, dict):
        return {k: make_json_serializable(v) for k, v in value.items()}
    else:
        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value) 

# Object to handle the image
class SourceImage:
    def __init__(self, source, auth=None, additional_metadata=None):
        """
        Initializes the SourceImage by detecting the source type and loading data accordingly.
        :param source: File path, S3 URL (s3://bucket/key), or HTTP/HTTPS URL
        :param auth: Optional authentication for URL
        :param additional_metadata: Optional dictionary to add to the metadata
        """
        self.source = source
        self.source_type = self._determine_source_type(source)
        self.file_suffix = extract_file_suffix(source)
        
        # Load binary data based on source type
        self.binary_data = self._load_binary_data(source, auth)
        self.base64_data = base64.b64encode(self.binary_data).decode("utf-8")
        
        # Extract and store metadata
        self.metadata = extract_image_metadata(self.binary_data)
        if additional_metadata:
            self.add_metadata(additional_metadata)

    def _determine_source_type(self, source):
        if isinstance(source, str):
            if source.startswith("s3://"):
                return "s3"
            elif source.startswith(("http://", "https://")):
                return "url"
            elif Path(source).exists():
                return "file"
        raise ValueError("Invalid source. Provide a valid file path, S3 URL, or HTTP/HTTPS URL.")

    def _load_binary_data(self, source, auth):
        if self.source_type == "file":
            return FileLoader.load(source)
        elif self.source_type == "s3":
            bucket_name, key = parse_s3_url(source)
            return S3Loader.load(bucket_name, key)
        elif self.source_type == "url":
            return URLLoader.load(source, auth)

    def add_metadata(self, metadata_dict):
        """Adds or updates metadata using a dictionary."""
        if not isinstance(metadata_dict, dict):
            raise ValueError("Metadata must be a dictionary.")
        self.metadata.update(metadata_dict)

    def get_binary(self):
        """Returns the binary data of the image."""
        return self.binary_data

    def get_base64(self):
        """Returns the base64 encoded string of the image."""
        return self.base64_data

    def get_metadata(self):
        """Returns the image metadata."""
        return self.metadata

    def get_source(self):
        """Returns the original source."""
        return self.source

# Loaders
class FileLoader:
    @staticmethod
    def load(filepath):
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found at {filepath}")
        return path.read_bytes()

class S3Loader:
    @staticmethod
    def load(bucket_name, key):
        try:
            s3_client = boto3.client("s3", region_name=AWS_REGION)
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            return response["Body"].read()
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise RuntimeError("AWS credentials error.") from e
        except BotoCoreError as e:
            raise RuntimeError(f"Failed to load image from S3: {bucket_name}/{key}") from e

class URLLoader:
    @staticmethod
    def load(url, auth=None):
        response = requests.get(url, auth=auth, timeout=10)
        if response.status_code == 200:
            return response.content
        raise ValueError(f"Failed to download from {url}. HTTP status code: {response.status_code}")

class ImageWriter:
    @staticmethod
    def write_to_filesystem(binary_data, filepath, metadata=None):
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(binary_data)
        
        if metadata:
            metadata_file = filepath.with_suffix(".metadata.json")
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=4)

    @staticmethod
    def write_to_s3(binary_data, bucket_name, key, metadata=None):
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=binary_data)
        
        if metadata:
            metadata_key = f"{key}.metadata.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata)
            ) 