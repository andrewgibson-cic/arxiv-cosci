# ArXiv AI Co-Scientist

> A Production-Ready Scientific Intelligence Engine for Physics and Mathematics Research

A zero-cost scientific intelligence platform that discovers, interprets, categorizes, connects, and predicts scientific content from arXiv. Built with Semantic Scholar API and Google Gemini for AI-powered analysis.

## 🚀 **Quick Start**

**Get started in 5 minutes:**

```bash
# 1. Clone and setup
git clone https://github.com/pythymcpyface/arxiv-cosci.git
cd arxiv-cosci
cp .env.example .env

# 2. Add your Gemini API key to .env file

# 3. Start everything
npm run start
```

✨ **That's it!** Your browser will open to the Dashboard where you can start collecting papers.

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed 5-minute setup guide**

---

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

##  Requirements

### System Requirements
- **OS**: macOS, Linux, or Windows (WSL2 recommended)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 15GB free space
- **CPU**: 4+ cores recommended

### Software Requirements
- **Python**: 3.11 or higher
- **Node.js**: 20 or higher (for frontend)
- **Poetry**: 1.7+ (Python dependency manager)
- **Docker**: 24+ with Docker Compose v2
- **Git**: 2.40+

### API Keys (Free Tier)
- **Gemini API**: Required ([get key](https://makersuite.google.com/app/apikey))
  - Free tier: 60 requests/minute, 1M tokens/day
- **Semantic Scholar**: Optional but recommended ([request key](https://www.semanticscholar.org/product/api))
  - Without key: 1 req/sec
  - With key: 10 req/sec

## 🚀 Complete Local Setup Guide

### Step 1: Install Prerequisites

#### macOS
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required software
brew install python@3.11 node@20 poetry docker git

# Start Docker Desktop
open -a Docker
```

#### Linux (Ubuntu/Debian)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install Git
sudo apt install git -y
```

#### Windows (WSL2)
```powershell
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu

# Then follow Linux instructions inside WSL
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone https://github.com/pythymcpyface/arxiv-cosci.git
cd arxiv-cosci

# Verify you're on the main branch
git branch
```

### Step 3: Setup Python Environment

```bash
# Install all Python dependencies (this may take 5-10 minutes)
poetry install

# Verify installation
poetry run python --version  # Should show Python 3.11+
poetry run arxiv-cosci --version  # Should show 0.1.0

# Check all dependencies
poetry run arxiv-cosci check
```

**Expected output:**
```
System Check
┌─────────────────────┬────────┬───────────────┐
│ Component           │ Status │ Details       │
├─────────────────────┼────────┼───────────────┤
│ Python              │ OK     │ 3.11.x        │
│ PyMuPDF (fitz)      │ OK     │ Installed     │
│ ChromaDB            │ OK     │ Installed     │
│ Neo4j               │ OK     │ Installed     │
│ Docker              │ OK     │ /usr/bin/...  │
└─────────────────────┴────────┴───────────────┘
```

### Step 4: Configure Environment

```bash
# Copy development environment template
cp .env.development .env

# Open in your preferred editor
nano .env  # or vim, code, etc.
```

**Required Configuration:**
```bash
# REQUIRED: Add your Gemini API key
GEMINI_API_KEY=your_actual_gemini_api_key_here

# OPTIONAL: Add Semantic Scholar key for higher rate limits
S2_API_KEY=your_s2_api_key_here

# These are fine as defaults for local development:
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=development-password
REDIS_URL=redis://localhost:6379
LLM_PROVIDER=gemini
```

**Get Gemini API Key:**
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy key and paste into `.env`

### Step 5: Start Database Services

```bash
# Start Neo4j and Redis with Docker Compose
docker compose up -d

# Verify services are running
docker compose ps

# Expected output:
# NAME                IMAGE            STATUS
# neo4j               neo4j:5.23       Up (healthy)
# redis               redis:7-alpine   Up
```

**Wait for Neo4j to be ready** (usually 30-60 seconds):
```bash
# Check Neo4j logs
docker compose logs -f neo4j

# Look for: "Remote interface available at http://localhost:7474/"
# Press Ctrl+C to exit logs
```

### Step 6: Initialize Database

```bash
# Initialize Neo4j schema and constraints
poetry run arxiv-cosci init-db
```

**Expected output:**
```
Initializing Neo4j schema...
Schema initialization complete!
```

**Verify Neo4j is working:**
```bash
# Open Neo4j Browser
open http://localhost:7474  # macOS
# or visit http://localhost:7474 in browser

# Login with:
# Username: neo4j
# Password: development-password
```

### Step 7: Test the System

```bash
# Check AI/LLM status
poetry run arxiv-cosci ai-check

# Expected output:
# AI System Status
# ┌──────────┬───────────────┬────────────┐
# │ Component│ Status        │ Details    │
# ├──────────┼───────────────┼────────────┤
# │ Provider │ CONFIGURED    │ gemini     │
# │ Service  │ RUNNING       │ Connected  │
# └──────────┴───────────────┴────────────┘

# Test database connection
poetry run arxiv-cosci db-stats

# Fetch a test paper
poetry run arxiv-cosci fetch 2401.00001
```

### Step 8: Start API Server

Open a **new terminal** window:

```bash
cd arxiv-cosci

# Start FastAPI development server
poetry run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Test API:**
```bash
# In another terminal:
curl http://localhost:8000/api/health

# Expected: {"status":"healthy","database":"connected"}

# Open API docs in browser:
open http://localhost:8000/docs  # Interactive Swagger UI
```

### Step 9: Start Frontend (Optional)

Open **another new terminal** window:

```bash
cd arxiv-cosci/apps/web

# Install Node.js dependencies
npm install

# Start development server
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
➜  Network: http://192.168.x.x:5173/
```

**Access the application:**
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

### Step 10: Load Sample Data

```bash
# Fetch some papers
poetry run arxiv-cosci fetch 2401.12345 2401.12346 2401.12347 \
  --with-citations \
  -o data/papers.json

# Ingest into databases
poetry run arxiv-cosci ingest \
  -i data/processed \
  --to-neo4j \
  --to-chroma

# Try semantic search
poetry run arxiv-cosci search "quantum error correction" --limit 10

# View in Neo4j Browser (http://localhost:7474):
# MATCH (p:Paper) RETURN p LIMIT 25
```

## 🔧 Troubleshooting

### Common Issues

**1. "Command not found: poetry"**
```bash
# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc to make permanent
```

**2. "Docker daemon is not running"**
```bash
# macOS: Start Docker Desktop
open -a Docker

# Linux: Start Docker service
sudo systemctl start docker
```

**3. "Neo4j connection refused"**
```bash
# Check if Neo4j is running
docker compose ps neo4j

# Restart Neo4j
docker compose restart neo4j

# Check logs
docker compose logs neo4j
```

**4. "Python version 3.11 not found"**
```bash
# macOS:
brew install python@3.11

# Linux:
sudo apt install python3.11 python3.11-venv

# Tell Poetry to use correct Python
poetry env use python3.11
```

**5. "API key invalid"**
```bash
# Verify your .env file has the correct key
cat .env | grep GEMINI_API_KEY

# Test the key directly
poetry run python -c "import os; print(os.getenv('GEMINI_API_KEY'))"
```

**6. "Port already in use"**
```bash
# Find what's using the port
lsof -i :8000  # for API
lsof -i :7474  # for Neo4j

# Kill the process or use different ports
docker compose down  # stops all services
```

### Getting Help

If you encounter issues:

1. **Check logs:**
   ```bash
   # Docker services
   docker compose logs -f
   
   # API server (in terminal where it's running)
   # Frontend (in terminal where it's running)
   ```

2. **Reset everything:**
   ```bash
   # Stop all services
   docker compose down -v  # -v removes volumes
   
   # Clear data
   rm -rf data/chroma/*
   
   # Restart from Step 5
   ```

3. **Check system resources:**
   ```bash
   # Docker resource usage
   docker stats
   
   # Ensure you have enough disk space
   df -h
   ```

4. **Open an issue:** [GitHub Issues](https://github.com/pythymcpyface/arxiv-cosci/issues)

## 📚 Next Steps

After successful setup:

1. **Try the examples** in the "Usage Examples" section below
2. **Read the documentation** in `docs/` directory
3. **Run the tests**: `poetry run pytest tests/ -v`
4. **Explore the API**: http://localhost:8000/docs
5. **View the architecture** in this README

## 💡 Usage Examples

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
