import json, os, threading, time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import boto3, jsonschema
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer
from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
sqs = boto3.client("sqs", region_name=REGION)
ddb = boto3.client("dynamodb", region_name=REGION)
QUEUE_URL = sqs.get_queue_url(QueueName="v2x-events")["QueueUrl"]
SCHEMA = json.load(open("schema/v2x-event.schema.json"))
ser, des = TypeSerializer(), TypeDeserializer()
stats = {"received": 0, "stored": 0, "duplicate": 0, "invalid": 0, "alerts": 0}
state = {"last_poll": time.time()}

def item(d): return {k: ser.serialize(v) for k, v in d.items()}
def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def process(ev):
    ev.setdefault("trace", {})["cloud_received_time"] = now_iso()
    seg = ev["location"]["segment_id"]
    t = datetime.fromisoformat(ev["event_time"].replace("Z", "+00:00")).timestamp()
    ws, exp = int(t // 10 * 10), int(time.time()) + 86400
    p = ev["payload"]
    try:
        ddb.transact_write_items(TransactItems=[
            {"Put": {"TableName": "v2x-events", "Item": item(dict(ev, expire_at=exp)),
                     "ConditionExpression": "attribute_not_exists(event_id)"}},
            {"Update": {"TableName": "v2x-windows",
                        "Key": {"segment_id": {"S": seg}, "window_start": {"N": str(ws)}},
                        "UpdateExpression": "ADD event_count :one, speed_sum :s, speed_n :n, brake_count :b SET expire_at = :e",
                        "ExpressionAttributeValues": {
                            ":one": {"N": "1"}, ":s": {"N": str(p.get("speed_mps", 0))},
                            ":n": {"N": "1" if "speed_mps" in p else "0"},
                            ":b": {"N": "1" if ev["event_type"] == "brake" else "0"},
                            ":e": {"N": str(exp)}}}}])
    except ClientError as e:
        reasons = e.response.get("CancellationReasons", [{}])
        if e.response["Error"]["Code"] == "TransactionCanceledException" and reasons[0].get("Code") == "ConditionalCheckFailed":
            stats["duplicate"] += 1
            return
        raise
    stats["stored"] += 1
    if ev["event_type"] == "brake" and p["decel_mps2"] >= 4:
        alert = {"alert_id": f"brake:{ev['event_id']}", "alert_type": "sudden_braking", "origin": "cloud",
                 "severity": 2 if p["decel_mps2"] >= 7 else 1, "created_time": now_iso(),
                 "location": {"segment_id": seg, "rsu_id": ev["location"]["rsu_id"]},
                 "cause_event_ids": [ev["event_id"]], "schema_version": "1.0",
                 "message": f"Sudden braking by {ev['source_id']} on {seg}"}
        try:
            ddb.put_item(TableName="v2x-alerts", Item=item(alert),
                         ConditionExpression="attribute_not_exists(alert_id)")
            stats["alerts"] += 1
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise

def consume():
    while True:
        r = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=20)
        state["last_poll"] = time.time()
        for m in r.get("Messages", []):
            stats["received"] += 1
            try:
                ev = json.loads(m["Body"], parse_float=Decimal)
                jsonschema.validate(json.loads(m["Body"]), SCHEMA)
            except Exception:
                stats["invalid"] += 1
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=m["ReceiptHandle"])
                continue
            try:
                process(ev)
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=m["ReceiptHandle"])
            except Exception as e:  # not deleted: SQS redelivers after the visibility timeout
                print(json.dumps({"error": str(e), "event_id": ev.get("event_id")}), flush=True)

@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=consume, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    ok = time.time() - state["last_poll"] < 60
    return JSONResponse({"ok": ok}, status_code=200 if ok else 503)

@app.get("/alerts")
def alerts():
    rows = [{k: des.deserialize(v) for k, v in i.items()} for i in ddb.scan(TableName="v2x-alerts")["Items"]]
    return sorted(rows, key=lambda a: a["created_time"], reverse=True)[:100]

@app.get("/report")
def report():
    depth = sqs.get_queue_attributes(QueueUrl=QUEUE_URL, AttributeNames=["ApproximateNumberOfMessages"])
    return {**stats, "queue_depth": int(depth["Attributes"]["ApproximateNumberOfMessages"])}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return open("dashboard.html").read()   # small page that fetches /report and /alerts every 2 s
