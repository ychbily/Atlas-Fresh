# Atlas Fresh — Daily Apple Export Planner

> A Production Commercial planning workspace built for the daily apple export allocation committee. Compares expected vs. actual farm receipts, calculates deterministic client export allocations, highlights low-value local market residuals, and provides a grounded AI assistant.

---

## 🌐 Live Hosted Application

- **Production URL**: [https://atlas-fresh.vercel.app/](https://atlas-fresh.vercel.app/)

---

## 🚀 Quick Start & Environment Options

You can run and evaluate this project using **either** a standard local environment (Python virtualenv + Node.js) or **Docker Compose**.

### System Prerequisites

- **Option A (Local / Non-Docker)**: Python `3.10+` and Node.js `18+` (with `npm`).
- **Option B (Docker Containerized)**: Docker & Docker Compose.

---

### Option A: Standard Local Setup (Recommended if no Docker)

On a fresh clone, run the following commands:

```bash
# 1. Install Python virtualenv, backend requirements, and npm packages
make install

# 2. Run automated backend test suite (pytest)
make test

# 3. Launch local development servers (Backend :8000 & Frontend :5173)
make dev
```

- **Frontend Application**: [http://localhost:5173](http://localhost:5173)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

To stop local servers and clean build caches:
```bash
make clean
```

---

### Option B: Docker Containerized Setup (Zero local Python/Node required)

If you have Docker installed and prefer a fully containerized setup:

```bash
# 1. Build and start containers (Backend :8000 & Frontend :5173)
make docker

# 2. Run automated test suite inside Docker container
make docker-test
```

- **Frontend Application**: [http://localhost:5173](http://localhost:5173)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

To stop containers and clean Docker networks:
```bash
make clean-docker
```


## 🛠️ Architecture & Key Components

```
Atlas-Fresh/
├── backend/
│   ├── Dockerfile               # Backend container definition (FastAPI + Python 3.11)
│   ├── app/
│   │   ├── main.py              # FastAPI app instance, CORS middleware & API routes
│   │   ├── models.py            # Pydantic schemas (Farms, Clients, Station, Allocations, KPIs)
│   │   ├── data_loader.py       # Openpyxl Excel parser & strict data validation engine
│   │   ├── planning_engine.py   # Pure deterministic allocation algorithm & business rules
│   │   └── assistant.py         # Grounded AI assistant (Groq / gpt-oss-120b) & honest fallback
│   ├── data/
│   │   └── Atlas_Fresh_Production_Commercial_Data.xlsx  # Authoritative seed dataset
│   └── tests/                   # Automated pytest suite (6 test suites)
├── frontend/
│   ├── Dockerfile               # Frontend container definition (Node / Vite static server)
│   ├── src/
│   │   ├── components/          # Scoped React components (KPIs, Tables, Traceability, AI Panel)
│   │   ├── services/api.ts      # Explicit Axios API client with strict TypeScript interfaces
│   │   └── types/               # TypeScript interfaces matching backend models
├── docker-compose.yml           # Multi-container orchestration (Backend + Frontend)
├── Makefile                     # Developer workflow automation
└── .env.example                 # Environment template (GROQ_API_KEY configuration)
```

### Business Policy & Deterministic Allocation Engine
- **Price Priority**: Orders sorted by `export_price_per_t_eur` descending (tie-broken by `client_id`).
- **Quality Rules**: Supports `EXACT` and `MINIMUM` matching with lowest quality upgrade preference (e.g., fulfilling `MINIMUM C` with C before B or A).
- **5t Increments**: Allocates in discrete 5-tonne steps up to station capacity and actual farm receipts.
- **Local Residual**: Automatically sends all unexported actual tonnes to the local market at 10% of their segment reference price.

### Grounded AI Assistant Boundary
- **Read-Only**: The AI assistant explains the engine's calculated output and never alters allocations or calculates KPIs.
- **Citation Guardrails**: Validates and filters model output to ensure only valid client IDs (`C01`–`C10`), farm IDs (`F01`–`F20`), and quality segments are cited.
- **Honest Fallback**: When no LLM API key (`GROQ_API_KEY`) is provided or on provider failure, returns a structured, verifiable deterministic engine summary.

---

## 📊 Public Baseline Verification

All public checks match the reference baseline exactly:

| Metric | Target Value | Engine Output | Status |
| :--- | :--- | :--- | :---: |
| **Expected Plan** | 600.0 t | 600.0 t | ✅ Pass |
| **Actual Received** | 560.0 t | 560.0 t | ✅ Pass |
| **Station Capacity** | 500.0 t | 500.0 t | ✅ Pass |
| **Export Volume** | 500.0 t | 500.0 t | ✅ Pass |
| **Local Volume** | 60.0 t | 60.0 t | ✅ Pass |
| **Export Revenue** | EUR 549,500 | EUR 549,500 | ✅ Pass |
| **Local Value** | EUR 4,500 | EUR 4,500 | ✅ Pass |
| **Total Value** | EUR 554,000 | EUR 554,000 | ✅ Pass |
| **At-Risk Clients** | 3 (`C02`, `C09`, `C08`) | 3 | ✅ Pass |

---

## ⚠️ Project Assumptions & Limitations

1. **Single Daily Snapshot**: The system processes one day at a time using the provided workbook. It does not track long-term historical trends or store apples across multiple days.
2. **Rule-Based Business Priority**: Allocations follow the company's clear priority rules (highest paying orders first) instead of a complex multi-variable route or shipping optimizer.
3. **In-Memory Processing**: Data is loaded directly in memory without a permanent database, so changes reset when the server restarts.
4. **Simple Local Market Rate**: Apples that cannot be exported are given a fixed 10% value of their segment reference price, without modeling local warehouse storage limits or daily price fluctuations.

---

## 🔮 Future Roadmap (What Could Be Added With More Time)

1. **File Upload & Live Editing**:
   - Add a file upload box so users can easily drop in new Excel or CSV files without touching the server.
   - Let users edit farm receipts or client demand directly in the table to test changes on the fly.
2. **Database Storage (PostgreSQL / SQLite)**:
   - Save daily plans into a database to compare trends across weeks and keep a history of past committee decisions.
3. **Predictive Insights & Weather Trends**:
   - Use machine learning or an LLM to predict farm harvest yields based on weather forecasts, and automatically flag farms that often deliver below target.
4. **Extra Supply Chain Metrics**:
   - Track transport costs, delivery deadline penalties, and packaging limits to give a fuller financial picture.
5. **Multi-Station Planning**:
   - Support planning across multiple packaging stations and multi-day rolling schedules.

---

## 📝 AI Tool Disclosure & Engineering Attribution

- **Lovable AI**: Used early on to generate initial visual wireframes and layout ideas, helping shape the final custom React user interface.
- **Google Antigravity (powered by Gemini 3.7 Flash)**: Used as a coding assistant and guide during development, helping break down requirements, suggest clean code patterns, debug issues, write test cases, and polish documentation.
- **Groq API (`openai/gpt-oss-120b`)**: Used to power the Grounded AI Assistant with fast responses, strong reasoning, and a generous free tier.
- **Verified Items**: 6/6 automated pytest suites passing, strict TypeScript types throughout the frontend, zero build errors, and exact match with all public baseline numbers.
- **Approximate Time Spent**: ~11 hours total.
- **Intentional Omissions**: No user logins, external database, or unnecessary microservices, keeping strictly to the assessment instructions.

