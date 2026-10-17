import boto3, json, sys, uuid
from datetime import datetime, timezone

sqs = boto3.client("sqs", region_name="us-east-1")
url = sqs.get_queue_url(QueueName="v2x-events")["QueueUrl"]
event_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
ev = {
    "event_id": event_id, "source_id": "veh-0002", "source_type": "vehicle", "seq": 1,
    "event_type": "brake",
    "event_time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    "location": {"segment_id": "S03", "rsu_id": "rsu-1", "lane": 1, "x": 81.2, "y": -23.3},
    "payload": {"decel_mps2": 6.8, "speed_before_mps": 27.1},
    "schema_version": "1.0", "sim_time_s": 131.4,
}
sqs.send_message(QueueUrl=url, MessageBody=json.dumps(ev))
print("sent", event_id)
