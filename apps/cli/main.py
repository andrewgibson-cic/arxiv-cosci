"""Command-line interface for ArXiv AI Co-Scientist.

Usage:
    arxiv-cosci download --category quant-ph --limit 100
    arxiv-cosci parse --input data/raw --output data/processed
    arxiv-cosci stats data/raw/arxiv-metadata.json
"""

import asyncio
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

console = Console()
logger = structlog.get_logger()


@click.group()
@click.version_option(version="0.1.0", prog_name="arxiv-cosci")
def app() -> None:
    """ArXiv AI Co-Scientist: Scientific Intelligence Engine.

    A tool for analyzing physics and mathematics papers from arXiv.
    """
    pass


@app.command()
@click.argument("arxiv_ids", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file for metadata (JSON). If not provided, prints to stdout",
)
@click.option(
    "--with-citations",
    is_flag=True,
    default=False,
    help="Fetch incoming citations for each paper",
)
@click.option(
    "--with-references",
    is_flag=True,
    default=False,
    help="Fetch outgoing references for each paper",
)
def fetch(
    arxiv_ids: tuple[str, ...],
    output: Path | None,
    with_citations: bool,
    with_references: bool,
) -> None:
    """Fetch paper metadata from Semantic Scholar API.

    ARXIV_IDS: One or more arXiv identifiers (e.g., 2401.12345 or 2401.12345 2402.13579)
    """
    import json
    import os

    from packages.ingestion.s2_client import S2Client

    async def run_fetch() -> None:
        api_key = os.getenv("S2_API_KEY")
        client = S2Client(api_key=api_key)

        results = []
        with Progress(console=console) as progress:
            task = progress.add_task("Fetching papers...", total=len(arxiv_ids))

            for arxiv_id in arxiv_ids:
                paper = await client.get_paper_by_arxiv_id(arxiv_id)
                if paper:
                    metadata = client.paper_to_metadata(paper)
                    result = metadata.model_dump()

                    if with_citations:
                        citations = await client.get_paper_citations(arxiv_id, limit=20)
                        result["citations"] = citations

                    if with_references:
                        references = await client.get_paper_references(arxiv_id, limit=20)
                        result["references"] = references

                    results.append(result)
                    progress.update(task, advance=1)
                else:
                    console.print(f"[yellow]Paper not found: {arxiv_id}[/yellow]")
                    progress.update(task, advance=1)

        if not results:
            console.print("[red]No papers found[/red]")
            return

        # Output results
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(results, indent=2))
            console.print(f"\n[green]Saved {len(results)} papers to {output}[/green]")
        else:
            # Display in table
            table = Table(title=f"Fetched Papers ({len(results)} found)")
            table.add_column("arXiv ID", style="cyan")
            table.add_column("Title", max_width=50)
            table.add_column("Authors", max_width=40)
            table.add_column("Year")

            for result in results:
                table.add_row(
                    result.get("id", "-"),
                    result.get("title", "")[:50],
                    result.get("authors", "")[:40],
                    result.get("update_date", "-"),
                )

            console.print(table)

            # Show abstract if available
            for result in results:
                if result.get("abstract"):
                    console.print(f"\n[bold]{result['id']}:[/bold]")
                    console.print(result["abstract"][:300] + "...")

    asyncio.run(run_fetch())


@app.command()
@click.argument("metadata_file", type=click.Path(exists=True, path_type=Path))
@click.option("--top", default=20, help="Number of top categories to show")
def stats(metadata_file: Path, top: int) -> None:
    """Show statistics about the arXiv metadata file.

    METADATA_FILE: Path to arxiv-metadata-oai-snapshot.json
    """
    from packages.ingestion.kaggle_loader import get_category_counts, stream_kaggle_metadata

    console.print(f"\n[bold]Analyzing:[/bold] {metadata_file}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Counting categories...", total=None)
        counts = get_category_counts(metadata_file)

    # Create table
    table = Table(title="Top Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")

    for category, count in list(counts.items())[:top]:
        table.add_row(category, f"{count:,}")

    console.print(table)
    console.print(f"\n[dim]Total categories: {len(counts)}[/dim]")


