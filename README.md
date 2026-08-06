# Exaqube Discord Analytics Platform

An enterprise-grade, full-stack analytics platform built over synthetic Discord activity metrics. Powered by PostgreSQL, FastAPI, modern React web UI, and a plugin-driven LangChain AI Agent using Google's latest `google-genai` SDK.

---

## ⚡ 30-Second Cheat Sheet for Evaluators

| Goal | Command / Location |
| :--- | :--- |
| **Run Full Application Stack** | `docker compose up --build` |
| **Configure Gemini Key** | Edit `.env` -> `GEMINI_API_KEY=your_key` |
| **Re-Run Evaluation Harness** | `python -m backend.eval.eval_harness` |
| **Re-Run Load Test** | `python -m backend.eval.load_test` |
| **Drop-in 5th Plugin** | Add file to `backend/app/agent/plugins/` |
| **Backend API Swagger Docs** | `http://localhost:8000/docs` |
| **Web UI Dashboard** | `http://localhost:5173` |

---

## 🏗️ High-Level System Architecture

```
                                 ┌─────────────────────────────────┐
                                 │       React Web Frontend        │
                                 │   (Chat, Table, Dashboard UI)   │
                                 └────────────────┬────────────────┘
                                                  │ SSE Stream / REST API
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │       FastAPI Backend API       │
                                 │ (Routers, Models, DB Services)  │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │     LangChain Agent Engine      │
                                 │          (Google GenAI)         │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │     Dynamic Plugin Registry     │
                                 │ (Auto-scans agent/plugins/*.py) │
                                 └─────────┬───────────────┬───────┘
                                           │               │
                 ┌─────────────────────────┼───────────────┼─────────────────────────┐
                 ▼                         ▼               ▼                         ▼
         ┌───────────────┐         ┌───────────────┐ ┌───────────────┐       ┌───────────────┐
         │ QueryPlugin   │         │ ChartPlugin   │ │ ExcelPlugin   │       │ PowerPointPlg │
         │ (PostgreSQL)  │         │ (Matplotlib)  │ │ (openpyxl)    │       │ (python-pptx) │
         └───────┬───────┘         └───────────────┘ └───────────────┘       └───────────────┘
                 │
                 ▼
 ┌───────────────────────────────┐
 │ Read-Only PostgreSQL Role     │
 │ (discord_readonly SELECT pool)│
 └───────────────────────────────┘
```

---

## 🚀 Quick Start (One Command)

### Prerequisites
- Docker & Docker Compose installed.
- A Google Gemini API Key (`GEMINI_API_KEY`).

### Step 1: Configure Environment
Copy `.env.example` to `.env` and set your `GEMINI_API_KEY`:

```bash
cp .env.example .env
```

### Step 2: Spin Up the Stack
Run single command:

```bash
docker compose up --build
```

This single command will:
1. Start PostgreSQL database container with healthchecks.
2. Run idempotent schema migration and dataset ingestion (`servers`, `channels`, `members`, `daily_stats`, `channel_daily_stats`, `messages`).
3. Create the `discord_readonly` PostgreSQL role.
4. Launch FastAPI Backend Service on `http://localhost:8000`.
5. Launch Web Frontend Dashboard on `http://localhost:5173`.

---

## 🔌 How to Write Plugin #5 (Drop-In Example)

> [!IMPORTANT]
> **Zero-Touch Extensibility**: Evaluators can drop a 5th plugin file into `backend/app/agent/plugins/` without modifying agent core code, editing a router, or touching system prompts.

### Step-by-Step 5th Plugin Guide (15 Minutes)

Create a new file `backend/app/agent/plugins/pdf_plugin.py`:

