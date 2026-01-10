# Testing Guide

## Test Overview

The ArXiv Co-Scientist project has comprehensive test coverage across multiple layers:

- **Total Tests**: 190+ (Phase 7 expansion)
- **Unit Tests**: 160+ (passing)
- **Integration Tests**: 8 (require live database)
- **CLI Tests**: 70+ (all commands covered)
- **API Client Tests**: 25+ (S2 client fully tested)

## Running Tests

### All Tests
```bash
# Run all tests with coverage
poetry run pytest tests/ -v --cov=packages --cov=apps

# Run specific test file
poetry run pytest tests/test_ai.py -v

# Run with detailed output
poetry run pytest tests/ -vv
```

### Unit Tests Only
```bash
# Run tests that don't require external services
poetry run pytest tests/test_ai.py tests/test_ingestion.py tests/test_gemini_client.py tests/test_conversion_script.py -v
```

### Integration Tests
```bash
# Requires Neo4j and ChromaDB running
docker compose up -d

# Run API integration tests
poetry run pytest tests/test_api.py -v

# Run knowledge layer tests
poetry run pytest tests/test_knowledge.py -v
```

## Test Structure

### Unit Tests (58 tests - All Passing ✅)

**AI Layer** (`test_ai.py` - 12 tests)
- LLM client functionality (Ollama, Gemini, Groq)
- Summarization (brief, standard, detailed)
- Entity extraction (regex + LLM)
- Citation classification
- Batch processing

**Ingestion Layer** (`test_ingestion.py` - 17 tests)
- Paper metadata models (PaperMetadata, ParsedPaper, ArxivPaper)
- Citation and concept models
- Text extraction (arXiv ID, DOI, section detection)
- Kaggle loader (physics/math paper filtering)
- PDF downloader (rate limiting, path management)

**Gemini Client** (`test_gemini_client.py` - 5 tests)
- API availability checking
- Text generation
- JSON generation
- Structured output with Pydantic models

**Conversion Script** (`test_conversion_script.py` - 5 tests)
- S2 metadata → ParsedPaper conversion
- JSON serialization
- Empty field handling
- ParserType enum validation

**Knowledge Layer** (`test_knowledge.py` - 9 tests)
- ChromaDB operations (add, search, filters)
- Neo4j client initialization
- ParsedPaper ingestion models
- Hybrid search models

### Integration Tests (8 tests - Require Database)

**API Endpoints** (`test_api.py` - 8 tests requiring live DB)
These tests connect to actual Neo4j + ChromaDB instances:

- `test_list_papers_empty` - List papers with empty DB
- `test_list_papers_with_data` - List papers with data
- `test_get_paper_success` - Get paper by arXiv ID
- `test_semantic_search_empty` - Semantic search (no results)
- `test_semantic_search_with_results` - Semantic search (with results)
- `test_hybrid_search` - Hybrid semantic + citation search
- `test_citation_network` - Citation network graph query
- `test_link_predictions` - ML link prediction endpoint

**API Documentation Tests** (10 tests - All Passing ✅)
- Health check endpoints
- OpenAPI schema validation
- Swagger UI accessibility
- ReDoc page rendering

## Test Coverage

### By Module

| Module | Coverage | Notes |
|--------|----------|-------|
| `packages/ingestion/models.py` | 100% | Core data models |
| `packages/ai/llm_base.py` | 100% | LLM interface |
| `apps/api/config.py` | 100% | API configuration |
| `apps/api/schemas/*.py` | 100% | API schemas |
| `packages/ai/entity_extractor.py` | 82% | Entity extraction |
| `packages/ai/gemini_client.py` | 79% | Gemini API client |
| `packages/ai/summarizer.py` | 78% | Summarization |
| `packages/knowledge/chromadb_client.py` | 77% | Vector DB |
| `packages/ai/citation_classifier.py` | 68% | Citation classification |
| `apps/api/routers/*.py` | 34-84% | API endpoints |

### Coverage Summary
```
Total Coverage: 32%
```

**Note**: Low overall coverage is due to uncovered modules:
- CLI commands (0% - manual testing)
- PDF parsing pipeline (0% - requires Marker/Grobid services)
- ML models (0% - training/prediction tested manually)
- S2 API client (0% - requires API key)

## Setting Up Test Environment

### Prerequisites
```bash
# Install dependencies
poetry install

# Start database services
docker compose up -d

# Verify services
docker compose ps
```

### Environment Variables
Create a `.env` file for tests:
```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Optional: For API client tests
GEMINI_API_KEY=your_key_here
S2_API_KEY=your_key_here
```

## Writing New Tests

### Unit Test Example
```python
import pytest
from packages.ai.summarizer import summarize_paper

@pytest.mark.asyncio
async def test_summarize_brief(sample_paper):
    """Test brief summarization."""
    summary = await summarize_paper(sample_paper, level="brief")
    assert len(summary) > 0
    assert len(summary) < 500
```