@app.command()
@click.argument("metadata_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("data/raw/pdfs"),
    help="Output directory for PDFs",
)
@click.option("--category", "-c", multiple=True, help="Filter by category (can repeat)")
@click.option("--limit", "-n", type=int, default=10, help="Maximum papers to download")
@click.option("--skip-existing/--no-skip", default=True, help="Skip already downloaded")
def download(
    metadata_file: Path,
    output: Path,
    category: tuple[str, ...],
    limit: int,
    skip_existing: bool,
) -> None:
    """Download PDFs from arXiv.

    METADATA_FILE: Path to arxiv-metadata-oai-snapshot.json or filtered subset
    """
    from packages.ingestion.kaggle_loader import filter_by_categories, stream_kaggle_metadata
    from packages.ingestion.pdf_downloader import download_papers

    console.print(f"\n[bold]Downloading papers from:[/bold] {metadata_file}")
    console.print(f"[bold]Output directory:[/bold] {output}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    if category:
        console.print(f"[bold]Categories:[/bold] {', '.join(category)}")

    # Load metadata
    papers_iter = stream_kaggle_metadata(metadata_file, filter_physics_math=True, limit=None)

    if category:
        papers_iter = filter_by_categories(papers_iter, list(category))

    papers = []
    for paper in papers_iter:
        papers.append(paper)
        if len(papers) >= limit:
            break

    console.print(f"\n[green]Found {len(papers)} papers to download[/green]\n")

    if not papers:
        console.print("[yellow]No papers match the criteria[/yellow]")
        return

    # Download
    async def run_download() -> None:
        results = await download_papers(papers, output, skip_errors=True)
        console.print(f"\n[green]Successfully downloaded {len(results)} papers[/green]")

    asyncio.run(run_download())


@app.command()
@click.option(
    "--input",
    "-i",
    "input_dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/raw/pdfs"),
    help="Directory containing PDFs",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("data/processed"),
    help="Output directory for parsed content",
)
@click.option("--limit", "-n", type=int, default=None, help="Maximum papers to parse")
def parse(input_dir: Path, output: Path, limit: int | None) -> None:
    """Parse downloaded PDFs to extract text and structure.

    Extracts text, sections, citations, and equations from PDFs.
    """
    from packages.ingestion.text_extractor import parse_pdf_file

    output.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.rglob("*.pdf"))
    if limit:
        pdf_files = pdf_files[:limit]

    console.print(f"\n[bold]Parsing {len(pdf_files)} PDFs from:[/bold] {input_dir}")
    console.print(f"[bold]Output directory:[/bold] {output}\n")

    success_count = 0
    error_count = 0

    with Progress(console=console) as progress:
        task = progress.add_task("Parsing PDFs...", total=len(pdf_files))

        for pdf_path in pdf_files:
            try:
                parsed = parse_pdf_file(pdf_path)

                # Save as JSON
                output_file = output / f"{parsed.arxiv_id.replace('/', '_')}.json"
                output_file.write_text(parsed.model_dump_json(indent=2))

                success_count += 1
                progress.update(task, advance=1)

            except Exception as e:
                logger.error("parse_failed", path=str(pdf_path), error=str(e))
                error_count += 1
                progress.update(task, advance=1)

    console.print(f"\n[green]Parsed: {success_count}[/green]")
    if error_count:
        console.print(f"[red]Errors: {error_count}[/red]")


@app.command()
@click.argument("metadata_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file for filtered subset",
)
@click.option("--category", "-c", multiple=True, help="Categories to include")
@click.option("--limit", "-n", type=int, default=None, help="Maximum papers")
def subset(
    metadata_file: Path,
    output: Path,
    category: tuple[str, ...],
    limit: int | None,
) -> None:
    """Create a filtered subset of the metadata.

    Useful for creating smaller datasets for development.
    """
    from packages.ingestion.kaggle_loader import create_subset

    console.print(f"\n[bold]Creating subset from:[/bold] {metadata_file}")
    console.print(f"[bold]Output:[/bold] {output}")
    if category:
        console.print(f"[bold]Categories:[/bold] {', '.join(category)}")

    count = create_subset(
        metadata_file,
        output,
        categories=list(category) if category else None,
        limit=limit,
    )

    console.print(f"\n[green]Created subset with {count:,} papers[/green]")