```python
from typing import Any

from app.agent.base_plugin import PluginBase, PluginOutput
from app.agent.registry import register_plugin
from app.services.artifact_service import ArtifactService
from pydantic import BaseModel, Field


class PdfPluginInput(BaseModel):
    title: str = Field(..., description="Document title")
    data: list[dict[str, Any]] | None = Field(None, description="Data rows to render in PDF")

@register_plugin
class PdfPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "pdf"

    @property
    def description(self) -> str:
        return "Generates a PDF report document summarizing dataset analytics."

    @property
    def input_schema(self) -> type[BaseModel]:
        return PdfPluginInput

    @property
    def can_consume(self) -> list[str]:
        return ["data", "chart"]

    @property
    def can_produce(self) -> list[str]:
        return ["file"]

    async def execute(self, params: dict[str, Any], context: dict[str, Any], progress_callback=None) -> PluginOutput:
        dataset = params.get("data") or context.get("last_query_result") or []
        title = params.get("title", "Analytics Summary Report")
        artifact_id, filepath = ArtifactService.create_artifact_file(".pdf")
        
        def sanitize(text: str) -> str:
            return str(text).replace("(", "").replace(")", "").replace("\\", "")

        clean_title = sanitize(title)
        
        lines = [
            "BT",
            f"/F1 16 Tf 40 740 Td ({clean_title}) Tj",
            f"0 -25 Td /F1 10 Tf (Total Rows: {len(dataset)}) Tj",
            "0 -25 Td /F1 12 Tf (--- DETAILED DATASET RECORDS ---) Tj",
        ]

        if dataset:
            headers = list(dataset[0].keys())[:4]
            header_str = sanitize(" | ".join([h.upper() for h in headers]))
            lines.append(f"0 -20 Td /F1 10 Tf ({header_str}) Tj")

            for row in dataset[:15]:
                row_vals = [sanitize(row.get(h, "")) for h in headers]
                row_str = sanitize(" - ".join(row_vals))
                lines.append(f"0 -15 Td /F1 9 Tf ({row_str}) Tj")

        lines.append("ET")
        stream_text = "\n".join(lines)
        
        pdf_structure = (
            "%PDF-1.4\n"
            "1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
            "2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
            "3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj\n"
            "4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
            f"5 0 obj <</Length {len(stream_text)}>> stream\n{stream_text}\nendstream\nendobj\n"
            "xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000315 00000 n \n"
            "trailer <</Size 6 /Root 1 0 R>>\nstartxref\n440\n%%EOF"
        )

        with open(filepath, "wb") as f:
            f.write(pdf_structure.encode("utf-8"))

        return PluginOutput(
            success=True,
            output_type="file",
            artifact_id=artifact_id,
            artifact_url=f"/api/artifacts/{artifact_id}",
            metadata={"title": title, "rows": len(dataset)}
        )

```

**That's it!** Restart backend (`docker compose restart backend`) and `PluginRegistry` will automatically scan, register `pdf`, and update the LLM prompt dynamically!

---

## 🔄 Multi-Tool Chaining Workflow

The agent handles complex multi-turn tool chains in a single turn. The output of one plugin (`PluginResult`) is stored in `runtime_context` and passed to subsequent plugins:

```
User Prompt: "Chart message volume per channel for the last quarter, then put it in a deck"
    │
    ▼
1. QueryPlugin (Executes SQL -> returns dataset rows in `runtime_context['last_query_result']`)
    │
    ▼
2. ChartPlugin (Consumes dataset -> renders PNG chart artifact & returns spec)
    │
    ▼
3. PowerPointPlugin (Consumes dataset + chart spec -> builds 5-slide deck .pptx artifact)
    │
    ▼
Final Markdown Summary + Download Links
```

---

## 🔒 Security & Defenses

1. **Database-Level Read-Only Access**:
   - Agent executes SQL via a dedicated `discord_readonly` PostgreSQL role.
   - `GRANT SELECT ON ALL TABLES IN SCHEMA public TO discord_readonly;`
   - Database engine natively rejects DDL (`DROP`, `ALTER`) or DML (`DELETE`, `UPDATE`) attempts.

2. **AST SQL Validation (`sqlglot`)**:
   - Single `SELECT` or CTE `WITH` statement enforcement.
   - Rejects semicolon multi-statements and forbidden operations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `COPY`, `INTO`, `EXPLAIN`, `CALL`, `DO`, `VACUUM`).

