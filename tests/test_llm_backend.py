"""Tests for LLM backend interface, implementations, and factory."""

import json
from datetime import date
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prism.services.llm_backend import (
    LLMBackend,
    LLMResponse,
    TokenBudget,
    strip_code_fences,
)


# ── TokenBudget Tests ────────────────────────────────────────────────────────


class TestTokenBudget:
    def test_initial_state(self):
        budget = TokenBudget()
        assert budget.total_input_tokens == 0
        assert budget.total_output_tokens == 0
        assert budget.total_calls == 0
        assert budget.estimated_cost == 0.0

    def test_record_usage(self):
        budget = TokenBudget()
        response = LLMResponse(content="test", input_tokens=1000, output_tokens=500)
        budget.record(response)
        assert budget.total_input_tokens == 1000
        assert budget.total_output_tokens == 500
        assert budget.total_calls == 1

    def test_estimated_cost(self):
        budget = TokenBudget(cost_per_1k_input=0.003, cost_per_1k_output=0.015)
        response = LLMResponse(content="test", input_tokens=10000, output_tokens=2000)
        budget.record(response)
        # 10K * 0.003 + 2K * 0.015 = 0.03 + 0.03 = 0.06
        assert abs(budget.estimated_cost - 0.06) < 0.001

    def test_budget_check_within_budget(self):
        budget = TokenBudget(max_spend_usd=100.0)
        assert budget.check_budget() is True

    def test_budget_check_exhausted(self):
        budget = TokenBudget(max_spend_usd=0.01, cost_per_1k_input=0.003)
        response = LLMResponse(content="test", input_tokens=100000, output_tokens=0)
        budget.record(response)
        assert budget.check_budget() is False

    def test_budget_remaining(self):
        budget = TokenBudget(max_spend_usd=10.0)
        response = LLMResponse(content="test", input_tokens=1000, output_tokens=1000)
        budget.record(response)
        expected_remaining = 10.0 - budget.estimated_cost
        assert abs(budget.budget_remaining - expected_remaining) < 0.001

    def test_summary_format(self):
        budget = TokenBudget()
        response = LLMResponse(content="test", input_tokens=5000, output_tokens=1000)
        budget.record(response)
        summary = budget.summary()
        assert "API Calls: 1" in summary
        assert "5,000" in summary
        assert "1,000" in summary
        assert "$" in summary

    def test_local_inference_zero_cost(self):
        budget = TokenBudget(
            max_spend_usd=float("inf"),
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )
        response = LLMResponse(content="test", input_tokens=100000, output_tokens=50000)
        budget.record(response)
        assert budget.estimated_cost == 0.0
        assert budget.check_budget() is True

    def test_multiple_records(self):
        budget = TokenBudget()
        for _ in range(5):
            budget.record(LLMResponse(content="test", input_tokens=100, output_tokens=50))
        assert budget.total_calls == 5
        assert budget.total_input_tokens == 500
        assert budget.total_output_tokens == 250


# ── LLMResponse Tests ────────────────────────────────────────────────────────


class TestLLMResponse:
    def test_defaults(self):
        resp = LLMResponse(content="hello")
        assert resp.content == "hello"
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0
        assert resp.model == ""
        assert resp.latency_ms == 0
        assert resp.cached is False

    def test_full_construction(self):
        resp = LLMResponse(
            content='{"key": "value"}',
            input_tokens=500,
            output_tokens=200,
            model="claude-sonnet-4-20250514",
            latency_ms=1500,
            cached=True,
        )
        assert resp.input_tokens == 500
        assert resp.model == "claude-sonnet-4-20250514"
        assert resp.cached is True


# ── strip_code_fences Tests ──────────────────────────────────────────────────


