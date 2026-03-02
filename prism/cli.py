"""PRISM CLI — Click entry point with Rich formatting."""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from prism.config import (
    COMPOSITE_WEIGHTS,
    DOSSIERS_DIR,
    ICP_WEIGHTS,
    PRISM_PROMPT_VERSION,
    READINESS_WEIGHTS,
    SIGNAL_DECAY_CONFIG,
    TIER_THRESHOLDS,
    TIMING_WEIGHTS,
)

console = Console()
logger = logging.getLogger("prism")


def _setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
def cli(log_level: str) -> None:
    """PRISM — Predictive Revenue Intelligence & Signal Mapping."""
    _setup_logging(log_level)


@cli.command()
@click.argument("slug")
@click.option("--no-scrape", is_flag=True, help="Skip blog scraping, use fixtures only")
@click.option("--no-llm", is_flag=True, help="Skip LLM analysis, score from fixtures only")
def analyze(slug: str, no_scrape: bool, no_llm: bool) -> None:
    """Analyze a single company and generate dossier."""
    asyncio.run(_analyze_company(slug, no_scrape=no_scrape, no_llm=no_llm))


@cli.command(name="analyze-all")
@click.option("--no-scrape", is_flag=True, help="Skip blog scraping")
@click.option("--no-llm", is_flag=True, help="Skip LLM analysis")
def analyze_all(no_scrape: bool, no_llm: bool) -> None:
    """Analyze all companies in fixtures directory."""
    asyncio.run(_analyze_all(no_scrape=no_scrape, no_llm=no_llm))


@cli.command(name="list")
def list_companies() -> None:
    """List available companies in fixtures."""
    from prism.data.loader import list_companies as _list_companies, load_account

    slugs = _list_companies()
    if not slugs:
        console.print("[yellow]No companies found in fixtures/companies/[/yellow]")
        return

    table = Table(title="Available Companies", show_header=True)
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Industry")
    table.add_column("Stage")
    table.add_column("Headcount", justify="right")

    for slug in slugs:
        account = load_account(slug)
        if account:
            f = account.firmographics
            table.add_row(
                slug,
                account.company_name,
                f.industry or "—",
                f.funding_stage or "—",
                str(f.headcount) if f.headcount else "—",
            )
        else:
            table.add_row(slug, "[red]Error loading[/red]", "—", "—", "—")

    console.print(table)


@cli.command()
def weights() -> None:
    """Show current scoring weights configuration."""
    _print_weights("ICP Fit Weights", ICP_WEIGHTS)
    _print_weights("Buying Readiness Weights", READINESS_WEIGHTS)
    _print_weights("Timing Weights", TIMING_WEIGHTS)
    _print_weights("Composite Weights", COMPOSITE_WEIGHTS)

    table = Table(title="Tier Thresholds")
    table.add_column("Tier", style="bold")
    table.add_column("Threshold", justify="right")
    table.add_column("Action")

    tier_colors = {"tier_1": "red", "tier_2": "yellow", "tier_3": "blue"}
    tier_actions = {
        "tier_1": "Immediate Action",
        "tier_2": "Active Outreach",
        "tier_3": "Monitor & Nurture",
    }

    for tier, threshold in TIER_THRESHOLDS.items():
        color = tier_colors.get(tier, "white")
        table.add_row(
            Text(tier.replace("_", " ").upper(), style=color),
            f"{threshold:.2f}",
            tier_actions.get(tier, ""),
        )
    table.add_row(Text("NOT QUALIFIED", style="dim"), "< 0.25", "Archive")

    console.print(table)


@cli.command()
@click.argument("slug")
def estimate(slug: str) -> None:
    """Estimate analysis cost for a company."""
    from prism.data.loader import load_account, load_contacts, load_additional_content

    account = load_account(slug)
    if not account:
        console.print(f"[red]Company '{slug}' not found[/red]")
        return

    contacts = load_contacts(slug)
    content = load_additional_content(slug)

    contacts_with_posts = sum(1 for c in contacts if c.linkedin_posts)
    total_posts = sum(len(c.linkedin_posts) for c in contacts)

    # Estimate tokens
    stage1_tokens = len(content) * 3000
    stage2_tokens = 30000 + 4000
    stage3_tokens = contacts_with_posts * 5000
    stage4_tokens = 15000 + 3000
    activation_tokens = contacts_with_posts * 3000
    total_tokens = stage1_tokens + stage2_tokens + stage3_tokens + stage4_tokens + activation_tokens

    # Estimate cost (rough: $3/M input, $15/M output, ~70/30 split)
    input_tokens = int(total_tokens * 0.7)
    output_tokens = int(total_tokens * 0.3)
    est_cost = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)

    table = Table(title=f"Cost Estimate: {account.company_name}")
    table.add_column("Stage")
    table.add_column("Items", justify="right")
    table.add_column("Est. Tokens", justify="right")

    table.add_row("Stage 1: Extraction", str(len(content)), f"{stage1_tokens:,}")
    table.add_row("Stage 2: Synthesis", "1", f"{stage2_tokens:,}")
    table.add_row("Stage 3: Person", str(contacts_with_posts), f"{stage3_tokens:,}")
    table.add_row("Stage 4: Scoring", "1", f"{stage4_tokens:,}")
    table.add_row("Activation: Angles", str(contacts_with_posts), f"{activation_tokens:,}")
    table.add_row("", "", "")
    table.add_row("[bold]TOTAL[/bold]", "", f"[bold]{total_tokens:,}[/bold]")

    console.print(table)
    console.print(f"\nEstimated cost: [green]${est_cost:.4f}[/green]")
    console.print(f"Content items: {len(content)} | Contacts with posts: {contacts_with_posts} | Total posts: {total_posts}")