@app.command()
def check() -> None:
    """Check system requirements and dependencies."""
    import sys

    table = Table(title="System Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    table.add_row(
        "Python",
        "[green]OK[/green]" if py_ok else "[red]FAIL[/red]",
        py_version,
    )

    # Check imports
    checks = [
        ("PyMuPDF (fitz)", "fitz"),
        ("ChromaDB", "chromadb"),
        ("Sentence Transformers", "sentence_transformers"),
        ("Neo4j", "neo4j"),
        ("LangChain", "langchain"),
        ("PyTorch", "torch"),
        ("FastAPI", "fastapi"),
    ]

    for name, module in checks:
        try:
            __import__(module)
            table.add_row(name, "[green]OK[/green]", "Installed")
        except ImportError:
            table.add_row(name, "[yellow]MISSING[/yellow]", "Run: poetry install")

    # Check Ollama
    import shutil

    ollama_path = shutil.which("ollama")
    if ollama_path:
        table.add_row("Ollama", "[green]OK[/green]", ollama_path)
    else:
        table.add_row("Ollama", "[yellow]MISSING[/yellow]", "brew install ollama")

    # Check Docker
    docker_path = shutil.which("docker")
    if docker_path:
        table.add_row("Docker", "[green]OK[/green]", docker_path)
    else:
        table.add_row("Docker", "[yellow]MISSING[/yellow]", "Install Docker Desktop")

    console.print(table)


@app.command()
def init_db() -> None:
    """Initialize the Neo4j database schema."""
    from packages.knowledge.neo4j_client import neo4j_client

    async def run_init() -> None:
        try:
            console.print("[bold]Initializing Neo4j schema...[/bold]")
            await neo4j_client.init_schema()
            console.print("[green]Schema initialization complete![/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize schema: {e}[/red]")
            console.print("[yellow]Ensure Neo4j is running: docker compose up -d[/yellow]")
        finally:
            await neo4j_client.close()

    asyncio.run(run_init())


@app.command()
@click.option(
    "--input",
    "-i",
    "input_dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/processed"),
    help="Directory containing parsed JSON files",
)
@click.option("--to-neo4j/--no-neo4j", default=True, help="Ingest to Neo4j graph")
@click.option("--to-chroma/--no-chroma", default=True, help="Ingest to ChromaDB vectors")
@click.option("--limit", "-n", type=int, default=None, help="Maximum papers to ingest")
def ingest(
    input_dir: Path,
    to_neo4j: bool,
    to_chroma: bool,
    limit: int | None,
) -> None:
    """Ingest parsed papers into Neo4j and/or ChromaDB.

    Reads JSON files from the processed directory and ingests them
    into the knowledge graph and vector store.
    """
    import json

    from packages.ingestion.models import ParsedPaper
    from packages.knowledge.neo4j_client import neo4j_client
    from packages.knowledge.chromadb_client import chromadb_client

    json_files = list(input_dir.glob("*.json"))
    if limit:
        json_files = json_files[:limit]

    if not json_files:
        console.print(f"[yellow]No JSON files found in {input_dir}[/yellow]")
        return

    console.print(f"\n[bold]Ingesting {len(json_files)} papers from:[/bold] {input_dir}")
    console.print(f"[bold]Neo4j:[/bold] {'Yes' if to_neo4j else 'No'}")
    console.print(f"[bold]ChromaDB:[/bold] {'Yes' if to_chroma else 'No'}\n")

    # Load papers
    papers: list[ParsedPaper] = []
    with Progress(console=console) as progress:
        task = progress.add_task("Loading papers...", total=len(json_files))
        for json_file in json_files:
            try:
                data = json.loads(json_file.read_text())
                paper = ParsedPaper.model_validate(data)
                papers.append(paper)
            except Exception as e:
                logger.warning("load_failed", file=str(json_file), error=str(e))
            progress.update(task, advance=1)

    console.print(f"[green]Loaded {len(papers)} papers[/green]\n")

    # Ingest to Neo4j
    if to_neo4j and papers:
        async def ingest_neo4j() -> dict[str, int]:
            try:
                await neo4j_client.connect()
                stats = await neo4j_client.ingest_batch(papers, include_citations=True)
                return stats
            finally:
                await neo4j_client.close()

        console.print("[bold]Ingesting to Neo4j...[/bold]")
        try:
            stats = asyncio.run(ingest_neo4j())
            console.print(f"  Papers: [green]{stats['papers_ingested']}[/green]")
            console.print(f"  Citations: [green]{stats['citations_created']}[/green]")
        except Exception as e:
            console.print(f"[red]Neo4j ingest failed: {e}[/red]")
            console.print("[yellow]Ensure Neo4j is running: docker compose up -d[/yellow]")

    # Ingest to ChromaDB
    if to_chroma and papers:
        console.print("\n[bold]Ingesting to ChromaDB...[/bold]")
        try:
            count = chromadb_client.add_papers_batch(papers)
            console.print(f"  Embedded: [green]{count}[/green] papers")
        except Exception as e:
            console.print(f"[red]ChromaDB ingest failed: {e}[/red]")

    console.print("\n[green]Ingestion complete![/green]")