### Integration Test Example
```python
import pytest
from fastapi.testclient import TestClient

def test_api_endpoint(client):
    """Test API endpoint (requires live database)."""
    response = client.get("/api/papers")
    assert response.status_code == 200
    data = response.json()
    assert "papers" in data
```

### Mock Example
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test with mocked external service."""
    with patch("packages.ingestion.s2_client.S2Client") as mock:
        mock_client = AsyncMock()
        mock_client.get_paper = AsyncMock(return_value={"title": "Test"})
        mock.return_value = mock_client
        
        # Your test code here
```

## Test Markers

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Skip Tests
```python
@pytest.mark.skip(reason="Requires external service")
def test_external_api():
    pass
```

### Parametrize Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("2401.12345", True),
    ("invalid", False),
])
def test_arxiv_id_validation(input, expected):
    assert is_valid_arxiv_id(input) == expected
```

## Continuous Integration (Phase 7) ✅

### GitHub Actions Workflow

The project includes a comprehensive CI/CD pipeline at `.github/workflows/tests.yml`:

**Features:**
- ✅ Automated testing on every push and PR
- ✅ Neo4j service container for integration tests
- ✅ Separate jobs for tests, linting, and security
- ✅ Coverage reporting with Codecov
- ✅ Poetry dependency caching for faster builds
- ✅ Parallel job execution

**Workflow Jobs:**

1. **Test Job** - Runs all tests with live Neo4j
   - Unit tests (no external dependencies)
   - Integration tests (with Neo4j service)
   - Coverage report generation
   - Codecov upload

2. **Lint Job** - Code quality checks
   - Ruff linting
   - Ruff formatting verification
   - MyPy type checking (non-blocking)

3. **Security Job** - Vulnerability scanning
   - Safety dependency checks
   - Security advisory scanning

### Running CI Locally

To simulate CI environment locally:

```bash
# Start services like CI does
docker compose up -d

# Run tests with coverage
poetry run pytest tests/ -v \
  --cov=packages \
  --cov=apps \
  --cov-report=term \
  --cov-report=html

# Run linting
poetry run ruff check packages/ apps/ tests/
poetry run ruff format --check packages/ apps/ tests/

# Run type checking
poetry run mypy packages/ apps/ --ignore-missing-imports

# Security scanning
poetry run safety check
```

### Viewing CI Results

After pushing to the `phase-7-testing` branch:

1. **GitHub Actions Tab**: View workflow runs
2. **Codecov Dashboard**: View coverage reports  
3. **Pull Request Checks**: See status in PR

### CI Configuration

The workflow is configured to run on:
- Push to `main` branch
- Push to `phase-7-testing` branch
- All pull requests to `main`

**Environment Variables in CI:**
```yaml
env:
  NEO4J_URI: bolt://localhost:7687
  NEO4J_USER: neo4j
  NEO4J_PASSWORD: testpassword
```

### Coverage Tracking

Coverage reports are automatically uploaded to Codecov:
- View detailed coverage at codecov.io
- See coverage changes in PR comments
- Track coverage trends over time

**Target:** 80% code coverage (Phase 7 goal)
**Current:** ~32% → expanding with new tests

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure project is installed
poetry install
```

**2. Database Connection Errors**
```bash
# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs neo4j
```

**3. Async Test Failures**
```bash
# Install pytest-asyncio
poetry add --group dev pytest-asyncio
```

**4. Coverage Too Low**
```bash
# Run with verbose coverage
poetry run pytest --cov=packages --cov=apps --cov-report=html

# Open htmlcov/index.html to see details
```

## Test Categories

### Fast Tests (< 1 second)
- Model validation tests
- Regex pattern tests
- Schema validation tests

### Medium Tests (1-5 seconds)
- LLM mock tests
- API endpoint tests
- Database query tests

### Slow Tests (> 5 seconds)
- Full parsing pipeline tests
- ML model training tests
- Large batch processing tests

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Use Fixtures**: Share common setup via pytest fixtures
3. **Mock External Services**: Don't rely on external APIs in unit tests
4. **Test Edge Cases**: Include tests for error conditions
5. **Keep Tests Fast**: Use mocks to avoid slow operations
6. **Document Intent**: Clear docstrings explaining what's tested
7. **Arrange-Act-Assert**: Follow AAA pattern for clarity

## Future Testing Goals

- [ ] Increase coverage to 80%+
- [ ] Add property-based testing (Hypothesis)
- [ ] Add performance benchmarks
- [ ] Add contract tests for API
- [ ] Add visual regression tests for web UI
- [ ] Add load testing for API endpoints
- [ ] Add security scanning tests

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)