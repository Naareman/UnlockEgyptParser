#!/usr/bin/env python3
"""
UnlockEgypt Site Researcher - CLI Entry Point

A research-oriented tool that gathers comprehensive information about
Egyptian archaeological sites from multiple sources.

Usage:
    unlockegypt                          # Research all sites
    unlockegypt -t monuments             # Research only monuments
    unlockegypt -t museums -m 5          # Research first 5 museums
    unlockegypt -v                       # Verbose output
    unlockegypt --dry-run                # Preview without scraping
    unlockegypt --resume                 # Resume from checkpoint
"""

import argparse
import logging
import os

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from unlockegypt.site_researcher import PageType, SiteResearcher
from unlockegypt.utils.progress import ProgressManager, load_existing_output

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="UnlockEgypt Site Researcher - Comprehensive archaeological site research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Research Approach:
  This tool treats each site as a research subject, gathering information
  from multiple sources:
  - egymonuments.gov.eg (primary source)
  - Wikipedia (EN + AR)
  - Google Maps (practical info)
  - Official sources (tickets, hours)

Page Types:
  archaeological-sites  Ancient archaeological sites
  monuments            Historical monuments
  museums              Museums across Egypt
  sunken-monuments     Underwater archaeological sites

Examples:
  unlockegypt                              # Research all sites
  unlockegypt -t monuments                 # Research only monuments
  unlockegypt -t museums -m 3              # Research first 3 museums
  unlockegypt -o my_research.json          # Custom output path
  unlockegypt -v                           # Verbose output
  unlockegypt --dry-run                    # Preview sites without scraping
  unlockegypt --resume                     # Resume interrupted run
        """,
    )

    parser.add_argument(
        "-t",
        "--type",
        action="append",
        dest="page_types",
        choices=PageType.ALL_TYPES,
        help="Page type(s) to research (can be specified multiple times)",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join(os.path.dirname(__file__), "researched_sites.json"),
        help="Output JSON file path (default: researched_sites.json)",
    )

    parser.add_argument(
        "-m",
        "--max-sites",
        type=int,
        default=None,
        help="Maximum number of sites to research per page type",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose (debug) logging"
    )

    parser.add_argument(
        "--no-headless", action="store_true", help="Show browser window"
    )

    # New flags for improvements
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List sites that would be scraped without actually scraping",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous checkpoint (skip already processed sites)",
    )

    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Path to checkpoint file (default: .unlockegypt_checkpoint.json)",
    )

    parser.add_argument(
        "--clear-checkpoint",
        action="store_true",
        help="Clear existing checkpoint and start fresh",
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip sites that already exist in the output file",
    )

    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar (useful for logging to file)",
    )

    return parser.parse_args()


def print_header() -> None:
    """Print application header."""
    console.print(
        Panel.fit(
            "[bold blue]UnlockEgypt Site Researcher v3.4[/bold blue]\n"
            "[dim]Research-Oriented Multi-Source Data Collection[/dim]",
            border_style="blue",
        )
    )
    console.print()


def print_config(
    page_types: list[str],
    max_sites: int | None,
    dry_run: bool,
    resume: bool,
) -> None:
    """Print configuration summary."""
    table = Table(title="Configuration", show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    type_names = [PageType.get_display_name(t) for t in page_types]
    table.add_row("Page types", ", ".join(type_names))

    if max_sites:
        table.add_row("Max sites per type", str(max_sites))

    if dry_run:
        table.add_row("Mode", "[yellow]DRY RUN (no scraping)[/yellow]")
    elif resume:
        table.add_row("Mode", "[green]RESUME from checkpoint[/green]")
    else:
        table.add_row("Mode", "Normal")

    console.print(table)
    console.print()


def print_sources() -> None:
    """Print research sources."""
    console.print("[bold]Research sources:[/bold]")
    console.print("  [dim]-[/dim] egymonuments.gov.eg [dim](primary)[/dim]")
    console.print("  [dim]-[/dim] Wikipedia [dim](EN + AR)[/dim]")
    console.print("  [dim]-[/dim] Google Maps [dim](practical info)[/dim]")
    console.print("  [dim]-[/dim] Official sources [dim](tickets, hours)[/dim]")
    console.print()


def run_dry_run(
    researcher: SiteResearcher,
    page_types: list[str],
    max_sites: int | None,
    existing_sites: set[str],
) -> None:
    """Run in dry-run mode - list sites without scraping."""
    console.print("[bold yellow]DRY RUN MODE[/bold yellow] - Listing sites only\n")

    total_sites = 0

    for page_type in page_types:
        console.print(f"[bold]{PageType.get_display_name(page_type)}:[/bold]")

        with console.status(f"[dim]Loading {page_type} list...[/dim]"):
            site_links = researcher.get_site_links(
                page_type=page_type, max_sites=max_sites
            )

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Location", style="green")
        table.add_column("Status", style="yellow")

        for i, site in enumerate(site_links, 1):
            name = site.get("name", "Unknown")
            location = site.get("location", "")
            status = (
                "[dim]Already exists[/dim]" if name in existing_sites else "[green]New[/green]"
            )
            table.add_row(str(i), name, location, status)

        console.print(table)
        console.print(f"  Total: {len(site_links)} sites\n")
        total_sites += len(site_links)

    console.print(f"[bold]Grand total: {total_sites} sites[/bold]")

    new_sites = total_sites - len(existing_sites)
    if existing_sites:
        console.print(f"[dim]({new_sites} new, {len(existing_sites)} already exist)[/dim]")


def run_research(
    researcher: SiteResearcher,
    page_types: list[str],
    max_sites: int | None,
    progress_manager: ProgressManager,
    existing_sites: set[str],
    show_progress: bool,
) -> list[object]:
    """Run the actual research with progress tracking."""
    all_sites: list[object] = []

    for page_type in page_types:
        # Check if page type was already completed
        if progress_manager.should_skip_page_type(page_type):
            console.print(
                f"[dim]Skipping {PageType.get_display_name(page_type)} (already completed)[/dim]"
            )
            continue

        console.print(f"\n[bold]Processing: {PageType.get_display_name(page_type)}[/bold]")

        # Get site links
        with console.status("[dim]Loading site list...[/dim]"):
            site_links = researcher.get_site_links(
                page_type=page_type, max_sites=max_sites
            )

        # Filter out already processed sites
        sites_to_process = []
        for site_info in site_links:
            url = site_info.get("url", "")
            name = site_info.get("name", "")

            if progress_manager.should_skip_site(url, name):
                console.print(f"  [dim]Skipping (checkpoint): {name}[/dim]")
                continue

            if name in existing_sites:
                console.print(f"  [dim]Skipping (exists): {name}[/dim]")
                continue

            sites_to_process.append(site_info)

        if not sites_to_process:
            console.print("  [dim]No new sites to process[/dim]")
            progress_manager.mark_page_type_completed(page_type)
            continue

        console.print(f"  Sites to process: {len(sites_to_process)}")

        # Process sites with progress bar
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Researching {page_type}...",
                    total=len(sites_to_process),
                )

                for site_info in sites_to_process:
                    name = site_info.get("name", "Unknown")
                    progress.update(task, description=f"[cyan]{name[:40]}...")

                    site = researcher.research_site(site_info)
                    if site:
                        all_sites.append(site)
                        researcher.sites.append(site)

                    # Mark as processed
                    progress_manager.mark_site_processed(
                        site_info.get("url", ""),
                        name,
                    )

                    progress.update(task, advance=1)
        else:
            # No progress bar mode
            for i, site_info in enumerate(sites_to_process, 1):
                name = site_info.get("name", "Unknown")
                console.print(f"  [{i}/{len(sites_to_process)}] {name}")

                site = researcher.research_site(site_info)
                if site:
                    all_sites.append(site)
                    researcher.sites.append(site)

                progress_manager.mark_site_processed(
                    site_info.get("url", ""),
                    name,
                )

        # Mark page type as completed
        progress_manager.mark_page_type_completed(page_type)

    return all_sites


def print_summary(sites: list[object]) -> None:
    """Print research summary."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]RESEARCH COMPLETE[/bold green]\n"
            f"Total sites researched: {len(sites)}",
            border_style="green",
        )
    )

    if sites:
        table = Table(title="Sites Summary", show_lines=True)
        table.add_column("Name", style="cyan", max_width=30)
        table.add_column("Governorate", style="green")
        table.add_column("Era", style="yellow")
        table.add_column("Type")
        table.add_column("Facts", justify="right")
        table.add_column("Tips", justify="right")

        for site in sites:
            table.add_row(
                getattr(site, "name", "Unknown"),
                getattr(site, "governorate", "N/A") or "N/A",
                getattr(site, "era", "N/A") or "N/A",
                f"{getattr(site, 'tourismType', '')} / {getattr(site, 'placeType', '')}",
                str(len(getattr(site, "uniqueFacts", []))),
                str(len(getattr(site, "tips", []))),
            )

        console.print(table)


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    setup_logging(args.verbose)

    print_header()

    # Determine which page types to research
    page_types = args.page_types if args.page_types else PageType.ALL_TYPES

    # Initialize progress manager
    progress_manager = ProgressManager(
        checkpoint_file=args.checkpoint,
        auto_save=True,
        save_interval=1,
    )

    # Handle checkpoint operations
    if args.clear_checkpoint:
        progress_manager.clear_checkpoint()
        console.print("[yellow]Checkpoint cleared[/yellow]\n")

    if args.resume:
        if progress_manager.load_checkpoint():
            stats = progress_manager.get_stats()
            console.print(
                f"[green]Resuming from checkpoint: {stats['total_processed']} sites already processed[/green]\n"
            )
        else:
            console.print("[yellow]No checkpoint found, starting fresh[/yellow]\n")

    # Load existing output for duplicate detection
    existing_sites: set[str] = set()
    if args.skip_existing or args.dry_run:
        existing_sites = load_existing_output(args.output)

    print_config(page_types, args.max_sites, args.dry_run, args.resume)
    print_sources()

    headless = not args.no_headless
    show_progress = not args.no_progress

    with SiteResearcher(headless=headless) as researcher:
        if args.dry_run:
            run_dry_run(researcher, page_types, args.max_sites, existing_sites)
        else:
            sites = run_research(
                researcher,
                page_types,
                args.max_sites,
                progress_manager,
                existing_sites,
                show_progress,
            )

            # Export results
            if sites or researcher.sites:
                researcher.export_to_json(args.output)
                console.print(f"\n[green]Output saved to: {args.output}[/green]")

            print_summary(sites)

            # Final checkpoint save
            progress_manager.save_checkpoint()


if __name__ == "__main__":
    main()
