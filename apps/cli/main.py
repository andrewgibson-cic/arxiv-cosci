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
    logger_factory=structlog.PrintLoggerFactory(),
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


if __name__ == "__main__":
    app()