@app.command()
@click.argument("query")
@click.option("--limit", "-n", type=int, default=10, help="Maximum results")
@click.option("--category", "-c", default=None, help="Filter by category")
def search(query: str, limit: int, category: str | None) -> None:
    """Search papers by semantic similarity.

    QUERY: Natural language search query
    """
    from packages.knowledge.chromadb_client import chromadb_client

    console.print(f"\n[bold]Searching:[/bold] {query}\n")

    try:
        results = chromadb_client.search_papers(
            query, n_results=limit, category_filter=category
        )

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(title=f"Search Results ({len(results)} found)")
        table.add_column("arXiv ID", style="cyan")
        table.add_column("Title", max_width=60)
        table.add_column("Category")
        table.add_column("Similarity", justify="right", style="green")

        for paper in results:
            similarity = f"{paper.get('similarity', 0):.3f}" if paper.get('similarity') else "-"
            table.add_row(
                paper["arxiv_id"],
                paper.get("title", "")[:60],
                paper.get("primary_category", ""),
                similarity,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")


@app.command()
@click.argument("arxiv_id")
@click.option(
    "--level",
    "-l",
    type=click.Choice(["brief", "standard", "detailed"]),
    default="standard",
    help="Summary detail level",
)
def summarize(arxiv_id: str, level: str) -> None:
    """Summarize a paper using local LLM.

    ARXIV_ID: Paper ID or path to parsed JSON file
    """
    import json
    from pathlib import Path

    from packages.ai.factory import close_client, get_llm_client
    from packages.ai.summarizer import summarize_paper, SummaryLevel
    from packages.ingestion.models import ParsedPaper

    # Load paper
    json_path = Path(f"data/processed/{arxiv_id.replace('/', '_')}.json")
    if not json_path.exists():
        json_path = Path(arxiv_id)

    if not json_path.exists():
        console.print(f"[red]Paper not found: {arxiv_id}[/red]")
        console.print("[yellow]Ensure paper is parsed: arxiv-cosci parse[/yellow]")
        return

    paper = ParsedPaper.model_validate_json(json_path.read_text())

    console.print(f"\n[bold]Summarizing:[/bold] {paper.title[:60]}...")
    console.print(f"[bold]Level:[/bold] {level}\n")

    async def run_summarize() -> None:
        # Check LLM availability
        if not await get_llm_client().is_available():
            console.print("[red]LLM service not available[/red]")
            console.print("[yellow]Check configuration (Ollama running? API key set?)[/yellow]")
            return

        summary_level = SummaryLevel(level)
        summary = await summarize_paper(paper, summary_level)

        if isinstance(summary, str):
            console.print("[bold]Summary:[/bold]")
            console.print(summary)
        else:
            console.print("[bold]One-liner:[/bold]")
            console.print(summary.one_liner)
            console.print("\n[bold]Key Contribution:[/bold]")
            console.print(summary.key_contribution)
            console.print("\n[bold]Methodology:[/bold]")
            console.print(summary.methodology)
            if summary.key_findings:
                console.print("\n[bold]Key Findings:[/bold]")
                for finding in summary.key_findings:
                    console.print(f"  • {finding}")

        await close_client()

    asyncio.run(run_summarize())


@app.command()
@click.argument("arxiv_id")
@click.option("--use-llm/--no-llm", default=True, help="Use LLM for extraction (slower)")
def extract(arxiv_id: str, use_llm: bool) -> None:
    """Extract entities from a paper.

    ARXIV_ID: Paper ID or path to parsed JSON file
    """
    import json
    from pathlib import Path

    from packages.ai.entity_extractor import extract_entities, extract_entities_regex
    from packages.ai.factory import close_client, get_llm_client
    from packages.ingestion.models import ParsedPaper

    # Load paper
    json_path = Path(f"data/processed/{arxiv_id.replace('/', '_')}.json")
    if not json_path.exists():
        json_path = Path(arxiv_id)

    if not json_path.exists():
        console.print(f"[red]Paper not found: {arxiv_id}[/red]")
        return

    paper = ParsedPaper.model_validate_json(json_path.read_text())

    console.print(f"\n[bold]Extracting entities from:[/bold] {paper.title[:60]}...")
    console.print(f"[bold]Using LLM:[/bold] {use_llm}\n")

    async def run_extract() -> None:
        if use_llm:
            if not await get_llm_client().is_available():
                console.print("[yellow]LLM service not available, using regex only[/yellow]")
                entities = extract_entities_regex(paper)
            else:
                entities = await extract_entities(paper, use_llm=True)
        else:
            entities = extract_entities_regex(paper)

        # Display results
        categories = [
            ("Methods", entities.methods),
            ("Theorems", entities.theorems),
            ("Equations", entities.equations),
            ("Constants", entities.constants),
            ("Datasets", entities.datasets),
            ("Conjectures", entities.conjectures),
        ]

        for name, items in categories:
            if items:
                console.print(f"\n[bold]{name}:[/bold]")
                for item in items:
                    conf = f"({item.confidence:.0%})" if item.confidence < 1 else ""
                    console.print(f"  • {item.name} {conf}")

        if use_llm:
            await close_client()

    asyncio.run(run_extract())


@app.command()
def ai_check() -> None:
    """Check AI/LLM system status."""
    import asyncio
    import os
    import shutil

    from packages.ai.factory import close_client, get_llm_client

    table = Table(title="AI System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    table.add_row("Provider", "[green]CONFIGURED[/green]", provider)

    if provider == "ollama":
        # Check Ollama binary
        ollama_path = shutil.which("ollama")
        if ollama_path:
            table.add_row("Ollama Binary", "[green]OK[/green]", ollama_path)
        else:
            table.add_row("Ollama Binary", "[red]MISSING[/red]", "brew install ollama")

    # Check Service
    async def check_service() -> bool:
        available = await get_llm_client().is_available()
        await close_client()
        return available

    available = asyncio.run(check_service())

    if available:
        table.add_row("Service", "[green]RUNNING[/green]", "Connected")
    else:
        table.add_row("Service", "[red]UNAVAILABLE[/red]", "Check logs/config")

    console.print(table)


@app.command()
def db_stats() -> None:
    """Show database statistics."""
    from packages.knowledge.neo4j_client import neo4j_client
    from packages.knowledge.chromadb_client import chromadb_client

    table = Table(title="Database Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Neo4j", justify="right")
    table.add_column("ChromaDB", justify="right")

    # Get ChromaDB stats (sync)
    try:
        chroma_stats = chromadb_client.get_stats()
    except Exception:
        chroma_stats = {"papers": "-", "concepts": "-"}

    # Get Neo4j stats (async)
    async def get_neo4j_stats() -> dict[str, int]:
        try:
            await neo4j_client.connect()
            return await neo4j_client.get_stats()
        except Exception:
            return {}
        finally:
            await neo4j_client.close()

    neo4j_stats = asyncio.run(get_neo4j_stats())

    table.add_row(
        "Papers",
        str(neo4j_stats.get("papers", "-")),
        str(chroma_stats.get("papers", "-")),
    )
    table.add_row(
        "Authors",
        str(neo4j_stats.get("authors", "-")),
        "-",
    )
    table.add_row(
        "Categories",
        str(neo4j_stats.get("categories", "-")),
        "-",
    )
    table.add_row(
        "Citations",
        str(neo4j_stats.get("citations", "-")),
        "-",
    )
    table.add_row(
        "Concepts",
        "-",
        str(chroma_stats.get("concepts", "-")),
    )

    console.print(table)


if __name__ == "__main__":
    app()
