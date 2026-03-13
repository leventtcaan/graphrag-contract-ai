# IT Compliance & Contract Analyzer

> **B2B SaaS** platform that analyzes IT contracts and compliance requirements using a **GraphRAG** (Graph Retrieval-Augmented Generation) architecture powered by open-source LLMs.

---

## What Problem Does This Solve?

Legal and IT teams spend hours manually reviewing contracts — finding penalty clauses, cross-referencing regulations (GDPR, KVKK, ISO 27001), and mapping obligations to risks. This platform automates that process:

- Upload a contract PDF → the system extracts entities (clauses, obligations, penalties, parties) and builds a **knowledge graph** in Neo4j
- Ask natural language questions → the system translates them to Cypher queries, runs them against the graph, and returns precise, deterministic answers
- Multi-tenant architecture → each client's data is fully isolated

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| **API Framework** | FastAPI (Python) | Async-native, Pydantic v2, auto-swagger |
| **Relational DB** | PostgreSQL 16 | Users, tenants, contract metadata, audit |
| **Graph DB** | Neo4j 5 + APOC | Multi-hop compliance queries (GraphRAG) |
| **LLM** | Groq / Llama-3.3-70b | Zero-cost inference, 128K context, tool calling |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | Fully local, no API cost, 384-dim vectors |
| **LLM Orchestration** | LangChain | GraphCypherQAChain, LLMGraphTransformer |
| **Auth** | JWT (PyJWT) + bcrypt | Stateless, multi-service compatible |
| **Migrations** | Alembic (async) | Schema versioning with asyncpg |

---

## Why GraphRAG Instead of Vector RAG?

Classic vector RAG finds semantically similar text chunks. GraphRAG stores **structured relationships** between entities — which is exactly how legal documents work.

| Query | Vector RAG | GraphRAG (Cypher) |
|---|---|---|
| *"Which clauses reference both GDPR and KVKK?"* | Approximate similarity match | `MATCH (c)-[:REFERENCES]->(r) WHERE r.name IN [...]` — exact, deterministic |
| *"What obligations trigger this penalty clause?"* | LLM must infer from context | `MATCH (p:Penalty)<-[:PENALIZED_BY]-(o:Obligation)` — milliseconds |
| *"Which party agreed to the data security obligation?"* | May miss cross-paragraph links | Graph edge traversal — always accurate |

A Cypher query is **deterministic**: the same question returns the same answer every time. For legal analysis, this precision is non-negotiable.

---

## Architecture Overview

```
PDF Upload
    │
    ▼
PyPDFLoader → RecursiveCharacterTextSplitter (1000 tokens, 100 overlap)
    │
    ▼
LLMGraphTransformer (Groq/Llama-3.3-70b)
    │  Extracts: Contract, ContractClause, Obligation, Penalty,
    │            Organization, Regulation, RiskArea
    ▼
Neo4j Knowledge Graph
    │
    ▼
GraphCypherQAChain
    ├── Cypher Generation LLM (Groq) → MATCH query with contract_id filter
    ├── Neo4j execution → raw graph data
    └── QA LLM (Groq) → natural language answer
```

**Security layers on the chat pipeline:**
1. `contract_id` filter baked into every Cypher prompt (tenant isolation)
2. READ-only Cypher rules (no CREATE/DELETE/MERGE)
3. QA system prompt: answer only from graph data, reject role injection
4. `ChatRequest.question` max 500 chars (prompt injection surface reduction)

---

## Prerequisites

