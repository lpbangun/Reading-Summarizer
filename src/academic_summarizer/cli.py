"""Command-line interface for academic summarizer."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_settings
from .core.summarizer import AcademicSummarizer
from .utils.exceptions import AcademicSummarizerError
from .utils.logger import setup_logging, get_logger

console = Console()


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: same folder as PDF)",
)
@click.option(
    "--course",
    "-c",
    help="Override course code detection",
)
@click.option(
    "--week",
    "-w",
    help="Override week detection",
)
@click.option(
    "--no-history",
    is_flag=True,
    help="Skip historical context from previous summaries",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def summarize(
    pdf_path: Path,
    output: Path | None,
    course: str | None,
    week: str | None,
    no_history: bool,
    verbose: bool,
):
    """
    Generate an academic reading summary from a PDF file.

    This tool creates structured 11-12 minute summaries with automatic course
    context detection and cumulative learning connections to previous weeks.

    Example usage:

        \b
        # Basic usage (saves summary next to PDF)
        academic-summary readings/Week3/article.pdf

        \b
        # With manual course and week
        academic-summary article.pdf --course PSYCH101 --week 3

        \b
        # Skip historical context (faster)
        academic-summary article.pdf --no-history
    """
    try:
        # Load settings
        settings = get_settings()

        # Setup logging
        log_file = settings.get_log_file_path() if not verbose else None
        setup_logging(
            level=settings.log_level,
            log_file=log_file,
            verbose=verbose,
        )

        logger = get_logger()

        # Welcome message
        if not verbose:
            console.print(
                Panel(
                    "[bold cyan]Academic Reading Summary Generator[/bold cyan]\n"
                    "Generating 11-12 minute structured summaries with cumulative learning",
                    expand=False,
                )
            )

        # Create summarizer
        summarizer = AcademicSummarizer(settings)

        # Show progress
        if not verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Processing {pdf_path.name}...", total=None
                )

                output_path = summarizer.generate_summary(
                    pdf_path=pdf_path,
                    output_path=output,
                    course_override=course,
                    week_override=week,
                    enable_history=not no_history,
                )

                progress.update(task, description="[green]✓ Complete!")
        else:
            # Verbose mode - let logs show progress
            output_path = summarizer.generate_summary(
                pdf_path=pdf_path,
                output_path=output,
                course_override=course,
                week_override=week,
                enable_history=not no_history,
            )

        # Success message
        console.print("\n[bold green]✓ Summary generated successfully![/bold green]")
        console.print(f"\n[cyan]Summary saved to:[/cyan] {output_path}")

        # Show master file locations
        if settings.auto_update_masters:
            console.print("\n[cyan]Master files updated:[/cyan]")
            # Try to show course master if it exists
            course_master = output_path.parent.parent / f"*_master.md"
            console.print(f"  • Course master: Check course folder")
            console.print(
                f"  • Global master: {settings.get_global_master_path()}"
            )

        console.print(
            f"\n[dim]Reading time: 11-12 minutes | Model: {settings.model_name}[/dim]"
        )

    except AcademicSummarizerError as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}", style="red")
        if verbose:
            console.print_exception()
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(
            f"\n[bold red]Unexpected error:[/bold red] {str(e)}", style="red"
        )
        if verbose:
            console.print_exception()
        else:
            console.print(
                "\n[dim]Run with --verbose for detailed error information[/dim]"
            )
        sys.exit(1)


def main():
    """Entry point for CLI."""
    summarize()


if __name__ == "__main__":
    main()
