# ArXiv AI Co-Scientist

A Scientific Intelligence Engine for physics and mathematics research. This tool discovers, interprets, categorizes, connects, and predicts scientific content from arXiv - entirely cost-free using Semantic Scholar API and Gemini for AI analysis.

## Features

- **Rich Metadata**: Fetch comprehensive paper data from Semantic Scholar API (citations, influence metrics, TLDR)
- **AI Analysis**: Gemini API for summarization, entity extraction, and hypothesis generation
- **Knowledge Graph**: Store papers and concepts in Neo4j with rich citation relationships
- **Semantic Search**: Vector similarity search using ChromaDB
- **Link Prediction**: GraphSAGE-based prediction of future citations
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
- Docker (for Neo4j)
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

# Start Neo4j
docker compose up -d neo4j

# Initialize database schema
poetry run arxiv-cosci init-db
```

## Usage

### Fetch a single paper
```bash
poetry run arxiv-cosci fetch 2401.12345
# Fetches metadata from Semantic Scholar
# Analyzes with Gemini
# Stores in Neo4j + ChromaDB
```

### Bulk ingestion by category
```bash
poetry run arxiv-cosci ingest --category quant-ph --limit 1000
# Searches S2 for quantum physics papers
# Processes in batches with rate limiting
# Enriches with Gemini analysis
```

### Semantic search
```bash
poetry run arxiv-cosci search "topological quantum computing"
# Vector search in ChromaDB
# Returns ranked papers with relevance scores
```

### Explore citations
```bash
poetry run arxiv-cosci citations 2401.12345
# Fetches citation network from S2
# Displays influential citations
# Shows citation context
```

### Generate insights
```bash
poetry run arxiv-cosci analyze 2401.12345
# Gemini-powered analysis:
# - Paper summary (TLDR + detailed)
# - Extracted entities (theorems, methods, concepts)
# - Related work recommendations
# - Hypothesis generation
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

## Development

```bash
# Run tests
poetry run pytest

# Type checking
poetry run mypy .

# Linting
poetry run ruff check .

# Format code
poetry run ruff format .
```

## License

MIT
