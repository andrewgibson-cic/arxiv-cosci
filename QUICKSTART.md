# 🚀 Quick Start Guide

Get ArXiv AI Co-Scientist running in **5 minutes**!

## Prerequisites (2 minutes)

You need these installed:

- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)
- **Node.js 20+** - [Download](https://nodejs.org/)
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Poetry** - [Install](https://python-poetry.org/docs/#installation)

Quick check if you have them:
```bash
docker --version
node --version
python3 --version
poetry --version
```

## Setup (3 minutes)

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/pythymcpyface/arxiv-cosci.git
cd arxiv-cosci

# Copy environment template
cp .env.example .env
```

### 2. Add Your API Key

Edit `.env` and add your Gemini API key:

```bash
GEMINI_API_KEY=your_key_here
```

Get a free key here: https://makersuite.google.com/app/apikey

### 3. Start Everything

```bash
npm run start
```

That's it! 🎉

The startup script will:
- ✅ Check all prerequisites
- ✅ Start Docker services (Neo4j, Grobid)
- ✅ Install dependencies (if needed)
- ✅ Start the API server
- ✅ Start the frontend
- ✅ Open your browser to the Dashboard

## What You Get

After starting, you'll have access to:

- **Dashboard**: http://localhost:5173/dashboard
  - Start paper collection
  - Monitor progress
  - View statistics
  
- **Graph Visualization**: http://localhost:5173/graph
  - Interactive citation networks
  - Explore paper relationships
  
- **API Documentation**: http://localhost:8000/docs
  - Full REST API reference
  - Try endpoints interactively

- **Neo4j Browser**: http://localhost:7474
  - Query the knowledge graph directly
  - Login: `neo4j` / `password`

## Your First Papers

### From the Dashboard

1. Go to http://localhost:5173/dashboard
2. Set "Number of Papers" (start with 10-20)
3. Click "Start Ingestion"
4. Watch the progress in real-time
5. Click "View Graph" when done

### From Command Line

```bash
# Fetch specific papers
poetry run arxiv-cosci fetch 2401.12345 --with-citations

# Search for papers
poetry run arxiv-cosci search "quantum computing" --limit 10

# View in graph
open http://localhost:5173/graph
```

## Common Commands

```bash
# Start everything
npm run start

# Stop everything
npm run stop

# View logs
tail -f logs/api.log
tail -f logs/frontend.log

# Check Docker services
docker compose ps

# Restart Docker services
docker compose restart
```

## Troubleshooting

### "Docker daemon is not running"
→ Start Docker Desktop application

### "Port already in use"
→ Stop conflicting services: `npm run stop`

### "GEMINI_API_KEY not found"
→ Check your `.env` file has the API key

### "Neo4j connection failed"
→ Wait 30 seconds for Neo4j to start, or restart: `docker compose restart neo4j`

### "Grobid failed to start" (macOS)
→ This is a known issue on macOS - Grobid is optional
→ PDF parsing will use fallback methods (PyMuPDF)
→ System will work fine without Grobid

### Still having issues?
→ Check the full [README.md](README.md) or open an issue

## Next Steps

Once you have papers loaded:

1. **Explore the Graph**
   - Visualize citation networks
   - Filter by category or time
   - Inspect paper details

2. **Run Semantic Search**
   - Find papers by concept
   - Discover similar research

3. **Train ML Models**
   - Predict missing citations
   - Find research gaps
   - Generate hypotheses

See the full [README.md](README.md) for detailed documentation.

## Quick Reference

| What | Command |
|------|---------|
| Start all services | `npm run start` |
| Stop all services | `npm run stop` |
| View dashboard | http://localhost:5173/dashboard |
| View graph | http://localhost:5173/graph |
| API docs | http://localhost:8000/docs |
| Check logs | `tail -f logs/api.log` |

---

**Need help?** Open an issue on GitHub or check the full documentation in [README.md](README.md)