# Log Aggregator Service

[![CI](https://github.com/CHUKEPC/log-aggregator/actions/workflows/ci.yml/badge.svg)](https://github.com/CHUKEPC/log-aggregator/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.12+-005571.svg?logo=elasticsearch&logoColor=white)](https://www.elastic.co/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)

A high-performance centralized log aggregation and analytics service. Designed as a lightweight, developer-friendly alternative to the ELK stack, featuring multi-format log parsing, Elasticsearch storage, full-text search, live WebSocket log tailing (`tail -f`), pattern-based alerting rules, and automated retention cleanup.

[Русская версия (Russian documentation)](README_RU.md)

---

## Features

- **Multi-Transport Log Ingestion**:
  - **REST API**: Single and bulk batch ingestion for structured JSON payloads.
  - **Raw Text Ingest**: Single and batch raw log endpoints with auto-detection or explicit format specifier.
  - **TCP Socket Receiver**: High-throughput asyncio TCP server (port 9000) for streaming raw log lines directly from syslog daemons, FluentBit, Logstash, or netcat.
- **Multi-Format Parsing Engine**:
  - **JSON**: Arbitrary structured logs with automatic field extraction and metadata preservation.
  - **Syslog**: Standard RFC 5424 and RFC 3164 (BSD) format parsing with PRI facility/severity mapping.
  - **Nginx**: Combined access logs (with HTTP status mapping) and error logs.
  - **Apache**: Combined and Common Log Format (CLF).
  - **Regex & Custom**: Named capture groups for custom application log formats.
- **Storage & Search (Elasticsearch)**:
  - Full-text search across messages, service names, and host sources.
  - Granular filtering: severity levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`), source, service, and tags.
  - Time-range queries (`start_time`, `end_time`) with ISO-8601 timestamps.
  - In-memory backend fallback for lightweight local development and testing.
- **Real-Time Streaming (WebSocket)**:
  - Live log streaming (`tail -f`) over `/ws/logs` with real-time per-client filtering by service, min level, and keyword.
- **Aggregation & Metrics**:
  - Distribution histograms by hour.
  - Log volume counts grouped by severity level and service.
  - Top error messages frequency rankings.
- **Pattern-Based Alerting**:
  - Configurable alert rules with error threshold count, regex keyword matching, or log velocity within sliding time windows.
  - Automated asynchronous webhook dispatching upon breach.
  - Historical alert events auditing.
- **Log Retention Policy (TTL)**:
  - Automated or manual pruning of expired logs older than $N$ days (`/api/v1/retention/cleanup`).
- **Production-Ready Security**:
  - OAuth2 Password Bearer & JWT authentication.
  - Service-to-service API key authentication via `X-API-Key` headers.
  - Client-level sliding window rate limiting.

---

## Tech Stack

- **Language & Runtime**: Python 3.11+ (tested on 3.11, 3.12, 3.13)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/), [Starlette](https://www.starlette.io/), [Uvicorn](https://www.uvicorn.org/)
- **Search Engine**: [Elasticsearch](https://www.elastic.co/) (`elasticsearch-py` async client)
- **Data Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/), [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Security**: PyJWT, Bcrypt, HTTPBearer
- **Real-Time Transport**: WebSockets, Asyncio TCP sockets
- **Quality & Testing**: Pytest, Pytest-Asyncio, Pytest-Cov, Ruff, Mypy (strict mode)
- **Containerization**: Docker, Docker Compose

---

## Architecture & Project Structure

The codebase adheres strictly to clean architecture principles with sub-packages dividing concern domains:

```
log-aggregator/
├── src/log_aggregator/
│   ├── __init__.py
│   ├── main.py                 # Application factory & lifecycle hooks (no business logic)
│   ├── config.py               # Pydantic BaseSettings environment config
│   ├── exceptions.py           # Domain exception hierarchy
│   ├── api/                    # HTTP & WebSocket routing layer
│   │   ├── __init__.py
│   │   ├── router.py           # Top-level API router (/api/v1)
│   │   ├── deps.py             # Security, rate limiting & DI providers
│   │   ├── auth.py             # JWT token issuance (/auth/login, /auth/token)
│   │   ├── ingest.py           # Log ingestion endpoints (/ingest, /ingest/batch, /ingest/raw)
│   │   ├── search.py           # Query & retrieve logs (/search, /logs/{id})
│   │   ├── stats.py            # Summary metrics & histograms (/stats)
│   │   ├── alerts.py           # Alert rules & events (/alerts/rules, /alerts/events)
│   │   ├── retention.py        # Log pruning endpoints (/retention/cleanup)
│   │   └── stream.py           # Real-time WebSocket streaming (/ws/logs)
│   ├── models/                 # Core domain dataclasses & enums
│   │   ├── __init__.py
│   │   └── log_entry.py        # LogEntry, LogFilter, LogStats, LogLevel, LogFormat
│   ├── schemas/                # Pydantic request & response models
│   │   ├── __init__.py
│   │   ├── auth.py             # Login credentials & JWT payload schemas
│   │   ├── log.py              # Ingest requests, search results & stats schemas
│   │   └── alerts.py           # Alert configuration & event schemas
│   ├── parsers/                # Log format parsing engine
│   │   ├── __init__.py
│   │   ├── base.py             # BaseLogParser abstract class
│   │   ├── factory.py          # Format auto-detection & parser resolver
│   │   ├── json_parser.py      # Structured JSON log parser
│   │   ├── syslog_parser.py    # RFC 5424 & RFC 3164 syslog parser
│   │   ├── nginx_parser.py     # Nginx access & error parser
│   │   ├── apache_parser.py    # Apache Combined & Common Log Format parser
│   │   └── regex_parser.py     # Custom regex named-capture parser
│   ├── storage/                # Data persistence layer
│   │   ├── __init__.py
│   │   ├── base.py             # LogStorage interface abstraction
│   │   ├── elasticsearch.py    # Async Elasticsearch backend
│   │   └── memory.py           # In-memory thread-safe storage (for tests/local dev)
│   ├── services/               # Core business logic layer
│   │   ├── __init__.py
│   │   ├── ingester.py         # Ingestion orchestration (parse -> store -> alert -> stream)
│   │   ├── searcher.py         # Full-text search & aggregate computation
│   │   ├── alerter.py          # Alert rules management
│   │   ├── retention.py        # TTL cleanup operations
│   │   └── streamer.py         # WebSocket pub/sub connection pool
│   ├── alerts/                 # Alerting domain engine
│   │   ├── __init__.py
│   │   ├── models.py           # AlertRule & AlertEvent domain entities
│   │   ├── evaluator.py        # Sliding-window threshold evaluator
│   │   └── notifier.py         # Asynchronous webhook dispatcher & event history
│   └── transport/              # Network receivers
│       ├── __init__.py
│       └── tcp_server.py       # Asyncio TCP socket server
├── tests/                      # Mirror test structure (unit & integration)
│   ├── conftest.py             # Shared pytest fixtures & mocks
│   ├── test_api/
│   ├── test_parsers/
│   ├── test_services/
│   ├── test_storage/
│   ├── test_alerts/
│   └── test_transport/
├── docker-compose.yml          # Full stack (App + Elasticsearch 8 + Kibana)
├── Dockerfile                  # Multi-stage production build
├── Makefile                    # Developer task automation
├── pyproject.toml              # Unified configuration (ruff, mypy, pytest)
├── .env.example                # Sample environment variables
├── README.md                   # English documentation
└── README_RU.md                # Russian documentation
```

---

## Installation & Quickstart

### Prerequisites
- Python 3.11+
- (Optional for full stack) Docker & Docker Compose

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/CHUKEPC/log-aggregator.git
   cd log-aggregator
   ```

2. **Create virtual environment and install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

4. **Run with in-memory storage (no Elasticsearch required)**:
   In `.env`, set:
   ```env
   USE_MEMORY_STORAGE=true
   ENVIRONMENT=development
   ```

5. **Start the API service**:
   ```bash
   uvicorn log_aggregator.main:app --reload --port 8000
   ```
   Open Swagger UI at: `http://localhost:8000/docs`

---

## Running with Docker Compose (Elasticsearch + Kibana)

Start the complete production stack (Log Aggregator + Elasticsearch 8.12 + Kibana):

```bash
docker-compose up -d
```

- **API Service**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **TCP Socket Listener**: `localhost:9000`
- **Elasticsearch API**: `http://localhost:9200`
- **Kibana Web UI**: `http://localhost:5601`

To stop services:
```bash
docker-compose down
```

---

## API Usage & Endpoints

### 1. Authentication

#### Obtain JWT Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpassword"}'
```
Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in_minutes": 60
}
```

---

### 2. Ingesting Logs

#### Ingest Structured Log (REST)
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "User failed checkout due to insufficient funds",
    "service": "payment-service",
    "level": "WARNING",
    "source": "api-gateway",
    "metadata": {
      "user_id": 98412,
      "amount": 250.00
    },
    "tags": ["payment", "checkout"]
  }'
```

#### Bulk Batch Ingestion
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/batch" \
  -H "X-API-Key: secret-payment-key" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {"message": "Cache refreshed", "service": "redis-cache", "level": "INFO"},
      {"message": "Database query latency exceeded 500ms", "service": "db-proxy", "level": "WARNING"}
    ]
  }'
```

#### Raw Ingest (Nginx, Syslog, JSON, Regex)
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/raw" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "raw": "192.168.1.1 - admin [10/Oct/2023:13:55:36 +0000] \"GET /api/v1/users HTTP/1.1\" 200 450",
    "format": "NGINX"
  }'
