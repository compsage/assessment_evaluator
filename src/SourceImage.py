from PIL import Image, ExifTags
from fractions import Fraction
import base64
import os
from pathlib import Path
from urllib.parse import urlparse
import requests
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError, PartialCredentialsError
import io
import json


class SourceImage:
    # Class-level source type (either "file", "s3", or "url")
    source_type = None
    # Class-level file suffix (e.g., .jpg, .png)
    file_suffix = None

    def __init__(self, source, auth=None, additional_metadata=None):
        """
        Initializes the SourceImage by detecting the source type and loading data accordingly.
        :param source: File path (for 'file'), S3 URL (e.g., 's3://bucket/key'), or HTTP/HTTPS URL.
        :param auth: Optional authentication for URL (tuple for basic auth, e.g., (username, password)).
        :param additional_metadata: Optional dictionary to add to the metadata.
        """
        self.binary_data = None
        self.base64_data = None
        self.metadata = {}

        try:
            # Determine the source type and extract the file suffix
            if isinstance(source, str) and source.startswith("s3://"):
                SourceImage.source_type = "s3"
                bucket_name, key = self._parse_s3_url(source)
                SourceImage.file_suffix = self._extract_file_suffix(key)
                self._load_from_s3(bucket_name, key)
            elif isinstance(source, str) and Path(source).exists():
                SourceImage.source_type = "file"
                SourceImage.file_suffix = self._extract_file_suffix(source)
                self._load_from_file(source)
            elif isinstance(source, str) and source.startswith(("http://", "https://")):
                SourceImage.source_type = "url"
                SourceImage.file_suffix = self._extract_file_suffix(source)
                self._load_from_url(source, auth)
            else:
                raise ValueError("Invalid source. Provide a valid file path, S3 URL, or HTTP/HTTPS URL.")

            # Extract metadata after loading binary data
            self._extract_metadata()

            # Add any additional metadata passed in the constructor
            if additional_metadata:
                self.add_metadata(additional_metadata)

        except Exception as e:
            raise RuntimeError(f"Failed to initialize SourceImage for source: {source}") from e

    def _parse_s3_url(self, s3_url):
        """
        Parses an S3 URL into bucket name and key.
        :param s3_url: S3 URL (e.g., 's3://bucket/key').
        :return: Tuple (bucket_name, key).
        """
        parsed = urlparse(s3_url)
        if not parsed.netloc or not parsed.path:
            raise ValueError("Invalid S3 URL format. Expected 's3://bucket/key'.")
        bucket_name = parsed.netloc
        key = parsed.path.lstrip("/")
        return bucket_name, key

    def _load_from_file(self, filepath):
        """
        Loads image data from the filesystem.
        :param filepath: Path to the image file.
        """
        try:
            path = Path(filepath)
            if not path.is_file():
                raise FileNotFoundError(f"Image not found at {filepath}")

            self.binary_data = path.read_bytes()
            self.base64_data = base64.b64encode(self.binary_data).decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {filepath}") from e
    
    @staticmethod
    def _extract_file_suffix(source):
        """
        Extracts the file suffix from the source (e.g., '.jpg', '.png').
        :param source: The input source path or URL.
        :return: File suffix as a string (e.g., '.jpg').
        """
        return Path(source).suffix.lower()


    def _load_from_s3(self, bucket_name, key):
        """
        Loads image data from S3.
        :param bucket_name: S3 bucket name.
        :param key: S3 object key.
        """
        try:
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            s3_client = boto3.client("s3", region_name=aws_region)

            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            self.binary_data = response["Body"].read()
            self.base64_data = base64.b64encode(self.binary_data).decode("utf-8")
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise RuntimeError("AWS credentials error.") from e
        except BotoCoreError as e:
            raise RuntimeError(f"Failed to load image from S3: {bucket_name}/{key}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error accessing S3: {bucket_name}/{key}") from e

    def _load_from_url(self, url, auth):
        """
        Loads image data from a URL.
        :param url: HTTP/HTTPS URL to the image file.
        :param auth: Optional authentication for the URL.
        """
        try:
            response = requests.get(url, auth=auth, timeout=10)
            if response.status_code == 200:
                self.binary_data = response.content
                self.base64_data = base64.b64encode(self.binary_data).decode("utf-8")
            else:
                raise ValueError(f"Failed to download from {url}. HTTP status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error downloading media from {url}") from e

    def _extract_metadata(self):
        """
        Extracts metadata from image binary data if the image format supports it.
        """
        try:
            image = Image.open(io.BytesIO(self.binary_data))
            self.metadata = {"format": image.format, "size": image.size, "mode": image.mode}

            # Extract EXIF metadata if available
            if hasattr(image, "_getexif"):
                exif_data = image._getexif()
                if exif_data is not None:
                    self.metadata["exif"] = {
                        ExifTags.TAGS.get(tag, tag): self._make_json_serializable(value)
                        for tag, value in exif_data.items()
                    }
        except Exception as e:
            # Log the error but continue gracefully
            print(f"Warning: Failed to extract metadata: {e}")

    @staticmethod
    def _make_json_serializable(value):
        """
        Converts non-serializable objects (e.g., IFDRational) to JSON-serializable formats.
        :param value: The value to convert.
        :return: JSON-serializable value.
        """
        if isinstance(value, Fraction):
            # Convert IFDRational or Fraction to float
            return float(value)
        elif isinstance(value, bytes):
            # Convert bytes to string for JSON compatibility
            return value.decode('utf-8', errors='replace')
        elif isinstance(value, tuple):
            # Recursively convert tuple elements
            return tuple(SourceImage._make_json_serializable(v) for v in value)
        elif isinstance(value, list):
            # Recursively convert list elements
            return [SourceImage._make_json_serializable(v) for v in value]
        elif isinstance(value, dict):
            # Recursively convert dictionary values
            return {k: SourceImage._make_json_serializable(v) for k, v in value.items()}
        else:
            try:
                # Attempt to directly return simple types (int, str, float)
                json.dumps(value)  # Test if value is JSON-serializable
                return value
            except TypeError:
                # Fallback to converting to string
                return str(value)

    def add_metadata(self, metadata_dict):
        """
        Adds or updates metadata using a dictionary.
        :param metadata_dict: Dictionary of metadata to add or update.
        """
        if not isinstance(metadata_dict, dict):
            raise ValueError("Metadata must be a dictionary.")
        self.metadata.update(metadata_dict)

    def write(self, destination, filename, write_metadata=True):
        """
        Writes the image and optionally its metadata to the specified destination.
        :param destination: The path or S3 bucket to write to.
        :param filename: The name of the image file.
        :param write_metadata: Whether to write metadata as a JSON file (default: True).
        """
        try:
            if destination.startswith("s3://"):
                bucket_name, key_prefix = self._parse_s3_url(destination)
                self._write_to_s3(bucket_name, f"{key_prefix}/{filename}")
                if write_metadata:
                    self._write_metadata_to_s3(bucket_name, f"{key_prefix}/{filename}.metadata.json")
            else:
                output_file = Path(destination) / filename
                self._write_to_file(output_file)
                if write_metadata:
                    metadata_file = output_file.with_suffix(".metadata.json")
                    self._write_metadata_to_file(metadata_file)
        except Exception as e:
            raise RuntimeError(f"Failed to write to destination: {destination}") from e

    def _write_to_file(self, filepath):
        """
        Writes binary data to the filesystem.
        :param filepath: Full file path to save the binary image.
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(self.binary_data)

    def _write_metadata_to_file(self, filepath):
        """
        Writes metadata to a JSON file on the filesystem.
        :param filepath: Full file path for the metadata file.
        """
        with open(filepath, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def _write_metadata_to_s3(self, bucket_name, key):
        """
        Writes metadata to an S3 bucket as a JSON file.
        :param bucket_name: S3 bucket name.
        :param key: S3 object key for the metadata file.
        """
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        s3_client = boto3.client("s3", region_name=aws_region)
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=json.dumps(self.metadata))

    def _write_to_s3(self, bucket_name, key):
        """
        Writes binary data to an S3 bucket.
        :param bucket_name: S3 bucket name.
        :param key: S3 object key for the image.
        """
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        s3_client = boto3.client("s3", region_name=aws_region)
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=self.binary_data)

    def get_binary(self):
        """
        Returns the binary data of the image.
        :return: Binary data.
        """
        if self.binary_data is None:
            raise RuntimeError("No binary data available. Ensure the source was loaded correctly.")
        return self.binary_data

    def get_base64(self):
        """
        Returns the base64 encoded string of the image.
        :return: Base64 encoded string.
        """
        if self.base64_data is None:
            raise RuntimeError("No base64 data available. Ensure the source was loaded correctly.")
        return self.base64_data

    def get_metadata(self):
        if self.metadata is None:
            raise RuntimeError("No metadata available.")
        return self.metadata