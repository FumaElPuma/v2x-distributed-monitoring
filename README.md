# V2X Distributed Monitoring

## Architecture (example of devops pipeline 3)

```text
Simulator ──▶ SQS v2x-events ──▶ V2X-SERVICE (Docker on EC2) ──▶ DynamoDB
               (+ DLQ)            consumer + dashboard :8080      events / windows / alerts

GitHub Actions ──▶ ECR v2x-service ──▶ EC2 (deploy.sh through SSM)
```

- **Simulator** (`simulator/`): five vehicles on a synthetic ring road, six event types, sent to SQS.
- **V2X-SERVICE** (`services/v2x-service/`): validates and stores each event, raises a sudden-braking alert
  (deceleration ≥ 4 m/s²), serves the dashboard and REST API.
- **CI/CD** (`.github/workflows/ci.yml`): tests and build on every push; on `main`, push to ECR and deploy to EC2.

## Design decisions

- **SQS between producer and consumer**: either side can stop without losing events; standard queue, order
  recovered from `seq` and `event_time`; failing messages go to a dead-letter queue after 5 receives.
- **Idempotent processing**: the event is stored only if its `event_id` is new, in the same DynamoDB transaction
  as the aggregate update; the SQS message is deleted only after the writes succeed. Duplicates are never counted
  or alerted twice.
- **Shared JSON Schema** (`schema/v2x-event.schema.json`) validated by the service and the tests.
- **Physics-based simulator** (Intelligent Driver Model): alerts come from real braking, reproducible from a seed.
  Segments are already split into two RSU zones so the edge layer can be added without changing the data.
- **No keys on EC2**: the instance uses `LabInstanceProfile`; no SSH, deployment through SSM; images tagged with
  the commit SHA for traceability.

## Structure

```text
.github/workflows/    ci.yml, aws-check.yml, ecr-smoke.yml
simulator/            simulator and scenarios (see simulator/README.md)
services/v2x-service/ app.py, dashboard.html, requirements.txt, Dockerfile
schema/               v2x-event.schema.json
infra/aws/            userdata-service.sh (EC2 user data, installs Docker and deploy.sh)
infra/scripts/        send_test_event.py
tests/unit/           tests
```

## Tests

```bash
pip install pytest jsonschema -r simulator/requirements.txt
pytest -q
```

## Run

Requires an AWS Academy session (`us-east-1`) with credentials in `~/.aws/credentials`, the SQS queue
`v2x-events`, the DynamoDB tables `v2x-events`, `v2x-windows`, `v2x-alerts` and the instance deployed.

```bash
# simulator: 5 vehicles, accident scenario, 5 minutes in real time
python -m simulator --scenario simulator/scenarios/accident.yaml --transport sqs

# dashboard
aws ec2 describe-instances --filters Name=tag:Role,Values=v2x-service Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].PublicIpAddress' --output text     # open http://<IP>:8080
```

Manual deployment of an image tag:

```bash
aws ssm send-command --document-name AWS-RunShellScript --targets Key=tag:Role,Values=v2x-service \
  --parameters 'commands=["/opt/v2x/deploy.sh <tag>"]'
```

## CI/CD configuration

Repository secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` (Learner Lab session
credentials, updated every session) and variables `AWS_REGION = us-east-1`, `ECR_REPOSITORY = v2x-service`.