```

#### Ingestion via TCP Socket (e.g. netcat or logger)
```bash
echo '{"message": "Worker finished batch task", "service": "worker", "level": "INFO"}' | nc localhost 9000
```

---

### 3. Searching Logs

#### Full-Text Search with Filters
```bash
curl -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=failed" \
  --data-urlencode "service=payment-service" \
  --data-urlencode "level=WARNING" \
  --data-urlencode "limit=20"
```

Response:
```json
{
  "total": 1,
  "limit": 20,
  "offset": 0,
  "logs": [
    {
      "id": "4b6bb0ea-0bf1-4475-8eb9-a29dcf106b2f",
      "timestamp": "2026-10-23T20:30:00Z",
      "level": "WARNING",
      "service": "payment-service",
      "message": "User failed checkout due to insufficient funds",
      "source": "api-gateway",
      "metadata": {
        "user_id": 98412,
        "amount": 250.0
      },
      "tags": ["payment", "checkout"],
      "raw": null
    }
  ]
}
```

---

### 4. Real-Time Streaming (`tail -f` via WebSocket)

Connect to `/ws/logs` with optional query parameters to stream new incoming logs live:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/logs?service=payment-service&min_level=ERROR");

ws.onmessage = (event) => {
  const logEntry = JSON.parse(event.data);
  console.log(`[${logEntry.timestamp}] [${logEntry.level}] ${logEntry.message}`);
};
```

