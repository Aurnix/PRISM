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
    from prism.analysis.content_intel import ContentIntelligenceChain
    from prism.analysis.scoring import score_account
    from prism.analysis.signal_decay import calculate_decay_weight
    from prism.data.loader import (
        load_account,
        load_additional_content,
        load_contacts,
        load_scraped_content,
        load_signals,
    )
    from prism.models.analysis import (
        AnalyzedAccount,
        ConfidenceAssessment,
        ContentIntelligenceSummary,
        WhyNowHypothesis,
    )
    from prism.models.activation import AccountBrief, Play
    from prism.models.content import ContentCorpus
    from prism.output.dossier import render_dossier
    from prism.services.llm import LLMService
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

        # Also build content items from contact LinkedIn posts
        for contact in contacts:
            for post in contact.linkedin_posts:
                content_items.append(
                    __import__("prism.models.content", fromlist=["ContentItem"]).ContentItem(
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
        corpus = ContentCorpus(
            account_slug=slug,
            assembly_date=current_date,
            items=all_content,
        )
        corpus._update_metadata()

        progress.update(task, description=f"Content corpus: {corpus.total_items} items")

    # Calculate signal decay weights
    for signal in signals:
        signal.decay_weight = calculate_decay_weight(
            signal.signal_type, signal.detected_date, current_date
        )

    # Content Intelligence analysis
    stage1_results = []
    stage2_result = None
    person_analyses = []
    stage4_result = None

    if not no_llm and corpus.total_items > 0:
        llm = LLMService()
        chain = ContentIntelligenceChain(llm)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Content Intelligence chain...", total=None)

            stage1_results, stage2_result, person_analyses, stage4_result = await chain.analyze(
                account=account,
                corpus=corpus,
                contacts=contacts,
                signals=signals,
                current_date=current_date,
            )

            progress.update(task, description="Content Intelligence complete")

        # Print LLM usage
        console.print(f"\n[dim]{llm.usage.summary()}[/dim]")
    elif no_llm:
        console.print("[yellow]Skipping LLM analysis (--no-llm flag)[/yellow]")
    else:
        console.print("[yellow]No content items — skipping Content Intelligence[/yellow]")

    # Extract stage 4 results
    urgency_score = 0.10
    window_closing_score = 1.0
    why_now_data = {}
    confidence_data = {}
    play_data = {}
    discovery_questions = []
    collection_gaps = []

    if stage4_result:
        urgency_score = stage4_result.get("urgency_score", 0.10)
        window_closing_score = stage4_result.get("window_closing_score", 1.0)
        why_now_data = stage4_result.get("why_now", {})
        confidence_data = stage4_result.get("confidence", {})
        play_data = stage4_result.get("recommended_play", {})
        discovery_questions = stage4_result.get("discovery_questions", [])
        collection_gaps = stage4_result.get("collection_gaps", [])

    # Score the account
    scores = score_account(
        account=account,
        contacts=contacts,
        signals=signals,
        synthesis=stage2_result,
        urgency_score=urgency_score,
        window_closing_score=window_closing_score,
        current_date=current_date,
    )

    # Build content intelligence summary
    ci_summary = None
    if stage2_result:
        ci_summary = ContentIntelligenceSummary(
            pain_coherence_score=stage2_result.pain_coherence.get("score", 0.0),
            primary_pain_themes=stage2_result.pain_coherence.get("primary_pain_themes", []),
            org_stress_level=stage2_result.stress_indicators.get("level", "low"),
            solution_sophistication=stage2_result.solution_sophistication.get("level", "unaware"),
            stated_vs_actual_alignment=stage2_result.priority_alignment.get("aligned", True),
            trajectory_direction=stage2_result.trajectory.get("direction", "stable"),
            notable_absences=[
                a.get("expected_topic", "") for a in stage2_result.absences
            ],
        )

    # Build why-now hypothesis
    why_now = WhyNowHypothesis(
        headline=why_now_data.get("headline", ""),
        narrative=why_now_data.get("narrative", ""),
        trigger_event=why_now_data.get("trigger_event"),
        trigger_date=_safe_parse_date(why_now_data.get("trigger_date")),
        window_estimate=why_now_data.get("window_estimate", "90 days"),
    )

    # Build confidence assessment
    confidence = ConfidenceAssessment(
        overall_confidence=confidence_data.get("overall", "low"),
        extracted_signals=confidence_data.get("extracted_signals", []),
        interpolated_signals=confidence_data.get("interpolated_signals", []),
        generated_signals=confidence_data.get("generated_signals", []),
        counter_signals=stage4_result.get("counter_signals", []) if stage4_result else [],
        unknowns=confidence_data.get("unknowns", []),
        corpus_size=corpus.total_items,
        corpus_quality="high" if corpus.total_items >= 10 else "medium" if corpus.total_items >= 5 else "low",
        corpus_sufficient=corpus.meets_minimum,
    )

    # Auto-downgrade confidence for sparse corpus
    if corpus.total_items < 5 or not corpus.meets_minimum:
        confidence.overall_confidence = "low"

    # Build play
    play = Play(
        play_name=play_data.get("play_name", ""),
        description=play_data.get("description", ""),
        sequence=play_data.get("sequence", []),
        timeline=play_data.get("timeline", ""),
        entry_point=play_data.get("entry_point"),
        fallback_play=play_data.get("fallback_play"),
    )

    # Generate angles if we have person analyses and LLM
    if not no_llm and person_analyses and stage2_result:
        llm = LLMService()
        chain = ContentIntelligenceChain(llm)
        angles = await chain.generate_angles(
            account=account,
            person_analyses=person_analyses,
            why_now_headline=why_now.headline,
            pain_themes=ci_summary.primary_pain_themes if ci_summary else [],
            stress_level=ci_summary.org_stress_level if ci_summary else "unknown",
            play=play,
        )
        play.angles = angles
        console.print(f"[dim]Angle generation: {llm.usage.summary()}[/dim]")

    # Determine journey position from stage 2
    journey_position = 0.0
    journey_label = "status_quo"
    journey_velocity = "stable"
    if stage2_result:
        pain_score = stage2_result.pain_coherence.get("score", 0.0)
        soph = stage2_result.solution_sophistication.get("level", "unaware")
        soph_map = {"decided": 0.80, "evaluating": 0.55, "articulate": 0.35, "frustrated": 0.20, "unaware": 0.05}
        journey_position = max(pain_score, soph_map.get(soph, 0.05))

        if journey_position >= 0.60:
            journey_label = "decision_ready"
        elif journey_position >= 0.40:
            journey_label = "active_evaluation"
        elif journey_position >= 0.25:
            journey_label = "solution_exploring"
        elif journey_position >= 0.15:
            journey_label = "problem_aware"
        else:
            journey_label = "status_quo"

        urgency_trend = stage2_result.trajectory.get("urgency_trend", "stable")
        if urgency_trend == "increasing":
            journey_velocity = "accelerating"
        elif urgency_trend == "decreasing":
            journey_velocity = "stalling"

    # Build analyzed account
    llm_service = LLMService() if not no_llm else None
    analyzed = AnalyzedAccount(
        account_slug=slug,
        company_name=account.company_name,
        domain=account.domain,
        analysis_date=current_date,
        prompt_version=PRISM_PROMPT_VERSION,
        scores=scores,
        journey_position=journey_position,
        journey_position_label=journey_label,
        journey_velocity=journey_velocity,
        why_now=why_now,
        content_intelligence=ci_summary,
        stage2_synthesis=stage2_result,
        person_analyses=person_analyses,
        confidence=confidence,
        signals=signals,
        total_input_tokens=llm_service.usage.total_input_tokens if llm_service else 0,
        total_output_tokens=llm_service.usage.total_output_tokens if llm_service else 0,
        total_api_calls=llm_service.usage.total_calls if llm_service else 0,
        estimated_cost_usd=llm_service.usage.estimated_cost if llm_service else 0.0,
        limited_analysis=corpus.total_items == 0 or no_llm,
        limited_analysis_reason=(
            "No public content corpus" if corpus.total_items == 0
            else "LLM analysis skipped" if no_llm
            else None
        ),
    )

    # Build brief
    brief = AccountBrief(
        company_name=account.company_name,
        priority_tier=scores.priority_tier,
        composite_score=scores.composite_score,
        one_line_why_now=why_now.headline,
        discovery_questions=discovery_questions,
        collection_gaps=collection_gaps,
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


def _safe_parse_date(date_str: object) -> date | None:
    """Safely parse a date string."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


if __name__ == "__main__":
    cli()
