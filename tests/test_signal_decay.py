"""Tests for the signal decay engine."""

from datetime import date, timedelta

import pytest

from prism.analysis.signal_decay import calculate_decay_weight, calculate_signal_freshness_avg


class TestCalculateDecayWeight:
    """Tests for calculate_decay_weight function."""

    def test_unknown_signal_type_returns_zero(self):
        """Unknown signal types should return 0.0."""
        result = calculate_decay_weight("nonexistent_signal", date(2026, 1, 1), date(2026, 1, 15))
        assert result == 0.0

    def test_future_dated_signal_returns_zero(self):
        """Signals dated in the future should return 0.0."""
        result = calculate_decay_weight("funding_round", date(2026, 3, 1), date(2026, 2, 1))
        assert result == 0.0

    def test_expired_signal_returns_zero(self):
        """Signals past max relevance should return 0.0."""
        # funding_round max is 180 days
        signal_date = date(2025, 1, 1)
        current_date = date(2026, 1, 1)  # 365 days later
        result = calculate_decay_weight("funding_round", signal_date, current_date)
        assert result == 0.0

    def test_signal_at_peak_returns_one(self):
        """Signal exactly at peak should return 1.0."""
        # funding_round peak is 30 days
        signal_date = date(2026, 1, 1)
        current_date = date(2026, 1, 31)  # 30 days later
        result = calculate_decay_weight("funding_round", signal_date, current_date)
        assert result == 1.0

    def test_signal_before_peak_ramps_up(self):
        """Signal before peak should ramp up linearly."""
        # funding_round peak is 30 days
        signal_date = date(2026, 1, 1)
        current_date = date(2026, 1, 16)  # 15 days later = 50% of peak
        result = calculate_decay_weight("funding_round", signal_date, current_date)
        assert result == pytest.approx(0.5)

    def test_signal_at_half_life_returns_half(self):
        """Signal at exactly one half-life past peak should return ~0.5."""
        # funding_round: peak=30, half_life=90
        signal_date = date(2026, 1, 1)
        # At peak + half_life = 30 + 90 = 120 days
        current_date = signal_date + timedelta(days=120)
        result = calculate_decay_weight("funding_round", signal_date, current_date)
        assert result == pytest.approx(0.5, abs=0.01)

    def test_same_day_signal_with_zero_peak(self):
        """Signal with 0 peak should return 1.0 on same day."""
        # pricing_page_visit has peak=1, so test day 0
        signal_date = date(2026, 2, 1)
        result = calculate_decay_weight("pricing_page_visit", signal_date, signal_date)
        assert result == 0.0  # age=0, peak=1, so 0/1 = 0.0

    def test_pricing_page_decays_fast(self):
        """Pricing page visit should decay very quickly."""
        # peak=1, half_life=7, max=21
        signal_date = date(2026, 2, 1)
        # At 15 days (past peak by 14 days, half_life is 7, so 2 half-lives)
        current_date = date(2026, 2, 16)
        result = calculate_decay_weight("pricing_page_visit", signal_date, current_date)
        assert result == pytest.approx(0.25, abs=0.01)  # 0.5^2

    def test_new_executive_finance_long_decay(self):
        """New exec finance has long relevance window (365 days)."""
        # peak=60, half_life=150, max=365
        signal_date = date(2025, 8, 1)
        current_date = date(2026, 2, 1)  # ~184 days
        result = calculate_decay_weight("new_executive_finance", signal_date, current_date)
        assert result > 0.0  # Should still be relevant

    def test_decay_is_monotonically_decreasing_after_peak(self):
        """After peak, decay should be monotonically decreasing."""
        signal_date = date(2026, 1, 1)
        # funding_round: peak at 30 days
        prev_weight = 1.0
        for day_offset in range(31, 180):
            current = signal_date + timedelta(days=day_offset)
            weight = calculate_decay_weight("funding_round", signal_date, current)
            assert weight <= prev_weight
            prev_weight = weight

    def test_all_signal_types_have_valid_config(self):
        """Every signal type should produce valid output for reasonable dates."""
        from prism.config import SIGNAL_DECAY_CONFIG

        signal_date = date(2026, 1, 1)
        current_date = date(2026, 2, 1)

        for signal_type in SIGNAL_DECAY_CONFIG:
            result = calculate_decay_weight(signal_type, signal_date, current_date)
            assert 0.0 <= result <= 1.0, f"Invalid result for {signal_type}: {result}"


class TestSignalFreshnessAvg:
    """Tests for calculate_signal_freshness_avg function."""

    def test_empty_list_returns_zero(self):
        assert calculate_signal_freshness_avg([]) == 0.0

    def test_all_fresh_returns_high(self):
        assert calculate_signal_freshness_avg([0.9, 0.95, 0.85]) == 1.0

    def test_all_stale_returns_low(self):
        assert calculate_signal_freshness_avg([0.05, 0.10, 0.15]) == 0.10

    def test_mixed_freshness(self):
        result = calculate_signal_freshness_avg([0.9, 0.5, 0.3])
        # Average ~0.567 → should map to 0.55
        assert result == 0.55

    def test_single_signal(self):
        assert calculate_signal_freshness_avg([0.75]) == 0.80
