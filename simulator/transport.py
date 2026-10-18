"""Where generated events go: SQS (D1), stdout (dry runs), a list (tests). MQTT arrives in D2."""
import json
import sys
import time


class ListTransport:
    def __init__(self):
        self.events = []

    def send(self, events):
        self.events.extend(events)

    def close(self):
        pass


class StdoutTransport:
    def send(self, events):
        for ev in events:
            sys.stdout.write(json.dumps(ev, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    def close(self):
        pass


class SqsTransport:
    """Sends events to an SQS queue with SendMessageBatch (10 per call), retrying failed entries."""

    def __init__(self, queue_name="v2x-events", region="us-east-1", max_retries=3):
        import boto3  # imported here so tests and dry runs do not need AWS
        self.sqs = boto3.client("sqs", region_name=region)
        self.url = self.sqs.get_queue_url(QueueName=queue_name)["QueueUrl"]
        self.max_retries = max_retries
        self.stats = {"sent": 0, "failed": 0, "batches": 0}

    def send(self, events):
        for i in range(0, len(events), 10):
            self._send_batch(events[i:i + 10])

    def _send_batch(self, batch):
        entries = {str(n): json.dumps(ev, separators=(",", ":")) for n, ev in enumerate(batch)}
        for attempt in range(self.max_retries + 1):
            resp = self.sqs.send_message_batch(
                QueueUrl=self.url,
                Entries=[{"Id": k, "MessageBody": body} for k, body in entries.items()])
            self.stats["batches"] += 1
            self.stats["sent"] += len(resp.get("Successful", []))
            failed = {f["Id"] for f in resp.get("Failed", [])}
            entries = {k: v for k, v in entries.items() if k in failed}
            if not entries:
                return
            time.sleep(0.2 * 2 ** attempt)
        self.stats["failed"] += len(entries)

    def close(self):
        pass


class MqttTransport:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("MQTT transport is part of Deliverable 2")