---

### 5. Statistics & Aggregations

Retrieve distribution counts by log level, service, top error occurrences, and hourly histogram:

```bash
curl "http://localhost:8000/api/v1/stats"
```

Response:
```json
{
  "total_logs": 1540,
  "by_level": {
    "INFO": 1200,
    "WARNING": 240,
    "ERROR": 95,
    "CRITICAL": 5
  },
  "by_service": {
    "payment-service": 620,
    "auth-service": 510,
    "frontend": 410
  },
  "top_errors": [
    {"message": "Database connection timeout", "count": 45},
    {"message": "Out of memory", "count": 5}
  ],
  "time_histogram": [
    {"timestamp": "2026-10-23T18:00:00Z", "count": 480},
    {"timestamp": "2026-10-23T19:00:00Z", "count": 520},
    {"timestamp": "2026-10-23T20:00:00Z", "count": 540}
  ]
}
```

---

### 6. Pattern-Based Alerting

#### Create Alert Rule
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/rules" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Payment Gateway Failure Alert",
    "condition": "ERROR_COUNT",
    "service": "payment-service",
    "level": "ERROR",
    "threshold": 5,
    "window_minutes": 2,
    "webhook_url": "https://hooks.slack.com/services/...",
    "enabled": true
  }'
```

#### Query Triggered Alert Events
```bash
curl "http://localhost:8000/api/v1/alerts/events" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 7. Retention Policy

Execute manual pruning of expired logs (defaults to `RETENTION_DAYS=30`):
```bash
curl -X POST "http://localhost:8000/api/v1/retention/cleanup?days=14" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Testing & Quality Assurance

Run complete test suite, linter, and static type checker:

```bash
# Run tests with coverage report (target: 80%+)
pytest

# Run linter checks
ruff check src/ tests/
ruff format --check src/ tests/

# Run static type checking in strict mode
mypy src/
```

Or using the `Makefile`:
```bash
make test
make lint
make type-check
make all
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