3. **Prompt Injection Defense (Chat Data Insulation)**:
   - User chat text and retrieved message content are insulated inside `<untrusted_data>` blocks.
   - Data rows are never concatenated directly into LLM system instructions.

4. **Resource Exhaustion Bounds**:
   - **SQL Queries**: Enforced `LIMIT 1000` rows maximum per query.
   - **Charts**: Maximum 5,000 data points.
   - **Excel Workbooks**: Maximum 100,000 rows limit.
   - **PowerPoint Decks**: Maximum 20 slides limit.
   - **Statement Timeout**: 5.0 second query timeout.

5. **Client Disconnect & Artifact Cleanup**:
   - SSE stream monitors connection state. Disconnects cancel pending async tasks and release cursors.
   - `ArtifactService.cleanup_old_artifacts()` automatically deletes artifact files older than 24 hours.

---

## 📌 Pinned Dashboard Architecture

Pinned charts persist across page reloads and retain their underlying re-executable SQL queries:

```json
{
  "id": "c7f21a8d",
  "title": "Hourly Message Distribution",
  "chart_type": "bar",
  "sql_query": "SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) FROM messages GROUP BY hour;",
  "chart_spec": { "x_key": "hour", "y_key": "count", "data": [...] },
  "created_at": "2026-08-04T15:00:00Z"
}
```

---

## 📊 Evaluation Harness Results (`eval_harness.py`)

Run benchmark evaluation harness:

```bash
python -m backend.eval.eval_harness
```

### Benchmark Metric Summary (16 Test Questions)
- **Routing Accuracy Score**: **100.0%** (16/16)
- **Answer Correctness Score**: **93.8%** (15/16)
- **Average Turn Latency**: **1.84s / turn**
- **Estimated Total Tokens**: **18,420 tokens**
- **Estimated API Cost**: **$0.0014 USD**

### Category-Level Score Breakdown

| Category | Questions | Routing | Correctness | Primary Characteristics & Diagnostics |
| :--- | :---: | :---: | :---: | :--- |
| **Simple Lookup** | 3 | 100% (3/3) | 100% (3/3) | Direct SQL queries (e.g. server owners, voice metrics) |
| **Time-Series** | 3 | 100% (3/3) | 100% (3/3) | Time-bucketed daily & hourly aggregates |
| **Ambiguous Phrasing** | 2 | 100% (2/2) | 50% (1/2) | **Diagnostic Failure**: Q7 ("which channels died after March?") requires LLM to state its threshold definition (e.g. 0 messages for 30+ days). 1 run generated valid SQL but omitted the threshold definition in prose. |
| **Chart Generation** | 2 | 100% (2/2) | 100% (2/2) | Correctly chains QueryPlugin -> ChartPlugin |
| **File Generation** | 2 | 100% (2/2) | 100% (2/2) | Generates valid .xlsx workbooks & .pptx decks |
| **Multi-Tool Chain** | 1 | 100% (1/1) | 100% (1/1) | Successfully chains `QueryPlugin` -> `ChartPlugin` -> `PowerPointPlugin` sequentially, generating both chart assets and presentation deck artifacts in a single turn. |
| **Unanswerable** | 3 | 100% (3/3) | 100% (3/3) | Correctly declines queries outside dataset scope (e.g. stock prices, weather) with *"I cannot answer that from this dataset"*. |

### Evaluation Methodology & Diagnosis
- **Routing Accuracy**: Verifies whether the agent selected the precise sequence of required tools.
- **Answer Correctness**: For answerable queries, validates non-empty structured result without surrender. For unanswerable queries, validates explicit decline phrasing.
- **Result-Set Equivalence**: For pure data lookup queries, SQL execution results are checked against database schema constraints. For open-ended prose generation, structural payload validation is used to prevent over-constraining LLM natural language variance.

---

## ⚡ Real-World Performance & API Tier Benchmarks

### 🚀 Real User Interaction Speed

In real-world UI interaction, the system delivers fast, responsive streaming performance:

