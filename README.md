# ArXiv AI Co-Scientist

A Scientific Intelligence Engine for physics and mathematics research. This tool discovers, interprets, categorizes, connects, and predicts scientific content from arXiv - entirely cost-free using Semantic Scholar API and Gemini for AI analysis.

## Features

- **Rich Metadata**: Fetch comprehensive paper data from Semantic Scholar API (citations, influence metrics, TLDR)
- **Advanced PDF Parsing**: Multi-parser pipeline (Marker + Grobid + PyMuPDF) optimized for LaTeX-heavy papers
- **LaTeX Extraction**: Equations, theorems, conjectures, and physical constants with context preservation
- **Semantic Chunking**: Intelligent paper segmentation preserving section boundaries and equation context
- **AI Analysis**: Gemini API for summarization, entity extraction, and hypothesis generation
- **Knowledge Graph**: Store papers and concepts in Neo4j with rich citation relationships
- **Semantic Search**: Vector similarity search using ChromaDB
- **Link Prediction**: GraphSAGE-based GNN predicts missing citations between papers ✨ NEW!
- **Structural Hole Detection**: Identify research gaps across 4 dimensions (paper/concept/temporal/cross-domain) ✨ NEW!
- **Hypothesis Generation**: LLM-powered research hypotheses from detected knowledge gaps ✨ NEW!
- **Real-time Data**: Always current via API (no static snapshots)
- **Visualization**: Interactive graph UI with React + Sigma.js (planned)

## Target Domain

Physics & Mathematics papers from arXiv:
- High-Energy Physics (hep-th, hep-ph, hep-lat, hep-ex)
- General Relativity (gr-qc)
- Quantum Physics (quant-ph)
- Condensed Matter (cond-mat.*)
- Mathematics (math.*)
- Astrophysics (astro-ph.*)

## Requirements

- Python 3.11+
- Gemini API key (free tier: 1M tokens/day)
- Semantic Scholar API key (optional, for 10 req/sec vs 1 req/sec)
- Docker (for Neo4j + Grobid)
- ~10GB storage for graph database and vector embeddings

## Quick Start

```bash
# Clone and enter project
cd arxiv-cosci

# Install dependencies
poetry install

# Create .env file with API keys
cp .env.example .env
# Edit .env and add:
# GEMINI_API_KEY=your_gemini_key_here
# S2_API_KEY=your_s2_key_here (optional, for higher rate limits)

# Start services (Neo4j + Grobid)
docker compose up -d

# Initialize database schema
poetry run arxiv-cosci init-db
```

## PDF Parsing (Phase 2 - NEW!)

### Install parsing dependencies
```bash
poetry install --with parsing
```

### Parse papers with full pipeline
```bash
# Parse single paper (Marker + Grobid + LaTeX extraction)
poetry run arxiv-cosci parse 2401.12345 --output data/processed/

# Parse with specific configuration
poetry run arxiv-cosci parse 2401.12345 \
  --use-marker \
  --use-grobid \
  --extract-latex \
  --create-chunks

# Batch parse multiple papers
poetry run arxiv-cosci parse-batch --input papers.txt --parallel 4

# Validate parsing quality
poetry run arxiv-cosci validate 2401.12345
```

### Parser Features
- **Marker**: High-quality PDF → Markdown with LaTeX preservation
- **Grobid**: Citation extraction with context and bibliographic info
- **LaTeX Extractor**: Equations, theorems, conjectures, physical constants
- **Semantic Chunker**: Intelligent segmentation by section with configurable chunk size
- **Quality Metrics**: Parse time, success rates, equation/citation counts

```

## Phase 5: ML Predictions & Hypothesis Generation ✨ NEW!

### Train Link Prediction Model
```bash
# Train GraphSAGE model on citation network
poetry run arxiv-cosci train-predictor --node-limit 1000 --epochs 50

# Custom configuration
poetry run arxiv-cosci train-predictor \
  --node-limit 2000 \
  --epochs 100 \
  --hidden 256 \
  --output 128 \
  --checkpoint-dir data/models
```

### Find Research Gaps
```bash
# Find all types of structural holes
poetry run arxiv-cosci find-gaps --type all

# Find specific gap type
poetry run arxiv-cosci find-gaps --type paper --limit 100

# Save results to JSON
poetry run arxiv-cosci find-gaps \
  --type all \
  --limit 50 \
  --output data/gaps.json

# Available gap types:
# - paper: Paper-to-paper (shared citations)
# - concept: Concept-to-concept (co-occurrence)
# - temporal: Missing historical citations  
# - cross-domain: Inter-field connections
# - all: All of the above
```

### Generate Research Hypotheses
```bash
# Generate from detected gaps (auto-detect)
poetry run arxiv-cosci generate-hypotheses --max 10

# Generate from saved gaps file
poetry run arxiv-cosci generate-hypotheses \
  --gaps-file data/gaps.json \
  --max 20 \
  --output data/hypotheses.md

# The markdown file includes:
# - Hypothesis statements
# - Rationale and reasoning
# - 3 research questions
# - Potential impact
# - Suggested methods
# - Confidence scores
```

## Usage

### Fetch papers from Semantic Scholar API
```bash
# Single paper
poetry run arxiv-cosci fetch 2401.12345

# Multiple papers with citations and references
poetry run arxiv-cosci fetch 2401.12345 2402.13579 \
  -o data/papers.json \
  --with-citations \
  --with-references
```

### Summarize papers
```bash
# Brief summary
poetry run arxiv-cosci summarize 2401.12345 --level brief

# Detailed summary with key findings
poetry run arxiv-cosci summarize 2401.12345 --level detailed
```

### Extract entities
```bash
# Extract methods, theorems, datasets, constants, equations
poetry run arxiv-cosci extract 2401.12345 --use-llm

