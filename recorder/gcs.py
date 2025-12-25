import logging

from pydantic import BaseModel
from google.cloud import storage


class Recording(BaseModel):
    time: str
    url: str


def upload_to_gcs(source: str, gcs_path: str) -> str:
    bucket_name, dest = _get_bucket_and_blob_name(gcs_path)
    logging.info(f"Uploading {source} to {dest} in {bucket_name}.")
    client = storage.Client(project="birdhouse-464804")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest)
    blob.upload_from_filename(source)
    logging.info(f"File {source} uploaded to {dest} in {bucket_name}.")
    return blob.public_url


def _get_bucket_and_blob_name(gcs_path: str) -> tuple[str, str]:
    *_, bucket_name, blob_name = gcs_path.split("/", maxsplit=3)
    return bucket_name, blob_name
