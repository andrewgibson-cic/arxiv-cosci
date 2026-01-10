# ArXiv AI Co-Scientist

> **Status:** ✅ **97% Complete** | Production-Ready Scientific Intelligence Engine

A zero-cost Scientific Intelligence Engine for physics and mathematics research. Discovers, interprets, categorizes, connects, and predicts scientific content from arXiv using Semantic Scholar API and Gemini for AI analysis.

## 🎯 What's New (January 2026)

- ✅ **Phase 8 Complete**: Production observability with structured logging, metrics, and health checks
- ✅ **Phase 7 Complete**: 255+ automated tests with GitHub Actions CI/CD
- ✅ **Phase 6 Complete**: Interactive Sigma.js graph visualization
- ✅ **Full Stack Ready**: React + TypeScript frontend with FastAPI backend
- ✅ **Production Deployment**: Docker Compose + Kubernetes ready
- ✅ **Zero Cost**: All free-tier APIs and open-source tools

## 🚀 Features

### Data & Parsing
- **Rich Metadata**: Semantic Scholar API (citations, influence metrics, TLDR)
- **Advanced PDF Parsing**: Multi-parser pipeline (Marker + Grobid + PyMuPDF)
- **LaTeX Extraction**: Equations, theorems, conjectures, physical constants
- **Semantic Chunking**: Intelligent section-aware segmentation

### AI & ML
- **AI Analysis**: Gemini/Groq/Ollama for summarization and entity extraction
- **Link Prediction**: GraphSAGE GNN predicts missing citations
- **Structural Hole Detection**: Identify research gaps across 4 dimensions
- **Hypothesis Generation**: LLM-powered research hypotheses
- **Knowledge Graph**: Neo4j with rich citation relationships
- **Semantic Search**: ChromaDB vector similarity search

### Production Features
- **Interactive Visualization**: Sigma.js graph networks
- **REST API**: 20+ FastAPI endpoints with OpenAPI docs
- **Web Interface**: React + TypeScript frontend
- **Monitoring**: Structured logging with metrics and health checks
- **CI/CD**: GitHub Actions with 255+ automated tests
- **Deployment**: Docker Compose and Kubernetes ready

## 📊 Project Status

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Foundation | ✅ Complete | 100% |
| Phase 2: PDF Parsing | ✅ Complete | 100% |
| Phase 3: Knowledge Graph | ✅ Complete | 100% |
| Phase 4: AI Analysis | ✅ Complete | 100% |
| Phase 5: ML Predictions | ✅ Complete | 100% |
| Phase 6: Frontend | ✅ Complete | 95% |
| Phase 7: Testing & CI/CD | ✅ Complete | 100% |
| Phase 8: Production-Ready | ✅ Complete | 100% |
| **Overall** | **✅ Production-Ready** | **97%** |

See [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) for remaining 3% (polish & enhancements).

## Requirements

- Python 3.11+
- Node.js 20+ (for frontend)
- Docker & Docker Compose
- Gemini API key (free tier: 1M tokens/day)
- Semantic Scholar API key (optional: 10 req/sec vs 1 req/sec)
- ~15GB storage

## Quick Start

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/arxiv-cosci.git
cd arxiv-cosci

# Install Python dependencies
poetry install

# Setup environment
cp .env.example .env
# Edit .env and add your API keys:
# GEMINI_API_KEY=your_key
# S2_API_KEY=your_key (optional)

# Start services
docker compose up -d

# Initialize database
poetry run arxiv-cosci init-db

# Start API server
poetry run uvicorn apps.api.main:app --reload

# Start frontend (new terminal)
cd apps/web
npm install
npm run dev
```

Access the application:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j**: http://localhost:7474

### Production Deployment

```bash
# Configure production environment
cp .env.example .env.prod
# Edit .env.prod with production values

# Deploy with Docker Compose
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Check health
curl http://localhost:8000/api/health
curl http://localhost:8000/metrics
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment guide.

## 📚 Usage Examples

### CLI Commands

```bash
# Fetch papers
poetry run arxiv-cosci fetch 2401.12345 --with-citations

# Parse PDFs
poetry run arxiv-cosci parse 2401.12345 --extract-latex

# Semantic search
poetry run arxiv-cosci search "quantum computing" --limit 20

# Train ML model
poetry run arxiv-cosci train-predictor --epochs 50

# Find research gaps
poetry run arxiv-cosci find-gaps --type all --limit 50

# Generate hypotheses
poetry run arxiv-cosci generate-hypotheses --max 10

# System health
poetry run arxiv-cosci check
```

### API Examples

