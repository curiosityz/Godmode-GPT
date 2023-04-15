import time
from google.cloud import storage

private_bucket_name = "godmode-ai"
public_bucket_name = "godmode-public"

client = storage.Client()
private_bucket = client.bucket(private_bucket_name)


def upload_log(text: str, session_id: str):
    timestamp = time.time()
    blob = private_bucket.blob(f"godmode-logs/{session_id}/{int(timestamp * 1000)}.txt")
    blob.upload_from_string(
        text,
        content_type="text/plain",
    )

bucket = client.bucket(public_bucket_name)

def write_file(text: str, filename: str, agent_id: str):
    blob = bucket.blob(f"godmode-files/{agent_id}/{filename}")
    blob.upload_from_string(
        text,
        content_type="text/plain",
    )


def get_file(filename: str, agent_id: str):
    blob = bucket.blob(f"godmode-files/{agent_id}/{filename}")
    try:
        text = blob.download_as_text()
        return text
    except Exception as e:
        return ""


def list_files(agent_id: str):
    blobs = bucket.list_blobs(prefix=f"godmode-files/{agent_id}/")
    return [file.name for file in blobs]


def get_file_urls(agent_id: str):
    blobs = client.list_blobs(public_bucket_name, prefix=f"godmode-files/{agent_id}/")
    return [file.public_url for file in blobs]
