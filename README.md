<h1 align="center">Customer Query Classification & Routing System</h1>

<p align="center">
  A high-performance, stateless AI application built with <strong>FastAPI</strong>, <strong>Pydantic AI</strong>, and <strong>Google Gemini</strong>
  for validated query classification, deterministic multi-agent routing, and isolated concurrent request processing.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Latest-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Pydantic_AI-Latest-E92063.svg" alt="Pydantic AI">
  <img src="https://img.shields.io/badge/Google_Gemini-3.6_Flash-4285F4.svg" alt="Google Gemini">
  <img src="https://img.shields.io/badge/uv-Package_Manager-purple.svg" alt="uv">
  <img src="https://img.shields.io/badge/Tests-22_Passing-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## Overview

The Customer Query Classification and Routing System is a production-grade, stateless backend service designed to process high-throughput customer inquiries without persistent storage. Incoming queries are validated, categorized via Google Gemini with strict structured output enforcement, and deterministically dispatched to specialized domain handlers.

- **FastAPI Core** — Async REST API endpoints for full chat processing, classification introspection, and operational health probes.
- **Pydantic AI Classification** — Structured schema validation enforcing Category, Urgency, Complexity, Confidence, and Clarification flags.
- **Deterministic Handler Routing** — Hardened routing logic that prevents arbitrary LLM handler execution and transparently diverts low-confidence or ambiguous inquiries to a fallback handler.
- **In-Memory Concurrency Management** — Controlled asynchronous concurrency bounded by an `asyncio.Semaphore` ensuring zero cross-session context leakage.

---

## Features

### 🤖 Intelligent Query Classification
- Powered by **Pydantic AI** and **Google Gemini** (`gemini-3.6-flash`)
- Validates queries into multi-dimensional structured data:
  - **Category**: `general`, `technical`, `account`, `billing`, `complex`, or `unknown`
  - **Urgency**: `low`, `normal`, `high`, `critical` (evaluated independently of category)
  - **Complexity**: `simple`, `medium`, `complex`
  - **Confidence**: Normalized float score ($0.0 \le \text{confidence} \le 1.0$)
  - **Requires Clarification**: Boolean flag signaling underspecified or vague queries

### 🧭 Deterministic Agent Routing
- Strict application-level category mapping table prevents untrusted handler execution
- Automatic rerouting to `fallback_handler` when:
  - `confidence` is below the configured threshold (default: `0.70`)
  - `requires_clarification` is set to `True`
  - The query is categorized as `unknown`
- Six specialized domain response handlers:
  - `general_handler` — Greetings, pleasantries, general information
  - `technical_handler` — API status, incident triage, troubleshooting guides
  - `account_handler` — Password resets, profile changes, security guidance
  - `billing_handler` — Invoicing, payment status, subscription inquiries
  - `complex_handler` — Multi-layered architecture and staged execution plans
  - `fallback_handler` — Targeted follow-up questions for ambiguous inquiries

### ⚡ Concurrency & Request Isolation
- In-memory concurrency limiter enforcing a maximum of 5–6 simultaneous requests
- Complete session isolation: each request generates an independent `request_id`
- Fully stateless design: no database, message queue, or persistent cache required

### 🛡️ Safety & Resilience
- Bounded retries with exponential backoff for transient provider failures
- Clear domain exceptions: `ProviderTimeoutError` (504), `RateLimitError` (429), and `ClassificationError` (422)
- Zero exposure of API keys, internal credentials, or sensitive headers

### 🪵 Structured Logging & Diagnostics
- Standardized logging configured via `app/core/logger.py` with console and rotating file output
- High-resolution per-request latency tracking for both classification and handler execution

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.12+ | Asynchronous runtime |
| FastAPI | REST API web framework |
| Uvicorn | High-performance ASGI production server |
| Pydantic v2 | Data modeling, validation, and serialization |
| Pydantic Settings | Environment configuration and typed settings |
| Pydantic AI | Agent framework for structured Gemini generation |
| Google Gemini | Generative LLM provider |
| HTTPX | Asynchronous HTTP client for testing and transports |
| Pytest + Pytest-Asyncio | Test automation suite |
| uv | Lightning-fast Python package and environment manager |

---

## Project Structure

