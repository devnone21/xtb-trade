import os
import json
from google.cloud import pubsub_v1, storage, exceptions
from typing import Union


class Cloud:
    """Class of Cloud client. Currently only GCP."""
    def __init__(self) -> None:
        self.client: Union[tuple[None], pubsub_v1, storage] = None

    def pub(self, message: str) -> str:
        self.client = pubsub_v1.PublisherClient()
        topic_path = self.client.topic_path(
            project=os.getenv('GOOGLE_CLOUD_PROJECT'),
            topic=os.getenv('GOOGLE_PUBSUB_TOPIC'),
        )
        future = self.client.publish(topic_path, str(message).encode(), attr='ATTR VALUE')
        return future.result()

    def download_setting(self, appname: str) -> dict:
        bucket_name = "xtb-setting"
        blob_name = f"{appname}.json"
        self.client = storage.Client()
        try:
            blob = self.client.bucket(bucket_name).blob(blob_name)
            contents = blob.download_as_string()
            return json.loads(contents.decode())
        except exceptions.NotFound:
            return {}
