## ArXiv Co-Scientist API

FastAPI backend for the ArXiv Co-Scientist project.

### Features

- **Papers API**: CRUD operations for scientific papers
- **Search API**: Semantic and hybrid search using ChromaDB + Neo4j
- **Graph API**: Citation network visualization and clustering
- **Predictions API**: ML-powered link predictions and hypothesis generation
- **Health Checks**: Service and database health monitoring

### Running the API

```bash
# Start the API server
poetry run python -m apps.api.main

# Or use uvicorn directly
poetry run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### Health
- `GET /api/health` - Basic health check
- `GET /api/health/db` - Database connectivity check

#### Papers
- `GET /api/papers` - List papers (paginated)
- `GET /api/papers/{arxiv_id}` - Get paper details
- `POST /api/papers/batch` - Fetch multiple papers

#### Search
- `GET /api/search/semantic?q=query` - Semantic search
- `GET /api/search/hybrid?q=query` - Hybrid search (semantic + citations)
- `GET /api/search/similar/{arxiv_id}` - Find similar papers

#### Graph
- `GET /api/graph/citations/{arxiv_id}` - Citation network
- `GET /api/graph/clusters` - Paper clusters/communities

#### Predictions
- `GET /api/predictions/links` - Predicted citations
- `GET /api/predictions/hypotheses` - Research hypotheses

### Configuration

Set environment variables in `.env`:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma

# LLM
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

### Development

```bash
# Run with auto-reload
poetry run uvicorn apps.api.main:app --reload

# Run tests
poetry run pytest tests/

# Type checking
poetry run mypy apps/api

# Linting
poetry run ruff check apps/api
```

### Architecture

```
apps/api/
├── main.py           # FastAPI app + middleware
├── config.py         # Settings configuration
├── dependencies.py   # Dependency injection
├── routers/          # API route handlers
│   ├── health.py
│   ├── papers.py
│   ├── search.py
│   ├── graph.py
│   └── predictions.py
└── schemas/          # Pydantic response models
    ├── paper.py
    ├── search.py
    └── graph.py