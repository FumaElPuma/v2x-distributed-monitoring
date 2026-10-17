# V2X Distributed Monitoring

Group project for the Distributed Systems course.

The goal of the project is to build a distributed V2X monitoring and
alerting system using synthetic vehicle events and AWS services.

## Deliverable 1 — MVP

For the first deliverable, the system will implement the following path:

Simulator → Amazon SQS → V2X-SERVICE → DynamoDB / Alerts

The simulator generates synthetic events for at least five vehicles.
These events are sent to the `v2x-events` SQS queue.

V2X-SERVICE runs as a Docker container on EC2, consumes the events,
stores the required information and generates alerts when a configured
condition is detected.

GitHub Actions is used to automatically run the project tests, build
the V2X-SERVICE Docker image and publish it to Amazon ECR.

RSUs, MQTT and SNS alert distribution are outside the scope of
Deliverable 1 and will be introduced in Deliverable 2.

## Repository structure

```text
v2x-distributed-monitoring/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── simulator/
│   └── Synthetic vehicle simulator
│
├── services/
│   └── v2x-service/
│       └── Cloud event processing service
│
├── schema/
│   └── Shared event and alert schemas
│
├── infra/
│   └── AWS infrastructure configuration
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
│
├── docs/
│   └── Project documentation
│
├── .gitignore
└── README.md