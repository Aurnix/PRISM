"""Tests for background task functions."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest


class TestTaskWorkerSettings:
    def test_worker_settings_has_functions(self):
        from prism.tasks import WorkerSettings

        assert len(WorkerSettings.functions) == 6

    def test_worker_settings_function_names(self):
        from prism.tasks import (
            analyze_company_task,
            daily_reanalyze,
            enrich_company_task,
            full_pipeline_task,
            generate_dossier_task,
            weekly_scrape,
        )

        # Just verify they are importable
        assert callable(enrich_company_task)
        assert callable(analyze_company_task)
        assert callable(generate_dossier_task)
        assert callable(full_pipeline_task)
        assert callable(daily_reanalyze)
        assert callable(weekly_scrape)


class TestEnrichCompanyTask:
    @pytest.mark.asyncio
    async def test_returns_error_for_missing_account(self):
        from prism.tasks import enrich_company_task

        # FixtureDAL won't find a nonexistent slug
        result = await enrich_company_task(slug="nonexistent_xyz")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_enrichment_runs_for_valid_account(self):
        from prism.tasks import enrich_company_task
        from prism.data.loader import list_companies

        slugs = list_companies()
        if not slugs:
            pytest.skip("No fixture companies available")

        # This will run with real fixture data — blog scraper + job boards
        # Both may fail (no network in test), but task should handle gracefully
        result = await enrich_company_task(slug=slugs[0])
        assert isinstance(result, dict)
        assert "error" not in result


class TestAnalyzeCompanyTask:
    @pytest.mark.asyncio
    async def test_returns_error_for_missing_account(self):
        from prism.tasks import analyze_company_task

        result = await analyze_company_task(slug="nonexistent_xyz", run_llm=False)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_runs_without_llm(self):
        from prism.data.loader import list_companies
        from prism.tasks import analyze_company_task

        slugs = list_companies()
        if not slugs:
            pytest.skip("No fixture companies available")

        result = await analyze_company_task(slug=slugs[0], run_llm=False)
        assert result["status"] == "complete"
        assert "tier" in result
        assert "composite_score" in result


class TestGenerateDossierTask:
    @pytest.mark.asyncio
    async def test_returns_error_for_missing_account(self):
        from prism.tasks import generate_dossier_task

        result = await generate_dossier_task(slug="nonexistent_xyz", run_llm=False)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generates_dossier_file(self):
        from prism.data.loader import list_companies
        from prism.tasks import generate_dossier_task

        slugs = list_companies()
        if not slugs:
            pytest.skip("No fixture companies available")

        result = await generate_dossier_task(slug=slugs[0], run_llm=False)
        assert result["status"] == "complete"
        assert "dossier_path" in result
