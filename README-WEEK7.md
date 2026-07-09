# Week 7: Incident Intake + Python Log Parser

## What Was Added

* `backend/incident-service` accepts alert webhooks, saves incidents to PostgreSQL, and calls the Python parser.
* `log-parser-service` exposes `POST /parse-log`, extracts log fields, and persists them to `parsed_logs`.
* Prometheus + Alertmanager now route blocked payment alerts into `incident-service`.
* Splunk now ingests the Logstash stream, runs a scheduled login-failure search, and posts matching results into `incident-service`.

## End-to-End Flow

```text
Alert Triggered
      |
      v
Alertmanager or Splunk webhook
      |
      v
incident-service
      |
      v
Incidents table
      |
      v
log-parser-service
      |
      v
parsed_logs table
```

## Demo Options

### Option 1: Live platform flow

1. Start the stack with Docker Compose.
2. Let `log-generator-service` run its scheduled batch.
3. The high-value payment block generates a `400` response in `payment-service`.
4. Prometheus fires `PaymentServiceBlockedPayments`.
5. Alertmanager sends the webhook to `incident-service`.
6. `incident-service` saves the incident and calls `log-parser-service`.
7. `log-parser-service` stores the parsed record in `parsed_logs`.

### Option 2: Splunk live flow

1. Start the stack with Docker Compose.
2. Let `log-generator-service` run its scheduled batch.
3. Logstash forwards the JSON logs to Splunk over TCP `10514`.
4. Splunk runs `Incident Platform - Login Failure` every minute.
5. Splunk posts the normalized webhook payload to `incident-service`.
6. `incident-service` saves the incident and calls `log-parser-service`.
7. `log-parser-service` stores the parsed record in `parsed_logs`.

### Option 3: Manual review demo

Use the provided script:

```powershell
./scripts/week7-demo.ps1
```

That posts `scripts/week7-demo-alert.json` to the webhook endpoint and then prints:

* saved incidents from `incident-service`
* saved parsed logs from `log-parser-service`