```text
Customer_Query_Classification/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # Endpoints: /chat, /classify, /health
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── classifier.py        # Pydantic AI Google Gemini classification agent
│   │   └── handlers.py          # Domain response handlers
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── classification.py    # QueryClassification structured Pydantic schema
│   │   ├── request.py           # ChatRequest & ClassifyRequest schemas
│   │   └── response.py          # ChatResponse, ClassificationResponse, HealthResponse
│   ├── services/
│   │   ├── __init__.py
│   │   ├── classifier_service.py# Timeouts, bounded retries, provider error mapping
│   │   ├── router_service.py    # Deterministic category router & handler registry
│   │   └── chat_service.py      # Concurrency semaphore & request orchestration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Typed settings via pydantic-settings
│   │   ├── exceptions.py        # Domain exceptions (Timeout, RateLimit, Routing)
│   │   └── logger.py            # Centralized application logging
│   ├── constants/
│   │   └── prompts.py           # Classification system prompt definition
│   └── main.py                  # FastAPI lifespan and exception handlers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures, mock agents, test client
│   ├── test_api.py              # End-to-end endpoint & HTTP status tests
│   ├── test_classifier.py       # Pydantic schema validation & category tests
│   ├── test_concurrency.py      # Concurrency semaphore & storage absence tests
│   └── test_routing.py          # Deterministic routing & anti-tampering tests
│
├── simulate_concurrent_requests.py # Concurrency simulation script
├── pyproject.toml               # Project metadata & dependency definitions
├── requirements.txt             # Pip dependencies
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.12 or higher
- A Google AI Studio API Key (for live Gemini classification)
- `uv` (recommended) or `pip`

Install **uv** (optional, recommended):

```bash
pip install uv
```

---

### 1. Clone & Set Up Virtual Environment

```bash
git clone <repository-url>
cd Customer_Query_Classification
```

Using **uv**:
```bash
uv venv
```

Activate the environment:

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

---

### 2. Install Dependencies

Using **uv**:
```bash
uv sync
```

---

### 3. Configure Environment Variables

Create or configure your environment variables:

| Variable | Type | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | string | *None* | Google AI Studio Gemini API key |
| `GEMINI_MODEL` | string | `gemini-3.6-flash` | Gemini model identifier |
| `APP_ENV` | string | `development` | Deployment environment (`development`, `production`, `testing`) |
| `LOG_LEVEL` | string | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CLASSIFICATION_CONFIDENCE_THRESHOLD` | float | `0.70` | Cutoff below which queries divert to fallback |
| `MAX_CONCURRENT_REQUESTS` | integer | `6` | Maximum concurrent model requests handled |
| `REQUEST_TIMEOUT_SECONDS` | float | `30.0` | Maximum timeout in seconds per request |
| `MAX_RETRIES` | integer | `2` | Bounded retries for transient provider failures |