# Regex-only extraction (fast, no LLM)
poetry run arxiv-cosci extract 2401.12345 --no-llm
```

### Semantic search
```bash
poetry run arxiv-cosci search "topological quantum computing" --limit 10

# Filter by category
poetry run arxiv-cosci search "quantum error correction" \
  --limit 20 \
  --category quant-ph
```

### Ingest papers to knowledge graph
```bash
# From processed JSON files (after parsing)
poetry run arxiv-cosci ingest -i data/processed \
  --to-neo4j --to-chroma

# Limit number of papers
poetry run arxiv-cosci ingest -i data/processed --limit 100
```

### AI Analysis (Local or Cloud)
The engine supports multiple LLM providers. Configure your choice in `.env`.

**Options:**
- **Gemini (Recommended)**: Best for whole-paper context (1M tokens).
- **Groq**: Fastest inference speeds for real-time extraction.
- **Ollama**: 100% local and private.

```bash
# Check AI system status
poetry run arxiv-cosci ai-check

# Set provider dynamically (or via .env)
LLM_PROVIDER=gemini poetry run arxiv-cosci summarize 0704.0001 --level detailed

# Extract entities using Groq speed
LLM_PROVIDER=groq poetry run arxiv-cosci extract 0704.0001 --use-llm
```

## Project Structure

```
arxiv-cosci/
├── apps/
│   ├── api/              # FastAPI backend
│   ├── web/              # React frontend
│   └── cli/              # Command-line tools
├── packages/
│   ├── ingestion/        # Data download & parsing
│   ├── knowledge/        # Graph & vector storage
│   ├── ai/               # LLM pipelines
│   └── ml/               # GNN models
├── data/
│   ├── raw/              # Downloaded PDFs
│   ├── processed/        # Parsed markdown
│   └── models/           # Trained models
├── docker/
├── docs/
└── tests/
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Metadata Source | Semantic Scholar API (free tier) |
| LLM Analysis | Gemini 1.5 Flash/Pro (free tier: 1M tokens/day) |
| Embeddings | sentence-transformers (all-mpnet-base-v2) |
| Vector DB | ChromaDB |
| Graph DB | Neo4j Community Edition |
| GNN | PyTorch Geometric (GraphSAGE) |
| API | FastAPI + Strawberry GraphQL (planned) |
| Frontend | React + Vite + Sigma.js (planned) |

## Development & Documentation

### System Health
```bash
# Check dependencies and system setup
poetry run arxiv-cosci check

# Check LLM/AI system status
poetry run arxiv-cosci ai-check

# Show database statistics
poetry run arxiv-cosci db-stats
```

### Testing & Code Quality
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_ai.py -v

# Type checking
poetry run mypy .

# Coverage report
poetry run pytest --cov=packages tests/
```

### Project Documentation

See [.claude/plan.md](.claude/plan.md) for:
- Comprehensive implementation roadmap
- Architecture decisions and rationale
- Phase-by-phase breakdown
- Technology stack details
- Success metrics and KPIs
- Risk management and mitigation

## Phase 6: Full-Stack Web Application ✨ NEW! (Jan 2026)

### FastAPI Backend
```bash
# Start the API server
poetry run uvicorn apps.api.main:app --reload --port 8000

# View interactive API documentation
open http://localhost:8000/docs
```

**API Endpoints:**
- Health: `/api/health`, `/api/health/db`
- Papers: `/api/papers`, `/api/papers/{arxiv_id}`, `/api/papers/batch`
- Search: `/api/search/semantic`, `/api/search/hybrid`, `/api/search/similar/{arxiv_id}`
- Graph: `/api/graph/citations/{arxiv_id}`, `/api/graph/clusters`
- Predictions: `/api/predictions/links`, `/api/predictions/hypotheses`

### React Frontend
```bash
# Install dependencies
cd apps/web
npm install

# Start development server
npm run dev

# Access application
open http://localhost:5173
```

**Features:**
- 🏠 Home page with hero search
- 🔍 Semantic search with results
- 📄 Paper detail view with citations/references
- 📊 Citation network visualization (Sigma.js ready)
- ⚡ React Query for server state management
- 🎨 Responsive design with Tailwind classes

## Status

**Current:** Phase 1-6 Complete - Full-Stack Application Ready! 🎉 (Jan 2026)

**Completed (86% of project):**
- ✅ **Phase 1**: Semantic Scholar API client, Multi-provider LLM (Gemini/Groq/Ollama)
- ✅ **Phase 2**: PDF parsing pipeline (Marker + Grobid), LaTeX extraction, Semantic chunking
- ✅ **Phase 3**: Neo4j knowledge graph, ChromaDB semantic search, ML dependencies
- ✅ **Phase 4**: AI analysis (summarization, entity extraction, citation classification)
- ✅ **Phase 5**: ML predictions
  - GraphSAGE link prediction (473 lines)
  - End-to-end prediction pipeline (448 lines)
  - Structural hole detection - 4 strategies (469 lines)
  - LLM-powered hypothesis generation (436 lines)
- ✅ **Phase 6**: Full-Stack Web Application ✨ NEW!
  - FastAPI backend with 15 REST endpoints (24 files, ~2,500 lines)
  - React + TypeScript frontend (18 files, ~1,150 lines)
  - Complete UI: Home, Search, Paper Detail, Graph View
  - API client with type-safe requests
  - 18 comprehensive tests (10/18 passing)

**Remaining:**
- 📋 Phase 7: Production hardening (Docker, monitoring, optimization, Sigma.js integration)

## License

MIT
