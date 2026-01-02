# ArXiv AI Co-Scientist

A Scientific Intelligence Engine for physics and mathematics research. This tool scrapes, interprets, categorizes, connects, and predicts scientific content from arXiv - entirely cost-free using local computation and open-source tools.

## Features

- **Data Ingestion**: Bulk download from Kaggle + incremental sync via OAI-PMH
- **PDF Parsing**: Extract text, equations, and citations from scientific PDFs
- **Knowledge Graph**: Store papers and concepts in Neo4j with citation relationships
- **Semantic Search**: Vector similarity search using ChromaDB
- **AI Analysis**: Local LLM-powered summarization and entity extraction
- **Link Prediction**: GraphSAGE-based prediction of future citations
- **Visualization**: Interactive graph UI with React + Sigma.js

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
- Apple Silicon Mac (M1/M2/M3) recommended for local LLM inference
- Docker (for Neo4j)
- ~100GB storage for papers and models

## Quick Start

```bash
# Clone and enter project
cd arxiv-cosci

# Install dependencies
poetry install

# Check system requirements
poetry run arxiv-cosci check

# Install Ollama for local LLM
brew install ollama
ollama pull llama3.2:8b

# Start Neo4j
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:community

# Download Kaggle arXiv metadata
# (Requires Kaggle API credentials)
kaggle datasets download -d Cornell-University/arxiv
unzip arxiv.zip -d data/raw/
```

## Usage

### View dataset statistics
```bash
poetry run arxiv-cosci stats data/raw/arxiv-metadata-oai-snapshot.json
```

### Create a filtered subset
```bash
poetry run arxiv-cosci subset data/raw/arxiv-metadata-oai-snapshot.json \
  -o data/raw/quant-ph-subset.jsonl \
  -c quant-ph \
  --limit 10000
```

### Download PDFs
```bash
poetry run arxiv-cosci download data/raw/quant-ph-subset.jsonl \
  -o data/raw/pdfs \
  --limit 100
```

### Parse PDFs
```bash
poetry run arxiv-cosci parse \
  -i data/raw/pdfs \
  -o data/processed
```

### Knowledge Graph & Search
```bash
# Initialize Neo4j schema
poetry run arxiv-cosci init-db

# Ingest papers into Neo4j and ChromaDB
poetry run arxiv-cosci ingest \
  -i data/processed \
  --to-neo4j --to-chroma

# Semantic search
poetry run arxiv-cosci search "topological quantum computing"
```

### AI Analysis (Requires Ollama)
```bash
# Check AI system status
poetry run arxiv-cosci ai-check

# Summarize a paper
poetry run arxiv-cosci summarize 0704.0001 --level detailed

# Extract entities
poetry run arxiv-cosci extract 0704.0001 --use-llm
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
| PDF Parsing | PyMuPDF, Nougat (equations), Grobid (citations) |
| Embeddings | sentence-transformers (all-mpnet-base-v2) |
| LLM | Ollama + Llama 3.2 (8B) |
| Vector DB | ChromaDB |
| Graph DB | Neo4j Community Edition |
| GNN | PyTorch Geometric (GraphSAGE) |
| API | FastAPI + Strawberry GraphQL |
| Frontend | React + Vite + Sigma.js |

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