**Example (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="your-google-api-key-here"
$env:GEMINI_MODEL="gemini-3.6-flash"
$env:MAX_CONCURRENT_REQUESTS="6"
```

---

### 4. Start the Application

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## API Endpoints Reference

### 1. `GET /health`
Returns system status without exposing sensitive credentials or keys.

**Response (200 OK):**
```json
{
  "status": "ok",
  "app_name": "Intelligent Query Classification and Routing System",
  "version": "0.1.0",
  "environment": "development",
  "model": "gemini-3.6-flash"
}
```

---

### 2. `POST /classify`
Analyzes a user query and returns structured classification metadata without invoking domain handlers.

**Request:**
```json
{
  "query": "Our production API is down and returning 500 errors",
  "user_id": "user_101",
  "session_id": "sess_202"
}
```

**Response (200 OK):**
```json
{
  "request_id": "req_8a3f9e2b10cd",
  "category": "technical",
  "urgency": "critical",
  "complexity": "medium",
  "confidence": 0.96,
  "target_agent": "technical_handler",
  "reason": "Production incident detected",
  "requires_clarification": false,
  "classification_latency_ms": 12.4,
  "status": "success"
}
```

---

### 3. `POST /chat`
End-to-end endpoint: validates query, classifies intent, deterministically routes, executes the target handler, and returns the response.

**Request:**
```json
{
  "query": "Where can I download my billing invoice for last month?",
  "user_id": "user_42",
  "session_id": "sess_100"
}
```

**Response (200 OK):**
```json
{
  "request_id": "req_1d5a7f9c3e4b",
  "category": "billing",
  "urgency": "normal",
  "complexity": "simple",
  "confidence": 0.92,
  "target_agent": "billing_handler",
  "answer": "Billing & Subscription Assistance:\nWe can help answer questions regarding plan tiers, invoice statements, and payment methods...",
  "requires_clarification": false,
  "status": "success",
  "total_latency_ms": 15.8
}
```

---

## Deterministic Routing Matrix

| Category | Resolved Handler | Low-Confidence / Ambiguity Rule |
|---|---|---|
| `general` | `general_handler` | If confidence < 0.70 or requires clarification $\rightarrow$ `fallback_handler` |
| `technical` | `technical_handler` | If confidence < 0.70 or requires clarification $\rightarrow$ `fallback_handler` |
| `account` | `account_handler` | If confidence < 0.70 or requires clarification $\rightarrow$ `fallback_handler` |
| `billing` | `billing_handler` | If confidence < 0.70 or requires clarification $\rightarrow$ `fallback_handler` |
| `complex` | `complex_handler` | If confidence < 0.70 or requires clarification $\rightarrow$ `fallback_handler` |
| `unknown` | `fallback_handler` | Direct fallback prompting the user for clarification |

---

## Concurrency & Request Isolation

Simulate 6 simultaneous asynchronous inquiries using the built-in benchmarking script:

```bash
python simulate_concurrent_requests.py
```

Sample output:
```text
============================================================
Sending 6 concurrent requests simultaneously to http://127.0.0.1:8001/chat...
============================================================

USER     | STATUS  | CATEGORY     | URGENCY   | HANDLER            | ROUNDTRIP
---------------------------------------------------------------------------
user_1   | 200     | general      | normal    | general_handler    | 12.3 ms
user_2   | 200     | technical    | critical  | technical_handler  | 14.1 ms
user_3   | 200     | billing      | normal    | billing_handler    | 11.8 ms
user_4   | 200     | account      | normal    | account_handler    | 13.5 ms
user_5   | 200     | complex      | high      | complex_handler    | 16.2 ms
user_6   | 200     | unknown      | normal    | fallback_handler   | 10.9 ms
---------------------------------------------------------------------------
Total wall-clock duration for all 6 concurrent requests: 22.4 ms
```

---

## Running Tests

All automated tests use mock classifier injection, requiring **no active database** and incurring **zero paid Gemini API calls**.

```bash
# Run all tests
pytest -v

# Run a specific test suite
pytest tests/test_api.py -v
pytest tests/test_concurrency.py -v
pytest tests/test_routing.py -v
pytest tests/test_classifier.py -v
```

### Test Coverage Breakdown

| File | Test Count | Scope |
|---|---|---|
| `test_api.py` | 8 | Health endpoint, validation errors, timeouts, rate limits, and handler responses |
| `test_classifier.py` | 6 | Pydantic schema validation, bounds checks, timeouts, and category coverage |
| `test_concurrency.py` | 2 | 6 simultaneous concurrent requests, session isolation, and storage absence |
| `test_routing.py` | 6 | Deterministic category routing, confidence fallback, anti-tampering, urgency independence |

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Client User Query                    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP POST (/chat or /classify)
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Layer                       │
│  ┌───────────────────────┐   ┌──────────────────────┐  │
│  │   Request Validation  │   │  Exception Handlers  │  │
│  │    (Pydantic Schema)  │   │   (504, 429, 422)    │  │
│  └───────────┬───────────┘   └──────────────────────┘  │
└──────────────┼─────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────┐
│               Concurrency Control                      │
│        (asyncio.Semaphore: 6 Slots Max)                │
└──────────────┬─────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────┐
│              Classification Service                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │     Pydantic AI Agent (Google Gemini)            │  │
│  │  Structured Output: QueryClassification Schema   │  │
│  └───────────────────────────┬──────────────────────┘  │
│                              │ Validated Metadata      │
│  ┌───────────────────────────▼──────────────────────┐  │
│  │          Deterministic Router Engine             │  │
│  │  - Confidence Check (< 0.70 -> Fallback)         │  │
│  │  - Clarification Check (True -> Fallback)        │  │
│  │  - Category-to-Handler Resolution Table          │  │
│  └───────────────────────────┬──────────────────────┘  │
└──────────────────────────────┼─────────────────────────┘
                               │ Dispatched Handler
┌──────────────────────────────▼─────────────────────────┐
│                  Domain Handlers                       │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐  │
│  │   General   │ │  Technical  │ │     Account      │  │
│  └─────────────┘ └─────────────┘ └──────────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐  │
│  │   Billing   │ │   Complex   │ │     Fallback     │  │
│  └─────────────┘ └─────────────┘ └──────────────────┘  │
└──────────────────────────────┬─────────────────────────┘
                               │ Validated ChatResponse
┌──────────────────────────────▼─────────────────────────┐
│               Originating HTTP Response                │
└────────────────────────────────────────────────────────┘
```

---

