# Contributing to ArXiv AI Co-Scientist

Thank you for your interest in contributing to the ArXiv AI Co-Scientist project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Areas for Contribution](#areas-for-contribution)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- **Be Respectful**: Treat everyone with respect and kindness
- **Be Collaborative**: Work together towards common goals
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Patient**: Remember that everyone has different skill levels and backgrounds
- **Be Inclusive**: Welcome contributors from all backgrounds and perspectives

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Poetry (for dependency management)
- Docker & Docker Compose (for services)
- Git
- Node.js 18+ (for frontend development)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
```bash
git clone https://github.com/YOUR_USERNAME/arxiv-cosci.git
cd arxiv-cosci
```

3. Add the upstream repository:
```bash
git remote add upstream https://github.com/pythymcpyface/arxiv-cosci.git
```

## Development Setup

### Backend Setup

```bash
# Install dependencies
poetry install

# Install development dependencies
poetry install --with dev

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start services
docker compose up -d

# Initialize database
poetry run arxiv-cosci init-db

# Run tests to verify setup
poetry run pytest
```

### Frontend Setup

```bash
cd apps/web

# Install dependencies
npm install

# Start development server
npm run dev
```

## How to Contribute

### Reporting Bugs

- Check if the issue already exists in GitHub Issues
- Use the bug report template
- Include:
  - Clear description of the problem
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Python version, etc.)
  - Relevant logs or error messages

### Suggesting Enhancements

- Check if the enhancement has already been suggested
- Use the feature request template
- Include:
  - Clear description of the feature
  - Use cases and benefits
  - Possible implementation approach
  - Any relevant examples or mockups

### Contributing Code

1. **Create a Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make Your Changes**
- Write clean, readable code
- Follow the coding standards
- Add tests for new functionality
- Update documentation as needed

3. **Test Your Changes**
```bash
# Run tests
poetry run pytest

# Run linting
poetry run ruff check .

# Run type checking
poetry run mypy packages/ apps/

# Run formatting
poetry run black packages/ apps/ tests/
```

4. **Commit Your Changes**
```bash
git add .
git commit -m "feat: add new feature"
# or
git commit -m "fix: resolve bug in..."
```

Follow conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `style:` - Code style changes (formatting, etc.)
- `chore:` - Maintenance tasks

5. **Push to Your Fork**
```bash
git push origin feature/your-feature-name
```

6. **Create a Pull Request**
- Go to the original repository on GitHub
- Click "New Pull Request"
- Select your fork and branch
- Fill out the PR template
- Link any related issues

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use Black for automatic formatting
- Use Ruff for linting

```python
# Good example
async def fetch_paper(
    arxiv_id: str,
    include_citations: bool = False
) -> PaperMeta
    """
    Fetch paper metadata from Semantic Scholar API.
    
    Args:
        arxiv_id: The arXiv ID of the paper
        include_citations: Whether to include citation data
        
    Returns:
        PaperMetadata object with paper details
        
    Raises:
        ValueError: If arxiv_id is invalid
        APIError: If API request fails
    """
    if not is_valid_arxiv_id(arxiv_id):
        raise ValueError(f"Invalid arXiv ID: {arxiv_id}")
    
    # Implementation...
    return metadata
```

### TypeScript/React Code Style

- Use functional components with hooks
- Use TypeScript for type safety
- Follow Airbnb React style guide
- Use Prettier for formatting

```typescript
// Good example
interface SearchResultsProps {
  query: string;
  results: Paper[];
  onPaperClick: (paper: Paper) => void;
}

export const SearchResults: React.FC<SearchResultsProps> = ({
  query,
  results,
  onPaperClick
}) => {
  return (
    <div className="space-y-4">
      {results.map((paper) => (
        <PaperCard
          key={paper.arxiv_id}
          paper={paper}
          onClick={() => onPaperClick(paper)}
        />
      ))}
    </div>
  );
};
```

### Documentation Standards

- Write clear docstrings for all public functions/classes
- Use Google-style docstrings format
- Update README.md for user-facing changes
- Update API documentation for endpoint changes
- Add inline comments for complex logic