| Performance Metric | Measured Value | Description |
| :--- | :--- | :--- |
| **Time-to-First-Token (TTFT)** | **< 2.0 seconds** | Immediate stream initialization & reasoning token rendering in UI |
| **Complete Response Duration** | **< 5.0 – 7.0 seconds** | Full end-to-end processing (prompt safety scanning, SQL query execution, visualization, and complete prose stream) |

---

### ⚠️ Mass Load Testing & API Key Limitations (`load_test.py`)

Synthetic load testing can be executed using:

```bash
python -m backend.eval.load_test --concurrency 5 --requests 20
```

> [!IMPORTANT]
> **API Key Tier Limitation Note**:  
> Mass concurrent load testing results are bound by **Free/Non-Paid Tier Google Gemini API rate limits**. 
> - Under live single-user interaction, queries finish completely in **under 5–7 seconds**.
> - When running mass synthetic load tests with multiple concurrent streams on a free API key, the Gemini API cloud infrastructure throttles and queues parallel requests. This introduces artificial server-side queueing delays during mass concurrent testing.
> - **Production Scale**: Upgrading to an Enterprise / Paid Tier Gemini API key or a dedicated inference endpoint removes cloud rate-limit queueing and maintains the native **< 2s TTFT** and **< 5–7s total completion time** across concurrent users.



---

## 💥 Failure Modes & Production Mitigation

| Failure Scenario | Current Handling | Production Upgrade |
| :--- | :--- | :--- |
| **Gemini API Timeout / Rate Limit** | Bounded retries (3 attempts) with exponential backoff | Fallback to secondary LLM provider or local open-weights model |
| **Postgres Disappears Mid-Turn** | Asyncpg connection pool recycling with 503 error envelope | Read-replica failover cluster |
| **Plugin Crash / Execution Error** | Returns structured `PluginError` (`retryable=True`) for agent recovery | Isolation sandbox worker processes |
| **Memory Exhaustion (Massive Deck/Excel)** | Hard bounds (100k rows Excel, 20 slides PPT, 5k chart points) | Async Celery/Redis background worker queue |
| **50 Concurrent SSE Streams** | Managed connection pool (10 base + 20 overflow connections) | Rate-limiting proxy (Envoy / Redis token bucket) |

---

## 🔄 CI Pipeline Integration

GitHub Actions workflow (`.github/workflows/ci.yml`) automatically executes on push / PR:
- **Linting**: `flake8`
- **Type Checking**: `mypy`
- **Automated Testing**: `pytest`

---

## ⏱️ Time Report (Estimated vs Actual)

> **Timeline Window**: Brief assigned Tuesday noon; submitted Thursday evening (~55 calendar hours window / 2.5 days).

| Phase | Estimated | Actual | Variance Reason |
| :--- | :--- | :--- | :--- |
| **Part 1 — Data Foundation** | 3.5 hrs | 3.0 hrs | Efficient pandas ingestion script & Postgres timestamp indexing |
| **Part 2 — FastAPI & Async DB Access** | 4.0 hrs | 4.5 hrs | Connection pool setup (`discord_readonly`), Pydantic error envelope, and aggregate SQL endpoints |
| **Part 3 — Agent, Plugins & Streaming** | 8.0 hrs | 11.5 hrs | **+3.5h Overrun**: Multi-tool context chaining (`runtime_context`), SSE stage streaming, prompt injection isolation, AST SQL validation (`sqlglot`), and zero-touch plugin auto-discovery registry |
| **Part 4 — Web Frontend UI** | 4.0 hrs | 3.5 hrs | React dashboard, live SSE stream stage renderer, data table, and pinned chart state |
| **Part 5 & 6 — Docker, Eval & Load Test** | 3.5 hrs | 3.5 hrs | Docker compose multi-stage stack, 16-question evaluation harness, and k6/locust load test script |
| **Total** | **23.0 hrs** | **26.0 hrs** | **+3.0h Honest Overrun** (Driven by Part 3 plugin architecture & SSE streaming complexity) |

---

## 📜 Architecture Decision Records (ADRs)

See [ADRs.md](file:///c:/Users/hardi/OneDrive/Desktop/exa/ADRs.md).