```python
import requests

# Search papers
response = requests.get(
    "http://localhost:8000/api/search/semantic",
    params={"query": "quantum error correction", "limit": 10}
)

# Get paper details
paper = requests.get("http://localhost:8000/api/papers/2401.12345")

# Get citation network
network = requests.get("http://localhost:8000/api/graph/citations/2401.12345?depth=2")

# Get predictions
predictions = requests.get("http://localhost:8000/api/predictions/links?arxiv_id=2401.12345")
```

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|----------|
| **Language** | Python 3.11+ | Backend & ML |
| **Frontend** | React 18 + TypeScript | Web interface |
| **API** | FastAPI | REST endpoints |
| **LLM** | Gemini/Groq/Ollama | AI analysis |
| **Graph DB** | Neo4j Community | Knowledge graph |
| **Vector DB** | ChromaDB | Semantic search |
| **ML** | PyTorch Geometric | GraphSAGE |
| **Visualization** | Sigma.js | Graph networks |
| **Monitoring** | structlog + metrics | Observability |
| **CI/CD** | GitHub Actions | Automated testing |

### Project Structure

```
arxiv-cosci/
├── apps/
│   ├── api/              # FastAPI backend (✅ 20+ endpoints)
│   ├── web/              # React frontend (✅ Sigma.js viz)
│   └── cli/              # CLI tools (✅ 18 commands)
├── packages/
│   ├── ingestion/        # PDF parsing & S2 API
│   ├── knowledge/        # Neo4j + ChromaDB
│   ├── ai/               # LLM integrations
│   ├── ml/               # GraphSAGE predictions
│   └── observability/    # Logging + metrics ✨ NEW!
├── docs/                 # Comprehensive documentation
│   ├── DEPLOYMENT.md     # Production guide
│   ├── GAP_ANALYSIS.md   # Remaining work
│   ├── PHASE6_SUMMARY.md # Frontend status
│   ├── PHASE7_SUMMARY.md # Testing guide
│   └── PHASE8_SUMMARY.md # Observability guide
├── tests/                # 255+ automated tests
├── docker-compose.yml    # Development setup
├── docker-compose.prod.yml # Production setup ✨ NEW!
└── Dockerfile.api        # API container ✨ NEW!
```

## 📖 Documentation

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment guide (500+ lines)
- **[GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md)** - Remaining work breakdown
- **[TESTING.md](TESTING.md)** - Testing guide and coverage
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[API Docs](http://localhost:8000/docs)** - Interactive OpenAPI documentation

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=packages tests/

# Run specific test file
poetry run pytest tests/test_cli.py -v

# Linting and type checking
poetry run ruff check .
poetry run mypy packages/
```

**Test Coverage:**
- 255+ automated tests
- CLI: 70+ tests (18 commands)
- API: 25+ tests (20+ endpoints)
- ML Pipeline: 40+ tests
- E2E Workflows: 15+ tests

## 🎯 Use Cases

1. **Literature Discovery**: Semantic search across physics/math papers
2. **Citation Analysis**: Visualize and analyze citation networks
3. **Research Gap Detection**: Find structural holes in research
4. **Hypothesis Generation**: AI-powered research suggestions
5. **Knowledge Mapping**: Build comprehensive knowledge graphs
6. **Trend Analysis**: Identify emerging research topics

## 💰 Cost Breakdown

**Total Monthly Cost: $0**

- Semantic Scholar API: Free
- Gemini API: Free tier (1M tokens/day)
- Neo4j: Community edition (free)
- ChromaDB: Embedded (free)
- All other tools: Open source

## 🚀 Performance

- API response time: <100ms (average)
- Graph query: <500ms (typical)
- PDF parsing: 2-5 minutes per paper
- ML training: ~30 minutes (1000 papers)
- Semantic search: <200ms

## 🔒 Security

- Structured logging with sensitive data redaction
- Non-root Docker containers
- CORS configuration
- Rate limiting ready
- Health check endpoints
- Environment-based configuration

## 📈 Monitoring

- Structured JSON logging (production)
- Performance metrics (`/metrics` endpoint)
- Health checks (`/api/health/*`)
- Request tracking with unique IDs
- Slow request detection
- Error tracking and reporting

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

Built with:
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [Google Gemini](https://ai.google.dev/)
- [Neo4j](https://neo4j.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Sigma.js](https://www.sigmajs.org/)

## 📧 Contact

- GitHub Issues: For bugs and feature requests
- Documentation: See `docs/` directory
- API Docs: http://localhost:8000/docs (when running)

---

**Status:** ✅ Production-Ready | **Version:** 0.4.0 | **Updated:** January 2026