class TestStripCodeFences:
    def test_no_fences(self):
        assert strip_code_fences('{"key": "value"}') == '{"key": "value"}'

    def test_json_fences(self):
        text = '```json\n{"key": "value"}\n```'
        assert strip_code_fences(text) == '{"key": "value"}'

    def test_plain_fences(self):
        text = '```\n{"key": "value"}\n```'
        assert strip_code_fences(text) == '{"key": "value"}'

    def test_whitespace_padding(self):
        text = '  ```json\n  {"key": "value"}  \n  ```  '
        result = strip_code_fences(text)
        assert '"key"' in result

    def test_multiline_content(self):
        text = '```json\n{\n  "a": 1,\n  "b": 2\n}\n```'
        result = strip_code_fences(text)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}


# ── LLMBackend ABC Tests ────────────────────────────────────────────────────


class MockBackend(LLMBackend):
    """Mock backend for testing the ABC."""

    def __init__(self):
        self._budget = TokenBudget()
        self._responses: list[Optional[LLMResponse]] = []
        self._call_count = 0

    def add_response(self, content: str, input_tokens: int = 100, output_tokens: int = 50):
        resp = LLMResponse(content=content, input_tokens=input_tokens, output_tokens=output_tokens)
        self._responses.append(resp)

    def add_none_response(self):
        self._responses.append(None)

    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: str = "json",
        **kwargs,
    ) -> Optional[LLMResponse]:
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
            self._call_count += 1
            if resp:
                self._budget.record(resp)
            return resp
        return None

    def get_budget(self) -> TokenBudget:
        return self._budget


class TestLLMBackendABC:
    @pytest.mark.asyncio
    async def test_query_json_success(self):
        backend = MockBackend()
        backend.add_response('{"status": "ok", "score": 0.85}')
        result = await backend.query_json("system", "user")
        assert result == {"status": "ok", "score": 0.85}

    @pytest.mark.asyncio
    async def test_query_json_with_code_fences(self):
        backend = MockBackend()
        backend.add_response('```json\n{"status": "ok"}\n```')
        result = await backend.query_json("system", "user")
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_query_json_parse_failure(self):
        backend = MockBackend()
        backend.add_response("This is not JSON at all")
        result = await backend.query_json("system", "user")
        assert result is None

    @pytest.mark.asyncio
    async def test_query_json_none_response(self):
        backend = MockBackend()
        backend.add_none_response()
        result = await backend.query_json("system", "user")
        assert result is None

    @pytest.mark.asyncio
    async def test_query_text_success(self):
        backend = MockBackend()
        backend.add_response("Hello, this is a text response.")
        result = await backend.query_text("system", "user")
        assert result == "Hello, this is a text response."

    @pytest.mark.asyncio
    async def test_query_text_none_response(self):
        backend = MockBackend()
        backend.add_none_response()
        result = await backend.query_text("system", "user")
        assert result is None

    @pytest.mark.asyncio
    async def test_budget_tracking_through_query_json(self):
        backend = MockBackend()
        backend.add_response('{"a": 1}', input_tokens=500, output_tokens=200)
        backend.add_response('{"b": 2}', input_tokens=300, output_tokens=100)

        await backend.query_json("sys", "prompt1")
        await backend.query_json("sys", "prompt2")

        budget = backend.get_budget()
        assert budget.total_calls == 2
        assert budget.total_input_tokens == 800
        assert budget.total_output_tokens == 300


# ── ModelRouter Tests ────────────────────────────────────────────────────────