def _print_weights(title: str, weights: dict) -> None:
    """Print a weights table."""
    table = Table(title=title, show_header=True)
    table.add_column("Component")
    table.add_column("Weight", justify="right")
    table.add_column("Bar")

    for key, val in weights.items():
        bar_len = int(val * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        table.add_row(key, f"{val:.2f}", bar)

    console.print(table)
    console.print()


async def _analyze_company(
    slug: str,
    no_scrape: bool = False,
    no_llm: bool = False,
) -> None:
    """Full analysis pipeline for a single company."""
    from prism.data.loader import (
        load_account,
        load_additional_content,
        load_contacts,
        load_scraped_content,
        load_signals,
    )
    from prism.models.content import ContentItem
    from prism.output.dossier import render_dossier
    from prism.pipeline import AnalysisPipeline
    from prism.services import get_llm_backend
    from prism.services.scraper import BlogScraper

    current_date = date.today()

    console.print(Panel(
        f"[bold]Analyzing: {slug}[/bold]",
        title="PRISM",
        subtitle="Content Intelligence Engine",
    ))

    # Load data
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading fixture data...", total=None)
        account = load_account(slug)
        if not account:
            console.print(f"[red]Company '{slug}' not found in fixtures[/red]")
            return

        contacts = load_contacts(slug)
        signals = load_signals(slug)
        content_items = load_additional_content(slug)
        progress.update(task, description="Fixture data loaded")

        # Scrape blog
        scraped_items: list = []
        if not no_scrape and (account.blog_url or account.blog_rss or account.domain):
            progress.update(task, description="Scraping blog content...")
            try:
                scraper = BlogScraper()
                scraped_items = await scraper.scrape(
                    slug=slug,
                    blog_url=account.blog_url,
                    blog_rss=account.blog_rss,
                    domain=account.domain,
                )
            except Exception as e:
                logger.warning("Blog scraping failed: %s", e)
                scraped_items = load_scraped_content(slug)
        else:
            scraped_items = load_scraped_content(slug)

        # Build content items from contact LinkedIn posts
        for contact in contacts:
            for post in contact.linkedin_posts:
                content_items.append(
                    ContentItem(
                        source_type="linkedin",
                        title=f"LinkedIn post by {contact.name}",
                        author=contact.name,
                        author_role=contact.title,
                        publish_date=post.date,
                        raw_text=post.text,
                        is_authored=True,
                    )
                )

        all_content = scraped_items + content_items
        progress.update(task, description=f"Content corpus: {len(all_content)} items")

    # Run pipeline
    llm = get_llm_backend()
    pipeline = AnalysisPipeline(llm)

    run_llm = not no_llm and len(all_content) > 0

    if run_llm:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Content Intelligence chain...", total=None)
            analyzed, play, brief = await pipeline.analyze(
                account=account,
                contacts=contacts,
                signals=signals,
                content_items=all_content,
                run_llm=True,
                current_date=current_date,
            )
            progress.update(task, description="Content Intelligence complete")

        budget = llm.get_budget()
        console.print(f"\n[dim]{budget.summary()}[/dim]")
    else:
        if no_llm:
            console.print("[yellow]Skipping LLM analysis (--no-llm flag)[/yellow]")
        else:
            console.print("[yellow]No content items — skipping Content Intelligence[/yellow]")

        analyzed, play, brief = await pipeline.analyze(
            account=account,
            contacts=contacts,
            signals=signals,
            content_items=all_content,
            run_llm=False,
            current_date=current_date,
        )

    # Render dossier
    dossier = render_dossier(
        account=account,
        analyzed=analyzed,
        contacts=contacts,
        play=play,
        brief=brief,
    )

    # Save dossier
    DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOSSIERS_DIR / f"{slug}_dossier.md"
    output_path.write_text(dossier)

    # Print result summary
    scores = analyzed.scores
    tier_colors = {
        "tier_1": "red",
        "tier_2": "yellow",
        "tier_3": "blue",
        "not_qualified": "dim",
    }
    tier_color = tier_colors.get(scores.priority_tier, "white")

    console.print()
    console.print(Panel(
        f"[bold {tier_color}]{scores.priority_tier.replace('_', ' ').upper()}[/bold {tier_color}] | "
        f"Composite: {scores.composite_score:.0%} | "
        f"ICP: {scores.icp_fit_score:.0%} | "
        f"Readiness: {scores.buying_readiness_score:.0%} | "
        f"Timing: {scores.timing_score:.0%}",
        title=account.company_name,
        subtitle=f"Dossier saved: {output_path}",
    ))


async def _analyze_all(no_scrape: bool = False, no_llm: bool = False) -> None:
    """Analyze all companies."""
    from prism.data.loader import list_companies as _list_companies

    slugs = _list_companies()
    if not slugs:
        console.print("[yellow]No companies found in fixtures/companies/[/yellow]")
        return

    console.print(f"\n[bold]Analyzing {len(slugs)} companies...[/bold]\n")

    for i, slug in enumerate(slugs, 1):
        console.print(f"\n{'━' * 60}")
        console.print(f"  [{i}/{len(slugs)}] {slug}")
        console.print(f"{'━' * 60}\n")

        try:
            await _analyze_company(slug, no_scrape=no_scrape, no_llm=no_llm)
        except Exception as e:
            console.print(f"[red]Error analyzing {slug}: {e}[/red]")
            logger.exception("Analysis failed for %s", slug)

    console.print(f"\n[bold green]Done! Analyzed {len(slugs)} companies.[/bold green]")


if __name__ == "__main__":
    cli()