### Git Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense
- Keep first line under 72 characters
- Add detailed description if needed

```bash
# Good examples
git commit -m "feat: add link prediction model training"
git commit -m "fix: resolve Neo4j connection timeout issue"
git commit -m "docs: update API endpoint documentation"

# With detailed description
git commit -m "feat: implement structural hole detection

- Add 4 detection strategies (paper, concept, temporal, cross-domain)
- Integrate with Neo4j graph queries
- Add confidence scoring for gaps
- Include comprehensive tests"
```

## Testing Guidelines

### Writing Tests

- Write tests for all new functionality
- Aim for at least 80% code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
@pytest.mark.asyncio
async def test_fetch_paper_success():
    """Test successful paper fetch from S2 API."""
    # Arrange
    arxiv_id = "2401.12345"
    client = S2Client(api_key="test_key")
    
    # Act
    paper = await client.get_paper(arxiv_id)
    
    # Assert
    assert paper is not None
    assert paper.arxiv_id == arxiv_id
    assert len(paper.title) > 0
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_ai.py

# Run with coverage
poetry run pytest --cov=packages --cov=apps

# Run only unit tests (fast)
poetry run pytest tests/test_ai.py tests/test_ingestion.py

# Run integration tests (requires DB)
docker compose up -d
poetry run pytest tests/test_api.py tests/test_knowledge.py
```

## Pull Request Process

1. **Before Submitting**
   - Ensure all tests pass
   - Run linting and formatting
   - Update documentation
   - Rebase on latest main branch
   - Squash commits if needed

2. **PR Description**
   - Clearly describe what the PR does
   - Reference related issues
   - List any breaking changes
   - Include screenshots for UI changes

3. **Review Process**
   - Address reviewer feedback promptly
   - Make requested changes
   - Re-request review after updates

4. **After Approval**
   - Maintainer will merge your PR
   - Delete your feature branch
   - Celebrate! 🎉

## Project Structure

```
arxiv-cosci/
├── apps/
│   ├── api/          # FastAPI backend
│   ├── cli/          # CLI commands
│   └── web/          # React frontend
├── packages/
│   ├── ai/           # LLM integrations
│   ├── ingestion/    # PDF parsing & data fetching
│   ├── knowledge/    # Database clients
│   └── ml/           # Machine learning models
├── tests/            # Test files
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

### Where to Add Code

- **New AI feature**: `packages/ai/`
- **New API endpoint**: `apps/api/routers/`
- **New CLI command**: `apps/cli/main.py`
- **New React component**: `apps/web/src/components/` or `apps/web/src/pages/`
- **New ML model**: `packages/ml/`
- **New parser**: `packages/ingestion/`

## Areas for Contribution

### High Priority

- [ ] Improve test coverage (especially integration tests)
- [ ] Add Sigma.js graph visualization
- [ ] Implement GraphQL API
- [ ] Add user authentication
- [ ] Improve error handling and logging
- [ ] Add performance monitoring

### Medium Priority

- [ ] Add more LLM providers
- [ ] Improve parsing quality for complex PDFs
- [ ] Add batch processing UI
- [ ] Implement caching layer
- [ ] Add export functionality (CSV, JSON, BibTeX)
- [ ] Create data ingestion pipeline UI

### Documentation

- [ ] Add architecture diagrams
- [ ] Create video tutorials
- [ ] Write deployment guides
- [ ] Add API examples
- [ ] Create contributor guide improvements

### Frontend

- [ ] Add dark mode
- [ ] Improve mobile responsiveness
- [ ] Add keyboard shortcuts
- [ ] Create paper comparison view
- [ ] Add advanced search filters

### Backend

- [ ] Add rate limiting
- [ ] Implement API versioning
- [ ] Add WebSocket support for real-time updates
- [ ] Create admin dashboard
- [ ] Add metrics and monitoring

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: File a GitHub Issue
- **Chat**: Join our Discord (link in README)
- **Email**: Contact maintainers directly

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to ArXiv AI Co-Scientist! 🚀