class TestModelRouter:
    @pytest.mark.asyncio
    async def test_default_routing(self):
        from prism.services.backends.router import ModelRouter

        default = MockBackend()
        default.add_response('{"routed": "default"}')

        router = ModelRouter(default_backend=default)
        result = await router.query_json("sys", "user")
        assert result == {"routed": "default"}

    @pytest.mark.asyncio
    async def test_task_type_routing(self):
        from prism.services.backends.router import ModelRouter

        default = MockBackend()
        extraction = MockBackend()
        extraction.add_response('{"routed": "extraction"}')

        router = ModelRouter(
            default_backend=default,
            routes={"extraction": extraction},
        )
        result = await router.query(
            "sys", "user", task_type="extraction"
        )
        assert result is not None
        assert '"extraction"' in result.content

    @pytest.mark.asyncio
    async def test_unknown_task_type_falls_to_default(self):
        from prism.services.backends.router import ModelRouter

        default = MockBackend()
        default.add_response('{"routed": "default"}')

        router = ModelRouter(
            default_backend=default,
            routes={"extraction": MockBackend()},
        )
        result = await router.query_json("sys", "user")
        assert result == {"routed": "default"}

    def test_get_all_budgets(self):
        from prism.services.backends.router import ModelRouter

        default = MockBackend()
        extraction = MockBackend()

        router = ModelRouter(
            default_backend=default,
            routes={"extraction": extraction, "synthesis": default},
        )
        budgets = router.get_all_budgets()
        # default and extraction are different backends, synthesis points to default
        assert "default" in budgets
        assert "extraction" in budgets
        assert len(budgets) == 2  # synthesis uses same backend as default


# ── Backend Factory Tests ────────────────────────────────────────────────────


class TestGetLLMBackend:
    def test_factory_returns_anthropic_by_default(self):
        from prism.services import get_llm_backend
        from prism.services.backends.anthropic_backend import AnthropicBackend

        backend = get_llm_backend("anthropic")
        assert isinstance(backend, AnthropicBackend)

    def test_factory_returns_local(self):
        from prism.services import get_llm_backend
        from prism.services.backends.local_backend import LocalInferenceBackend

        backend = get_llm_backend("local")
        assert isinstance(backend, LocalInferenceBackend)

    def test_factory_returns_router(self):
        from prism.services import get_llm_backend
        from prism.services.backends.router import ModelRouter

        backend = get_llm_backend("router")
        assert isinstance(backend, ModelRouter)

    def test_factory_unknown_falls_back(self):
        from prism.services import get_llm_backend
        from prism.services.backends.anthropic_backend import AnthropicBackend

        backend = get_llm_backend("nonexistent_backend")
        assert isinstance(backend, AnthropicBackend)


# ── Pipeline Integration Test ────────────────────────────────────────────────


class TestPipelineWithMockBackend:
    @pytest.mark.asyncio
    async def test_pipeline_no_llm(self, sample_account, sample_contacts, sample_signals):
        from prism.pipeline import AnalysisPipeline

        backend = MockBackend()
        pipeline = AnalysisPipeline(backend)

        analyzed, play, brief = await pipeline.analyze(
            account=sample_account,
            contacts=sample_contacts,
            signals=sample_signals,
            content_items=[],
            run_llm=False,
            current_date=date(2026, 3, 1),
        )

        assert analyzed.account_slug == "test_company"
        assert analyzed.limited_analysis is True
        assert analyzed.scores.composite_score >= 0.0
        assert play.play_name != ""
        assert brief.company_name == "Test Corp"

    @pytest.mark.asyncio
    async def test_pipeline_scoring_without_llm(self, sample_account, sample_contacts, sample_signals):
        from prism.pipeline import AnalysisPipeline

        backend = MockBackend()
        pipeline = AnalysisPipeline(backend)

        analyzed, play, brief = await pipeline.analyze(
            account=sample_account,
            contacts=sample_contacts,
            signals=sample_signals,
            content_items=[],
            run_llm=False,
            current_date=date(2026, 3, 1),
        )

        # Verify scoring still works correctly without LLM
        assert 0.0 <= analyzed.scores.icp_fit_score <= 1.0
        assert 0.0 <= analyzed.scores.buying_readiness_score <= 1.0
        assert 0.0 <= analyzed.scores.timing_score <= 1.0
        assert 0.0 <= analyzed.scores.composite_score <= 1.0
        assert analyzed.scores.priority_tier in (
            "tier_1", "tier_2", "tier_3", "not_qualified"
        )