- Python 3.12+
- Docker Desktop (or OrbStack on macOS)
- A free [Groq API key](https://console.groq.com)

---

## Quick Start

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd itLawProject

# Copy the example env and fill in your values
cp .env.example .env
```

Open `.env` and set at minimum:

```env
GROQ_API_KEY=gsk_your-key-here
SECRET_KEY=your-random-32-char-secret
```

Everything else has working defaults for local development.

### 2. Start databases

```bash
docker compose up -d
```

Wait ~15 seconds for Neo4j to fully initialize (it downloads the APOC plugin on first run).

```bash
# Verify both services are healthy
docker compose ps
```

### 3. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 4. Run database migrations

```bash
alembic upgrade head
```

This creates the `tenants`, `users`, and `contracts` tables in PostgreSQL.

### 5. Seed the database

```bash
python scripts/seed_db.py
```

Output:
```
──────────────────────────────────────────────────
  IT Law Project — Veritabanı Tohumlama
──────────────────────────────────────────────────

[1/2] Tenant
  ✓ Tenant oluşturuldu: Test Hukuk Bürosu
    id: <uuid>

[2/2] Admin Kullanıcı
  ✓ Admin kullanıcı oluşturuldu: admin@test.com
    id:     <uuid>
    tenant: Test Hukuk Bürosu

──────────────────────────────────────────────────
  ✓ Seeding tamamlandı!
──────────────────────────────────────────────────

  Swagger UI:      http://localhost:8000/api/v1/docs
  Login endpoint:  POST /api/v1/auth/login/access-token
  Kullanıcı adı:   admin@test.com
  Şifre:           admin123
```

### 6. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

### 7. Open Swagger UI

Navigate to **http://localhost:8000/api/v1/docs**

Click **Authorize**, use the `/auth/login/access-token` endpoint with:
- `username`: `admin@test.com`
- `password`: `admin123`

Paste the returned `access_token` into the Authorize dialog.

---

## API Endpoints

### Authentication
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login/access-token` | Get JWT token (form-data: username, password) |

### Contracts
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/contracts/` | Create contract metadata |
| `GET` | `/api/v1/contracts/` | List contracts (paginated, filterable by status) |
| `GET` | `/api/v1/contracts/{id}` | Get contract detail |
| `PATCH` | `/api/v1/contracts/{id}` | Partial update |
| `DELETE` | `/api/v1/contracts/{id}` | Delete contract |
| `POST` | `/api/v1/contracts/{id}/upload` | Upload PDF file |
| `POST` | `/api/v1/contracts/{id}/analyze` | Run GraphRAG pipeline (LLM entity extraction → Neo4j) |
| `POST` | `/api/v1/contracts/{id}/chat` | Ask a natural language question about the contract |

### Contract Lifecycle

```
CREATE → UPLOADED → PROCESSING → ANALYZED
                              ↘ FAILED
```

1. `POST /contracts/` — create the metadata record
2. `POST /contracts/{id}/upload` — attach the PDF
3. `POST /contracts/{id}/analyze` — build the knowledge graph (takes 30–120s depending on contract size and Groq rate limits)
4. `POST /contracts/{id}/chat` — ask questions

### Example Chat Request

```json
POST /api/v1/contracts/{id}/chat
{
  "question": "Bu sözleşmede hangi ceza maddeleri var ve hangi yükümlülüklere bağlı?"
}
```

```json
{
  "answer": "Sözleşmede 3 ceza maddesi tespit edildi...",
  "context_nodes": [
    {"clause": "Madde 7", "obligation": "Gizliliği koruma", "penalty": "100.000 TL"}
  ],
  "generated_cypher": "MATCH (c:Contract {contract_db_id: '...'})-[:HAS_CLAUSE]->..."
}
```

---

## Project Structure

```
itLawProject/
├── app/
│   ├── api/
│   │   ├── deps.py                   # JWT auth dependency chain
│   │   └── v1/
│   │       ├── api.py                # Router registry
│   │       └── endpoints/
│   │           ├── auth.py           # Login endpoint
│   │           └── contracts.py      # All contract endpoints + chat
│   ├── core/
│   │   ├── config.py                 # Pydantic BaseSettings (env management)
│   │   ├── database.py               # SQLAlchemy async engine + session
│   │   ├── embeddings.py             # HuggingFace local embeddings
│   │   ├── graph_schema.py           # Neo4jGraph bridge + node/relationship constants
│   │   ├── llm.py                    # ChatGroq singleton (Llama-3.3-70b)
│   │   ├── neo4j_db.py               # Neo4j async driver singleton
│   │   └── security.py               # bcrypt + JWT
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── base.py                   # UUIDMixin, TimestampMixin
│   │   ├── contract.py
│   │   ├── tenant.py
│   │   └── user.py
│   ├── schemas/                      # Pydantic request/response schemas
│   │   ├── chat.py                   # ChatRequest, ChatResponse
│   │   └── contract.py
│   ├── services/                     # Business logic layer
│   │   ├── chat.py                   # GraphCypherQAChain + Text-to-Cypher
│   │   ├── contract.py               # CRUD operations
│   │   ├── document.py               # PDF upload + text extraction
│   │   └── graph_builder.py          # LLMGraphTransformer → Neo4j pipeline
│   └── main.py                       # FastAPI app + lifespan
├── alembic/
│   ├── env.py                        # Async migration setup
│   └── versions/                     # Migration history
├── docs/
│   └── developer_diary.md            # Architecture decision log (Turkish)
├── scripts/
│   └── seed_db.py                    # Dev database seeder
├── tests/
├── .env.example                      # Environment variable template
├── alembic.ini
├── docker-compose.yml                # PostgreSQL 16 + Neo4j 5 (APOC)
└── requirements.txt
```

---

## Key Design Decisions

**Dual database:** PostgreSQL handles structured relational data (users, tenants, metadata). Neo4j handles the knowledge graph. They're linked via `contract.neo4j_node_id` — a bridge field that lets us navigate from a PostgreSQL row to its Neo4j subgraph.

**Zero LLM cost on deployment:** Groq's free tier provides sufficient capacity for a portfolio/MVP. The `all-MiniLM-L6-v2` embedding model runs locally with no API calls. Switching to a paid provider requires changing one line in `app/core/llm.py`.

**Tenant isolation at every layer:** The database has `tenant_id` foreign keys on both `users` and `contracts`. The chat service uses `partial_variables` to lock every Cypher query to a specific `contract_db_id`. Endpoints return 404 (not 403) for cross-tenant access — never revealing record existence.

**Async throughout:** FastAPI → SQLAlchemy async → asyncpg → PostgreSQL. Synchronous LangChain operations (LLMGraphTransformer, GraphCypherQAChain) are isolated with `asyncio.to_thread()` to keep the event loop unblocked.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Free at console.groq.com |
| `SECRET_KEY` | `CHANGE_ME...` | JWT signing key — use a strong random value in production |
| `POSTGRES_USER` | `itlaw_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `itlaw_secret` | PostgreSQL password |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_DB` | `itlaw_db` | Database name |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt connection |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `itlaw_neo4j_secret` | Neo4j password |
| `UPLOAD_DIR` | `downloads/contracts` | Directory for uploaded PDFs |

---

## Development Notes

- **Swagger UI:** http://localhost:8000/api/v1/docs
- **Neo4j Browser:** http://localhost:7474 (explore the knowledge graph visually)
- **Groq rate limits (free tier):** ~6,000 tokens/min on `llama-3.3-70b-versatile`. Large contracts (30+ chunks) may hit this limit — consider adding delays between chunks for large documents.
- **Re-running seed:** `seed_db.py` is idempotent — safe to run multiple times.
- **Resetting the database:** `docker compose down -v` removes all data volumes.

---

## Roadmap

- [ ] Background task queue (Celery + Redis) for async contract analysis
- [ ] pgvector extension + hybrid search (vector + graph)
- [ ] Compliance ruleset engine (GDPR Article mapping, KVKK checklist)
- [ ] React frontend with real-time chat interface
- [ ] Row-Level Security (PostgreSQL RLS) as additional tenant isolation layer
- [ ] Refresh token + token blacklist

---

*Built with FastAPI, LangChain, Neo4j, PostgreSQL, and Groq — a zero-cost-to-deploy GraphRAG stack.*
