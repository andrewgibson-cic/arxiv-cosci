# Project Configuration

This file extends ~/.claude/CLAUDE.md with project-specific context.

---

## Project: arxiv-cosci (ArXiv AI Co-Scientist)

### Stack
- **Language**: Python 3.11+
- **Frameworks**: FastAPI, LangChain, Strawberry GraphQL
- **Database/ORM**: Neo4j (graph), ChromaDB (vectors)
- **ML**: PyTorch, PyTorch Geometric, sentence-transformers
- **Testing**: pytest
- **Build Tools**: Poetry, Docker Compose

### Key Directories
- Source: packages/ (monorepo modules)
- Apps: apps/api/, apps/web/, apps/cli/
- Tests: tests/
- Data: data/raw/, data/processed/, data/models/
- Documentation: docs/

---

## Stack-Specific Guidelines

### Python
- Use type hints (PEP 484) - strict mypy compliance
- Pydantic for all data models and API schemas
- Async/await for I/O-bound operations (aiohttp, async Neo4j)
- Use `pathlib` over `os.path`
- Context managers for database connections

### FastAPI Patterns
- Dependency injection for Neo4j/ChromaDB clients
- Background tasks for long-running operations
- Strawberry GraphQL for complex queries
- Structured logging with structlog

### Neo4j/Graph Patterns
- Use Cypher for complex traversals
- APOC procedures for graph algorithms
- Batch imports with UNWIND for bulk data
- Index on frequently queried properties (arxiv_id, category)

### ML/AI Patterns
- Ollama client with retry logic for LLM calls
- Batch embedding generation (device="mps")
- Checkpoint model training (PyTorch state_dict)
- Structured output parsing for entity extraction

### PDF Parsing Patterns
- Fallback chain: Nougat -> Marker -> PyMuPDF
- Validate LaTeX extraction with regex
- Store parsing metadata (parser used, confidence)
- Queue-based processing with Celery

---

## Domain-Specific Entities

This project extracts physics/math entities:

| Entity | Detection | Storage |
|--------|-----------|---------|
| Theorem/Lemma | Regex + LLM | Concept node |
| Named Equation | Pattern match | Concept node |
| Physical Constant | Ontology lookup | Property |
| Method/Technique | LLM extraction | Concept node |
| Citation Intent | LLM classification | Edge attribute |

---

## Token Optimization (Project-Specific)

### Delegate These Operations
- `pytest` -> `mcp__ultra-mcp__debug-issue`
- Neo4j query debugging -> `mcp__ultra-mcp__debug-issue`
- PDF parsing batch runs -> `mcp__ultra-mcp__analyze-code`
- Large embedding logs -> `mcp__ultra-mcp__analyze-code`
- GNN training output -> `mcp__ultra-mcp__analyze-code`

### Files to Skip Reading
- `data/raw/` (PDFs)
- `data/processed/` (large JSON/markdown)
- `data/models/` (PyTorch checkpoints)
- `.venv/`, `__pycache__/`
- `*.log`, `*.jsonl` (logs)

### Context-Heavy Operations
When working with this project, prefer:
1. Read package `__init__.py` files first for structure
2. Use Grep for specific function names
3. Limit Neo4j result previews to 5 records
4. Sample embeddings (first 5 dimensions only in logs)

---

## Common Commands

```bash
# Development
poetry install                    # Install dependencies
poetry run python -m apps.cli     # Run CLI
poetry run uvicorn apps.api:app   # Run API

# Testing
poetry run pytest                 # All tests
poetry run pytest -k "test_neo4j" # Specific tests
poetry run mypy .                 # Type check

# Data Pipeline
poetry run arxiv-cosci download --category quant-ph
poetry run arxiv-cosci parse --limit 100
poetry run arxiv-cosci ingest --to-neo4j

# Neo4j
docker compose up neo4j           # Start Neo4j
docker compose exec neo4j cypher-shell  # Interactive shell

# Ollama
ollama serve                      # Start server
ollama run llama3.2:8b            # Interactive LLM
```

---

## Key Files Reference

| Purpose | File |
|---------|------|
| Paper data model | packages/ingestion/models.py |
| Neo4j connection | packages/knowledge/neo4j_client.py |
| LLM prompts | packages/ai/prompts/ |
| Entity extraction | packages/ai/entity_extractor.py |
| GraphSAGE model | packages/ml/link_predictor.py |
| API routes | apps/api/routes/ |
| CLI commands | apps/cli/main.py |

---

*Project-specific configuration for ArXiv AI Co-Scientist*
